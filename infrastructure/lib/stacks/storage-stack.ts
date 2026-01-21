/**
 * AxiePro Storage Stack
 *
 * Creates storage infrastructure:
 * - S3 buckets for data lake, artifacts, and logs
 * - ECR repository for container images
 * - Lifecycle policies for cost optimization
 * - Cross-region replication (production only)
 */

import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';

export interface StorageStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  kmsKey: kms.IKey;
}

export class StorageStack extends cdk.Stack {
  // S3 Buckets
  public readonly dataBucket: s3.IBucket;
  public readonly artifactBucket: s3.IBucket;
  public readonly logsBucket: s3.IBucket;

  // ECR Repository
  public readonly ecrRepository: ecr.IRepository;

  constructor(scope: Construct, id: string, props: StorageStackProps) {
    super(scope, id, props);

    const { config, kmsKey } = props;

    // ========================================================================
    // Logs Bucket (for access logs)
    // ========================================================================

    this.logsBucket = new s3.Bucket(this, 'LogsBucket', {
      bucketName: getResourceName(`logs-${config.account}`, config),
      encryption: s3.BucketEncryption.S3_MANAGED, // Logs bucket uses S3-managed keys
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: false,
      removalPolicy: config.removalPolicy,
      autoDeleteObjects: config.autoDeleteObjects,

      // Lifecycle rules for logs
      lifecycleRules: [
        {
          id: 'DeleteOldLogs',
          enabled: true,
          expiration: cdk.Duration.days(90), // Delete logs after 90 days
        },
        {
          id: 'TransitionToIA',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
          ],
        },
      ],
    });

    // ========================================================================
    // Data Lake Bucket
    // ========================================================================

    this.dataBucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: getResourceName(`data-${config.account}`, config),
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: kmsKey,
      bucketKeyEnabled: true, // Reduce KMS costs
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      removalPolicy: config.removalPolicy,
      autoDeleteObjects: config.autoDeleteObjects,

      // Server access logging
      serverAccessLogsBucket: this.logsBucket,
      serverAccessLogsPrefix: 'data-bucket-logs/',

      // Intelligent tiering for cost optimization
      intelligentTieringConfigurations: config.costOptimization.enableS3IntelligentTiering
        ? [
            {
              name: 'ArchiveAccess',
              archiveAccessTierTime: cdk.Duration.days(90),
              deepArchiveAccessTierTime: cdk.Duration.days(180),
            },
          ]
        : undefined,

      // Lifecycle rules
      lifecycleRules: [
        {
          id: 'TransitionAndExpire',
          enabled: true,
          // Transition non-current versions
          noncurrentVersionTransitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
          // Delete non-current versions after 1 year
          noncurrentVersionExpiration: cdk.Duration.days(365),
        },
        {
          id: 'AbortIncompleteMultipartUpload',
          enabled: true,
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
        {
          id: 'ExpireDeleteMarkers',
          enabled: true,
          expiredObjectDeleteMarker: true,
        },
      ],

      // CORS configuration for frontend access
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.HEAD],
          allowedOrigins: ['*'], // Restrict in production
          allowedHeaders: ['*'],
          maxAge: 3000,
        },
      ],
    });

    // ========================================================================
    // Artifacts Bucket (for CI/CD)
    // ========================================================================

    this.artifactBucket = new s3.Bucket(this, 'ArtifactBucket', {
      bucketName: getResourceName(`artifacts-${config.account}`, config),
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: kmsKey,
      bucketKeyEnabled: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      removalPolicy: config.removalPolicy,
      autoDeleteObjects: config.autoDeleteObjects,

      // Server access logging
      serverAccessLogsBucket: this.logsBucket,
      serverAccessLogsPrefix: 'artifact-bucket-logs/',

      // Lifecycle rules
      lifecycleRules: [
        {
          id: 'ExpireOldArtifacts',
          enabled: true,
          expiration: cdk.Duration.days(30), // Keep artifacts for 30 days
          noncurrentVersionExpiration: cdk.Duration.days(7),
        },
        {
          id: 'AbortIncompleteMultipartUpload',
          enabled: true,
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(1),
        },
      ],
    });

    // ========================================================================
    // ECR Repository
    // ========================================================================

    this.ecrRepository = new ecr.Repository(this, 'EcrRepository', {
      repositoryName: getResourceName('backend', config),
      encryption: ecr.RepositoryEncryption.KMS,
      encryptionKey: kmsKey,
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.MUTABLE,
      removalPolicy: config.removalPolicy,
      emptyOnDelete: config.autoDeleteObjects,

      // Lifecycle rules to limit stored images
      // Note: TagStatus.ANY must have the highest priority number (executed last)
      lifecycleRules: [
        {
          description: 'Delete untagged images after 1 day',
          rulePriority: 1,
          maxImageAge: cdk.Duration.days(1),
          tagStatus: ecr.TagStatus.UNTAGGED,
        },
        {
          description: 'Keep last 10 images',
          rulePriority: 2,
          maxImageCount: 10,
          tagStatus: ecr.TagStatus.ANY,
        },
      ],
    });

    // Grant pull permissions to App Runner
    this.ecrRepository.addToResourcePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('build.apprunner.amazonaws.com')],
        actions: [
          'ecr:GetDownloadUrlForLayer',
          'ecr:BatchGetImage',
          'ecr:BatchCheckLayerAvailability',
        ],
      })
    );

    // ========================================================================
    // Bucket Policies
    // ========================================================================

    // Deny non-HTTPS requests to data bucket
    this.dataBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: 'DenyNonHTTPS',
        effect: iam.Effect.DENY,
        principals: [new iam.AnyPrincipal()],
        actions: ['s3:*'],
        resources: [this.dataBucket.bucketArn, `${this.dataBucket.bucketArn}/*`],
        conditions: {
          Bool: { 'aws:SecureTransport': 'false' },
        },
      })
    );

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'DataBucketName', {
      value: this.dataBucket.bucketName,
      description: 'Data lake bucket name',
      exportName: `${id}-DataBucketName`,
    });

    new cdk.CfnOutput(this, 'DataBucketArn', {
      value: this.dataBucket.bucketArn,
      description: 'Data lake bucket ARN',
      exportName: `${id}-DataBucketArn`,
    });

    new cdk.CfnOutput(this, 'ArtifactBucketName', {
      value: this.artifactBucket.bucketName,
      description: 'Artifacts bucket name',
      exportName: `${id}-ArtifactBucketName`,
    });

    new cdk.CfnOutput(this, 'LogsBucketName', {
      value: this.logsBucket.bucketName,
      description: 'Logs bucket name',
      exportName: `${id}-LogsBucketName`,
    });

    new cdk.CfnOutput(this, 'EcrRepositoryUri', {
      value: this.ecrRepository.repositoryUri,
      description: 'ECR repository URI',
      exportName: `${id}-EcrRepositoryUri`,
    });

    new cdk.CfnOutput(this, 'EcrRepositoryArn', {
      value: this.ecrRepository.repositoryArn,
      description: 'ECR repository ARN',
      exportName: `${id}-EcrRepositoryArn`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Storage');
  }
}

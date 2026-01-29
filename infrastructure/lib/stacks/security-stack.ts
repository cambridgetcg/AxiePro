/**
 * AxiePro Security Stack
 *
 * Creates security resources:
 * - KMS keys for data encryption (at-rest)
 * - Secrets Manager for API keys and credentials
 * - IAM roles for services (App Runner, Lambda, ECS)
 * - Service-linked roles and policies
 */

import * as cdk from 'aws-cdk-lib';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';

export interface SecurityStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.IVpc;
}

export class SecurityStack extends cdk.Stack {
  // KMS Keys
  public readonly dataKey: kms.IKey;
  public readonly secretsKey: kms.IKey;

  // Secrets
  public readonly apiSecretsArn: string;
  public readonly databaseSecret: secretsmanager.ISecret;

  // Parameter Store
  public readonly parameterPrefix: string;

  // IAM Roles
  public readonly appRunnerInstanceRole: iam.Role;
  public readonly appRunnerAccessRole: iam.Role;
  public readonly lambdaExecutionRole: iam.Role;
  public readonly ecsTaskRole: iam.Role;
  public readonly ecsExecutionRole: iam.Role;

  constructor(scope: Construct, id: string, props: SecurityStackProps) {
    super(scope, id, props);

    const { config } = props;

    // ========================================================================
    // KMS Keys
    // ========================================================================

    // Data encryption key (for RDS, ElastiCache, S3, Kinesis)
    this.dataKey = new kms.Key(this, 'DataKey', {
      alias: getResourceName('data-key', config),
      description: 'KMS key for encrypting AxiePro data at rest',
      enableKeyRotation: true,
      rotationPeriod: cdk.Duration.days(365),
      removalPolicy: config.removalPolicy,
      pendingWindow: cdk.Duration.days(7),

      // Key policy
      policy: new iam.PolicyDocument({
        statements: [
          // Allow root account full access
          new iam.PolicyStatement({
            sid: 'AllowRootAccess',
            effect: iam.Effect.ALLOW,
            principals: [new iam.AccountRootPrincipal()],
            actions: ['kms:*'],
            resources: ['*'],
          }),
          // Allow CloudWatch Logs to use the key
          new iam.PolicyStatement({
            sid: 'AllowCloudWatchLogs',
            effect: iam.Effect.ALLOW,
            principals: [
              new iam.ServicePrincipal(`logs.${config.region}.amazonaws.com`),
            ],
            actions: [
              'kms:Encrypt',
              'kms:Decrypt',
              'kms:ReEncrypt*',
              'kms:GenerateDataKey*',
              'kms:DescribeKey',
            ],
            resources: ['*'],
            conditions: {
              ArnLike: {
                'kms:EncryptionContext:aws:logs:arn': `arn:aws:logs:${config.region}:${config.account}:log-group:*`,
              },
            },
          }),
        ],
      }),
    });

    // Secrets encryption key
    this.secretsKey = new kms.Key(this, 'SecretsKey', {
      alias: getResourceName('secrets-key', config),
      description: 'KMS key for encrypting AxiePro secrets',
      enableKeyRotation: true,
      rotationPeriod: cdk.Duration.days(365),
      removalPolicy: config.removalPolicy,
      pendingWindow: cdk.Duration.days(7),
    });

    // ========================================================================
    // Secrets Manager
    // ========================================================================

    // API Keys Secret (Moralis, SkyMavis, etc.)
    const apiSecrets = new secretsmanager.Secret(this, 'ApiSecrets', {
      secretName: getResourceName('api-keys', config),
      description: 'API keys for external services (Moralis, SkyMavis, etc.)',
      encryptionKey: this.secretsKey,

      // Generate placeholder structure - values to be filled manually
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          MORALIS_API_KEY: 'PLACEHOLDER_MORALIS_KEY',
          SKYMAVIS_API_KEY: 'PLACEHOLDER_SKYMAVIS_KEY',
          COINGECKO_API_KEY: 'PLACEHOLDER_COINGECKO_KEY',
        }),
        generateStringKey: 'INTERNAL_SECRET', // Random string for internal use
      },
    });
    this.apiSecretsArn = apiSecrets.secretArn;

    // Database credentials secret
    this.databaseSecret = new secretsmanager.Secret(this, 'DatabaseSecret', {
      secretName: getResourceName('database-credentials', config),
      description: 'Aurora PostgreSQL database credentials',
      encryptionKey: this.secretsKey,

      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          username: 'axiepro_admin',
        }),
        generateStringKey: 'password',
        excludePunctuation: true,
        includeSpace: false,
        passwordLength: 32,
      },
    });

    // ========================================================================
    // Parameter Store (Configuration Parameters)
    // ========================================================================

    // Parameter prefix for this environment
    this.parameterPrefix = `/axiepro/${config.shortName}`;

    // Deal Detection Thresholds
    new ssm.StringParameter(this, 'DealThresholdPercent', {
      parameterName: `${this.parameterPrefix}/thresholds/deal_percent`,
      description: 'Minimum discount percentage to qualify as a deal',
      stringValue: '20',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'SnipeThresholdPercent', {
      parameterName: `${this.parameterPrefix}/thresholds/snipe_percent`,
      description: 'Minimum discount percentage to qualify as a snipe opportunity',
      stringValue: '40',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'MinDiscountEth', {
      parameterName: `${this.parameterPrefix}/thresholds/min_discount_eth`,
      description: 'Minimum absolute discount in ETH to qualify as a deal',
      stringValue: '0.001',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'NotificationThresholdScore', {
      parameterName: `${this.parameterPrefix}/thresholds/notification_score`,
      description: 'Minimum deal score to trigger notification',
      stringValue: '70',
      tier: ssm.ParameterTier.STANDARD,
    });

    // Meta Analysis Thresholds
    new ssm.StringParameter(this, 'PriceVelocityThreshold', {
      parameterName: `${this.parameterPrefix}/thresholds/price_velocity`,
      description: 'Price change percentage threshold for velocity detection',
      stringValue: '15',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'VolumeSpikeThreshold', {
      parameterName: `${this.parameterPrefix}/thresholds/volume_spike`,
      description: 'Volume increase percentage threshold for spike detection',
      stringValue: '200',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'EmergingMetaThreshold', {
      parameterName: `${this.parameterPrefix}/thresholds/emerging_meta`,
      description: 'Minimum trending score for emerging meta detection',
      stringValue: '10',
      tier: ssm.ParameterTier.STANDARD,
    });

    // Health Check Thresholds
    new ssm.StringParameter(this, 'ListingsFreshnessMinutes', {
      parameterName: `${this.parameterPrefix}/thresholds/listings_freshness`,
      description: 'Maximum age in minutes for listings to be considered fresh',
      stringValue: '15',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'SalesFreshnessMinutes', {
      parameterName: `${this.parameterPrefix}/thresholds/sales_freshness`,
      description: 'Maximum age in minutes for sales to be considered fresh',
      stringValue: '60',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'SnapshotsFreshnessMinutes', {
      parameterName: `${this.parameterPrefix}/thresholds/snapshots_freshness`,
      description: 'Maximum age in minutes for price snapshots to be considered fresh',
      stringValue: '30',
      tier: ssm.ParameterTier.STANDARD,
    });

    // ========================================================================
    // IAM Roles
    // ========================================================================

    // App Runner Access Role (for pulling images from ECR)
    this.appRunnerAccessRole = new iam.Role(this, 'AppRunnerAccessRole', {
      roleName: getResourceName('apprunner-access-role', config),
      description: 'Role for App Runner to access ECR and other AWS services',
      assumedBy: new iam.ServicePrincipal('build.apprunner.amazonaws.com'),
    });

    // Grant ECR pull permissions
    this.appRunnerAccessRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'ecr:GetDownloadUrlForLayer',
          'ecr:BatchGetImage',
          'ecr:BatchCheckLayerAvailability',
          'ecr:GetAuthorizationToken',
        ],
        resources: ['*'],
      })
    );

    // App Runner Instance Role (runtime permissions)
    this.appRunnerInstanceRole = new iam.Role(this, 'AppRunnerInstanceRole', {
      roleName: getResourceName('apprunner-instance-role', config),
      description: 'Role for App Runner instances to access AWS services',
      assumedBy: new iam.ServicePrincipal('tasks.apprunner.amazonaws.com'),
    });

    // Grant Secrets Manager access
    apiSecrets.grantRead(this.appRunnerInstanceRole);
    this.databaseSecret.grantRead(this.appRunnerInstanceRole);

    // Grant KMS access
    this.dataKey.grantDecrypt(this.appRunnerInstanceRole);
    this.secretsKey.grantDecrypt(this.appRunnerInstanceRole);

    // Grant X-Ray access for tracing
    this.appRunnerInstanceRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess')
    );

    // Grant RDS IAM authentication permission
    this.appRunnerInstanceRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'RDSIAMAuthentication',
        effect: iam.Effect.ALLOW,
        actions: ['rds-db:connect'],
        resources: [
          `arn:aws:rds-db:${config.region}:${config.account}:dbuser:*/*`,
        ],
      })
    );

    // Lambda Execution Role
    this.lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      roleName: getResourceName('lambda-execution-role', config),
      description: 'Execution role for Lambda functions',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaVPCAccessExecutionRole'
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess'),
      ],
    });

    // Grant Lambda permissions
    apiSecrets.grantRead(this.lambdaExecutionRole);
    this.databaseSecret.grantRead(this.lambdaExecutionRole);
    this.dataKey.grantEncryptDecrypt(this.lambdaExecutionRole);
    this.secretsKey.grantDecrypt(this.lambdaExecutionRole);

    // Grant SSM Parameter Store read access
    this.lambdaExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'SSMParameterStoreAccess',
        effect: iam.Effect.ALLOW,
        actions: [
          'ssm:GetParameter',
          'ssm:GetParameters',
          'ssm:GetParametersByPath',
        ],
        resources: [
          `arn:aws:ssm:${config.region}:${config.account}:parameter${this.parameterPrefix}/*`,
        ],
      })
    );

    // Add CloudWatch Logs permissions
    this.lambdaExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        resources: [
          `arn:aws:logs:${config.region}:${config.account}:log-group:/aws/lambda/*`,
        ],
      })
    );

    // ECS Task Execution Role (for ECS to pull images and get secrets)
    this.ecsExecutionRole = new iam.Role(this, 'EcsExecutionRole', {
      roleName: getResourceName('ecs-execution-role', config),
      description: 'Execution role for ECS tasks',
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AmazonECSTaskExecutionRolePolicy'
        ),
      ],
    });

    // Grant secrets access to ECS execution role
    apiSecrets.grantRead(this.ecsExecutionRole);
    this.databaseSecret.grantRead(this.ecsExecutionRole);
    this.secretsKey.grantDecrypt(this.ecsExecutionRole);

    // ECS Task Role (runtime permissions for the container)
    this.ecsTaskRole = new iam.Role(this, 'EcsTaskRole', {
      roleName: getResourceName('ecs-task-role', config),
      description: 'Task role for ECS containers',
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // Grant task role permissions
    apiSecrets.grantRead(this.ecsTaskRole);
    this.databaseSecret.grantRead(this.ecsTaskRole);
    this.dataKey.grantEncryptDecrypt(this.ecsTaskRole);
    this.secretsKey.grantDecrypt(this.ecsTaskRole);

    // X-Ray access for ECS tasks
    this.ecsTaskRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess')
    );

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'DataKeyArn', {
      value: this.dataKey.keyArn,
      description: 'Data encryption KMS key ARN',
      exportName: `${id}-DataKeyArn`,
    });

    new cdk.CfnOutput(this, 'SecretsKeyArn', {
      value: this.secretsKey.keyArn,
      description: 'Secrets encryption KMS key ARN',
      exportName: `${id}-SecretsKeyArn`,
    });

    new cdk.CfnOutput(this, 'ApiSecretsArn', {
      value: this.apiSecretsArn,
      description: 'API secrets ARN',
      exportName: `${id}-ApiSecretsArn`,
    });

    new cdk.CfnOutput(this, 'DatabaseSecretArn', {
      value: this.databaseSecret.secretArn,
      description: 'Database credentials secret ARN',
      exportName: `${id}-DatabaseSecretArn`,
    });

    new cdk.CfnOutput(this, 'AppRunnerInstanceRoleArn', {
      value: this.appRunnerInstanceRole.roleArn,
      description: 'App Runner instance role ARN',
      exportName: `${id}-AppRunnerInstanceRoleArn`,
    });

    new cdk.CfnOutput(this, 'LambdaExecutionRoleArn', {
      value: this.lambdaExecutionRole.roleArn,
      description: 'Lambda execution role ARN',
      exportName: `${id}-LambdaExecutionRoleArn`,
    });

    new cdk.CfnOutput(this, 'EcsTaskRoleArn', {
      value: this.ecsTaskRole.roleArn,
      description: 'ECS task role ARN',
      exportName: `${id}-EcsTaskRoleArn`,
    });

    new cdk.CfnOutput(this, 'ParameterPrefix', {
      value: this.parameterPrefix,
      description: 'SSM Parameter Store prefix for this environment',
      exportName: `${id}-ParameterPrefix`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Security');
  }
}

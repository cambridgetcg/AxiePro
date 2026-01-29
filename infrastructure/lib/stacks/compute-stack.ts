/**
 * AxiePro Compute Stack
 *
 * Creates compute infrastructure:
 * - App Runner service for FastAPI backend
 * - ECS Fargate cluster for batch processing
 * - Lambda functions for scheduled and event-driven tasks
 * - Auto-scaling configurations
 */

import * as cdk from 'aws-cdk-lib';
import * as apprunner from 'aws-cdk-lib/aws-apprunner';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as lambdaDestinations from 'aws-cdk-lib/aws-lambda-destinations';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as kinesis from 'aws-cdk-lib/aws-kinesis';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';
import { DB_NAME, DB_PORT, DB_SCHEMA, REDIS_PORT } from '../config/constants';

export interface ComputeStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.IVpc;
  computeSecurityGroup: ec2.ISecurityGroup;
  lambdaSecurityGroup: ec2.ISecurityGroup;
  databaseCluster: rds.IDatabaseCluster;
  redisEndpoint: string;
  redisPort: number;
  secretsArn: string;
  databaseSecretsArn: string;  // Database credentials secret
  kmsKey: kms.IKey;
  secretsKey: kms.IKey;  // KMS key for secrets decryption
  dataBucket: s3.IBucket;
  listingsStream: kinesis.IStream;
  dealAlertsTopic: sns.ITopic;
  batchQueue: sqs.IQueue;
  deadLetterQueue: sqs.IQueue;  // DLQ for failed Lambda invocations
  ecrRepository: ecr.IRepository;
  parameterPrefix: string;  // SSM Parameter Store prefix for configuration
  // IAM roles from Security stack
  appRunnerInstanceRole: iam.IRole;
  appRunnerAccessRole: iam.IRole;
  ecsTaskRole: iam.IRole;
}

export class ComputeStack extends cdk.Stack {
  // App Runner (optional - requires Docker image in ECR)
  public readonly appRunnerService?: apprunner.CfnService;
  public readonly appRunnerServiceUrl: string;
  public readonly appRunnerServiceArn: string;

  // ECS
  public readonly ecsCluster: ecs.ICluster;
  public readonly batchTaskDefinition: ecs.FargateTaskDefinition;

  // Lambda functions
  public readonly lambdaFunctions: { [key: string]: lambda.IFunction };

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    const {
      config,
      vpc,
      computeSecurityGroup,
      lambdaSecurityGroup,
      databaseCluster,
      redisEndpoint,
      redisPort,
      secretsArn,
      databaseSecretsArn,
      kmsKey,
      secretsKey,
      dataBucket,
      listingsStream,
      dealAlertsTopic,
      batchQueue,
      deadLetterQueue,
      ecrRepository,
      parameterPrefix,
      appRunnerInstanceRole,
      appRunnerAccessRole,
      ecsTaskRole,
    } = props;

    this.lambdaFunctions = {};

    // ========================================================================
    // App Runner Service (FastAPI Backend) - Optional
    // ========================================================================
    // Requires Docker image to be pushed to ECR first
    // Enable with config.features.enableAppRunner = true

    if (config.features.enableAppRunner) {
      // VPC Connector for App Runner to access private resources
      const vpcConnector = new apprunner.CfnVpcConnector(this, 'VpcConnector', {
        vpcConnectorName: getResourceName('vpc-connector', config),
        subnets: vpc.privateSubnets.map(s => s.subnetId),
        securityGroups: [computeSecurityGroup.securityGroupId],
      });

      // For development, use the existing axiepro-backend repo which has the image
      // For other environments, use the CDK-managed repo
      const ecrImageUri = config.name === 'development'
        ? `${config.account}.dkr.ecr.${config.region}.amazonaws.com/axiepro-backend:latest`
        : `${ecrRepository.repositoryUri}:latest`;

      // App Runner Service (using roles from Security stack)
      this.appRunnerService = new apprunner.CfnService(this, 'AppRunnerService', {
        serviceName: getResourceName('api', config),

        sourceConfiguration: {
          authenticationConfiguration: {
            accessRoleArn: appRunnerAccessRole.roleArn,
          },
          autoDeploymentsEnabled: true,
          imageRepository: {
            imageIdentifier: ecrImageUri,
            imageRepositoryType: 'ECR',
            imageConfiguration: {
              port: '8000',
              runtimeEnvironmentVariables: [
                { name: 'ENVIRONMENT', value: config.name },
                { name: 'AWS_REGION', value: config.region },
                // Use IAM authentication for database (no password needed)
                { name: 'USE_IAM_AUTH', value: 'true' },
                { name: 'DB_HOST', value: databaseCluster.clusterEndpoint.hostname },
                { name: 'DB_PORT', value: DB_PORT.toString() },
                { name: 'DB_NAME', value: DB_NAME },
                { name: 'DB_USER', value: 'axiepro_admin' },
                // Redis URL with TLS
                { name: 'REDIS_URL', value: `rediss://${redisEndpoint}:${redisPort}` },
                // AWS Secrets for API keys only
                { name: 'USE_AWS_SECRETS', value: 'true' },
                { name: 'AWS_SECRET_NAME', value: secretsArn },
                // Other config
                { name: 'S3_DATA_BUCKET', value: dataBucket.bucketName },
                { name: 'KINESIS_STREAM_NAME', value: listingsStream.streamName },
                { name: 'LOG_LEVEL', value: config.name === 'development' ? 'DEBUG' : 'INFO' },
                { name: 'DEBUG', value: config.name === 'development' ? 'true' : 'false' },
              ],
              startCommand: 'uvicorn src.main:app --host 0.0.0.0 --port 8000',
            },
          },
        },

        instanceConfiguration: {
          cpu: config.compute.appRunner.cpu.toString(),
          memory: config.compute.appRunner.memory.toString(),
          instanceRoleArn: appRunnerInstanceRole.roleArn,
        },

        networkConfiguration: {
          egressConfiguration: {
            egressType: 'VPC',
            vpcConnectorArn: vpcConnector.attrVpcConnectorArn,
          },
          ingressConfiguration: {
            isPubliclyAccessible: true,
          },
        },

        autoScalingConfigurationArn: this.createAutoScalingConfig(config),

        healthCheckConfiguration: {
          protocol: 'HTTP',
          path: '/health',
          interval: 10,
          timeout: 5,
          healthyThreshold: 1,
          unhealthyThreshold: 5,
        },

        observabilityConfiguration: {
          observabilityEnabled: config.monitoring.enableXRay,
          observabilityConfigurationArn: config.monitoring.enableXRay
            ? this.createObservabilityConfig(config)
            : undefined,
        },

        tags: [
          { key: 'Name', value: getResourceName('api', config) },
          { key: 'Environment', value: config.name },
          { key: 'Application', value: 'axiepro' },
        ],
      });

      this.appRunnerServiceUrl = this.appRunnerService.attrServiceUrl;
      this.appRunnerServiceArn = this.appRunnerService.attrServiceArn;
    } else {
      // App Runner disabled - provide placeholder values
      this.appRunnerServiceUrl = 'app-runner-disabled';
      this.appRunnerServiceArn = 'app-runner-disabled';
    }

    // ========================================================================
    // ECS Fargate Cluster (Batch Processing)
    // ========================================================================

    this.ecsCluster = new ecs.Cluster(this, 'EcsCluster', {
      clusterName: getResourceName('cluster', config),
      vpc,
      containerInsights: config.monitoring.enableDetailedMetrics,
      enableFargateCapacityProviders: true,
    });

    // ECS execution role (created here to avoid cross-stack grant issues with ECR)
    const ecsExecutionRole = new iam.Role(this, 'EcsExecutionRole', {
      roleName: getResourceName('compute-ecs-execution-role', config),
      description: 'Execution role for ECS tasks',
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AmazonECSTaskExecutionRolePolicy'
        ),
      ],
    });

    // Grant ECS execution role access to secrets
    ecsExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'secretsmanager:GetSecretValue',
          'secretsmanager:DescribeSecret',
        ],
        resources: [secretsArn, `${secretsArn}*`],
      })
    );
    kmsKey.grantDecrypt(ecsExecutionRole);

    // Batch processing task definition
    this.batchTaskDefinition = new ecs.FargateTaskDefinition(this, 'BatchTaskDef', {
      family: getResourceName('batch-processor', config),
      cpu: config.compute.fargate.cpu,
      memoryLimitMiB: config.compute.fargate.memory,
      executionRole: ecsExecutionRole,
      taskRole: ecsTaskRole,
      runtimePlatform: {
        cpuArchitecture: ecs.CpuArchitecture.X86_64,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    // Add container to task definition
    const batchContainer = this.batchTaskDefinition.addContainer('BatchProcessor', {
      containerName: 'batch-processor',
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, 'latest'),
      command: ['python', '-m', 'src.services.batch_processor'],
      environment: {
        ENVIRONMENT: config.name,
        AWS_REGION: config.region,
        USE_AWS_SECRETS: 'true',
        AWS_SECRET_NAME: secretsArn,
        DATABASE_HOST: databaseCluster.clusterEndpoint.hostname,
        DATABASE_PORT: DB_PORT.toString(),
        DATABASE_NAME: DB_NAME,
        DATABASE_SCHEMA: DB_SCHEMA,
        REDIS_HOST: redisEndpoint,
        REDIS_PORT: redisPort.toString(),
        S3_DATA_BUCKET: dataBucket.bucketName,
        SQS_QUEUE_URL: batchQueue.queueUrl,
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'batch-processor',
        logRetention: config.monitoring.logRetentionDays,
      }),
      healthCheck: {
        command: ['CMD-SHELL', 'python -c "print(\'healthy\')" || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },
    });

    // ========================================================================
    // Lambda Functions
    // ========================================================================

    // Note: Lambda security group is created in NetworkingStack and passed via props
    // Security rules for Lambda to access database/cache are also in NetworkingStack

    // Lambda execution role (created here to avoid cross-stack grant issues)
    const lambdaRole = new iam.Role(this, 'LambdaRole', {
      roleName: getResourceName('compute-lambda-role', config),
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaVPCAccessExecutionRole'
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess'),
      ],
    });

    // Grant Lambda permissions
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'secretsmanager:GetSecretValue',
          'secretsmanager:DescribeSecret',
        ],
        resources: [
          secretsArn,
          `${secretsArn}*`,
          databaseSecretsArn,
          `${databaseSecretsArn}*`,
        ],
      })
    );

    kmsKey.grantDecrypt(lambdaRole);
    secretsKey.grantDecrypt(lambdaRole);  // Grant access to secrets KMS key
    dataBucket.grantReadWrite(lambdaRole);
    listingsStream.grantRead(lambdaRole);
    listingsStream.grantWrite(lambdaRole);
    dealAlertsTopic.grantPublish(lambdaRole);
    batchQueue.grantSendMessages(lambdaRole);
    deadLetterQueue.grantSendMessages(lambdaRole);  // Allow Lambda to write to DLQ

    // Grant SSM Parameter Store read access for configuration
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'SSMParameterStoreAccess',
        effect: iam.Effect.ALLOW,
        actions: [
          'ssm:GetParameter',
          'ssm:GetParameters',
          'ssm:GetParametersByPath',
        ],
        resources: [
          `arn:aws:ssm:${config.region}:${config.account}:parameter${parameterPrefix}/*`,
        ],
      })
    );

    // Common Lambda environment variables
    const lambdaEnv = {
      ENVIRONMENT: config.name,
      AWS_REGION_NAME: config.region,
      USE_AWS_SECRETS: 'true',
      AWS_SECRET_NAME: secretsArn,
      DATABASE_SECRET_NAME: databaseSecretsArn,  // Database credentials
      DATABASE_HOST: databaseCluster.clusterEndpoint.hostname,
      DATABASE_PORT: DB_PORT.toString(),
      DATABASE_NAME: DB_NAME,
      DATABASE_SCHEMA: DB_SCHEMA,
      REDIS_HOST: redisEndpoint,
      REDIS_PORT: redisPort.toString(),
      REDIS_SSL: 'true',
      S3_DATA_BUCKET: dataBucket.bucketName,
      KINESIS_STREAM_NAME: listingsStream.streamName,
      SNS_DEAL_ALERTS_TOPIC: dealAlertsTopic.topicArn,
      PARAMETER_PREFIX: parameterPrefix,  // SSM Parameter Store prefix for configuration
      POWERTOOLS_SERVICE_NAME: 'axiepro',
      POWERTOOLS_METRICS_NAMESPACE: 'AxiePro',
      LOG_LEVEL: config.name === 'development' ? 'DEBUG' : 'INFO',
    };

    // Lambda layer for dependencies
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      layerVersionName: getResourceName('dependencies-layer', config),
      description: 'Python dependencies for Lambda functions',
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      code: lambda.Code.fromAsset('../backend/lambda-layer'),
      removalPolicy: config.removalPolicy,
    });

    // Common Lambda code asset with exclusions to avoid packaging venv and other unnecessary files
    const lambdaCodeAsset = lambda.Code.fromAsset('../backend', {
      exclude: [
        'venv',
        'venv/**',
        '.venv',
        '.venv/**',
        '__pycache__',
        '**/__pycache__',
        '*.pyc',
        '**/*.pyc',
        'tests',
        'tests/**',
        'lambda-layer',
        'lambda-layer/**',
        '.git',
        '.git/**',
        '.pytest_cache',
        '**/.pytest_cache',
        '*.egg-info',
        '**/*.egg-info',
        'dist',
        'dist/**',
        'build',
        'build/**',
        '.mypy_cache',
        '**/.mypy_cache',
        '.ruff_cache',
        '**/.ruff_cache',
        'htmlcov',
        'htmlcov/**',
        '.coverage',
        '*.md',
        'Dockerfile',
        'docker-compose*.yml',
      ],
    });

    // 1. Price Ingestion Lambda
    const priceIngestionLambda = new lambda.Function(this, 'PriceIngestionLambda', {
      functionName: getResourceName('price-ingestion', config),
      description: 'Fetches floor prices from Sky Mavis and stores snapshots',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.price_ingestion.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: config.compute.lambda.timeout,
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
      reservedConcurrentExecutions: config.compute.lambda.reservedConcurrency,
    });
    this.lambdaFunctions['priceIngestion'] = priceIngestionLambda;

    // Configure DLQ for async invocations (EventBridge scheduled)
    priceIngestionLambda.configureAsyncInvoke({
      onFailure: new lambdaDestinations.SqsDestination(deadLetterQueue),
      retryAttempts: 2,
    });

    // 2. Sales Ingestion Lambda
    const salesIngestionLambda = new lambda.Function(this, 'SalesIngestionLambda', {
      functionName: getResourceName('sales-ingestion', config),
      description: 'Fetches settled sales from Ronin RPC and stores in database',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.sales_ingestion.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: cdk.Duration.minutes(5), // Longer timeout for RPC block scanning
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
      reservedConcurrentExecutions: config.compute.lambda.reservedConcurrency,
    });
    this.lambdaFunctions['salesIngestion'] = salesIngestionLambda;

    // Configure DLQ for async invocations (EventBridge scheduled)
    salesIngestionLambda.configureAsyncInvoke({
      onFailure: new lambdaDestinations.SqsDestination(deadLetterQueue),
      retryAttempts: 2,
    });

    // 3. Metadata Ingestion Lambda - populates axies table using Moralis + SkyMavis
    const metadataIngestionLambda = new lambda.Function(this, 'MetadataIngestionLambda', {
      functionName: getResourceName('metadata-ingestion', config),
      description: 'Fetches axie metadata from Moralis/SkyMavis and populates axies table',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.metadata_ingestion.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: cdk.Duration.minutes(5), // Longer timeout for batch metadata fetching
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
      reservedConcurrentExecutions: config.compute.lambda.reservedConcurrency,
    });
    this.lambdaFunctions['metadataIngestion'] = metadataIngestionLambda;

    // Configure DLQ for async invocations (EventBridge scheduled)
    metadataIngestionLambda.configureAsyncInvoke({
      onFailure: new lambdaDestinations.SqsDestination(deadLetterQueue),
      retryAttempts: 2,
    });

    // 4. Listings Ingestion Lambda - publishes to Kinesis for deal detection
    const listingsIngestionLambda = new lambda.Function(this, 'ListingsIngestionLambda', {
      functionName: getResourceName('listings-ingestion', config),
      description: 'Fetches active listings and publishes to Kinesis for deal detection',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.listings_ingestion.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: cdk.Duration.minutes(5), // Longer timeout for multi-class pagination
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
      reservedConcurrentExecutions: config.compute.lambda.reservedConcurrency,
    });
    this.lambdaFunctions['listingsIngestion'] = listingsIngestionLambda;

    // Configure DLQ for async invocations (EventBridge scheduled)
    listingsIngestionLambda.configureAsyncInvoke({
      onFailure: new lambdaDestinations.SqsDestination(deadLetterQueue),
      retryAttempts: 2,
    });

    // 5. Deal Detector Lambda (triggered by Kinesis)
    const dealDetectorLambda = new lambda.Function(this, 'DealDetectorLambda', {
      functionName: getResourceName('deal-detector', config),
      description: 'Detects undervalued listings from Kinesis stream',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.deal_detector.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: cdk.Duration.seconds(30),
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
    });
    this.lambdaFunctions['dealDetector'] = dealDetectorLambda;

    // Add Kinesis event source with DLQ for failed record batches
    dealDetectorLambda.addEventSource(
      new lambdaEventSources.KinesisEventSource(listingsStream, {
        batchSize: 100,
        maxBatchingWindow: cdk.Duration.seconds(5),
        startingPosition: lambda.StartingPosition.LATEST,
        retryAttempts: 3,
        bisectBatchOnError: true,
        reportBatchItemFailures: true,
        onFailure: new lambdaDestinations.SqsDestination(deadLetterQueue),
      })
    );

    // 6. Meta Analyzer Lambda
    const metaAnalyzerLambda = new lambda.Function(this, 'MetaAnalyzerLambda', {
      functionName: getResourceName('meta-analyzer', config),
      description: 'Analyzes market trends and detects meta shifts',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.meta_analyzer.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: 1024, // Needs more memory for analysis
      timeout: cdk.Duration.minutes(5),
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
    });
    this.lambdaFunctions['metaAnalyzer'] = metaAnalyzerLambda;

    // Configure DLQ for async invocations (EventBridge scheduled)
    metaAnalyzerLambda.configureAsyncInvoke({
      onFailure: new lambdaDestinations.SqsDestination(deadLetterQueue),
      retryAttempts: 2,
    });

    // 7. Valuation Lambda
    const valuationLambda = new lambda.Function(this, 'ValuationLambda', {
      functionName: getResourceName('valuation', config),
      description: 'Computes fair value estimates for Axies',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.valuation.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: cdk.Duration.seconds(30),
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
    });
    this.lambdaFunctions['valuation'] = valuationLambda;

    // 8. Run Migrations Lambda - database schema management
    const runMigrationsLambda = new lambda.Function(this, 'RunMigrationsLambda', {
      functionName: getResourceName('run-migrations', config),
      description: 'Runs database migrations against Aurora PostgreSQL',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.run_migrations.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: cdk.Duration.minutes(5), // Migrations may take time
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
    });
    this.lambdaFunctions['runMigrations'] = runMigrationsLambda;

    // 9. Health Check Lambda - monitors data freshness
    const healthCheckLambda = new lambda.Function(this, 'HealthCheckLambda', {
      functionName: getResourceName('health-check', config),
      description: 'Monitors data freshness and pipeline health',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'src.lambdas.health_check.handler',
      code: lambdaCodeAsset,
      layers: [dependenciesLayer],
      memorySize: config.compute.lambda.memorySize,
      timeout: cdk.Duration.seconds(30),
      role: lambdaRole,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      environment: lambdaEnv,
      tracing: config.monitoring.enableXRay
        ? lambda.Tracing.ACTIVE
        : lambda.Tracing.DISABLED,
    });
    this.lambdaFunctions['healthCheck'] = healthCheckLambda;

    // Configure DLQ for async invocations (EventBridge scheduled)
    healthCheckLambda.configureAsyncInvoke({
      onFailure: new lambdaDestinations.SqsDestination(deadLetterQueue),
      retryAttempts: 2,
    });

    // ========================================================================
    // EventBridge Rules (Scheduled Triggers)
    // ========================================================================

    // Price ingestion - every 15 minutes (reduced from 5 to avoid rate limiting)
    new events.Rule(this, 'PriceIngestionSchedule', {
      ruleName: getResourceName('price-ingestion-trigger', config),
      description: 'Triggers price ingestion every 15 minutes',
      schedule: events.Schedule.rate(cdk.Duration.minutes(15)),
      targets: [new targets.LambdaFunction(priceIngestionLambda)],
    });

    // Sales ingestion - every 30 minutes (reduced from 15 to avoid rate limiting)
    new events.Rule(this, 'SalesIngestionSchedule', {
      ruleName: getResourceName('sales-ingestion-trigger', config),
      description: 'Triggers sales ingestion every 30 minutes',
      schedule: events.Schedule.rate(cdk.Duration.minutes(30)),
      targets: [new targets.LambdaFunction(salesIngestionLambda)],
    });

    // Listings ingestion - every 5 minutes (publishes to Kinesis for deal detection)
    new events.Rule(this, 'ListingsIngestionSchedule', {
      ruleName: getResourceName('listings-ingestion-trigger', config),
      description: 'Triggers listings ingestion every 5 minutes',
      schedule: events.Schedule.rate(cdk.Duration.minutes(5)),
      targets: [new targets.LambdaFunction(listingsIngestionLambda)],
    });

    // Metadata ingestion - every hour (backfills axie metadata)
    new events.Rule(this, 'MetadataIngestionSchedule', {
      ruleName: getResourceName('metadata-ingestion-trigger', config),
      description: 'Triggers metadata ingestion every hour',
      schedule: events.Schedule.rate(cdk.Duration.hours(1)),
      targets: [new targets.LambdaFunction(metadataIngestionLambda)],
    });

    // Meta analysis - every hour
    new events.Rule(this, 'MetaAnalysisSchedule', {
      ruleName: getResourceName('meta-analysis-trigger', config),
      description: 'Triggers meta analysis every hour',
      schedule: events.Schedule.rate(cdk.Duration.hours(1)),
      targets: [new targets.LambdaFunction(metaAnalyzerLambda)],
    });

    // Health check - every 5 minutes (monitors data freshness)
    new events.Rule(this, 'HealthCheckSchedule', {
      ruleName: getResourceName('health-check-trigger', config),
      description: 'Triggers health check every 5 minutes',
      schedule: events.Schedule.rate(cdk.Duration.minutes(5)),
      targets: [new targets.LambdaFunction(healthCheckLambda)],
    });

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'AppRunnerServiceUrl', {
      value: `https://${this.appRunnerServiceUrl}`,
      description: 'App Runner service URL',
      exportName: `${id}-AppRunnerServiceUrl`,
    });

    new cdk.CfnOutput(this, 'AppRunnerServiceArn', {
      value: this.appRunnerServiceArn,
      description: 'App Runner service ARN',
      exportName: `${id}-AppRunnerServiceArn`,
    });

    new cdk.CfnOutput(this, 'EcsClusterArn', {
      value: this.ecsCluster.clusterArn,
      description: 'ECS cluster ARN',
      exportName: `${id}-EcsClusterArn`,
    });

    new cdk.CfnOutput(this, 'BatchTaskDefinitionArn', {
      value: this.batchTaskDefinition.taskDefinitionArn,
      description: 'Batch task definition ARN',
      exportName: `${id}-BatchTaskDefArn`,
    });

    new cdk.CfnOutput(this, 'PriceIngestionLambdaArn', {
      value: priceIngestionLambda.functionArn,
      description: 'Price ingestion Lambda ARN',
      exportName: `${id}-PriceIngestionLambdaArn`,
    });

    new cdk.CfnOutput(this, 'DealDetectorLambdaArn', {
      value: dealDetectorLambda.functionArn,
      description: 'Deal detector Lambda ARN',
      exportName: `${id}-DealDetectorLambdaArn`,
    });

    new cdk.CfnOutput(this, 'SalesIngestionLambdaArn', {
      value: salesIngestionLambda.functionArn,
      description: 'Sales ingestion Lambda ARN',
      exportName: `${id}-SalesIngestionLambdaArn`,
    });

    new cdk.CfnOutput(this, 'MetadataIngestionLambdaArn', {
      value: metadataIngestionLambda.functionArn,
      description: 'Metadata ingestion Lambda ARN',
      exportName: `${id}-MetadataIngestionLambdaArn`,
    });

    new cdk.CfnOutput(this, 'ListingsIngestionLambdaArn', {
      value: listingsIngestionLambda.functionArn,
      description: 'Listings ingestion Lambda ARN',
      exportName: `${id}-ListingsIngestionLambdaArn`,
    });

    new cdk.CfnOutput(this, 'HealthCheckLambdaArn', {
      value: healthCheckLambda.functionArn,
      description: 'Health check Lambda ARN',
      exportName: `${id}-HealthCheckLambdaArn`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Compute');
  }

  /**
   * Creates an auto-scaling configuration for App Runner
   */
  private createAutoScalingConfig(config: EnvironmentConfig): string {
    const autoScalingConfig = new apprunner.CfnAutoScalingConfiguration(
      this,
      'AutoScalingConfig',
      {
        autoScalingConfigurationName: getResourceName('autoscaling', config),
        minSize: config.compute.appRunner.minInstances,
        maxSize: config.compute.appRunner.maxInstances,
        maxConcurrency: 100, // Requests per instance before scaling
      }
    );
    return autoScalingConfig.attrAutoScalingConfigurationArn;
  }

  /**
   * Creates an observability configuration for App Runner (X-Ray tracing)
   */
  private createObservabilityConfig(config: EnvironmentConfig): string {
    const observabilityConfig = new apprunner.CfnObservabilityConfiguration(
      this,
      'ObservabilityConfig',
      {
        observabilityConfigurationName: getResourceName('observability', config),
        traceConfiguration: {
          vendor: 'AWSXRAY',
        },
      }
    );
    return observabilityConfig.attrObservabilityConfigurationArn;
  }
}

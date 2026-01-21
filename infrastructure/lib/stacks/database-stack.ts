/**
 * AxiePro Database Stack
 *
 * Creates database resources:
 * - Aurora Serverless v2 PostgreSQL cluster (with TimescaleDB support)
 * - DynamoDB tables for fast key-value lookups
 * - Database parameter groups for PostgreSQL optimization
 * - Automated backups and point-in-time recovery
 */

import * as cdk from 'aws-cdk-lib';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';
import { DB_NAME, DB_PORT, DB_SCHEMA } from '../config/constants';

export interface DatabaseStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.IVpc;
  databaseSecurityGroup: ec2.ISecurityGroup;
  kmsKey: kms.IKey;
}

export class DatabaseStack extends cdk.Stack {
  // Aurora cluster
  public readonly cluster: rds.IDatabaseCluster;
  public readonly clusterEndpoint: string;
  public readonly clusterReadEndpoint: string;

  // DynamoDB tables
  public readonly checkpointTable: dynamodb.Table;
  public readonly valuationCacheTable: dynamodb.Table;
  public readonly sessionTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    const { config, vpc, databaseSecurityGroup, kmsKey } = props;

    // ========================================================================
    // Aurora Serverless v2 PostgreSQL
    // ========================================================================

    // Parameter group for PostgreSQL optimization
    const parameterGroup = new rds.ParameterGroup(this, 'ParameterGroup', {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_15_8,
      }),
      description: 'AxiePro Aurora PostgreSQL parameter group',
      parameters: {
        // Connection management
        'max_connections': '1000',
        'idle_in_transaction_session_timeout': '300000', // 5 minutes

        // Memory settings (adjusted by Aurora automatically)
        'shared_buffers': '{DBInstanceClassMemory/32768}',
        'effective_cache_size': '{DBInstanceClassMemory*3/32768}',

        // Query optimization
        'random_page_cost': '1.1', // SSD-optimized
        'effective_io_concurrency': '200',

        // Logging
        'log_min_duration_statement': '1000', // Log queries > 1 second
        'log_connections': '1',
        'log_disconnections': '1',

        // TimescaleDB compatibility
        'shared_preload_libraries': 'pg_stat_statements',

        // Statement timeout for long-running queries
        'statement_timeout': '300000', // 5 minutes
      },
    });

    // Cluster parameter group
    const clusterParameterGroup = new rds.ParameterGroup(this, 'ClusterParameterGroup', {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_15_8,
      }),
      description: 'AxiePro Aurora PostgreSQL cluster parameter group',
      parameters: {
        // Replication settings
        'rds.logical_replication': '1',

        // Force SSL connections
        'rds.force_ssl': '1',
      },
    });

    // Subnet group
    const subnetGroup = new rds.SubnetGroup(this, 'SubnetGroup', {
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      description: 'Subnet group for Aurora PostgreSQL',
      subnetGroupName: getResourceName('aurora-subnet-group', config),
    });

    // Aurora Serverless v2 Cluster
    const cluster = new rds.DatabaseCluster(this, 'AuroraCluster', {
      clusterIdentifier: getResourceName('aurora-cluster', config),
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_15_8,
      }),
      defaultDatabaseName: DB_NAME,
      port: DB_PORT,

      // Credentials
      credentials: rds.Credentials.fromGeneratedSecret('axiepro_admin', {
        secretName: getResourceName('aurora-credentials', config),
        encryptionKey: kmsKey,
      }),

      // Serverless v2 configuration
      serverlessV2MinCapacity: config.database.minCapacity,
      serverlessV2MaxCapacity: config.database.maxCapacity,

      // Writer instance (Serverless v2)
      writer: rds.ClusterInstance.serverlessV2('Writer', {
        autoMinorVersionUpgrade: true,
        enablePerformanceInsights: true,
        performanceInsightRetention: rds.PerformanceInsightRetention.DEFAULT,
        publiclyAccessible: false,
      }),

      // Reader instance for production (only if Multi-AZ enabled)
      readers: config.database.enableMultiAz
        ? [
            rds.ClusterInstance.serverlessV2('Reader', {
              scaleWithWriter: true,
              autoMinorVersionUpgrade: true,
              enablePerformanceInsights: true,
              performanceInsightRetention: rds.PerformanceInsightRetention.DEFAULT,
              publiclyAccessible: false,
            }),
          ]
        : [],

      // Network configuration
      vpc,
      subnetGroup,
      securityGroups: [databaseSecurityGroup],

      // Parameter groups
      parameterGroup: clusterParameterGroup,

      // Encryption
      storageEncrypted: true,
      storageEncryptionKey: kmsKey,

      // Backup configuration
      backup: {
        retention: config.database.backupRetention,
        preferredWindow: '03:00-04:00', // 3-4 AM UTC
      },

      // Maintenance window
      preferredMaintenanceWindow: 'sun:04:00-sun:05:00', // Sunday 4-5 AM UTC

      // Deletion protection
      deletionProtection: config.database.deletionProtection,
      removalPolicy: config.removalPolicy,

      // CloudWatch logs
      cloudwatchLogsExports: ['postgresql'],
      cloudwatchLogsRetention: logs.RetentionDays.ONE_MONTH,

      // IAM authentication
      iamAuthentication: true,

      // Copy tags to snapshots
      copyTagsToSnapshot: true,
    });

    this.cluster = cluster;
    this.clusterEndpoint = cluster.clusterEndpoint.hostname;
    this.clusterReadEndpoint = cluster.clusterReadEndpoint.hostname;

    // ========================================================================
    // DynamoDB Tables
    // ========================================================================

    // Checkpoint table - tracks sync progress for blockchain indexing
    this.checkpointTable = new dynamodb.Table(this, 'CheckpointTable', {
      tableName: getResourceName('checkpoints', config),
      partitionKey: {
        name: 'checkpoint_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsKey,
      pointInTimeRecovery: config.name !== 'development',
      removalPolicy: config.removalPolicy,
      timeToLiveAttribute: 'ttl',
    });

    // Valuation cache table - stores computed valuations for quick retrieval
    this.valuationCacheTable = new dynamodb.Table(this, 'ValuationCacheTable', {
      tableName: getResourceName('valuation-cache', config),
      partitionKey: {
        name: 'axie_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.NUMBER,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsKey,
      pointInTimeRecovery: config.name !== 'development',
      removalPolicy: config.removalPolicy,
      timeToLiveAttribute: 'ttl',
    });

    // Add GSI for querying by class
    this.valuationCacheTable.addGlobalSecondaryIndex({
      indexName: 'class-timestamp-index',
      partitionKey: {
        name: 'axie_class',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.NUMBER,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Session table - stores user sessions and real-time state
    this.sessionTable = new dynamodb.Table(this, 'SessionTable', {
      tableName: getResourceName('sessions', config),
      partitionKey: {
        name: 'session_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsKey,
      pointInTimeRecovery: false, // Sessions are ephemeral
      removalPolicy: config.removalPolicy,
      timeToLiveAttribute: 'expires_at',
    });

    // Add GSI for querying sessions by user
    this.sessionTable.addGlobalSecondaryIndex({
      indexName: 'user-index',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.NUMBER,
      },
      projectionType: dynamodb.ProjectionType.KEYS_ONLY,
    });

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: this.clusterEndpoint,
      description: 'Aurora cluster writer endpoint',
      exportName: `${id}-ClusterEndpoint`,
    });

    new cdk.CfnOutput(this, 'ClusterReadEndpoint', {
      value: this.clusterReadEndpoint,
      description: 'Aurora cluster reader endpoint',
      exportName: `${id}-ClusterReadEndpoint`,
    });

    new cdk.CfnOutput(this, 'ClusterPort', {
      value: DB_PORT.toString(),
      description: 'Aurora cluster port',
      exportName: `${id}-ClusterPort`,
    });

    new cdk.CfnOutput(this, 'DatabaseName', {
      value: DB_NAME,
      description: 'Database name',
      exportName: `${id}-DatabaseName`,
    });

    new cdk.CfnOutput(this, 'DatabaseSchema', {
      value: DB_SCHEMA,
      description: 'Database schema',
      exportName: `${id}-DatabaseSchema`,
    });

    new cdk.CfnOutput(this, 'ClusterSecretArn', {
      value: cluster.secret?.secretArn || '',
      description: 'Aurora cluster credentials secret ARN',
      exportName: `${id}-ClusterSecretArn`,
    });

    new cdk.CfnOutput(this, 'CheckpointTableName', {
      value: this.checkpointTable.tableName,
      description: 'DynamoDB checkpoint table name',
      exportName: `${id}-CheckpointTableName`,
    });

    new cdk.CfnOutput(this, 'ValuationCacheTableName', {
      value: this.valuationCacheTable.tableName,
      description: 'DynamoDB valuation cache table name',
      exportName: `${id}-ValuationCacheTableName`,
    });

    new cdk.CfnOutput(this, 'SessionTableName', {
      value: this.sessionTable.tableName,
      description: 'DynamoDB session table name',
      exportName: `${id}-SessionTableName`,
    });

    // Connection string format (for documentation)
    new cdk.CfnOutput(this, 'ConnectionStringFormat', {
      value: `postgresql://{username}:{password}@${this.clusterEndpoint}:${DB_PORT}/${DB_NAME}`,
      description: 'PostgreSQL connection string format',
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Database');
  }
}

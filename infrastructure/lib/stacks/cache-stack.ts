/**
 * AxiePro Cache Stack
 *
 * Creates caching infrastructure:
 * - ElastiCache Redis cluster (replication group)
 * - Subnet groups for Redis deployment
 * - Parameter groups for Redis optimization
 * - Automatic failover configuration
 */

import * as cdk from 'aws-cdk-lib';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';
import { REDIS_PORT } from '../config/constants';

export interface CacheStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.IVpc;
  cacheSecurityGroup: ec2.ISecurityGroup;
  kmsKey: kms.IKey;
}

export class CacheStack extends cdk.Stack {
  public readonly replicationGroup: elasticache.CfnReplicationGroup;
  public readonly redisEndpoint: string;
  public readonly redisPort: number;

  constructor(scope: Construct, id: string, props: CacheStackProps) {
    super(scope, id, props);

    const { config, vpc, cacheSecurityGroup, kmsKey } = props;

    // ========================================================================
    // Subnet Group
    // ========================================================================

    const subnetGroup = new elasticache.CfnSubnetGroup(this, 'SubnetGroup', {
      cacheSubnetGroupName: getResourceName('redis-subnet-group', config),
      description: 'Subnet group for ElastiCache Redis',
      subnetIds: vpc.privateSubnets.map(subnet => subnet.subnetId),
    });

    // ========================================================================
    // Parameter Group (Redis 7.x optimized)
    // ========================================================================

    const parameterGroup = new elasticache.CfnParameterGroup(this, 'ParameterGroup', {
      cacheParameterGroupFamily: 'redis7',
      description: 'AxiePro Redis parameter group',
      properties: {
        // Memory management
        'maxmemory-policy': 'allkeys-lru',

        // Connection settings
        'timeout': '300', // 5 minutes idle timeout
        'tcp-keepalive': '60',

        // Performance settings
        'activedefrag': 'yes',
        'lazyfree-lazy-eviction': 'yes',
        'lazyfree-lazy-expire': 'yes',

        // Slow log
        'slowlog-log-slower-than': '10000', // 10ms
        'slowlog-max-len': '128',

        // Notification settings
        'notify-keyspace-events': 'Ex', // Expired events
      },
    });

    // ========================================================================
    // CloudWatch Log Groups for Redis
    // ========================================================================

    const slowLogGroup = new logs.LogGroup(this, 'SlowLogGroup', {
      logGroupName: `/aws/elasticache/${getResourceName('redis', config)}/slow-log`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: config.removalPolicy,
    });

    const engineLogGroup = new logs.LogGroup(this, 'EngineLogGroup', {
      logGroupName: `/aws/elasticache/${getResourceName('redis', config)}/engine-log`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: config.removalPolicy,
    });

    // ========================================================================
    // Redis Replication Group
    // ========================================================================

    this.replicationGroup = new elasticache.CfnReplicationGroup(this, 'RedisCluster', {
      replicationGroupDescription: 'AxiePro ElastiCache Redis cluster',
      replicationGroupId: getResourceName('redis', config),

      // Engine configuration
      engine: 'redis',
      engineVersion: '7.1',
      cacheNodeType: config.cache.nodeType,
      port: REDIS_PORT,

      // Cluster configuration
      numCacheClusters: config.cache.numReplicas + 1, // Primary + replicas
      automaticFailoverEnabled: config.cache.automaticFailover && config.cache.numReplicas > 0,
      multiAzEnabled: config.cache.numReplicas > 0,

      // Network configuration
      cacheSubnetGroupName: subnetGroup.cacheSubnetGroupName,
      securityGroupIds: [cacheSecurityGroup.securityGroupId],

      // Parameter group
      cacheParameterGroupName: parameterGroup.ref,

      // Encryption
      atRestEncryptionEnabled: true,
      kmsKeyId: kmsKey.keyId,
      transitEncryptionEnabled: true,
      transitEncryptionMode: 'required',

      // Authentication
      authToken: undefined, // Will use IAM auth instead

      // Maintenance
      preferredMaintenanceWindow: 'sun:05:00-sun:06:00',
      autoMinorVersionUpgrade: true,

      // Snapshots
      snapshotRetentionLimit: config.name === 'production' ? 7 : 1,
      snapshotWindow: '04:00-05:00',

      // Logging
      logDeliveryConfigurations: [
        {
          destinationType: 'cloudwatch-logs',
          logFormat: 'json',
          logType: 'slow-log',
          destinationDetails: {
            cloudWatchLogsDetails: {
              logGroup: `/aws/elasticache/${getResourceName('redis', config)}/slow-log`,
            },
          },
        },
        {
          destinationType: 'cloudwatch-logs',
          logFormat: 'json',
          logType: 'engine-log',
          destinationDetails: {
            cloudWatchLogsDetails: {
              logGroup: `/aws/elasticache/${getResourceName('redis', config)}/engine-log`,
            },
          },
        },
      ],

      // Tags
      tags: [
        { key: 'Name', value: getResourceName('redis', config) },
        { key: 'Environment', value: config.name },
        { key: 'Application', value: 'axiepro' },
      ],
    });

    // Ensure dependencies are created first
    this.replicationGroup.addDependency(subnetGroup);
    this.replicationGroup.addDependency(parameterGroup);
    this.replicationGroup.node.addDependency(slowLogGroup);
    this.replicationGroup.node.addDependency(engineLogGroup);

    // Set removal policy
    if (config.removalPolicy === cdk.RemovalPolicy.DESTROY) {
      this.replicationGroup.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);
    }

    // Get the primary endpoint
    this.redisEndpoint = this.replicationGroup.attrPrimaryEndPointAddress;
    this.redisPort = REDIS_PORT;

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'RedisEndpoint', {
      value: this.redisEndpoint,
      description: 'Redis primary endpoint',
      exportName: `${id}-RedisEndpoint`,
    });

    new cdk.CfnOutput(this, 'RedisPort', {
      value: REDIS_PORT.toString(),
      description: 'Redis port',
      exportName: `${id}-RedisPort`,
    });

    new cdk.CfnOutput(this, 'RedisConnectionString', {
      value: `rediss://${this.redisEndpoint}:${REDIS_PORT}`,
      description: 'Redis connection string (TLS)',
      exportName: `${id}-RedisConnectionString`,
    });

    new cdk.CfnOutput(this, 'ReplicationGroupId', {
      value: this.replicationGroup.replicationGroupId || '',
      description: 'Redis replication group ID',
      exportName: `${id}-ReplicationGroupId`,
    });

    // Reader endpoint (if replicas exist)
    if (config.cache.numReplicas > 0) {
      new cdk.CfnOutput(this, 'RedisReaderEndpoint', {
        value: this.replicationGroup.attrReaderEndPointAddress,
        description: 'Redis reader endpoint',
        exportName: `${id}-RedisReaderEndpoint`,
      });
    }

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Cache');
  }
}

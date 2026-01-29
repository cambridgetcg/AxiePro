/**
 * AxiePro Observability Stack
 *
 * Creates monitoring and observability infrastructure:
 * - CloudWatch dashboards for system overview
 * - CloudWatch alarms for critical metrics
 * - Log groups and metric filters
 * - X-Ray service map configuration
 */

import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as kinesis from 'aws-cdk-lib/aws-kinesis';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';
import { METRICS_NAMESPACE } from '../config/constants';

export interface ObservabilityStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  databaseCluster: rds.IDatabaseCluster;
  redisReplicationGroup: elasticache.CfnReplicationGroup;
  appRunnerServiceArn: string;
  lambdaFunctions: { [key: string]: lambda.IFunction };
  apiGateway: apigatewayv2.CfnApi;
  listingsStream: kinesis.IStream;
  batchQueue: sqs.IQueue;
  dealAlertsTopic: sns.ITopic;
}

export class ObservabilityStack extends cdk.Stack {
  public readonly dashboard: cloudwatch.Dashboard;
  public readonly alarmTopic: sns.ITopic;

  constructor(scope: Construct, id: string, props: ObservabilityStackProps) {
    super(scope, id, props);

    const {
      config,
      databaseCluster,
      redisReplicationGroup,
      appRunnerServiceArn,
      lambdaFunctions,
      apiGateway,
      listingsStream,
      batchQueue,
    } = props;

    // ========================================================================
    // SNS Topic for Alarms
    // ========================================================================

    this.alarmTopic = new sns.Topic(this, 'AlarmTopic', {
      topicName: getResourceName('alarms', config),
      displayName: 'AxiePro CloudWatch Alarms',
    });

    // Add email subscription (replace with actual email)
    // this.alarmTopic.addSubscription(
    //   new snsSubscriptions.EmailSubscription('alerts@axiepro.io')
    // );

    // ========================================================================
    // CloudWatch Dashboard
    // ========================================================================

    this.dashboard = new cloudwatch.Dashboard(this, 'Dashboard', {
      dashboardName: getResourceName('dashboard', config),
      periodOverride: cloudwatch.PeriodOverride.AUTO,
    });

    // Dashboard Header
    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: `# AxiePro Monitoring Dashboard (${config.name})

Real-time monitoring for the Axie Infinity Analytics Platform.

**Quick Links:** [App Runner Console](https://console.aws.amazon.com/apprunner) | [Lambda Console](https://console.aws.amazon.com/lambda) | [RDS Console](https://console.aws.amazon.com/rds)`,
        width: 24,
        height: 2,
      })
    );

    // ========================================================================
    // API & Compute Metrics
    // ========================================================================

    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: '## API & Compute',
        width: 24,
        height: 1,
      })
    );

    // API Gateway metrics
    const apiRequestsMetric = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: 'Count',
      dimensionsMap: {
        ApiId: apiGateway.ref,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(1),
    });

    const apiLatencyMetric = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: 'Latency',
      dimensionsMap: {
        ApiId: apiGateway.ref,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    const api4xxMetric = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: '4XXError',
      dimensionsMap: {
        ApiId: apiGateway.ref,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(1),
    });

    const api5xxMetric = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: '5XXError',
      dimensionsMap: {
        ApiId: apiGateway.ref,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(1),
    });

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Requests',
        left: [apiRequestsMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'API Latency (ms)',
        left: [apiLatencyMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'API Errors',
        left: [api4xxMetric, api5xxMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.SingleValueWidget({
        title: 'Current Requests/min',
        metrics: [apiRequestsMetric],
        width: 6,
        height: 6,
      })
    );

    // Lambda metrics
    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: '## Lambda Functions',
        width: 24,
        height: 1,
      })
    );

    const lambdaWidgets: cloudwatch.IWidget[] = [];
    for (const [name, fn] of Object.entries(lambdaFunctions)) {
      const invocations = fn.metricInvocations({ period: cdk.Duration.minutes(5) });
      const errors = fn.metricErrors({ period: cdk.Duration.minutes(5) });
      const duration = fn.metricDuration({ period: cdk.Duration.minutes(5) });

      lambdaWidgets.push(
        new cloudwatch.GraphWidget({
          title: `${name} - Invocations & Errors`,
          left: [invocations],
          right: [errors],
          width: 8,
          height: 5,
        })
      );
    }

    // Add lambda widgets in rows of 3
    for (let i = 0; i < lambdaWidgets.length; i += 3) {
      this.dashboard.addWidgets(...lambdaWidgets.slice(i, i + 3));
    }

    // ========================================================================
    // Database Metrics
    // ========================================================================

    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: '## Database (Aurora PostgreSQL)',
        width: 24,
        height: 1,
      })
    );

    const dbCpuMetric = new cloudwatch.Metric({
      namespace: 'AWS/RDS',
      metricName: 'CPUUtilization',
      dimensionsMap: {
        DBClusterIdentifier: databaseCluster.clusterIdentifier,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    const dbConnectionsMetric = new cloudwatch.Metric({
      namespace: 'AWS/RDS',
      metricName: 'DatabaseConnections',
      dimensionsMap: {
        DBClusterIdentifier: databaseCluster.clusterIdentifier,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    const dbCapacityMetric = new cloudwatch.Metric({
      namespace: 'AWS/RDS',
      metricName: 'ServerlessDatabaseCapacity',
      dimensionsMap: {
        DBClusterIdentifier: databaseCluster.clusterIdentifier,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    const dbReadLatencyMetric = new cloudwatch.Metric({
      namespace: 'AWS/RDS',
      metricName: 'ReadLatency',
      dimensionsMap: {
        DBClusterIdentifier: databaseCluster.clusterIdentifier,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Database CPU',
        left: [dbCpuMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Database Connections',
        left: [dbConnectionsMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Serverless Capacity (ACUs)',
        left: [dbCapacityMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Read Latency (seconds)',
        left: [dbReadLatencyMetric],
        width: 6,
        height: 6,
      })
    );

    // ========================================================================
    // Cache Metrics
    // ========================================================================

    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: '## Cache (ElastiCache Redis)',
        width: 24,
        height: 1,
      })
    );

    const redisCpuMetric = new cloudwatch.Metric({
      namespace: 'AWS/ElastiCache',
      metricName: 'CPUUtilization',
      dimensionsMap: {
        ReplicationGroupId: redisReplicationGroup.replicationGroupId || '',
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    const redisMemoryMetric = new cloudwatch.Metric({
      namespace: 'AWS/ElastiCache',
      metricName: 'DatabaseMemoryUsagePercentage',
      dimensionsMap: {
        ReplicationGroupId: redisReplicationGroup.replicationGroupId || '',
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    const redisCacheHitsMetric = new cloudwatch.Metric({
      namespace: 'AWS/ElastiCache',
      metricName: 'CacheHits',
      dimensionsMap: {
        ReplicationGroupId: redisReplicationGroup.replicationGroupId || '',
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(1),
    });

    const redisCacheMissesMetric = new cloudwatch.Metric({
      namespace: 'AWS/ElastiCache',
      metricName: 'CacheMisses',
      dimensionsMap: {
        ReplicationGroupId: redisReplicationGroup.replicationGroupId || '',
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(1),
    });

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Redis CPU',
        left: [redisCpuMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Redis Memory Usage (%)',
        left: [redisMemoryMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Cache Hit/Miss Ratio',
        left: [redisCacheHitsMetric, redisCacheMissesMetric],
        width: 12,
        height: 6,
      })
    );

    // ========================================================================
    // Event Processing Metrics
    // ========================================================================

    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: '## Event Processing',
        width: 24,
        height: 1,
      })
    );

    // Kinesis metrics
    const kinesisIncomingRecords = new cloudwatch.Metric({
      namespace: 'AWS/Kinesis',
      metricName: 'IncomingRecords',
      dimensionsMap: {
        StreamName: listingsStream.streamName,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(1),
    });

    const kinesisIteratorAge = new cloudwatch.Metric({
      namespace: 'AWS/Kinesis',
      metricName: 'GetRecords.IteratorAgeMilliseconds',
      dimensionsMap: {
        StreamName: listingsStream.streamName,
      },
      statistic: 'Maximum',
      period: cdk.Duration.minutes(1),
    });

    // SQS metrics
    const sqsMessagesVisible = new cloudwatch.Metric({
      namespace: 'AWS/SQS',
      metricName: 'ApproximateNumberOfMessagesVisible',
      dimensionsMap: {
        QueueName: batchQueue.queueName,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(1),
    });

    const sqsOldestMessage = new cloudwatch.Metric({
      namespace: 'AWS/SQS',
      metricName: 'ApproximateAgeOfOldestMessage',
      dimensionsMap: {
        QueueName: batchQueue.queueName,
      },
      statistic: 'Maximum',
      period: cdk.Duration.minutes(1),
    });

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Kinesis Incoming Records',
        left: [kinesisIncomingRecords],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Kinesis Iterator Age (ms)',
        left: [kinesisIteratorAge],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'SQS Queue Depth',
        left: [sqsMessagesVisible],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'SQS Message Age (seconds)',
        left: [sqsOldestMessage],
        width: 6,
        height: 6,
      })
    );

    // ========================================================================
    // Custom Application Metrics
    // ========================================================================

    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: '## Application Metrics',
        width: 24,
        height: 1,
      })
    );

    // Custom metrics (these would be published by the application)
    const dealsFoundMetric = new cloudwatch.Metric({
      namespace: METRICS_NAMESPACE,
      metricName: 'DealsFound',
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    const snipesFoundMetric = new cloudwatch.Metric({
      namespace: METRICS_NAMESPACE,
      metricName: 'SnipesFound',
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    const valuationsComputedMetric = new cloudwatch.Metric({
      namespace: METRICS_NAMESPACE,
      metricName: 'ValuationsComputed',
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    const blocksProcessedMetric = new cloudwatch.Metric({
      namespace: METRICS_NAMESPACE,
      metricName: 'BlocksProcessed',
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    // Circuit breaker and ingestion health metrics
    const circuitBreakerOpenMetric = new cloudwatch.Metric({
      namespace: METRICS_NAMESPACE,
      metricName: 'CircuitBreakerOpen',
      statistic: 'Maximum',
      period: cdk.Duration.minutes(5),
    });

    const circuitBreakerFailuresMetric = new cloudwatch.Metric({
      namespace: METRICS_NAMESPACE,
      metricName: 'CircuitBreakerFailures',
      statistic: 'Maximum',
      period: cdk.Duration.minutes(5),
    });

    const ingestionErrorsMetric = new cloudwatch.Metric({
      namespace: METRICS_NAMESPACE,
      metricName: 'IngestionErrors',
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Deals & Snipes Found',
        left: [dealsFoundMetric, snipesFoundMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Valuations Computed',
        left: [valuationsComputedMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Blocks Processed',
        left: [blocksProcessedMetric],
        width: 6,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Circuit Breaker & Ingestion Health',
        left: [circuitBreakerOpenMetric, circuitBreakerFailuresMetric],
        right: [ingestionErrorsMetric],
        width: 6,
        height: 6,
      })
    );

    // ========================================================================
    // CloudWatch Alarms
    // ========================================================================

    if (config.monitoring.alarmEnabled) {
      // API 5xx Error Rate Alarm
      new cloudwatch.Alarm(this, 'Api5xxAlarm', {
        alarmName: getResourceName('api-5xx-alarm', config),
        alarmDescription: 'API 5xx errors exceed threshold',
        metric: api5xxMetric,
        threshold: 10,
        evaluationPeriods: 2,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
        actionsEnabled: true,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // Database CPU Alarm
      new cloudwatch.Alarm(this, 'DbCpuAlarm', {
        alarmName: getResourceName('db-cpu-alarm', config),
        alarmDescription: 'Database CPU exceeds 80%',
        metric: dbCpuMetric,
        threshold: 80,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // Redis Memory Alarm
      new cloudwatch.Alarm(this, 'RedisMemoryAlarm', {
        alarmName: getResourceName('redis-memory-alarm', config),
        alarmDescription: 'Redis memory usage exceeds 80%',
        metric: redisMemoryMetric,
        threshold: 80,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // Lambda Error Alarms
      for (const [name, fn] of Object.entries(lambdaFunctions)) {
        new cloudwatch.Alarm(this, `${name}ErrorAlarm`, {
          alarmName: getResourceName(`${name}-error-alarm`, config),
          alarmDescription: `${name} Lambda function errors`,
          metric: fn.metricErrors({ period: cdk.Duration.minutes(5) }),
          threshold: 5,
          evaluationPeriods: 2,
          datapointsToAlarm: 2,
          comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
          treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
        }).addAlarmAction({
          bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
        });
      }

      // Kinesis Iterator Age Alarm (processing lag)
      new cloudwatch.Alarm(this, 'KinesisLagAlarm', {
        alarmName: getResourceName('kinesis-lag-alarm', config),
        alarmDescription: 'Kinesis processing lag exceeds 5 minutes',
        metric: kinesisIteratorAge,
        threshold: 300000, // 5 minutes in milliseconds
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // SQS Queue Depth Alarm
      new cloudwatch.Alarm(this, 'SqsDepthAlarm', {
        alarmName: getResourceName('sqs-depth-alarm', config),
        alarmDescription: 'SQS queue depth exceeds 1000 messages',
        metric: sqsMessagesVisible,
        threshold: 1000,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // Circuit Breaker Open Alarm - triggers when external API circuit breaker opens
      const circuitBreakerOpenMetric = new cloudwatch.Metric({
        namespace: METRICS_NAMESPACE,
        metricName: 'CircuitBreakerOpen',
        statistic: 'Maximum',
        period: cdk.Duration.minutes(5),
      });

      new cloudwatch.Alarm(this, 'CircuitBreakerOpenAlarm', {
        alarmName: getResourceName('circuit-breaker-open-alarm', config),
        alarmDescription: 'Circuit breaker is open - external API (SkyMavis) may be failing',
        metric: circuitBreakerOpenMetric,
        threshold: 1,
        evaluationPeriods: 1,
        datapointsToAlarm: 1,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // Circuit Breaker High Failures Alarm - early warning before circuit opens
      const circuitBreakerFailuresMetric = new cloudwatch.Metric({
        namespace: METRICS_NAMESPACE,
        metricName: 'CircuitBreakerFailures',
        statistic: 'Maximum',
        period: cdk.Duration.minutes(5),
      });

      new cloudwatch.Alarm(this, 'CircuitBreakerHighFailuresAlarm', {
        alarmName: getResourceName('circuit-breaker-failures-alarm', config),
        alarmDescription: 'Circuit breaker failure count is high - API may be degraded',
        metric: circuitBreakerFailuresMetric,
        threshold: 3,
        evaluationPeriods: 2,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // Ingestion Errors Alarm - high error rate during data ingestion
      const ingestionErrorsMetric = new cloudwatch.Metric({
        namespace: METRICS_NAMESPACE,
        metricName: 'IngestionErrors',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      });

      new cloudwatch.Alarm(this, 'IngestionErrorsAlarm', {
        alarmName: getResourceName('ingestion-errors-alarm', config),
        alarmDescription: 'High error rate during data ingestion',
        metric: ingestionErrorsMetric,
        threshold: 10,
        evaluationPeriods: 2,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });

      // Data Pipeline Health Alarm - triggers when health check reports unhealthy
      const dataPipelineHealthMetric = new cloudwatch.Metric({
        namespace: METRICS_NAMESPACE,
        metricName: 'DataPipelineHealthy',
        statistic: 'Minimum',
        period: cdk.Duration.minutes(5),
      });

      new cloudwatch.Alarm(this, 'DataPipelineUnhealthyAlarm', {
        alarmName: getResourceName('data-pipeline-unhealthy-alarm', config),
        alarmDescription: 'Data pipeline is unhealthy - data freshness check failed',
        metric: dataPipelineHealthMetric,
        threshold: 1,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.BREACHING,  // Missing data = unhealthy
      }).addAlarmAction({
        bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
      });
    }

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'DashboardUrl', {
      value: `https://${config.region}.console.aws.amazon.com/cloudwatch/home?region=${config.region}#dashboards:name=${this.dashboard.dashboardName}`,
      description: 'CloudWatch Dashboard URL',
      exportName: `${id}-DashboardUrl`,
    });

    new cdk.CfnOutput(this, 'AlarmTopicArn', {
      value: this.alarmTopic.topicArn,
      description: 'Alarm SNS topic ARN',
      exportName: `${id}-AlarmTopicArn`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Observability');
  }
}

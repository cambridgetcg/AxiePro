/**
 * AxiePro Events Stack
 *
 * Creates event processing infrastructure:
 * - EventBridge for scheduled tasks and event routing
 * - Kinesis Data Streams for real-time event ingestion
 * - SQS queues for reliable message processing
 * - SNS topics for notifications
 * - WebSocket API for real-time client updates
 */

import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as kinesis from 'aws-cdk-lib/aws-kinesis';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';

export interface EventsStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  kmsKey: kms.IKey;
}

export class EventsStack extends cdk.Stack {
  // EventBridge
  public readonly eventBus: events.IEventBus;

  // Kinesis
  public readonly listingsStream: kinesis.IStream;

  // SQS Queues
  public readonly batchProcessingQueue: sqs.IQueue;
  public readonly valuationQueue: sqs.IQueue;
  public readonly notificationQueue: sqs.IQueue;

  // SNS Topics
  public readonly dealAlertsTopic: sns.ITopic;
  public readonly metaInsightsTopic: sns.ITopic;
  public readonly systemAlertsTopic: sns.ITopic;

  // WebSocket API
  public readonly webSocketApi: apigatewayv2.CfnApi | undefined;
  public readonly webSocketStage: apigatewayv2.CfnStage | undefined;

  constructor(scope: Construct, id: string, props: EventsStackProps) {
    super(scope, id, props);

    const { config, kmsKey } = props;

    // ========================================================================
    // EventBridge Event Bus
    // ========================================================================

    this.eventBus = new events.EventBus(this, 'EventBus', {
      eventBusName: getResourceName('events', config),
    });

    // Archive events for replay capability (production only)
    if (config.name === 'production') {
      new events.Archive(this, 'EventArchive', {
        sourceEventBus: this.eventBus,
        archiveName: getResourceName('event-archive', config),
        description: 'Archive of all AxiePro events',
        retention: cdk.Duration.days(90),
        eventPattern: {
          source: [{ prefix: 'axiepro' }] as any,
        },
      });
    }

    // ========================================================================
    // Kinesis Data Stream
    // ========================================================================

    this.listingsStream = new kinesis.Stream(this, 'ListingsStream', {
      streamName: getResourceName('listings-stream', config),
      shardCount: config.kinesis.shardCount,
      retentionPeriod: cdk.Duration.hours(config.kinesis.retentionHours),
      encryption: kinesis.StreamEncryption.KMS,
      encryptionKey: kmsKey,
      streamMode: kinesis.StreamMode.PROVISIONED,
    });

    // ========================================================================
    // SQS Queues
    // ========================================================================

    // Dead letter queue for failed messages
    const deadLetterQueue = new sqs.Queue(this, 'DeadLetterQueue', {
      queueName: getResourceName('dlq', config),
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: kmsKey,
      retentionPeriod: cdk.Duration.days(14),
      removalPolicy: config.removalPolicy,
    });

    // Batch processing queue - for blockchain data fetching jobs
    this.batchProcessingQueue = new sqs.Queue(this, 'BatchProcessingQueue', {
      queueName: getResourceName('batch-processing', config),
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: kmsKey,
      visibilityTimeout: cdk.Duration.minutes(15), // Long timeout for batch jobs
      receiveMessageWaitTime: cdk.Duration.seconds(20), // Long polling
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: 3,
      },
      removalPolicy: config.removalPolicy,
    });

    // Valuation queue - for computing Axie valuations
    this.valuationQueue = new sqs.Queue(this, 'ValuationQueue', {
      queueName: getResourceName('valuation', config),
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: kmsKey,
      visibilityTimeout: cdk.Duration.seconds(60),
      receiveMessageWaitTime: cdk.Duration.seconds(10),
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: 3,
      },
      removalPolicy: config.removalPolicy,
    });

    // Notification queue - for sending alerts
    this.notificationQueue = new sqs.Queue(this, 'NotificationQueue', {
      queueName: getResourceName('notifications', config),
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: kmsKey,
      visibilityTimeout: cdk.Duration.seconds(30),
      receiveMessageWaitTime: cdk.Duration.seconds(5),
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: 5,
      },
      removalPolicy: config.removalPolicy,
    });

    // ========================================================================
    // SNS Topics
    // ========================================================================

    // Deal alerts topic - for notifying users about deals
    this.dealAlertsTopic = new sns.Topic(this, 'DealAlertsTopic', {
      topicName: getResourceName('deal-alerts', config),
      displayName: 'AxiePro Deal Alerts',
      masterKey: kmsKey,
    });

    // Meta insights topic - for market analysis updates
    this.metaInsightsTopic = new sns.Topic(this, 'MetaInsightsTopic', {
      topicName: getResourceName('meta-insights', config),
      displayName: 'AxiePro Meta Insights',
      masterKey: kmsKey,
    });

    // System alerts topic - for operational alerts
    this.systemAlertsTopic = new sns.Topic(this, 'SystemAlertsTopic', {
      topicName: getResourceName('system-alerts', config),
      displayName: 'AxiePro System Alerts',
      masterKey: kmsKey,
    });

    // ========================================================================
    // WebSocket API (for real-time updates)
    // ========================================================================

    if (config.features.enableWebSocket) {
      // Create WebSocket API
      this.webSocketApi = new apigatewayv2.CfnApi(this, 'WebSocketApi', {
        name: getResourceName('websocket-api', config),
        protocolType: 'WEBSOCKET',
        routeSelectionExpression: '$request.body.action',
        description: 'AxiePro WebSocket API for real-time updates',
      });

      // Create CloudWatch log group for WebSocket API
      const wsLogGroup = new logs.LogGroup(this, 'WebSocketApiLogs', {
        logGroupName: `/aws/apigateway/${getResourceName('websocket-api', config)}`,
        retention: config.monitoring.logRetentionDays,
        removalPolicy: config.removalPolicy,
      });

      // Create stage
      this.webSocketStage = new apigatewayv2.CfnStage(this, 'WebSocketStage', {
        apiId: this.webSocketApi.ref,
        stageName: config.shortName,
        autoDeploy: true,
        defaultRouteSettings: {
          loggingLevel: config.name === 'development' ? 'INFO' : 'ERROR',
          throttlingBurstLimit: 500,
          throttlingRateLimit: 100,
        },
        accessLogSettings: {
          destinationArn: wsLogGroup.logGroupArn,
          format: JSON.stringify({
            requestId: '$context.requestId',
            ip: '$context.identity.sourceIp',
            caller: '$context.identity.caller',
            user: '$context.identity.user',
            requestTime: '$context.requestTime',
            eventType: '$context.eventType',
            routeKey: '$context.routeKey',
            status: '$context.status',
            connectionId: '$context.connectionId',
          }),
        },
      });
    }

    // ========================================================================
    // EventBridge Rules
    // ========================================================================
    // Note: Scheduled rules are created in the Compute stack where Lambda
    // functions are defined, as scheduled rules must use the default event bus
    // and need targets to be useful.

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'EventBusName', {
      value: this.eventBus.eventBusName,
      description: 'EventBridge event bus name',
      exportName: `${id}-EventBusName`,
    });

    new cdk.CfnOutput(this, 'EventBusArn', {
      value: this.eventBus.eventBusArn,
      description: 'EventBridge event bus ARN',
      exportName: `${id}-EventBusArn`,
    });

    new cdk.CfnOutput(this, 'ListingsStreamName', {
      value: this.listingsStream.streamName,
      description: 'Kinesis listings stream name',
      exportName: `${id}-ListingsStreamName`,
    });

    new cdk.CfnOutput(this, 'ListingsStreamArn', {
      value: this.listingsStream.streamArn,
      description: 'Kinesis listings stream ARN',
      exportName: `${id}-ListingsStreamArn`,
    });

    new cdk.CfnOutput(this, 'BatchProcessingQueueUrl', {
      value: this.batchProcessingQueue.queueUrl,
      description: 'Batch processing queue URL',
      exportName: `${id}-BatchQueueUrl`,
    });

    new cdk.CfnOutput(this, 'ValuationQueueUrl', {
      value: this.valuationQueue.queueUrl,
      description: 'Valuation queue URL',
      exportName: `${id}-ValuationQueueUrl`,
    });

    new cdk.CfnOutput(this, 'DealAlertsTopicArn', {
      value: this.dealAlertsTopic.topicArn,
      description: 'Deal alerts SNS topic ARN',
      exportName: `${id}-DealAlertsTopicArn`,
    });

    new cdk.CfnOutput(this, 'SystemAlertsTopicArn', {
      value: this.systemAlertsTopic.topicArn,
      description: 'System alerts SNS topic ARN',
      exportName: `${id}-SystemAlertsTopicArn`,
    });

    if (this.webSocketApi) {
      new cdk.CfnOutput(this, 'WebSocketApiEndpoint', {
        value: `wss://${this.webSocketApi.ref}.execute-api.${config.region}.amazonaws.com/${config.shortName}`,
        description: 'WebSocket API endpoint',
        exportName: `${id}-WebSocketApiEndpoint`,
      });
    }

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Events');
  }
}

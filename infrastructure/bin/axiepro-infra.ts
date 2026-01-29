#!/usr/bin/env node
/**
 * AxiePro Infrastructure CDK Application
 *
 * Entry point for the AWS CDK application that provisions all infrastructure
 * for the AxiePro Axie Infinity analytics platform.
 *
 * Usage:
 *   npx cdk deploy --all -c environment=development
 *   npx cdk deploy --all -c environment=staging
 *   npx cdk deploy --all -c environment=production
 */

import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { getEnvironmentConfig, EnvironmentConfig } from '../lib/config/environments';

// Import all stacks
import { NetworkingStack } from '../lib/stacks/networking-stack';
import { SecurityStack } from '../lib/stacks/security-stack';
import { DatabaseStack } from '../lib/stacks/database-stack';
import { CacheStack } from '../lib/stacks/cache-stack';
import { StorageStack } from '../lib/stacks/storage-stack';
import { EventsStack } from '../lib/stacks/events-stack';
import { ComputeStack } from '../lib/stacks/compute-stack';
import { ApiStack } from '../lib/stacks/api-stack';
import { ObservabilityStack } from '../lib/stacks/observability-stack';
import { CiCdStack } from '../lib/stacks/cicd-stack';

// Create the CDK app
const app = new cdk.App();

// Get environment from context (default to development)
const environmentName = app.node.tryGetContext('environment') || 'development';
const config: EnvironmentConfig = getEnvironmentConfig(environmentName);

console.log(`\n🚀 Deploying AxiePro Infrastructure for environment: ${config.name}\n`);

// Common stack props
const commonProps: cdk.StackProps = {
  env: {
    account: config.account,
    region: config.region,
  },
  tags: {
    Application: 'axiepro',
    Environment: config.name,
    ManagedBy: 'CDK',
  },
};

// Stack name helper
const stackName = (name: string) => `AxiePro-${name}-${config.shortName}`;

/**
 * Stack Dependency Graph:
 *
 *                    ┌─────────────────┐
 *                    │   Networking    │
 *                    └────────┬────────┘
 *                             │
 *              ┌──────────────┼──────────────┐
 *              │              │              │
 *              ▼              ▼              ▼
 *        ┌──────────┐  ┌──────────┐  ┌──────────┐
 *        │ Security │  │ Database │  │  Cache   │
 *        └────┬─────┘  └────┬─────┘  └────┬─────┘
 *             │             │             │
 *             └──────────┬──┴─────────────┘
 *                        │
 *              ┌─────────┴─────────┐
 *              │                   │
 *              ▼                   ▼
 *        ┌──────────┐        ┌──────────┐
 *        │ Storage  │        │  Events  │
 *        └────┬─────┘        └────┬─────┘
 *             │                   │
 *             └─────────┬─────────┘
 *                       │
 *                       ▼
 *                ┌──────────┐
 *                │ Compute  │
 *                └────┬─────┘
 *                     │
 *                     ▼
 *                ┌──────────┐
 *                │   API    │
 *                └────┬─────┘
 *                     │
 *          ┌──────────┴──────────┐
 *          │                     │
 *          ▼                     ▼
 *    ┌─────────────┐      ┌──────────┐
 *    │Observability│      │  CI/CD   │
 *    └─────────────┘      └──────────┘
 */

// 1. Networking Stack - Foundation for all resources
const networkingStack = new NetworkingStack(app, stackName('Networking'), {
  ...commonProps,
  config,
  description: 'AxiePro VPC, subnets, security groups, and network configuration',
});

// 2. Security Stack - KMS, Secrets Manager, IAM roles
const securityStack = new SecurityStack(app, stackName('Security'), {
  ...commonProps,
  config,
  vpc: networkingStack.vpc,
  description: 'AxiePro security resources: KMS keys, secrets, and IAM roles',
});
securityStack.addDependency(networkingStack);

// 3. Database Stack - Aurora Serverless v2, DynamoDB
const databaseStack = new DatabaseStack(app, stackName('Database'), {
  ...commonProps,
  config,
  vpc: networkingStack.vpc,
  databaseSecurityGroup: networkingStack.databaseSecurityGroup,
  kmsKey: securityStack.dataKey,
  description: 'AxiePro database resources: Aurora PostgreSQL and DynamoDB',
});
databaseStack.addDependency(networkingStack);
databaseStack.addDependency(securityStack);

// 4. Cache Stack - ElastiCache Redis
const cacheStack = new CacheStack(app, stackName('Cache'), {
  ...commonProps,
  config,
  vpc: networkingStack.vpc,
  cacheSecurityGroup: networkingStack.cacheSecurityGroup,
  kmsKey: securityStack.dataKey,
  description: 'AxiePro caching layer: ElastiCache Redis cluster',
});
cacheStack.addDependency(networkingStack);
cacheStack.addDependency(securityStack);

// 5. Storage Stack - S3 buckets
const storageStack = new StorageStack(app, stackName('Storage'), {
  ...commonProps,
  config,
  kmsKey: securityStack.dataKey,
  description: 'AxiePro storage resources: S3 buckets for data lake and artifacts',
});
storageStack.addDependency(securityStack);

// 6. Events Stack - EventBridge, Kinesis, SQS, SNS
const eventsStack = new EventsStack(app, stackName('Events'), {
  ...commonProps,
  config,
  kmsKey: securityStack.dataKey,
  description: 'AxiePro event processing: EventBridge, Kinesis, SQS, and SNS',
});
eventsStack.addDependency(securityStack);

// 7. Compute Stack - App Runner, ECS Fargate, Lambda
const computeStack = new ComputeStack(app, stackName('Compute'), {
  ...commonProps,
  config,
  vpc: networkingStack.vpc,
  computeSecurityGroup: networkingStack.computeSecurityGroup,
  lambdaSecurityGroup: networkingStack.lambdaSecurityGroup,
  databaseCluster: databaseStack.cluster,
  redisEndpoint: cacheStack.redisEndpoint,
  redisPort: cacheStack.redisPort,
  secretsArn: securityStack.apiSecretsArn,
  databaseSecretsArn: securityStack.databaseSecret.secretArn,
  kmsKey: securityStack.dataKey,
  secretsKey: securityStack.secretsKey,
  dataBucket: storageStack.dataBucket,
  listingsStream: eventsStack.listingsStream,
  dealAlertsTopic: eventsStack.dealAlertsTopic,
  batchQueue: eventsStack.batchProcessingQueue,
  deadLetterQueue: eventsStack.deadLetterQueue,  // DLQ for failed Lambda invocations
  ecrRepository: storageStack.ecrRepository,
  parameterPrefix: securityStack.parameterPrefix,  // SSM Parameter Store prefix
  // IAM roles from Security stack
  appRunnerInstanceRole: securityStack.appRunnerInstanceRole,
  appRunnerAccessRole: securityStack.appRunnerAccessRole,
  ecsTaskRole: securityStack.ecsTaskRole,
  description: 'AxiePro compute resources: App Runner, ECS Fargate, and Lambda',
});
computeStack.addDependency(networkingStack);
computeStack.addDependency(securityStack);
computeStack.addDependency(databaseStack);
computeStack.addDependency(cacheStack);
computeStack.addDependency(storageStack);
computeStack.addDependency(eventsStack);

// 8. API Stack - API Gateway, CloudFront, WAF
const apiStack = new ApiStack(app, stackName('API'), {
  ...commonProps,
  config,
  appRunnerServiceUrl: computeStack.appRunnerServiceUrl,
  webSocketApi: eventsStack.webSocketApi,
  description: 'AxiePro API layer: API Gateway, CloudFront CDN, and WAF',
});
apiStack.addDependency(computeStack);
apiStack.addDependency(eventsStack);

// 9. Observability Stack - CloudWatch dashboards, alarms, X-Ray
const observabilityStack = new ObservabilityStack(app, stackName('Observability'), {
  ...commonProps,
  config,
  databaseCluster: databaseStack.cluster,
  redisReplicationGroup: cacheStack.replicationGroup,
  appRunnerServiceArn: computeStack.appRunnerServiceArn,
  lambdaFunctions: computeStack.lambdaFunctions,
  apiGateway: apiStack.httpApi,
  listingsStream: eventsStack.listingsStream,
  batchQueue: eventsStack.batchProcessingQueue,
  dealAlertsTopic: eventsStack.dealAlertsTopic,
  description: 'AxiePro observability: CloudWatch dashboards, alarms, and X-Ray tracing',
});
observabilityStack.addDependency(databaseStack);
observabilityStack.addDependency(cacheStack);
observabilityStack.addDependency(computeStack);
observabilityStack.addDependency(apiStack);
observabilityStack.addDependency(eventsStack);

// 10. CI/CD Stack - CodePipeline, CodeBuild (only for staging/production)
if (config.features.enableCiCd) {
  const cicdStack = new CiCdStack(app, stackName('CICD'), {
    ...commonProps,
    config,
    ecrRepository: storageStack.ecrRepository,
    appRunnerServiceArn: computeStack.appRunnerServiceArn,
    artifactBucket: storageStack.artifactBucket,
    description: 'AxiePro CI/CD pipeline: CodePipeline and CodeBuild',
  });
  cicdStack.addDependency(storageStack);
  cicdStack.addDependency(computeStack);
}

// Output summary
console.log(`
📋 Stack Summary for ${config.name}:
   ├── Networking: VPC with ${config.vpc.maxAzs} AZs, ${config.vpc.natGateways} NAT Gateway(s)
   ├── Database: Aurora Serverless v2 (${config.database.minCapacity}-${config.database.maxCapacity} ACUs)
   ├── Cache: ElastiCache Redis (${config.cache.nodeType}, ${config.cache.numReplicas} replicas)
   ├── Compute: App Runner (${config.compute.appRunner.minInstances}-${config.compute.appRunner.maxInstances} instances)
   ├── API: ${config.features.enableApiGateway ? 'API Gateway' : 'Direct'} + ${config.features.enableCloudFront ? 'CloudFront' : 'No CDN'}
   ├── WAF: ${config.features.enableWaf ? 'Enabled' : 'Disabled'}
   └── CI/CD: ${config.features.enableCiCd ? 'Enabled' : 'Disabled'}
`);

app.synth();

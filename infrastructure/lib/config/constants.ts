/**
 * AxiePro Infrastructure Constants
 *
 * Central location for all infrastructure constants and naming conventions.
 * These values are used across all stacks to ensure consistency.
 */

export const APP_NAME = 'axiepro';
export const APP_DESCRIPTION = 'Axie Infinity Analytics & Trading Platform';

// AWS Account and Region Configuration
export const AWS_ACCOUNT = process.env.CDK_DEFAULT_ACCOUNT || '034362054546';
export const AWS_REGION = process.env.CDK_DEFAULT_REGION || 'us-east-1';

// Resource Naming Conventions
export const RESOURCE_PREFIX = 'axiepro';

// Network Configuration
export const VPC_CIDR = '10.0.0.0/16';
export const MAX_AZS = 2;

// Database Configuration
export const DB_NAME = 'axiepro';
export const DB_SCHEMA = 'axie';
export const DB_PORT = 5432;

// Cache Configuration
export const REDIS_PORT = 6379;
export const REDIS_NODE_TYPE = 'cache.r6g.large';

// Compute Configuration
export const APPRUNNER_CPU = 1024; // 1 vCPU
export const APPRUNNER_MEMORY = 2048; // 2 GB
export const APPRUNNER_MIN_INSTANCES = 1;
export const APPRUNNER_MAX_INSTANCES = 10;

// ECS Fargate Configuration
export const FARGATE_CPU = 1024; // 1 vCPU
export const FARGATE_MEMORY = 2048; // 2 GB
export const FARGATE_SPOT_WEIGHT = 4; // Prefer spot instances 4:1

// Lambda Configuration
export const LAMBDA_MEMORY = 512; // MB
export const LAMBDA_TIMEOUT = 60; // seconds
export const LAMBDA_RUNTIME = 'python3.11';

// Kinesis Configuration
export const KINESIS_SHARD_COUNT = 1;
export const KINESIS_RETENTION_HOURS = 24;

// S3 Configuration
export const S3_LIFECYCLE_TRANSITION_DAYS = 30; // Move to IA
export const S3_LIFECYCLE_EXPIRATION_DAYS = 365; // Delete after 1 year

// API Gateway Configuration
export const API_THROTTLE_RATE = 1000; // requests per second
export const API_THROTTLE_BURST = 2000; // burst capacity

// CloudWatch Configuration
export const LOG_RETENTION_DAYS = 30;
export const METRICS_NAMESPACE = 'AxiePro';

// Tags applied to all resources
export const DEFAULT_TAGS: Record<string, string> = {
  Application: APP_NAME,
  ManagedBy: 'CDK',
  Environment: 'production', // Will be overridden per environment
};

// Domain Configuration (update these with your actual domain)
export const DOMAIN_NAME = 'axiepro.io';
export const API_SUBDOMAIN = 'api';
export const APP_SUBDOMAIN = 'app';

// External API Endpoints (for reference)
export const EXTERNAL_APIS = {
  SKYMAVIS_GRAPHQL: 'https://graphql-gateway.axieinfinity.com/graphql',
  RONIN_RPC: 'https://api.roninchain.com/rpc',
  MORALIS_API: 'https://deep-index.moralis.io/api/v2',
} as const;

// Marketplace Contract Addresses
export const CONTRACTS = {
  AXIE_MARKETPLACE: '0x213073989821f738a7ba3520c3d31a1f9ad31bbd',
  AXIE_NFT: '0x32950db2a7164ae833121501c797d79e7b79d74c',
} as const;

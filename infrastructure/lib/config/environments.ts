/**
 * AxiePro Environment Configuration
 *
 * Defines environment-specific settings for development, staging, and production.
 * Each environment has its own resource sizing, retention policies, and feature flags.
 */

import { Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as constants from './constants';

export type EnvironmentName = 'development' | 'staging' | 'production';

export interface EnvironmentConfig {
  // Environment identification
  name: EnvironmentName;
  shortName: string; // dev, stg, prod

  // AWS Account Configuration
  account: string;
  region: string;

  // Resource removal behavior
  removalPolicy: RemovalPolicy;
  autoDeleteObjects: boolean;

  // VPC Configuration
  vpc: {
    cidr: string;
    maxAzs: number;
    natGateways: number;
  };

  // Database Configuration
  database: {
    minCapacity: number; // ACUs for Aurora Serverless v2
    maxCapacity: number;
    enableMultiAz: boolean;
    backupRetention: Duration;
    deletionProtection: boolean;
  };

  // Cache Configuration
  cache: {
    nodeType: string;
    numReplicas: number;
    automaticFailover: boolean;
  };

  // Compute Configuration
  compute: {
    appRunner: {
      cpu: number;
      memory: number;
      minInstances: number;
      maxInstances: number;
    };
    fargate: {
      cpu: number;
      memory: number;
      minTasks: number;
      maxTasks: number;
      spotCapacityPercent: number;
    };
    lambda: {
      memorySize: number;
      timeout: Duration;
      reservedConcurrency?: number;
    };
  };

  // API Configuration
  api: {
    throttleRate: number;
    throttleBurst: number;
    cacheEnabled: boolean;
    cacheTtl: Duration;
  };

  // Kinesis Configuration
  kinesis: {
    shardCount: number;
    retentionHours: number;
  };

  // Monitoring Configuration
  monitoring: {
    logRetentionDays: number;
    enableXRay: boolean;
    enableDetailedMetrics: boolean;
    alarmEnabled: boolean;
  };

  // Feature Flags
  features: {
    enableWaf: boolean;
    enableCloudFront: boolean;
    enableApiGateway: boolean;
    enableWebSocket: boolean;
    enableCiCd: boolean;
    enableAppRunner: boolean; // Set to false until Docker image is pushed to ECR
  };

  // Cost optimization
  costOptimization: {
    enableSpotInstances: boolean;
    enableScheduledScaling: boolean;
    enableS3IntelligentTiering: boolean;
  };

  // Domain configuration
  domain?: {
    zoneName: string;
    certificateArn?: string;
  };
}

/**
 * Development Environment
 * - Minimal resources for cost savings
 * - Fast iteration with no deletion protection
 * - Single AZ deployment
 */
const developmentConfig: EnvironmentConfig = {
  name: 'development',
  shortName: 'dev',
  account: constants.AWS_ACCOUNT,
  region: constants.AWS_REGION,

  removalPolicy: RemovalPolicy.DESTROY,
  autoDeleteObjects: true,

  vpc: {
    cidr: '10.0.0.0/16',
    maxAzs: 2,
    natGateways: 1, // Single NAT for cost savings
  },

  database: {
    minCapacity: 0.5,
    maxCapacity: 2,
    enableMultiAz: false,
    backupRetention: Duration.days(1),
    deletionProtection: false,
  },

  cache: {
    nodeType: 'cache.t3.micro',
    numReplicas: 0,
    automaticFailover: false,
  },

  compute: {
    appRunner: {
      cpu: 512,
      memory: 1024,
      minInstances: 1,
      maxInstances: 2,
    },
    fargate: {
      cpu: 512,
      memory: 1024,
      minTasks: 0,
      maxTasks: 2,
      spotCapacityPercent: 100,
    },
    lambda: {
      memorySize: 256,
      timeout: Duration.seconds(30),
    },
  },

  api: {
    throttleRate: 100,
    throttleBurst: 200,
    cacheEnabled: false,
    cacheTtl: Duration.minutes(0),
  },

  kinesis: {
    shardCount: 1,
    retentionHours: 24,
  },

  monitoring: {
    logRetentionDays: 7,
    enableXRay: false,
    enableDetailedMetrics: false,
    alarmEnabled: false,
  },

  features: {
    enableWaf: false,
    enableCloudFront: false,
    enableApiGateway: true,
    enableWebSocket: false,
    enableCiCd: false,
    enableAppRunner: true, // Docker image exists in ECR
  },

  costOptimization: {
    enableSpotInstances: true,
    enableScheduledScaling: false,
    enableS3IntelligentTiering: false,
  },
};

/**
 * Staging Environment
 * - Production-like configuration at smaller scale
 * - Some protection enabled
 * - Multi-AZ with reduced replicas
 */
const stagingConfig: EnvironmentConfig = {
  name: 'staging',
  shortName: 'stg',
  account: constants.AWS_ACCOUNT,
  region: constants.AWS_REGION,

  removalPolicy: RemovalPolicy.SNAPSHOT,
  autoDeleteObjects: false,

  vpc: {
    cidr: '10.1.0.0/16',
    maxAzs: 2,
    natGateways: 1,
  },

  database: {
    minCapacity: 0.5,
    maxCapacity: 4,
    enableMultiAz: true,
    backupRetention: Duration.days(7),
    deletionProtection: false,
  },

  cache: {
    nodeType: 'cache.t3.small',
    numReplicas: 1,
    automaticFailover: true,
  },

  compute: {
    appRunner: {
      cpu: 1024,
      memory: 2048,
      minInstances: 1,
      maxInstances: 4,
    },
    fargate: {
      cpu: 1024,
      memory: 2048,
      minTasks: 0,
      maxTasks: 4,
      spotCapacityPercent: 80,
    },
    lambda: {
      memorySize: 512,
      timeout: Duration.seconds(60),
    },
  },

  api: {
    throttleRate: 500,
    throttleBurst: 1000,
    cacheEnabled: true,
    cacheTtl: Duration.minutes(1),
  },

  kinesis: {
    shardCount: 1,
    retentionHours: 24,
  },

  monitoring: {
    logRetentionDays: 14,
    enableXRay: true,
    enableDetailedMetrics: true,
    alarmEnabled: true,
  },

  features: {
    enableWaf: true,
    enableCloudFront: true,
    enableApiGateway: true,
    enableWebSocket: true,
    enableCiCd: true,
    enableAppRunner: true,
  },

  costOptimization: {
    enableSpotInstances: true,
    enableScheduledScaling: true,
    enableS3IntelligentTiering: true,
  },
};

/**
 * Production Environment
 * - Full redundancy and high availability
 * - Deletion protection enabled
 * - Multi-AZ with full replicas
 * - All features enabled
 */
const productionConfig: EnvironmentConfig = {
  name: 'production',
  shortName: 'prod',
  account: constants.AWS_ACCOUNT,
  region: constants.AWS_REGION,

  removalPolicy: RemovalPolicy.RETAIN,
  autoDeleteObjects: false,

  vpc: {
    cidr: '10.2.0.0/16',
    maxAzs: 2,
    natGateways: 2, // One per AZ for HA
  },

  database: {
    minCapacity: 0.5,
    maxCapacity: 16,
    enableMultiAz: true,
    backupRetention: Duration.days(30),
    deletionProtection: true,
  },

  cache: {
    nodeType: 'cache.r6g.large',
    numReplicas: 1,
    automaticFailover: true,
  },

  compute: {
    appRunner: {
      cpu: 1024,
      memory: 2048,
      minInstances: 1,
      maxInstances: 10,
    },
    fargate: {
      cpu: 1024,
      memory: 2048,
      minTasks: 1,
      maxTasks: 10,
      spotCapacityPercent: 70,
    },
    lambda: {
      memorySize: 512,
      timeout: Duration.seconds(60),
      reservedConcurrency: 100,
    },
  },

  api: {
    throttleRate: 1000,
    throttleBurst: 2000,
    cacheEnabled: true,
    cacheTtl: Duration.minutes(1),
  },

  kinesis: {
    shardCount: 2,
    retentionHours: 48,
  },

  monitoring: {
    logRetentionDays: 30,
    enableXRay: true,
    enableDetailedMetrics: true,
    alarmEnabled: true,
  },

  features: {
    enableWaf: true,
    enableCloudFront: true,
    enableApiGateway: true,
    enableWebSocket: true,
    enableCiCd: true,
    enableAppRunner: true,
  },

  costOptimization: {
    enableSpotInstances: true,
    enableScheduledScaling: true,
    enableS3IntelligentTiering: true,
  },

  domain: {
    zoneName: constants.DOMAIN_NAME,
    // certificateArn will be created by the stack
  },
};

// Environment configuration map
const environments: Record<EnvironmentName, EnvironmentConfig> = {
  development: developmentConfig,
  staging: stagingConfig,
  production: productionConfig,
};

/**
 * Get environment configuration
 * @param envName - Environment name (development, staging, production)
 * @returns Environment configuration object
 */
export function getEnvironmentConfig(envName: string): EnvironmentConfig {
  const env = envName as EnvironmentName;
  if (!environments[env]) {
    throw new Error(
      `Unknown environment: ${envName}. Valid environments are: ${Object.keys(environments).join(', ')}`
    );
  }
  return environments[env];
}

/**
 * Get resource name with environment prefix
 * @param baseName - Base resource name
 * @param config - Environment configuration
 * @returns Prefixed resource name
 */
export function getResourceName(baseName: string, config: EnvironmentConfig): string {
  return `${constants.RESOURCE_PREFIX}-${baseName}-${config.shortName}`;
}

/**
 * Get tags for a resource
 * @param config - Environment configuration
 * @param additionalTags - Additional tags to apply
 * @returns Combined tags object
 */
export function getResourceTags(
  config: EnvironmentConfig,
  additionalTags: Record<string, string> = {}
): Record<string, string> {
  return {
    ...constants.DEFAULT_TAGS,
    Environment: config.name,
    ...additionalTags,
  };
}

export default environments;

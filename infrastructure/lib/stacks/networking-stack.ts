/**
 * AxiePro Networking Stack
 *
 * Creates the foundational network infrastructure:
 * - VPC with public and private subnets across multiple AZs
 * - NAT Gateways for private subnet internet access
 * - Security groups for database, cache, and compute resources
 * - VPC Endpoints for AWS service access without internet
 * - Network ACLs for subnet-level security
 */

import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';
import { REDIS_PORT, DB_PORT } from '../config/constants';

export interface NetworkingStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
}

export class NetworkingStack extends cdk.Stack {
  // Exported resources for other stacks
  public readonly vpc: ec2.IVpc;
  public readonly databaseSecurityGroup: ec2.ISecurityGroup;
  public readonly cacheSecurityGroup: ec2.ISecurityGroup;
  public readonly computeSecurityGroup: ec2.ISecurityGroup;
  public readonly lambdaSecurityGroup: ec2.ISecurityGroup;
  public readonly vpcEndpointSecurityGroup: ec2.ISecurityGroup;

  constructor(scope: Construct, id: string, props: NetworkingStackProps) {
    super(scope, id, props);

    const { config } = props;

    // ========================================================================
    // VPC Configuration
    // ========================================================================

    this.vpc = new ec2.Vpc(this, 'VPC', {
      vpcName: getResourceName('vpc', config),
      ipAddresses: ec2.IpAddresses.cidr(config.vpc.cidr),
      maxAzs: config.vpc.maxAzs,
      natGateways: config.vpc.natGateways,

      // Subnet configuration
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
          mapPublicIpOnLaunch: false, // Security: don't auto-assign public IPs
        },
        {
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
        {
          name: 'Isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 24,
        },
      ],

      // Enable DNS support
      enableDnsHostnames: true,
      enableDnsSupport: true,

      // Flow logs for network monitoring
      flowLogs: {
        cloudwatch: {
          destination: ec2.FlowLogDestination.toCloudWatchLogs(),
          trafficType: ec2.FlowLogTrafficType.ALL,
        },
      },
    });

    // ========================================================================
    // Security Groups
    // ========================================================================

    // VPC Endpoint Security Group
    this.vpcEndpointSecurityGroup = new ec2.SecurityGroup(this, 'VpcEndpointSG', {
      vpc: this.vpc,
      securityGroupName: getResourceName('vpc-endpoint-sg', config),
      description: 'Security group for VPC endpoints',
      allowAllOutbound: false,
    });

    // Database Security Group (Aurora PostgreSQL)
    this.databaseSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSG', {
      vpc: this.vpc,
      securityGroupName: getResourceName('database-sg', config),
      description: 'Security group for Aurora PostgreSQL database',
      allowAllOutbound: false,
    });

    // Cache Security Group (ElastiCache Redis)
    this.cacheSecurityGroup = new ec2.SecurityGroup(this, 'CacheSG', {
      vpc: this.vpc,
      securityGroupName: getResourceName('cache-sg', config),
      description: 'Security group for ElastiCache Redis',
      allowAllOutbound: false,
    });

    // Compute Security Group (App Runner, ECS)
    this.computeSecurityGroup = new ec2.SecurityGroup(this, 'ComputeSG', {
      vpc: this.vpc,
      securityGroupName: getResourceName('compute-sg', config),
      description: 'Security group for compute resources (App Runner, ECS)',
      allowAllOutbound: true, // Needs internet access for external APIs
    });

    // Lambda Security Group
    this.lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSG', {
      vpc: this.vpc,
      securityGroupName: getResourceName('lambda-sg', config),
      description: 'Security group for Lambda functions',
      allowAllOutbound: true, // Needs internet for external APIs
    });

    // ========================================================================
    // Security Group Rules
    // ========================================================================

    // VPC Endpoints accept HTTPS from within VPC
    this.vpcEndpointSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(config.vpc.cidr),
      ec2.Port.tcp(443),
      'Allow HTTPS from VPC'
    );

    // Database accepts connections from compute and lambda
    this.databaseSecurityGroup.addIngressRule(
      this.computeSecurityGroup,
      ec2.Port.tcp(DB_PORT),
      'Allow PostgreSQL from compute'
    );
    this.databaseSecurityGroup.addIngressRule(
      this.lambdaSecurityGroup,
      ec2.Port.tcp(DB_PORT),
      'Allow PostgreSQL from Lambda'
    );

    // Cache accepts connections from compute and lambda
    this.cacheSecurityGroup.addIngressRule(
      this.computeSecurityGroup,
      ec2.Port.tcp(REDIS_PORT),
      'Allow Redis from compute'
    );
    this.cacheSecurityGroup.addIngressRule(
      this.lambdaSecurityGroup,
      ec2.Port.tcp(REDIS_PORT),
      'Allow Redis from Lambda'
    );

    // ========================================================================
    // VPC Endpoints (PrivateLink)
    // ========================================================================
    // These allow private access to AWS services without going through NAT

    // S3 Gateway Endpoint (free)
    this.vpc.addGatewayEndpoint('S3Endpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
      subnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
    });

    // DynamoDB Gateway Endpoint (free)
    this.vpc.addGatewayEndpoint('DynamoDBEndpoint', {
      service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
      subnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
    });

    // Interface Endpoints (cost per hour + data transfer)
    // Only create in staging/production to save costs in development
    if (config.name !== 'development') {
      // Secrets Manager Endpoint
      this.vpc.addInterfaceEndpoint('SecretsManagerEndpoint', {
        service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [this.vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });

      // CloudWatch Logs Endpoint
      this.vpc.addInterfaceEndpoint('CloudWatchLogsEndpoint', {
        service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [this.vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });

      // ECR Endpoints (for pulling container images)
      this.vpc.addInterfaceEndpoint('EcrApiEndpoint', {
        service: ec2.InterfaceVpcEndpointAwsService.ECR,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [this.vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });

      this.vpc.addInterfaceEndpoint('EcrDkrEndpoint', {
        service: ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [this.vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });

      // SQS Endpoint
      this.vpc.addInterfaceEndpoint('SqsEndpoint', {
        service: ec2.InterfaceVpcEndpointAwsService.SQS,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [this.vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });

      // SNS Endpoint
      this.vpc.addInterfaceEndpoint('SnsEndpoint', {
        service: ec2.InterfaceVpcEndpointAwsService.SNS,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [this.vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });

      // KMS Endpoint
      this.vpc.addInterfaceEndpoint('KmsEndpoint', {
        service: ec2.InterfaceVpcEndpointAwsService.KMS,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [this.vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });
    }

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC ID',
      exportName: `${id}-VpcId`,
    });

    new cdk.CfnOutput(this, 'VpcCidr', {
      value: config.vpc.cidr,
      description: 'VPC CIDR block',
      exportName: `${id}-VpcCidr`,
    });

    new cdk.CfnOutput(this, 'PrivateSubnetIds', {
      value: this.vpc.privateSubnets.map(s => s.subnetId).join(','),
      description: 'Private subnet IDs',
      exportName: `${id}-PrivateSubnetIds`,
    });

    new cdk.CfnOutput(this, 'PublicSubnetIds', {
      value: this.vpc.publicSubnets.map(s => s.subnetId).join(','),
      description: 'Public subnet IDs',
      exportName: `${id}-PublicSubnetIds`,
    });

    new cdk.CfnOutput(this, 'DatabaseSecurityGroupId', {
      value: this.databaseSecurityGroup.securityGroupId,
      description: 'Database security group ID',
      exportName: `${id}-DatabaseSGId`,
    });

    new cdk.CfnOutput(this, 'CacheSecurityGroupId', {
      value: this.cacheSecurityGroup.securityGroupId,
      description: 'Cache security group ID',
      exportName: `${id}-CacheSGId`,
    });

    new cdk.CfnOutput(this, 'ComputeSecurityGroupId', {
      value: this.computeSecurityGroup.securityGroupId,
      description: 'Compute security group ID',
      exportName: `${id}-ComputeSGId`,
    });

    new cdk.CfnOutput(this, 'LambdaSecurityGroupId', {
      value: this.lambdaSecurityGroup.securityGroupId,
      description: 'Lambda security group ID',
      exportName: `${id}-LambdaSGId`,
    });

    // Add tags to all resources in stack
    cdk.Tags.of(this).add('Stack', 'Networking');
  }
}

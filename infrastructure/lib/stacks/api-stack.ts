/**
 * AxiePro API Stack
 *
 * Creates API layer infrastructure:
 * - API Gateway HTTP API as a proxy to App Runner
 * - CloudFront distribution for global CDN
 * - WAF Web ACL for security protection
 * - Custom domain configuration
 */

import * as cdk from 'aws-cdk-lib';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as wafv2 from 'aws-cdk-lib/aws-wafv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';

export interface ApiStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  appRunnerServiceUrl: string;
  webSocketApi?: apigatewayv2.CfnApi;
}

export class ApiStack extends cdk.Stack {
  // API Gateway
  public readonly httpApi: apigatewayv2.CfnApi;
  public readonly httpApiEndpoint: string;

  // CloudFront
  public readonly distribution: cloudfront.IDistribution | undefined;
  public readonly distributionDomainName: string | undefined;

  // WAF
  public readonly webAcl: wafv2.CfnWebACL | undefined;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    const { config, appRunnerServiceUrl } = props;

    // ========================================================================
    // API Gateway HTTP API
    // ========================================================================

    // CloudWatch log group for API Gateway
    const apiLogGroup = new logs.LogGroup(this, 'ApiLogGroup', {
      logGroupName: `/aws/apigateway/${getResourceName('http-api', config)}`,
      retention: config.monitoring.logRetentionDays,
      removalPolicy: config.removalPolicy,
    });

    // HTTP API that proxies to App Runner
    this.httpApi = new apigatewayv2.CfnApi(this, 'HttpApi', {
      name: getResourceName('http-api', config),
      protocolType: 'HTTP',
      description: 'AxiePro API Gateway HTTP API',
      corsConfiguration: {
        allowOrigins: config.name === 'production'
          ? ['https://axiepro.io', 'https://app.axiepro.io']
          : ['*'],
        allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowHeaders: [
          'Content-Type',
          'Authorization',
          'X-Amz-Date',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
        maxAge: 86400, // 24 hours
        allowCredentials: config.name === 'production',
      },
      disableExecuteApiEndpoint: false,
    });

    // Integration with App Runner (only if App Runner is enabled)
    const isAppRunnerEnabled = !appRunnerServiceUrl.includes('app-runner-disabled');

    if (isAppRunnerEnabled) {
      const appRunnerIntegration = new apigatewayv2.CfnIntegration(
        this,
        'AppRunnerIntegration',
        {
          apiId: this.httpApi.ref,
          integrationType: 'HTTP_PROXY',
          integrationUri: `https://${appRunnerServiceUrl}`,
          integrationMethod: 'ANY',
          payloadFormatVersion: '1.0',
          connectionType: 'INTERNET',
          timeoutInMillis: 30000,
        }
      );

      // Default route to proxy all requests
      new apigatewayv2.CfnRoute(this, 'DefaultRoute', {
        apiId: this.httpApi.ref,
        routeKey: '$default',
        target: `integrations/${appRunnerIntegration.ref}`,
      });
    }

    // API Gateway stage
    const apiStage = new apigatewayv2.CfnStage(this, 'ApiStage', {
      apiId: this.httpApi.ref,
      stageName: '$default',
      autoDeploy: true,
      defaultRouteSettings: {
        throttlingBurstLimit: config.api.throttleBurst,
        throttlingRateLimit: config.api.throttleRate,
        detailedMetricsEnabled: config.monitoring.enableDetailedMetrics,
      },
      accessLogSettings: {
        destinationArn: apiLogGroup.logGroupArn,
        format: JSON.stringify({
          requestId: '$context.requestId',
          ip: '$context.identity.sourceIp',
          requestTime: '$context.requestTime',
          httpMethod: '$context.httpMethod',
          routeKey: '$context.routeKey',
          status: '$context.status',
          protocol: '$context.protocol',
          responseLength: '$context.responseLength',
          integrationLatency: '$context.integrationLatency',
          responseLatency: '$context.responseLatency',
        }),
      },
    });

    this.httpApiEndpoint = `https://${this.httpApi.ref}.execute-api.${config.region}.amazonaws.com`;

    // ========================================================================
    // WAF Web ACL
    // ========================================================================

    if (config.features.enableWaf) {
      this.webAcl = new wafv2.CfnWebACL(this, 'WebAcl', {
        name: getResourceName('waf', config),
        description: 'WAF Web ACL for AxiePro API',
        scope: 'CLOUDFRONT', // Must be CLOUDFRONT for CloudFront distribution
        defaultAction: { allow: {} },
        visibilityConfig: {
          cloudWatchMetricsEnabled: true,
          metricName: getResourceName('waf-metrics', config),
          sampledRequestsEnabled: true,
        },
        rules: [
          // AWS Managed Rules - Common Rule Set
          {
            name: 'AWSManagedRulesCommonRuleSet',
            priority: 1,
            overrideAction: { none: {} },
            statement: {
              managedRuleGroupStatement: {
                vendorName: 'AWS',
                name: 'AWSManagedRulesCommonRuleSet',
                excludedRules: [],
              },
            },
            visibilityConfig: {
              cloudWatchMetricsEnabled: true,
              metricName: 'AWSManagedRulesCommonRuleSet',
              sampledRequestsEnabled: true,
            },
          },
          // AWS Managed Rules - Known Bad Inputs
          {
            name: 'AWSManagedRulesKnownBadInputsRuleSet',
            priority: 2,
            overrideAction: { none: {} },
            statement: {
              managedRuleGroupStatement: {
                vendorName: 'AWS',
                name: 'AWSManagedRulesKnownBadInputsRuleSet',
              },
            },
            visibilityConfig: {
              cloudWatchMetricsEnabled: true,
              metricName: 'AWSManagedRulesKnownBadInputsRuleSet',
              sampledRequestsEnabled: true,
            },
          },
          // AWS Managed Rules - SQL Injection
          {
            name: 'AWSManagedRulesSQLiRuleSet',
            priority: 3,
            overrideAction: { none: {} },
            statement: {
              managedRuleGroupStatement: {
                vendorName: 'AWS',
                name: 'AWSManagedRulesSQLiRuleSet',
              },
            },
            visibilityConfig: {
              cloudWatchMetricsEnabled: true,
              metricName: 'AWSManagedRulesSQLiRuleSet',
              sampledRequestsEnabled: true,
            },
          },
          // Rate limiting rule
          {
            name: 'RateLimitRule',
            priority: 4,
            action: { block: {} },
            statement: {
              rateBasedStatement: {
                limit: 2000, // 2000 requests per 5 minutes per IP
                aggregateKeyType: 'IP',
              },
            },
            visibilityConfig: {
              cloudWatchMetricsEnabled: true,
              metricName: 'RateLimitRule',
              sampledRequestsEnabled: true,
            },
          },
          // Bot Control (optional, costs extra)
          // {
          //   name: 'AWSManagedRulesBotControlRuleSet',
          //   priority: 5,
          //   overrideAction: { none: {} },
          //   statement: {
          //     managedRuleGroupStatement: {
          //       vendorName: 'AWS',
          //       name: 'AWSManagedRulesBotControlRuleSet',
          //     },
          //   },
          //   visibilityConfig: {
          //     cloudWatchMetricsEnabled: true,
          //     metricName: 'AWSManagedRulesBotControlRuleSet',
          //     sampledRequestsEnabled: true,
          //   },
          // },
        ],
      });
    }

    // ========================================================================
    // CloudFront Distribution
    // ========================================================================

    if (config.features.enableCloudFront) {
      // Origin for API Gateway
      const apiOrigin = new origins.HttpOrigin(
        `${this.httpApi.ref}.execute-api.${config.region}.amazonaws.com`,
        {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
          originSslProtocols: [cloudfront.OriginSslPolicy.TLS_V1_2],
          connectionAttempts: 3,
          connectionTimeout: cdk.Duration.seconds(10),
          readTimeout: cdk.Duration.seconds(30),
          keepaliveTimeout: cdk.Duration.seconds(5),
        }
      );

      // Cache policy for API responses
      const apiCachePolicy = new cloudfront.CachePolicy(this, 'ApiCachePolicy', {
        cachePolicyName: getResourceName('api-cache-policy', config),
        comment: 'Cache policy for AxiePro API',
        defaultTtl: config.api.cacheEnabled ? config.api.cacheTtl : cdk.Duration.seconds(0),
        minTtl: cdk.Duration.seconds(0),
        maxTtl: cdk.Duration.minutes(5),
        cookieBehavior: cloudfront.CacheCookieBehavior.none(),
        headerBehavior: cloudfront.CacheHeaderBehavior.allowList(
          'Authorization',
          'Origin',
          'Access-Control-Request-Method',
          'Access-Control-Request-Headers'
        ),
        queryStringBehavior: cloudfront.CacheQueryStringBehavior.all(),
        enableAcceptEncodingGzip: true,
        enableAcceptEncodingBrotli: true,
      });

      // Origin request policy
      const originRequestPolicy = new cloudfront.OriginRequestPolicy(
        this,
        'OriginRequestPolicy',
        {
          originRequestPolicyName: getResourceName('origin-request-policy', config),
          comment: 'Origin request policy for AxiePro API',
          cookieBehavior: cloudfront.OriginRequestCookieBehavior.all(),
          headerBehavior: cloudfront.OriginRequestHeaderBehavior.allowList(
            'Origin',
            'Access-Control-Request-Method',
            'Access-Control-Request-Headers',
            'Referer',
            'User-Agent'
          ),
          queryStringBehavior: cloudfront.OriginRequestQueryStringBehavior.all(),
        }
      );

      // Response headers policy
      const responseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
        this,
        'ResponseHeadersPolicy',
        {
          responseHeadersPolicyName: getResourceName('response-headers-policy', config),
          comment: 'Response headers policy for AxiePro API',
          securityHeadersBehavior: {
            contentTypeOptions: { override: true },
            frameOptions: {
              frameOption: cloudfront.HeadersFrameOption.DENY,
              override: true,
            },
            referrerPolicy: {
              referrerPolicy: cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
              override: true,
            },
            strictTransportSecurity: {
              accessControlMaxAge: cdk.Duration.days(365),
              includeSubdomains: true,
              preload: true,
              override: true,
            },
            xssProtection: {
              protection: true,
              modeBlock: true,
              override: true,
            },
          },
          corsBehavior: {
            accessControlAllowOrigins: config.name === 'production'
              ? ['https://axiepro.io', 'https://app.axiepro.io']
              : ['*'],
            accessControlAllowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            accessControlAllowHeaders: ['*'],
            accessControlAllowCredentials: config.name === 'production',
            accessControlMaxAge: cdk.Duration.hours(24),
            originOverride: true,
          },
        }
      );

      // CloudFront distribution
      this.distribution = new cloudfront.Distribution(this, 'Distribution', {
        comment: `AxiePro API Distribution (${config.name})`,
        enabled: true,
        httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,
        priceClass: cloudfront.PriceClass.PRICE_CLASS_100, // US, Canada, Europe
        minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
        enableLogging: true,
        logBucket: s3.Bucket.fromBucketName(
          this,
          'LogsBucket',
          getResourceName(`logs-${config.account}`, config)
        ),
        logFilePrefix: 'cloudfront/',
        webAclId: this.webAcl?.attrArn,

        defaultBehavior: {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
          cachePolicy: apiCachePolicy,
          originRequestPolicy: originRequestPolicy,
          responseHeadersPolicy: responseHeadersPolicy,
          compress: true,
        },

        // Additional behaviors for specific paths
        additionalBehaviors: {
          // Health check - no caching
          '/health': {
            origin: apiOrigin,
            viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
            originRequestPolicy: originRequestPolicy,
          },
          // API v1 endpoints
          '/api/v1/*': {
            origin: apiOrigin,
            viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
            cachePolicy: apiCachePolicy,
            originRequestPolicy: originRequestPolicy,
            responseHeadersPolicy: responseHeadersPolicy,
            compress: true,
          },
        },

        errorResponses: [
          {
            httpStatus: 500,
            ttl: cdk.Duration.seconds(10),
          },
          {
            httpStatus: 502,
            ttl: cdk.Duration.seconds(10),
          },
          {
            httpStatus: 503,
            ttl: cdk.Duration.seconds(10),
          },
          {
            httpStatus: 504,
            ttl: cdk.Duration.seconds(10),
          },
        ],
      });

      this.distributionDomainName = this.distribution.distributionDomainName;
    }

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'HttpApiId', {
      value: this.httpApi.ref,
      description: 'HTTP API ID',
      exportName: `${id}-HttpApiId`,
    });

    new cdk.CfnOutput(this, 'HttpApiEndpoint', {
      value: this.httpApiEndpoint,
      description: 'HTTP API endpoint',
      exportName: `${id}-HttpApiEndpoint`,
    });

    if (this.distribution) {
      new cdk.CfnOutput(this, 'CloudFrontDistributionId', {
        value: this.distribution.distributionId,
        description: 'CloudFront distribution ID',
        exportName: `${id}-CloudFrontDistributionId`,
      });

      new cdk.CfnOutput(this, 'CloudFrontDomainName', {
        value: this.distributionDomainName!,
        description: 'CloudFront domain name',
        exportName: `${id}-CloudFrontDomainName`,
      });

      new cdk.CfnOutput(this, 'ApiUrl', {
        value: `https://${this.distributionDomainName}`,
        description: 'Production API URL (via CloudFront)',
        exportName: `${id}-ApiUrl`,
      });
    }

    if (this.webAcl) {
      new cdk.CfnOutput(this, 'WebAclArn', {
        value: this.webAcl.attrArn,
        description: 'WAF Web ACL ARN',
        exportName: `${id}-WebAclArn`,
      });
    }

    // Add tags
    cdk.Tags.of(this).add('Stack', 'API');
  }
}

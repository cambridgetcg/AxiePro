/**
 * AxiePro CI/CD Stack
 *
 * Creates CI/CD pipeline infrastructure:
 * - CodePipeline for automated deployments
 * - CodeBuild projects for building and testing
 * - GitHub integration for source control
 * - Automated deployment to App Runner
 */

import * as cdk from 'aws-cdk-lib';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { EnvironmentConfig, getResourceName } from '../config/environments';

export interface CiCdStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  ecrRepository: ecr.IRepository;
  appRunnerServiceArn: string;
  artifactBucket: s3.IBucket;
}

export class CiCdStack extends cdk.Stack {
  public readonly pipeline: codepipeline.Pipeline;
  public readonly buildProject: codebuild.Project;

  constructor(scope: Construct, id: string, props: CiCdStackProps) {
    super(scope, id, props);

    const { config, ecrRepository, appRunnerServiceArn, artifactBucket } = props;

    // ========================================================================
    // CodeBuild Project
    // ========================================================================

    // CodeBuild role
    const buildRole = new iam.Role(this, 'BuildRole', {
      roleName: getResourceName('codebuild-role', config),
      assumedBy: new iam.ServicePrincipal('codebuild.amazonaws.com'),
    });

    // Grant ECR permissions
    ecrRepository.grantPullPush(buildRole);

    // Grant S3 permissions for artifacts
    artifactBucket.grantReadWrite(buildRole);

    // Grant App Runner permissions for deployment
    buildRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'apprunner:StartDeployment',
          'apprunner:DescribeService',
          'apprunner:ListOperations',
        ],
        resources: [appRunnerServiceArn],
      })
    );

    // Grant CloudWatch Logs permissions
    buildRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        resources: ['*'],
      })
    );

    // CodeBuild log group
    const buildLogGroup = new logs.LogGroup(this, 'BuildLogGroup', {
      logGroupName: `/aws/codebuild/${getResourceName('build', config)}`,
      retention: config.monitoring.logRetentionDays,
      removalPolicy: config.removalPolicy,
    });

    // CodeBuild project for building and pushing Docker image
    this.buildProject = new codebuild.Project(this, 'BuildProject', {
      projectName: getResourceName('build', config),
      description: 'Build and push AxiePro Docker image to ECR',
      role: buildRole,
      source: codebuild.Source.gitHub({
        owner: 'YOUR_GITHUB_ORG', // Replace with actual GitHub org
        repo: 'AxiePro',
        webhook: true,
        webhookFilters: [
          codebuild.FilterGroup.inEventOf(codebuild.EventAction.PUSH).andBranchIs(
            config.name === 'production' ? 'main' : config.name
          ),
        ],
      }),
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        privileged: true, // Required for Docker builds
        computeType: codebuild.ComputeType.MEDIUM,
        environmentVariables: {
          AWS_ACCOUNT_ID: { value: config.account },
          AWS_REGION: { value: config.region },
          ECR_REPOSITORY_URI: { value: ecrRepository.repositoryUri },
          ENVIRONMENT: { value: config.name },
          APP_RUNNER_SERVICE_ARN: { value: appRunnerServiceArn },
        },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          pre_build: {
            commands: [
              'echo Logging in to Amazon ECR...',
              'aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com',
              'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
              'IMAGE_TAG=${COMMIT_HASH:=latest}',
            ],
          },
          build: {
            commands: [
              'echo Build started on `date`',
              'echo Building the Docker image...',
              'cd backend',
              'docker build -t $ECR_REPOSITORY_URI:$IMAGE_TAG .',
              'docker tag $ECR_REPOSITORY_URI:$IMAGE_TAG $ECR_REPOSITORY_URI:latest',
            ],
          },
          post_build: {
            commands: [
              'echo Build completed on `date`',
              'echo Pushing the Docker image...',
              'docker push $ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker push $ECR_REPOSITORY_URI:latest',
              'echo Triggering App Runner deployment...',
              'aws apprunner start-deployment --service-arn $APP_RUNNER_SERVICE_ARN',
              'echo Deployment triggered successfully',
              'echo Writing image definitions file...',
              'printf \'[{"name":"axiepro-api","imageUri":"%s"}]\' $ECR_REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json',
            ],
          },
        },
        artifacts: {
          files: ['imagedefinitions.json'],
          'discard-paths': 'yes',
        },
        cache: {
          paths: ['/root/.cache/pip/**/*', '/root/.docker/**/*'],
        },
      }),
      cache: codebuild.Cache.local(
        codebuild.LocalCacheMode.DOCKER_LAYER,
        codebuild.LocalCacheMode.CUSTOM
      ),
      logging: {
        cloudWatch: {
          logGroup: buildLogGroup,
          enabled: true,
        },
      },
      badge: true, // Enable build badge
    });

    // CodeBuild project for running tests
    const testProject = new codebuild.Project(this, 'TestProject', {
      projectName: getResourceName('test', config),
      description: 'Run AxiePro tests',
      role: buildRole,
      source: codebuild.Source.gitHub({
        owner: 'YOUR_GITHUB_ORG', // Replace with actual GitHub org
        repo: 'AxiePro',
      }),
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.SMALL,
        environmentVariables: {
          ENVIRONMENT: { value: 'test' },
        },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          install: {
            'runtime-versions': {
              python: '3.11',
            },
            commands: [
              'cd backend',
              'pip install -r requirements.txt',
              'pip install pytest pytest-cov pytest-asyncio',
            ],
          },
          build: {
            commands: [
              'echo Running tests...',
              'cd backend',
              'pytest tests/ -v --cov=src --cov-report=xml --cov-report=html',
            ],
          },
        },
        reports: {
          'pytest-reports': {
            files: ['backend/pytest-report.xml'],
            'file-format': 'JUNITXML',
          },
          'coverage-reports': {
            files: ['backend/coverage.xml'],
            'file-format': 'COBERTURAXML',
          },
        },
        artifacts: {
          files: ['backend/htmlcov/**/*'],
          'base-directory': '.',
        },
      }),
      logging: {
        cloudWatch: {
          logGroup: buildLogGroup,
          enabled: true,
        },
      },
    });

    // ========================================================================
    // CodePipeline
    // ========================================================================

    // Pipeline artifacts
    const sourceOutput = new codepipeline.Artifact('SourceOutput');
    const buildOutput = new codepipeline.Artifact('BuildOutput');
    const testOutput = new codepipeline.Artifact('TestOutput');

    // Create the pipeline
    this.pipeline = new codepipeline.Pipeline(this, 'Pipeline', {
      pipelineName: getResourceName('pipeline', config),
      artifactBucket: artifactBucket,
      pipelineType: codepipeline.PipelineType.V2,
      restartExecutionOnUpdate: true,

      stages: [
        // Source Stage
        {
          stageName: 'Source',
          actions: [
            new codepipeline_actions.CodeStarConnectionsSourceAction({
              actionName: 'GitHub_Source',
              owner: 'YOUR_GITHUB_ORG', // Replace with actual GitHub org
              repo: 'AxiePro',
              branch: config.name === 'production' ? 'main' : config.name,
              output: sourceOutput,
              connectionArn: `arn:aws:codestar-connections:${config.region}:${config.account}:connection/YOUR_CONNECTION_ID`, // Replace
              triggerOnPush: true,
            }),
          ],
        },

        // Test Stage
        {
          stageName: 'Test',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'Run_Tests',
              project: testProject,
              input: sourceOutput,
              outputs: [testOutput],
            }),
          ],
        },

        // Build Stage
        {
          stageName: 'Build',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'Build_and_Push',
              project: this.buildProject,
              input: sourceOutput,
              outputs: [buildOutput],
            }),
          ],
        },

        // Manual Approval (for staging/production)
        ...(config.name !== 'development'
          ? [
              {
                stageName: 'Approval',
                actions: [
                  new codepipeline_actions.ManualApprovalAction({
                    actionName: 'Manual_Approval',
                    notificationTopic: undefined, // Add SNS topic for notifications
                    additionalInformation: `Approve deployment to ${config.name}`,
                    externalEntityLink: `https://${config.region}.console.aws.amazon.com/apprunner`,
                  }),
                ],
              },
            ]
          : []),

        // Deploy Stage (App Runner auto-deploys on ECR push, this is for notification)
        {
          stageName: 'Deploy',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'Verify_Deployment',
              project: new codebuild.Project(this, 'DeployVerifyProject', {
                projectName: getResourceName('deploy-verify', config),
                description: 'Verify App Runner deployment status',
                role: buildRole,
                environment: {
                  buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
                  computeType: codebuild.ComputeType.SMALL,
                  environmentVariables: {
                    APP_RUNNER_SERVICE_ARN: { value: appRunnerServiceArn },
                  },
                },
                buildSpec: codebuild.BuildSpec.fromObject({
                  version: '0.2',
                  phases: {
                    build: {
                      commands: [
                        'echo Verifying App Runner deployment...',
                        'aws apprunner describe-service --service-arn $APP_RUNNER_SERVICE_ARN --query "Service.Status" --output text',
                        'echo Deployment verification complete',
                      ],
                    },
                  },
                }),
              }),
              input: buildOutput,
            }),
          ],
        },
      ],
    });

    // ========================================================================
    // Outputs
    // ========================================================================

    new cdk.CfnOutput(this, 'PipelineName', {
      value: this.pipeline.pipelineName,
      description: 'CodePipeline name',
      exportName: `${id}-PipelineName`,
    });

    new cdk.CfnOutput(this, 'PipelineUrl', {
      value: `https://${config.region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${this.pipeline.pipelineName}/view`,
      description: 'CodePipeline console URL',
      exportName: `${id}-PipelineUrl`,
    });

    new cdk.CfnOutput(this, 'BuildProjectName', {
      value: this.buildProject.projectName,
      description: 'CodeBuild project name',
      exportName: `${id}-BuildProjectName`,
    });

    // Note: Build badge URL can be retrieved from the CodeBuild console
    // or via: aws codebuild batch-get-projects --names <project-name>

    // Add tags
    cdk.Tags.of(this).add('Stack', 'CICD');
  }
}

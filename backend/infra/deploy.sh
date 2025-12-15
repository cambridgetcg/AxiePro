#!/bin/bash
set -e

# Axie Explorer Infrastructure Deployment Script
# Usage: ./deploy.sh [environment] [action]
# Example: ./deploy.sh production deploy

ENVIRONMENT="${1:-production}"
ACTION="${2:-deploy}"
STACK_NAME="axie-explorer-pipeline-${ENVIRONMENT}"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=========================================="
echo "Axie Explorer Infrastructure Deployment"
echo "=========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Action: ${ACTION}"
echo "Stack: ${STACK_NAME}"
echo "Region: ${REGION}"
echo "Account: ${ACCOUNT_ID}"
echo "=========================================="

# Get VPC and Subnet IDs (use default VPC if not specified)
if [ -z "$VPC_ID" ]; then
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
    echo "Using default VPC: ${VPC_ID}"
fi

if [ -z "$SUBNET_IDS" ]; then
    SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')
    echo "Using subnets: ${SUBNET_IDS}"
fi

case $ACTION in
    deploy)
        echo ""
        echo "Deploying CloudFormation stack..."

        aws cloudformation deploy \
            --template-file cloudformation.yaml \
            --stack-name "${STACK_NAME}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --parameter-overrides \
                Environment="${ENVIRONMENT}" \
                VpcId="${VPC_ID}" \
                SubnetIds="${SUBNET_IDS}" \
            --tags \
                Project=axie-explorer \
                Environment="${ENVIRONMENT}" \
            --region "${REGION}"

        echo ""
        echo "Stack outputs:"
        aws cloudformation describe-stacks \
            --stack-name "${STACK_NAME}" \
            --query 'Stacks[0].Outputs' \
            --output table \
            --region "${REGION}"
        ;;

    package-lambdas)
        echo ""
        echo "Packaging Lambda functions..."

        LAMBDA_DIR="../src/lambdas"
        BUILD_DIR="./lambda-packages"

        mkdir -p "${BUILD_DIR}"

        # Create Lambda layer with dependencies
        echo "Creating Lambda layer..."
        pip install \
            aws-lambda-powertools \
            httpx \
            psycopg2-binary \
            redis \
            -t "${BUILD_DIR}/layer/python"

        cd "${BUILD_DIR}/layer"
        zip -r ../lambda-layer.zip python
        cd -

        # Package each Lambda function
        for lambda in price_ingestion deal_detector meta_analyzer; do
            echo "Packaging ${lambda}..."
            cp "${LAMBDA_DIR}/${lambda}.py" "${BUILD_DIR}/"
            cd "${BUILD_DIR}"
            zip "${lambda}.zip" "${lambda}.py"
            cd -
        done

        echo "Lambda packages created in ${BUILD_DIR}/"
        ls -la "${BUILD_DIR}"/*.zip
        ;;

    upload-lambdas)
        echo ""
        echo "Uploading Lambda packages to S3..."

        BUILD_DIR="./lambda-packages"
        S3_BUCKET="axie-explorer-lambdas-${ACCOUNT_ID}-${REGION}"

        # Create S3 bucket if it doesn't exist
        aws s3 mb "s3://${S3_BUCKET}" --region "${REGION}" 2>/dev/null || true

        # Upload packages
        aws s3 cp "${BUILD_DIR}/lambda-layer.zip" "s3://${S3_BUCKET}/layers/"
        aws s3 cp "${BUILD_DIR}/price_ingestion.zip" "s3://${S3_BUCKET}/functions/"
        aws s3 cp "${BUILD_DIR}/deal_detector.zip" "s3://${S3_BUCKET}/functions/"
        aws s3 cp "${BUILD_DIR}/meta_analyzer.zip" "s3://${S3_BUCKET}/functions/"

        echo "Packages uploaded to s3://${S3_BUCKET}/"
        ;;

    update-lambdas)
        echo ""
        echo "Updating Lambda function code..."

        BUILD_DIR="./lambda-packages"

        for lambda in price_ingestion deal_detector meta_analyzer; do
            FUNCTION_NAME="axie-${lambda//_/-}-${ENVIRONMENT}"
            echo "Updating ${FUNCTION_NAME}..."

            aws lambda update-function-code \
                --function-name "${FUNCTION_NAME}" \
                --zip-file "fileb://${BUILD_DIR}/${lambda}.zip" \
                --region "${REGION}"
        done

        echo "Lambda functions updated."
        ;;

    status)
        echo ""
        echo "Stack status:"
        aws cloudformation describe-stacks \
            --stack-name "${STACK_NAME}" \
            --query 'Stacks[0].{Status:StackStatus,LastUpdated:LastUpdatedTime}' \
            --output table \
            --region "${REGION}"

        echo ""
        echo "Lambda functions:"
        for lambda in price-ingestion deal-detector meta-analyzer; do
            FUNCTION_NAME="axie-${lambda}-${ENVIRONMENT}"
            echo "  ${FUNCTION_NAME}:"
            aws lambda get-function \
                --function-name "${FUNCTION_NAME}" \
                --query 'Configuration.{State:State,LastModified:LastModified,MemorySize:MemorySize,Timeout:Timeout}' \
                --output table \
                --region "${REGION}" 2>/dev/null || echo "    Not deployed"
        done
        ;;

    delete)
        echo ""
        echo "WARNING: This will delete the stack and all resources!"
        read -p "Are you sure? (yes/no): " confirm

        if [ "$confirm" = "yes" ]; then
            aws cloudformation delete-stack \
                --stack-name "${STACK_NAME}" \
                --region "${REGION}"

            echo "Waiting for stack deletion..."
            aws cloudformation wait stack-delete-complete \
                --stack-name "${STACK_NAME}" \
                --region "${REGION}"

            echo "Stack deleted."
        else
            echo "Aborted."
        fi
        ;;

    *)
        echo "Unknown action: ${ACTION}"
        echo ""
        echo "Available actions:"
        echo "  deploy         - Deploy/update CloudFormation stack"
        echo "  package-lambdas - Package Lambda functions into zip files"
        echo "  upload-lambdas  - Upload Lambda packages to S3"
        echo "  update-lambdas  - Update Lambda function code"
        echo "  status         - Show current stack status"
        echo "  delete         - Delete the stack"
        exit 1
        ;;
esac

echo ""
echo "Done!"

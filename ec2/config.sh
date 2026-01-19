#!/bin/bash
# =============================================================================
# EC2 Configuration for AxiePro Data Fetcher
# =============================================================================
# Naming Convention: axiepro-<resource-type>[-<qualifier>]
# Examples: axiepro-ec2-fetcher, axiepro-sg-ec2, axiepro-db
# =============================================================================

# AWS Configuration
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="034362054546"

# EC2 Instance Configuration
export EC2_KEY_NAME="cach_excel"
export EC2_KEY_PATH="$HOME/.ssh/cach_excel.pem"
export EC2_AMI="ami-068c0051b15cdb816"  # Amazon Linux 2023
export EC2_INSTANCE_TYPE="t3.micro"
export EC2_SUBNET="subnet-01095623139ea0f77"

# Security Group (rename to axiepro-sg-ec2-fetcher in AWS console)
export EC2_SECURITY_GROUP="sg-05c5101c555c59f9c"
export EC2_SECURITY_GROUP_NAME="axiepro-sg-ec2-fetcher"

# IAM Role (rename to axiepro-ec2-fetcher-role in AWS console)
export EC2_IAM_ROLE="EC2"
export EC2_IAM_ROLE_NAME="axiepro-ec2-fetcher-role"

# Instance Details (add Name tag: axiepro-ec2-fetcher)
export EC2_INSTANCE_ID="i-0cbc98fa8fc906281"
export EC2_INSTANCE_NAME="axiepro-ec2-fetcher"
export EC2_PUBLIC_IP="3.91.12.195"

# Project paths
export PROJECT_DIR="/Users/alex/Ronin_API"
export REMOTE_DIR="/home/ec2-user/axie"

# =============================================================================
# Related AWS Resources (for reference)
# =============================================================================
# DEDICATED TO AXIEPRO:
#   App Runner:     axiepro-api
#   ECR:            axiepro-backend
#   ElastiCache:    axiepro-redis
#   VPC Connector:  axiepro-vpc-connector
#   Secrets:        axie-explorer/api-keys
#
# SHARED (multi-app):
#   RDS:            cardforum (shared with CardForum app, AxiePro uses 'axie' schema)
#   IAM Role:       EC2 (generic, shared across apps)
# =============================================================================

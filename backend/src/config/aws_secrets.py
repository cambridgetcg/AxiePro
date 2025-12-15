"""
AWS Secrets Manager integration for secure credential storage.

Usage:
    In production, secrets are fetched from AWS Secrets Manager.
    Locally, falls back to environment variables.
"""

import json
import os
from functools import lru_cache
from typing import Optional

# Only import boto3 if available (not required for local dev)
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


@lru_cache
def get_secret(secret_name: str, region: str = "us-east-1") -> Optional[dict]:
    """
    Retrieve a secret from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret in AWS
        region: AWS region

    Returns:
        Dict containing secret key-value pairs, or None if not found
    """
    if not HAS_BOTO3:
        return None

    try:
        client = boto3.client(
            service_name="secretsmanager",
            region_name=region,
        )

        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            return json.loads(response["SecretString"])
        else:
            # Binary secret (unusual for API keys)
            return None

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ResourceNotFoundException":
            print(f"Secret {secret_name} not found")
        elif error_code == "AccessDeniedException":
            print(f"Access denied to secret {secret_name}")
        else:
            print(f"Error retrieving secret: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def get_api_keys() -> dict:
    """
    Get API keys from AWS Secrets Manager or environment variables.

    Priority:
    1. AWS Secrets Manager (production)
    2. Environment variables (local development)

    Returns:
        Dict with goldrush_api_key and other config
    """
    # Try AWS Secrets Manager first (for production)
    aws_secret_name = os.getenv("AWS_SECRET_NAME", "axie-explorer/api-keys")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    secrets = get_secret(aws_secret_name, aws_region)

    if secrets:
        return {
            "goldrush_api_key": secrets.get("GOLDRUSH_API_KEY"),
            "skymavis_api_key": secrets.get("SKYMAVIS_API_KEY"),
            "database_url": secrets.get("DATABASE_URL"),
            "redis_url": secrets.get("REDIS_URL"),
        }

    # Fall back to environment variables (local development)
    return {
        "goldrush_api_key": os.getenv("GOLDRUSH_API_KEY"),
        "skymavis_api_key": os.getenv("SKYMAVIS_API_KEY"),
        "database_url": os.getenv("DATABASE_URL"),
        "redis_url": os.getenv("REDIS_URL"),
    }


# Example AWS CLI commands to create the secret:
"""
# Create secret
aws secretsmanager create-secret \
    --name axie-explorer/api-keys \
    --description "API keys for Axie Explorer" \
    --secret-string '{
        "MORALIS_API_KEY": "your-moralis-key",
        "SKYMAVIS_API_KEY": "your-skymavis-key",
        "DATABASE_URL": "postgresql://...",
        "REDIS_URL": "redis://..."
    }'

# Update secret
aws secretsmanager put-secret-value \
    --secret-id axie-explorer/api-keys \
    --secret-string '{"MORALIS_API_KEY": "new-key", ...}'

# Grant Lambda/ECS access via IAM policy:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:axie-explorer/*"
        }
    ]
}
"""

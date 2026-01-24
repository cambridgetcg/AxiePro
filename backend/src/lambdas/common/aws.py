"""
AWS Utilities for Lambda Functions

Provides secrets management with caching for efficient Lambda execution.
Secrets are cached per Lambda container to minimize Secrets Manager calls.

Environment Variables:
    AWS_SECRET_NAME / SECRET_NAME: Name of the API secrets in Secrets Manager
    DATABASE_SECRET_NAME: Name of the database credentials secret
    AWS_REGION: AWS region (defaults to us-east-1)
"""

import json
import os
from functools import lru_cache
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError


# Region configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


@lru_cache(maxsize=1)
def _get_secrets_client():
    """Get cached Secrets Manager client."""
    return boto3.client("secretsmanager", region_name=AWS_REGION)


def get_secrets(secret_name_env: str = "AWS_SECRET_NAME") -> Dict:
    """
    Retrieve secrets from AWS Secrets Manager.

    Supports fallback from AWS_SECRET_NAME to SECRET_NAME for compatibility.

    Args:
        secret_name_env: Environment variable containing the secret name.
                        Defaults to "AWS_SECRET_NAME".

    Returns:
        Dict containing secret key-value pairs.

    Raises:
        RuntimeError: If secret name env var is not set or secret not found.

    Example:
        secrets = get_secrets()
        api_key = secrets.get("SKYMAVIS_API_KEY")
    """
    # Support fallback for compatibility
    secret_name = os.environ.get(secret_name_env)
    if not secret_name and secret_name_env == "AWS_SECRET_NAME":
        secret_name = os.environ.get("SECRET_NAME")

    if not secret_name:
        raise RuntimeError(
            f"{secret_name_env} (or SECRET_NAME) environment variable not set"
        )

    try:
        client = _get_secrets_client()
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ResourceNotFoundException":
            raise RuntimeError(f"Secret '{secret_name}' not found") from e
        elif error_code == "AccessDeniedException":
            raise RuntimeError(f"Access denied to secret '{secret_name}'") from e
        raise RuntimeError(f"Error retrieving secret: {e}") from e


def get_db_credentials() -> Dict:
    """
    Retrieve database credentials from AWS Secrets Manager.

    The database secret should contain 'username' and 'password' keys.

    Returns:
        Dict with 'username' and 'password' keys.

    Raises:
        RuntimeError: If DATABASE_SECRET_NAME env var not set or secret not found.

    Example:
        creds = get_db_credentials()
        conn = psycopg2.connect(user=creds["username"], password=creds["password"])
    """
    secret_name = os.environ.get("DATABASE_SECRET_NAME")
    if not secret_name:
        raise RuntimeError("DATABASE_SECRET_NAME environment variable not set")

    try:
        client = _get_secrets_client()
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ResourceNotFoundException":
            raise RuntimeError(f"Database secret '{secret_name}' not found") from e
        elif error_code == "AccessDeniedException":
            raise RuntimeError(f"Access denied to database secret '{secret_name}'") from e
        raise RuntimeError(f"Error retrieving database credentials: {e}") from e


# Container-level caching for Lambda warm starts
_secrets_cache: Dict[str, Dict] = {}


def get_secrets_cached(secret_name_env: str = "AWS_SECRET_NAME") -> Dict:
    """
    Get secrets with container-level caching.

    More aggressive caching than lru_cache - persists across invocations
    in the same Lambda container. Useful for API keys that rarely change.

    Args:
        secret_name_env: Environment variable containing the secret name.

    Returns:
        Dict containing secret key-value pairs.
    """
    if secret_name_env not in _secrets_cache:
        _secrets_cache[secret_name_env] = get_secrets(secret_name_env)
    return _secrets_cache[secret_name_env]


def clear_secrets_cache() -> None:
    """
    Clear the secrets cache.

    Useful for testing or when secrets need to be refreshed.
    """
    global _secrets_cache
    _secrets_cache = {}
    _get_secrets_client.cache_clear()

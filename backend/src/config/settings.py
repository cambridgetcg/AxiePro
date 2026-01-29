"""
Application configuration settings.

Uses pydantic-settings to load configuration from environment variables.
In production (AWS), can also load from AWS Secrets Manager.
Supports IAM database authentication for secure, passwordless DB access.
"""

import os
from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


def _generate_iam_token(host: str, port: int, user: str, region: str) -> str:
    """Generate IAM auth token for RDS connection."""
    try:
        import boto3
        client = boto3.client('rds', region_name=region)
        token = client.generate_db_auth_token(
            DBHostname=host,
            Port=port,
            DBUsername=user,
            Region=region
        )
        return token
    except Exception as e:
        print(f"Failed to generate IAM token: {e}")
        return ""


def _get_aws_secrets() -> dict:
    """Load secrets from AWS Secrets Manager if explicitly enabled."""
    # Only try Secrets Manager if USE_AWS_SECRETS is explicitly set to "true"
    # This allows passing credentials directly via environment variables
    if os.getenv("USE_AWS_SECRETS", "").lower() == "true":
        try:
            from .aws_secrets import get_api_keys
            return get_api_keys()
        except Exception as e:
            print(f"Warning: Failed to load AWS secrets: {e}")
            pass
    return {}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Axie Ronin Explorer"
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development"  # development, staging, production

    # CORS - comma-separated list of allowed origins
    # In production, set to your frontend domain(s)
    # Default includes production domains for safety
    cors_origins: str = "https://axiepro.io,https://www.axiepro.io,https://app.axiepro.io,http://localhost:3000"

    # Database
    database_url: str = "postgresql://axie:axie_dev_password@localhost:5432/axie_explorer"

    # IAM Database Authentication (for AWS RDS)
    use_iam_auth: bool = False
    db_host: str = "cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com"
    db_port: int = 5432
    db_name: str = "cardforum"
    db_user: str = "iamuser"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # External APIs
    goldrush_api_key: Optional[str] = None
    skymavis_api_key: Optional[str] = None
    moralis_api_key: Optional[str] = None

    # Authentication
    jwt_secret: str = "change-this-in-production-min-32-chars"
    jwt_expiry_hours: int = 24
    auth_challenge_ttl_minutes: int = 5

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_secret_name: str = "axie-explorer/api-keys"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with AWS secrets if available
        aws_secrets = _get_aws_secrets()
        if aws_secrets.get("goldrush_api_key"):
            self.goldrush_api_key = aws_secrets["goldrush_api_key"]
        if aws_secrets.get("skymavis_api_key"):
            self.skymavis_api_key = aws_secrets["skymavis_api_key"]
        if aws_secrets.get("moralis_api_key"):
            self.moralis_api_key = aws_secrets["moralis_api_key"]
        if aws_secrets.get("database_url"):
            self.database_url = aws_secrets["database_url"]
        if aws_secrets.get("redis_url"):
            self.redis_url = aws_secrets["redis_url"]

    # Ronin Network Configuration
    # Set to 'testnet' to use Saigon testnet, 'mainnet' for production
    ronin_network: str = "mainnet"

    # Ronin RPC URLs (automatically selected based on ronin_network)
    ronin_mainnet_rpc_url: str = "https://api.roninchain.com/rpc"
    ronin_testnet_rpc_url: str = "https://saigon-testnet.roninchain.com/rpc"

    # Ronin Chain IDs
    ronin_mainnet_chain_id: int = 2020
    ronin_testnet_chain_id: int = 2021

    @property
    def ronin_rpc_url(self) -> str:
        """Get the Ronin RPC URL for the configured network."""
        if self.ronin_network == "testnet":
            return self.ronin_testnet_rpc_url
        return self.ronin_mainnet_rpc_url

    @property
    def ronin_chain_id(self) -> int:
        """Get the Ronin chain ID for the configured network."""
        if self.ronin_network == "testnet":
            return self.ronin_testnet_chain_id
        return self.ronin_mainnet_chain_id

    @property
    def ronin_explorer_url(self) -> str:
        """Get the Ronin explorer URL for the configured network."""
        if self.ronin_network == "testnet":
            return "https://saigon-app.roninchain.com"
        return "https://app.roninchain.com"

    @property
    def is_testnet(self) -> bool:
        """Check if running on testnet."""
        return self.ronin_network == "testnet"

    # API Rate Limits (requests per minute)
    goldrush_rate_limit: int = 100
    moralis_rate_limit: int = 25  # Free tier: 25 req/sec = 1500/min, conservative

    # Cache TTLs (seconds)
    cache_ttl_listings: int = 300  # 5 minutes
    cache_ttl_floor_prices: int = 60  # 1 minute
    cache_ttl_axie_details: int = 600  # 10 minutes

    def get_database_url(self) -> str:
        """Get database URL, generating IAM token if configured."""
        if self.use_iam_auth:
            token = _generate_iam_token(
                self.db_host, self.db_port, self.db_user, self.aws_region
            )
            # URL-encode the token as it contains special characters
            encoded_token = quote_plus(token)
            return f"postgresql://{self.db_user}:{encoded_token}@{self.db_host}:{self.db_port}/{self.db_name}?sslmode=require"
        return self.database_url

    @property
    def goldrush_base_url(self) -> str:
        return "https://api.covalenthq.com/v1"

    @property
    def goldrush_chain_id(self) -> str:
        """Goldrush chain identifier for Ronin (mainnet only - testnet not supported)."""
        return "axie-mainnet"

    @property
    def moralis_base_url(self) -> str:
        """Moralis API base URL."""
        return "https://deep-index.moralis.io/api/v2.2"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

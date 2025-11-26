"""
Configuration Management.

Environment-based configuration with validation and type safety.
Uses Pydantic for validation and type checking.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseSettings):
    """Configuration for LLM providers."""
    
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_organization: Optional[str] = Field(None, description="OpenAI organization ID")
    
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class VectorStoreConfig(BaseSettings):
    """Configuration for vector databases."""

    qdrant_host: str = Field("localhost", description="Qdrant host")
    qdrant_port: int = Field(6333, description="Qdrant port")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant API key")
    qdrant_use_https: bool = Field(False, description="Use HTTPS when connecting to Qdrant")
    qdrant_timeout_seconds: float = Field(
        10.0, description="Request timeout when talking to Qdrant"
    )
    
    chroma_persist_dir: Optional[str] = Field(None, description="ChromaDB persist directory")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class RedisConfig(BaseSettings):
    """Configuration for Redis."""

    redis_url: Optional[str] = Field(
        None, description="Full Redis URL (supports rediss:// for Upstash)",
    )
    redis_host: str = Field("localhost", description="Redis host")
    redis_port: int = Field(6379, description="Redis port")
    redis_password: Optional[str] = Field(None, description="Redis password")
    redis_db: int = Field(0, description="Redis database number")
    redis_ssl: bool = Field(False, description="Enable SSL/TLS for Redis")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def connection_kwargs(self) -> dict:
        """Return connection kwargs compatible with redis-py."""

        # Prefer URL when provided (e.g., Upstash rediss:// URLs)
        if self.redis_url:
            return {
                "url": self.redis_url,
                "ssl": self.redis_url.startswith("rediss://") or self.redis_ssl,
                "decode_responses": True,
            }

        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "password": self.redis_password,
            "db": self.redis_db,
            "ssl": self.redis_ssl,
            "decode_responses": True,
        }


class DatabaseConfig(BaseSettings):
    """Configuration for PostgreSQL database."""
    
    database_url: Optional[str] = Field(
        None,
        description="Full PostgreSQL connection URL (overrides individual fields)"
    )
    database_host: str = Field("localhost", description="Database host")
    database_port: int = Field(5432, description="Database port")
    database_name: str = Field("aiagents", description="Database name")
    database_user: str = Field("postgres", description="Database user")
    database_password: Optional[str] = Field(None, description="Database password")
    database_pool_size: int = Field(10, description="Connection pool size")
    database_max_overflow: int = Field(20, description="Max connections above pool size")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    def get_url(self) -> str:
        """Get database URL (full URL or build from components)."""
        if self.database_url:
            return self.database_url
        
        password_part = f":{self.database_password}" if self.database_password else ""
        return (
            f"postgresql+asyncpg://"
            f"{self.database_user}{password_part}@"
            f"{self.database_host}:{self.database_port}/"
            f"{self.database_name}"
        )


class ObservabilityConfig(BaseSettings):
    """Configuration for observability."""

    log_level: str = Field("INFO", description="Log level")
    enable_tracing: bool = Field(False, description="Enable distributed tracing")
    otel_exporter_endpoint: Optional[str] = Field(
        None,
        description="OpenTelemetry exporter endpoint",
    )
    sentry_dsn: Optional[str] = Field(
        None, description="Sentry DSN for error reporting",
    )
    sentry_environment: Optional[str] = Field(
        None, description="Sentry environment tag (e.g., production)",
    )
    sentry_traces_sample_rate: float = Field(
        0.05,
        description="Sample rate for Sentry tracing (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
    )
    enable_metrics: bool = Field(True, description="Enable Prometheus metrics")
    metrics_port: int = Field(9090, description="Metrics server port")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AgentConfig(BaseSettings):
    """Configuration for agent execution."""
    
    default_agent_timeout: int = Field(
        300,
        description="Default agent timeout in seconds",
    )
    max_agent_retries: int = Field(
        3,
        description="Max retries for agent execution",
    )
    agent_execution_memory_limit_mb: int = Field(
        512,
        description="Memory limit per agent execution",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class SupabaseConfig(BaseSettings):
    """Configuration for Supabase services (Auth, DB, Storage)."""

    supabase_url: Optional[str] = Field(None, description="Supabase project URL")
    supabase_service_role_key: Optional[str] = Field(
        None, description="Supabase service role key",
    )
    supabase_anon_key: Optional[str] = Field(None, description="Supabase anon key")
    supabase_jwt_secret: Optional[str] = Field(
        None, description="Supabase JWT secret for server-side verification",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class EmailConfig(BaseSettings):
    """Configuration for outbound email providers."""

    sendgrid_api_key: Optional[str] = Field(None, description="SendGrid API key")
    resend_api_key: Optional[str] = Field(None, description="Resend API key")
    admin_email: Optional[str] = Field(None, description="Admin/notification email")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AuthConfig(BaseSettings):
    """Configuration for API authentication."""

    jwt_secret_key: str = Field(
        "CHANGE_THIS_IN_PRODUCTION_USE_LONG_RANDOM_STRING",
        description="Secret for issuing internal JWTs",
    )
    jwt_algorithm: str = Field("HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(
        60 * 24, description="Access token expiry in minutes",
    )
    supabase_jwt_secret: Optional[str] = Field(
        None,
        description=(
            "Supabase JWT secret for verifying tokens issued by Supabase Auth; "
            "falls back to jwt_secret_key when not set"
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class RateLimitConfig(BaseSettings):
    """Configuration for rate limiting."""
    
    max_requests_per_minute: int = Field(
        60,
        description="Max API requests per minute",
    )
    max_tokens_per_request: int = Field(
        4000,
        description="Max tokens per LLM request",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AppConfig(BaseSettings):
    """
    Main application configuration.
    
    Aggregates all configuration sections and provides validation.
    """
    
    app_env: str = Field("development", description="Application environment")
    app_name: str = Field("aiagents", description="Application name")
    
    # Sub-configurations
    llm: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    supabase: SupabaseConfig = Field(default_factory=SupabaseConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env.lower() == "development"
    
    def validate_required_config(self) -> None:
        """
        Validate that required configuration is present.
        
        Raises ValueError if critical config is missing in production.
        """
        if self.is_production():
            # In production, require at least one LLM provider
            if not self.llm.openai_api_key and not self.llm.anthropic_api_key:
                raise ValueError(
                    "Production requires at least one LLM provider API key"
                )

            # Require observability in production
            if not self.observability.enable_metrics:
                raise ValueError("Metrics must be enabled in production")

            # Require Supabase JWT secret when Supabase URL configured
            if self.supabase.supabase_url and not self.supabase.supabase_jwt_secret:
                raise ValueError(
                    "SUPABASE_JWT_SECRET is required in production when SUPABASE_URL is set"
                )


# Global config instance (lazy loaded)
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get application configuration (singleton pattern).
    
    Loads config from environment variables and .env file.
    """
    global _config
    if _config is None:
        _config = AppConfig(
            llm=LLMProviderConfig(),
            vector_store=VectorStoreConfig(),
            redis=RedisConfig(),
            database=DatabaseConfig(),
            observability=ObservabilityConfig(),
            supabase=SupabaseConfig(),
            email=EmailConfig(),
            auth=AuthConfig(),
            agent=AgentConfig(),
            rate_limit=RateLimitConfig(),
        )
        _config.validate_required_config()
    return _config

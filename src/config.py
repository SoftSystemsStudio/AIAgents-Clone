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
    )


class VectorStoreConfig(BaseSettings):
    """Configuration for vector databases."""
    
    qdrant_host: str = Field("localhost", description="Qdrant host")
    qdrant_port: int = Field(6333, description="Qdrant port")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant API key")
    
    chroma_persist_dir: Optional[str] = Field(None, description="ChromaDB persist directory")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class RedisConfig(BaseSettings):
    """Configuration for Redis."""
    
    redis_host: str = Field("localhost", description="Redis host")
    redis_port: int = Field(6379, description="Redis port")
    redis_password: Optional[str] = Field(None, description="Redis password")
    redis_db: int = Field(0, description="Redis database number")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


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
    enable_metrics: bool = Field(True, description="Enable Prometheus metrics")
    metrics_port: int = Field(9090, description="Metrics server port")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
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
    agent: AgentConfig = Field(default_factory=AgentConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
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
            agent=AgentConfig(),
            rate_limit=RateLimitConfig(),
        )
        _config.validate_required_config()
    return _config

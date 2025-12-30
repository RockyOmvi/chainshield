"""
ChainShield Configuration Module

Loads all settings from environment variables with validation.
No hardcoded values - everything is configurable.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = Field(default="chainshield", description="Application name")
    app_env: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(..., description="Secret key for signing")
    api_v1_prefix: str = Field(default="/api/v1", description="API prefix")
    
    # -------------------------------------------------------------------------
    # Server
    # -------------------------------------------------------------------------
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=4, description="Number of workers")
    reload: bool = Field(default=False, description="Auto-reload")
    
    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_max_overflow: int = Field(default=20, description="Max overflow connections")
    database_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    
    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    redis_cache_ttl: int = Field(default=3600, description="Default cache TTL")
    redis_rate_limit_prefix: str = Field(default="rate:", description="Rate limit key prefix")
    
    # -------------------------------------------------------------------------
    # Blockchain Providers
    # -------------------------------------------------------------------------
    alchemy_api_key: Optional[str] = Field(default=None, description="Alchemy API key")
    alchemy_network: str = Field(default="eth-mainnet", description="Alchemy network")
    
    infura_api_key: Optional[str] = Field(default=None, description="Infura API key")
    infura_network: str = Field(default="mainnet", description="Infura network")
    
    public_rpc_url: str = Field(
        default="https://eth.llamarpc.com",
        description="Public RPC fallback URL"
    )
    
    blockchain_timeout: int = Field(default=30, description="RPC timeout in seconds")
    blockchain_max_retries: int = Field(default=5, description="Max retry attempts")
    blockchain_retry_delay: float = Field(default=1.0, description="Base retry delay")
    
    # -------------------------------------------------------------------------
    # AI Providers
    # -------------------------------------------------------------------------
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model")
    openai_max_tokens: int = Field(default=1000, description="Max tokens")
    openai_temperature: float = Field(default=0.3, description="Temperature")
    
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Claude model")
    
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama URL")
    ollama_model: str = Field(default="llama2", description="Ollama model")
    
    ai_cache_ttl: int = Field(default=3600, description="AI response cache TTL")
    ai_max_retries: int = Field(default=3, description="AI provider max retries")
    
    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Global per-minute limit")
    rate_limit_requests_per_hour: int = Field(default=1000, description="Global per-hour limit")
    
    rate_limit_wallet_analyze: int = Field(default=100, description="Wallet analyze per hour")
    rate_limit_tx_analyze: int = Field(default=200, description="TX analyze per hour")
    rate_limit_ai_explain: int = Field(default=50, description="AI explain per hour")
    
    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    jwt_secret_key: str = Field(..., description="JWT signing key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, description="Access token TTL")
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh token TTL")
    
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_key_prefix: str = Field(default="cs_", description="API key prefix")
    
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")
    
    # -------------------------------------------------------------------------
    # Circuit Breaker
    # -------------------------------------------------------------------------
    circuit_breaker_failure_threshold: int = Field(default=5, description="Failures to open")
    circuit_breaker_recovery_timeout: int = Field(default=30, description="Recovery timeout")
    circuit_breaker_half_open_requests: int = Field(default=2, description="Half-open test requests")
    
    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # -------------------------------------------------------------------------
    # Risk Engine
    # -------------------------------------------------------------------------
    risk_model_path: str = Field(
        default="app/services/risk/models/risk_model.pkl",
        description="Path to risk model"
    )
    risk_score_cache_ttl: int = Field(default=1800, description="Risk score cache TTL")
    risk_high_threshold: int = Field(default=70, description="High risk threshold")
    risk_medium_threshold: int = Field(default=40, description="Medium risk threshold")
    
    # -------------------------------------------------------------------------
    # Data Retention
    # -------------------------------------------------------------------------
    data_retention_hot_days: int = Field(default=90, description="Hot storage days")
    data_retention_archive_enabled: bool = Field(default=True, description="Enable archival")
    data_archive_s3_bucket: Optional[str] = Field(default=None, description="Archive bucket")
    
    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    feature_ai_explanations: bool = Field(default=True, description="Enable AI explanations")
    feature_graph_analysis: bool = Field(default=True, description="Enable graph analysis")
    feature_real_time_alerts: bool = Field(default=True, description="Enable real-time alerts")
    
    # -------------------------------------------------------------------------
    # OpenTelemetry
    # -------------------------------------------------------------------------
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    otel_service_name: str = Field(default="chainshield", description="OTEL service name")
    otel_exporter_endpoint: Optional[str] = Field(
        default=None, 
        description="OTLP exporter endpoint (e.g., http://localhost:4317)"
    )
    otel_sample_rate: float = Field(default=1.0, description="Trace sample rate 0.0-1.0")
    
    # -------------------------------------------------------------------------
    # Monitoring
    # -------------------------------------------------------------------------
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus")
    prometheus_port: int = Field(default=9090, description="Prometheus port")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env == "development"
    
    @property
    def alchemy_url(self) -> Optional[str]:
        """Get Alchemy RPC URL."""
        if self.alchemy_api_key:
            return f"https://{self.alchemy_network}.g.alchemy.com/v2/{self.alchemy_api_key}"
        return None
    
    @property
    def infura_url(self) -> Optional[str]:
        """Get Infura RPC URL."""
        if self.infura_api_key:
            return f"https://{self.infura_network}.infura.io/v3/{self.infura_api_key}"
        return None
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to avoid reloading on every request.
    """
    return Settings()


# Convenience export
settings = get_settings()

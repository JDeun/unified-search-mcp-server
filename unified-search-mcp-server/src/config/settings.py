# src/config/settings.py
"""
Application settings management using Pydantic v2
"""
import os
from typing import Optional, List, Any, Dict
from functools import lru_cache
import logging

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with Pydantic v2 patterns"""
    
    model_config = ConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='forbid'
    )
    
    # Environment settings
    environment: str = Field(default="development", alias="MCP_ENV")
    debug: bool = Field(default=False, alias="MCP_DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", alias="MCP_HOST")
    port: int = Field(default=8000, alias="MCP_PORT", ge=1, le=65535)
    workers: int = Field(default=1, alias="MCP_WORKERS", ge=1, le=100)
    
    # Logging settings
    log_level: str = Field(default="INFO", alias="MCP_LOG_LEVEL")
    log_file: str = Field(default="unified_search.log", alias="MCP_LOG_FILE")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        alias="MCP_LOG_FORMAT"
    )
    
    # Cache settings
    cache_ttl: int = Field(default=3600, alias="MCP_CACHE_TTL", ge=60, le=86400)
    cache_max_size: int = Field(default=1000, alias="MCP_CACHE_MAX_SIZE", ge=100, le=10000)
    redis_url: Optional[str] = Field(default=None, alias="MCP_REDIS_URL")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="MCP_RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="MCP_RATE_LIMIT_REQUESTS", ge=1)
    rate_limit_window: int = Field(default=3600, alias="MCP_RATE_LIMIT_WINDOW", ge=60)
    
    # Search settings
    max_results_per_source: int = Field(default=50, alias="MCP_MAX_RESULTS", ge=1, le=100)
    default_results_count: int = Field(default=10, alias="MCP_DEFAULT_RESULTS", ge=1, le=50)
    search_timeout: int = Field(default=30, alias="MCP_SEARCH_TIMEOUT", ge=5, le=120)
    
    # Google Scholar settings
    scholar_rate_limit_delay: float = Field(default=2.0, alias="MCP_SCHOLAR_DELAY", ge=1.0, le=10.0)
    scholar_max_retries: int = Field(default=3, alias="MCP_SCHOLAR_RETRIES", ge=1, le=5)
    scholar_retry_delay: float = Field(default=5.0, alias="MCP_SCHOLAR_RETRY_DELAY", ge=1.0, le=30.0)
    
    # API Rate Limits (daily limits)
    google_web_daily_limit: int = Field(default=100, alias="MCP_GOOGLE_WEB_LIMIT", ge=1)
    youtube_daily_limit: int = Field(default=100, alias="MCP_YOUTUBE_LIMIT", ge=1)
    
    # Monitoring settings
    metrics_enabled: bool = Field(default=True, alias="MCP_METRICS_ENABLED")
    metrics_port: int = Field(default=9090, alias="MCP_METRICS_PORT", ge=1, le=65535)
    tracing_enabled: bool = Field(default=False, alias="MCP_TRACING_ENABLED")
    tracing_endpoint: Optional[str] = Field(default=None, alias="MCP_TRACING_ENDPOINT")
    
    # Security settings
    cors_enabled: bool = Field(default=True, alias="MCP_CORS_ENABLED")
    cors_origins: List[str] = Field(default=["*"], alias="MCP_CORS_ORIGINS")
    request_id_header: str = Field(default="X-Request-ID", alias="MCP_REQUEST_ID_HEADER")
    
    # External service timeouts
    http_timeout: int = Field(default=30, alias="MCP_HTTP_TIMEOUT", ge=5, le=120)
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {', '.join(allowed_envs)}")
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {', '.join(allowed_levels)}")
        return v.upper()
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return v.split(',')
        return v
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == 'development'
    
    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        handlers = {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'level': self.log_level,
            }
        }
        
        # Add file handler only if log file is specified
        if self.log_file:
            handlers['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': self.log_file,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'json' if self.is_production() else 'default',
                'level': self.log_level,
            }
        
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': self.log_format,
                },
                'json': {
                    'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
                    'class': 'pythonjsonlogger.jsonlogger.JsonFormatter' if self.is_production() else 'logging.Formatter'
                }
            },
            'handlers': handlers,
            'root': {
                'level': self.log_level,
                'handlers': list(handlers.keys())
            }
        }


@lru_cache()
def get_settings() -> Settings:
    """Get settings singleton"""
    return Settings()


# Environment-specific overrides
def get_environment_settings() -> Dict[str, Any]:
    """Get environment-specific additional settings"""
    settings = get_settings()
    
    overrides = {
        'development': {
            'debug': True,
            'log_level': 'DEBUG',
            'rate_limit_enabled': False,
            'metrics_enabled': False,
        },
        'staging': {
            'debug': False,
            'log_level': 'INFO',
            'rate_limit_enabled': True,
            'metrics_enabled': True,
        },
        'production': {
            'debug': False,
            'log_level': 'WARNING',
            'rate_limit_enabled': True,
            'metrics_enabled': True,
            'tracing_enabled': True,
        }
    }
    
    return overrides.get(settings.environment, {})

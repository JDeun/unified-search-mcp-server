# src/config/security.py
"""
Security configuration and API key management
"""
import os
import re
import secrets
import hashlib
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, field_validator, ConfigDict
import logging

logger = logging.getLogger(__name__)


class SecurityConfig(BaseModel):
    """Security configuration with validation"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    google_api_key: Optional[str] = Field(default=None, min_length=20, max_length=100)
    google_cse_id: Optional[str] = Field(default=None, min_length=10, max_length=50)
    youtube_api_key: Optional[str] = Field(default=None, min_length=20, max_length=100)
    encryption_key: Optional[str] = Field(default=None)
    max_query_length: int = Field(default=500, ge=50, le=1000)
    allowed_origins: List[str] = Field(default=["*"])
    rate_limit_secret: Optional[str] = Field(default=None)
    
    @field_validator('google_api_key', 'youtube_api_key')
    @classmethod
    def validate_api_key_format(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^[A-Za-z0-9\-_]+$', v):
            raise ValueError("Invalid API key format")
        return v
    
    @field_validator('google_cse_id')
    @classmethod
    def validate_cse_id_format(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^[A-Za-z0-9\-_:]+$', v):
            raise ValueError("Invalid CSE ID format")
        return v


class SecureKeyManager:
    """API key security manager"""
    
    def __init__(self):
        self._encryption_key = self._get_or_create_encryption_key()
        self._fernet = Fernet(self._encryption_key)
        self._key_cache: Dict[str, bytes] = {}
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key"""
        key_env = os.getenv("MCP_ENCRYPTION_KEY")
        if key_env:
            # Ensure key is valid Fernet key
            try:
                return key_env.encode() if len(key_env) == 44 else Fernet.generate_key()
            except Exception:
                logger.warning("Invalid encryption key format, generating new one")
                return Fernet.generate_key()
        
        # Production requires environment variable
        if os.getenv("MCP_ENV") == "production":
            raise ValueError("MCP_ENCRYPTION_KEY must be set in production")
            
        # Auto-generate for development only
        logger.warning("Generating temporary encryption key for development")
        return Fernet.generate_key()
    
    def encrypt_key(self, key: str, key_name: str) -> str:
        """Encrypt API key"""
        if not key:
            return ""
        
        # Use key hash as cache key
        cache_key = hashlib.sha256(f"{key_name}:{key}".encode()).hexdigest()
        
        if cache_key not in self._key_cache:
            encrypted = self._fernet.encrypt(key.encode())
            self._key_cache[cache_key] = encrypted
        
        return self._key_cache[cache_key].decode()
    
    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt API key"""
        if not encrypted_key:
            return ""
        
        try:
            decrypted = self._fernet.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt key: {e}")
            raise ValueError("Invalid encrypted key")


class InputSanitizer:
    """Input validation and sanitization"""
    
    # XSS prevention patterns
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe[^>]*>', re.IGNORECASE),
        re.compile(r'<object[^>]*>', re.IGNORECASE),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
    ]
    
    # SQL Injection prevention patterns
    SQL_PATTERNS = [
        re.compile(r'(union|select|insert|update|delete|drop|create)\s', re.IGNORECASE),
        re.compile(r'(--|#|/\*|\*/)', re.IGNORECASE),
        re.compile(r"('|\"|;|\\)", re.IGNORECASE),
    ]
    
    @classmethod
    def sanitize_query(cls, query: str, max_length: int = 500) -> str:
        """Sanitize search query"""
        if not query:
            return ""
        
        # Length limit
        query = query[:max_length]
        
        # Remove XSS patterns
        for pattern in cls.XSS_PATTERNS:
            query = pattern.sub('', query)
        
        # Remove HTML tags
        query = re.sub(r'<[^>]+>', '', query)
        
        # Normalize special characters
        query = query.replace('\x00', '')  # Null byte
        query = re.sub(r'\s+', ' ', query)  # Remove consecutive spaces
        query = query.strip()
        
        return query
    
    @classmethod
    def validate_numeric_param(
        cls, 
        value: Any, 
        min_val: Optional[int] = None, 
        max_val: Optional[int] = None
    ) -> int:
        """Validate numeric parameter"""
        try:
            num_value = int(value)
        except (ValueError, TypeError):
            raise ValueError("Invalid numeric parameter")
        
        if min_val is not None and num_value < min_val:
            raise ValueError(f"Value must be at least {min_val}")
        
        if max_val is not None and num_value > max_val:
            raise ValueError(f"Value must be at most {max_val}")
        
        return num_value
    
    @classmethod
    def validate_enum_param(cls, value: str, allowed_values: List[str]) -> str:
        """Validate enum parameter"""
        if value not in allowed_values:
            raise ValueError(f"Value must be one of: {', '.join(allowed_values)}")
        return value


class RateLimitManager:
    """Rate limiting manager"""
    
    def __init__(self, secret: Optional[str] = None):
        self.secret = secret or secrets.token_urlsafe(32)
        self._request_counts: Dict[str, List[float]] = {}
        
    def generate_request_id(self, client_id: str, endpoint: str) -> str:
        """Generate request ID"""
        data = f"{client_id}:{endpoint}:{self.secret}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def check_rate_limit(
        self, 
        client_id: str, 
        endpoint: str, 
        max_requests: int = 100, 
        window_seconds: int = 3600
    ) -> bool:
        """Check rate limit"""
        request_id = self.generate_request_id(client_id, endpoint)
        current_time = secrets.SystemRandom().uniform(0, 1)  # Timing attack prevention
        
        # TODO: Replace with Redis-based implementation
        # This is a temporary in-memory implementation
        return True


# Singleton instances
_security_config: Optional[SecurityConfig] = None
_key_manager: Optional[SecureKeyManager] = None
_rate_limiter: Optional[RateLimitManager] = None


def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    global _security_config
    
    if _security_config is None:
        _security_config = SecurityConfig(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            google_cse_id=os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID"),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
            encryption_key=os.getenv("MCP_ENCRYPTION_KEY"),
            rate_limit_secret=os.getenv("MCP_RATE_LIMIT_SECRET"),
            allowed_origins=os.getenv("MCP_ALLOWED_ORIGINS", "*").split(",")
        )
    
    return _security_config


def get_key_manager() -> SecureKeyManager:
    """Get key manager"""
    global _key_manager
    
    if _key_manager is None:
        _key_manager = SecureKeyManager()
    
    return _key_manager


def get_rate_limiter() -> RateLimitManager:
    """Get rate limiter"""
    global _rate_limiter
    
    if _rate_limiter is None:
        config = get_security_config()
        _rate_limiter = RateLimitManager(config.rate_limit_secret)
    
    return _rate_limiter

# src/models/__init__.py
"""
데이터 모델 및 에러 정의
"""
from .search import (
    SearchSource,
    SafeSearchLevel,
    VideoDuration,
    UploadDate,
    SortOrder,
    BaseResult,
    ScholarResult,
    WebResult,
    YouTubeResult,
    SearchRequest,
    SearchResponse,
    APIUsageStats
)
from .errors import (
    ErrorResponse,
    ValidationError,
    ServiceError,
    ExternalAPIError,
    RateLimitError,
    TimeoutError,
    CacheError,
    handle_unexpected_error
)

__all__ = [
    # Enums
    'SearchSource',
    'SafeSearchLevel',
    'VideoDuration',
    'UploadDate',
    'SortOrder',
    
    # Results
    'BaseResult',
    'ScholarResult',
    'WebResult',
    'YouTubeResult',
    
    # Requests/Responses
    'SearchRequest',
    'SearchResponse',
    'APIUsageStats',
    
    # Errors
    'ErrorResponse',
    'ValidationError',
    'ServiceError',
    'ExternalAPIError',
    'RateLimitError',
    'TimeoutError',
    'CacheError',
    'handle_unexpected_error',
]

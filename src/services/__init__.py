# src/services/__init__.py
"""
검색 서비스 모듈
"""
from typing import Optional

from .base import BaseSearchService, RetryMixin, ConcurrentSearchMixin
from .scholar import GoogleScholarService
from .web import GoogleWebService
from .youtube import YouTubeService
from .unified import UnifiedSearchService, get_unified_service

# 서비스 인스턴스
_scholar_service: Optional[GoogleScholarService] = None
_web_service: Optional[GoogleWebService] = None
_youtube_service: Optional[YouTubeService] = None


def create_scholar_service() -> GoogleScholarService:
    """Scholar 서비스 생성"""
    global _scholar_service
    if _scholar_service is None:
        _scholar_service = GoogleScholarService()
    return _scholar_service


def create_web_search_service() -> GoogleWebService:
    """Web 검색 서비스 생성"""
    global _web_service
    if _web_service is None:
        _web_service = GoogleWebService()
    return _web_service


def create_youtube_service() -> YouTubeService:
    """YouTube 서비스 생성"""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service


__all__ = [
    # Base classes
    'BaseSearchService',
    'RetryMixin',
    'ConcurrentSearchMixin',
    
    # Services
    'GoogleScholarService',
    'GoogleWebService',
    'YouTubeService',
    'UnifiedSearchService',
    
    # Factory functions
    'get_unified_service',
    'create_scholar_service',
    'create_web_search_service',
    'create_youtube_service',
]

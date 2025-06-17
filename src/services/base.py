# src/services/base.py
"""
서비스 베이스 클래스
공통 기능 및 인터페이스 정의
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, TypeVar, Generic
import asyncio
import logging
from datetime import datetime

import httpx

from ..config import get_settings, get_security_config
from ..models import ServiceError, ExternalAPIError, TimeoutError
from ..cache import get_cache_manager, cached
from ..utils import get_logger, PerformanceLogger, get_audit_logger
from ..monitoring import MetricsCollector

T = TypeVar('T')

logger = get_logger(__name__)


class BaseSearchService(ABC, Generic[T]):
    """검색 서비스 베이스 클래스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.security_config = get_security_config()
        self.cache_manager = get_cache_manager()
        self.audit_logger = get_audit_logger()
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """서비스 이름"""
        pass
    
    @property
    @abstractmethod
    def api_base_url(self) -> str:
        """API 베이스 URL"""
        pass
    
    async def get_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 가져오기 (연결 풀링)"""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self.settings.http_timeout),
                        limits=httpx.Limits(
                            max_keepalive_connections=5,
                            max_connections=10
                        ),
                        headers=self._get_default_headers()
                    )
        return self._client
    
    def _get_default_headers(self) -> Dict[str, str]:
        """기본 헤더"""
        return {
            'User-Agent': f'UnifiedSearchMCP/{self.settings.environment}',
            'Accept': 'application/json',
        }
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[T]:
        """검색 수행"""
        pass
    
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """HTTP 요청 수행"""
        client = await self.get_client()
        
        async with PerformanceLogger(
            f"{self.service_name}_request",
            logger
        ).add_context(method=method, url=url) as perf:
            
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                
                # 메트릭 기록
                MetricsCollector.record_api_call(
                    api=self.service_name,
                    endpoint=url,
                    success=True,
                    duration=perf.duration if hasattr(perf, 'duration') else 0
                )
                
                return response
                
            except httpx.TimeoutException as e:
                MetricsCollector.record_api_call(
                    api=self.service_name,
                    endpoint=url,
                    success=False,
                    duration=self.settings.http_timeout
                )
                raise TimeoutError(
                    service=self.service_name,
                    timeout=self.settings.http_timeout,
                    details={'url': url}
                )
                
            except httpx.HTTPStatusError as e:
                MetricsCollector.record_api_call(
                    api=self.service_name,
                    endpoint=url,
                    success=False,
                    duration=perf.duration if hasattr(perf, 'duration') else 0
                )
                
                # 상태 코드별 처리
                if e.response.status_code == 429:
                    # Rate limit
                    retry_after = e.response.headers.get('Retry-After', '60')
                    raise ExternalAPIError(
                        service=self.service_name,
                        message=f"Rate limit exceeded. Retry after {retry_after}s",
                        details={
                            'status_code': 429,
                            'retry_after': retry_after
                        }
                    )
                elif e.response.status_code >= 500:
                    # 서버 에러
                    raise ExternalAPIError(
                        service=self.service_name,
                        message=f"Server error: {e.response.status_code}",
                        details={'status_code': e.response.status_code}
                    )
                else:
                    # 클라이언트 에러
                    raise ExternalAPIError(
                        service=self.service_name,
                        message=f"Client error: {e.response.status_code}",
                        details={
                            'status_code': e.response.status_code,
                            'response': e.response.text[:500]  # 응답 일부
                        }
                    )
                    
            except Exception as e:
                MetricsCollector.record_error(
                    error_type=type(e).__name__,
                    source=self.service_name
                )
                raise
    
    async def close(self):
        """리소스 정리"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def log_search(
        self,
        query: str,
        results_count: int,
        duration: float,
        **extra
    ):
        """검색 감사 로그"""
        self.audit_logger.log_search(
            query=query,
            source=self.service_name,
            results_count=results_count,
            duration=duration,
            **extra
        )


class RetryMixin:
    """재시도 믹스인"""
    
    async def retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ):
        """지수 백오프로 재시도"""
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
                else:
                    logger.error(f"All {max_retries} attempts failed")
        
        raise last_exception


class ConcurrentSearchMixin:
    """동시 검색 믹스인"""
    
    async def search_concurrently(
        self,
        search_funcs: List[tuple],
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """동시 검색 수행"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_search(name: str, func):
            async with semaphore:
                try:
                    return name, await func()
                except Exception as e:
                    logger.error(f"Search {name} failed: {e}")
                    return name, {'error': str(e)}
        
        tasks = [
            limited_search(name, func)
            for name, func in search_funcs
        ]
        
        results = await asyncio.gather(*tasks)
        return dict(results)

# src/cache/decorators.py
"""
캐시 데코레이터
함수 결과를 자동으로 캐싱하는 데코레이터
"""
import functools
import inspect
from typing import Optional, Callable, Any
import logging

from .manager import get_cache_manager

logger = logging.getLogger(__name__)


def cached(
    ttl: Optional[int] = None,
    source: Optional[str] = None,
    key_prefix: Optional[str] = None
):
    """
    캐시 데코레이터
    
    Args:
        ttl: 캐시 TTL (초)
        source: 캐시 소스 (통계용)
        key_prefix: 키 프리픽스
    """
    def decorator(func: Callable) -> Callable:
        # 비동기 함수인지 확인
        is_async = inspect.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache_manager = get_cache_manager()
                
                # 캐시 키 생성
                cache_key_data = {
                    'func': func.__name__,
                    'args': str(args),
                    'kwargs': str(sorted(kwargs.items())),
                    'source': source or func.__module__
                }
                
                if key_prefix:
                    cache_key_data['prefix'] = key_prefix
                
                cache_key = cache_manager.make_key(**cache_key_data)
                
                # 캐시 조회
                cached_value = await cache_manager.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"캐시에서 반환: {func.__name__}")
                    return cached_value
                
                # 함수 실행
                result = await func(*args, **kwargs)
                
                # 캐시 저장
                await cache_manager.set(
                    cache_key,
                    result,
                    ttl=ttl,
                    source=source
                )
                
                return result
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 동기 함수는 캐싱하지 않음 (현재 비동기 전용)
                logger.warning(f"동기 함수 {func.__name__}에는 캐싱이 지원되지 않습니다")
                return func(*args, **kwargs)
            
            return sync_wrapper
    
    return decorator


def invalidate_cache(source: Optional[str] = None):
    """
    캐시 무효화 데코레이터
    함수 실행 후 특정 소스의 캐시를 무효화
    
    Args:
        source: 무효화할 캐시 소스 (None이면 전체)
    """
    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 함수 실행
                result = await func(*args, **kwargs)
                
                # 캐시 무효화
                cache_manager = get_cache_manager()
                await cache_manager.clear(source=source)
                logger.info(f"캐시 무효화됨: {source or '전체'}")
                
                return result
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                logger.warning(f"동기 함수 {func.__name__}에서는 캐시 무효화가 지원되지 않습니다")
                return result
            
            return sync_wrapper
    
    return decorator


class CacheKey:
    """캐시 키 생성 도우미"""
    
    @staticmethod
    def for_search(query: str, source: str, **filters) -> str:
        """검색용 캐시 키 생성"""
        cache_manager = get_cache_manager()
        return cache_manager.make_key(
            type='search',
            query=query,
            source=source,
            filters=filters
        )
    
    @staticmethod
    def for_author(author_name: str) -> str:
        """저자 정보용 캐시 키 생성"""
        cache_manager = get_cache_manager()
        return cache_manager.make_key(
            type='author',
            author_name=author_name,
            source='scholar'
        )
    
    @staticmethod
    def for_api_stats(service: str) -> str:
        """API 통계용 캐시 키 생성"""
        cache_manager = get_cache_manager()
        return cache_manager.make_key(
            type='api_stats',
            service=service,
            source='stats'
        )

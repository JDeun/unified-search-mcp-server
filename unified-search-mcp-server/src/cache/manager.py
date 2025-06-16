# src/cache/manager.py
"""
캐시 관리자
Redis 기반 분산 캐싱 및 로컬 폴백
"""
import json
import asyncio
import hashlib
from typing import Optional, Any, Dict, TypeVar, Generic
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
import pickle

import redis.asyncio as redis
from cachetools import TTLCache

from ..config import get_settings
from ..models import CacheError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheBackend(ABC, Generic[T]):
    """캐시 백엔드 인터페이스"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[T]:
        """캐시에서 값 가져오기"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """캐시에 값 설정"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        pass
    
    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """캐시 클리어"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        pass
    
    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """TTL 확인"""
        pass


class RedisCache(CacheBackend[Any]):
    """Redis 캐시 백엔드"""
    
    def __init__(self, redis_url: str, key_prefix: str = "mcp"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()
    
    async def _get_client(self) -> redis.Redis:
        """Redis 클라이언트 가져오기"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = await redis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=False
                    )
        return self._client
    
    def _make_key(self, key: str) -> str:
        """키 생성"""
        return f"{self.key_prefix}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            value = await client.get(full_key)
            
            if value is None:
                return None
            
            # 역직렬화
            return pickle.loads(value)
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            raise CacheError(f"캐시 조회 실패: {e}")
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 설정"""
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            
            # 직렬화
            serialized = pickle.dumps(value)
            
            if ttl:
                await client.setex(full_key, ttl, serialized)
            else:
                await client.set(full_key, serialized)
            
            return True
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            raise CacheError(f"캐시 설정 실패: {e}")
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            result = await client.delete(full_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            raise CacheError(f"캐시 삭제 실패: {e}")
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """캐시 클리어"""
        try:
            client = await self._get_client()
            
            if pattern:
                search_pattern = self._make_key(f"{pattern}*")
            else:
                search_pattern = self._make_key("*")
            
            count = 0
            async for key in client.scan_iter(match=search_pattern):
                await client.delete(key)
                count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            raise CacheError(f"캐시 클리어 실패: {e}")
    
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            return await client.exists(full_key) > 0
            
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """TTL 확인"""
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            ttl = await client.ttl(full_key)
            return ttl if ttl > 0 else None
            
        except Exception as e:
            logger.error(f"Redis TTL error: {e}")
            return None
    
    async def close(self):
        """연결 종료"""
        if self._client:
            await self._client.close()
            self._client = None


class LocalCache(CacheBackend[Any]):
    """로컬 메모리 캐시 백엔드 (폴백용)"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache = TTLCache(maxsize=max_size, ttl=default_ttl)
        self.default_ttl = default_ttl
        self._ttls: Dict[str, datetime] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.error(f"Local cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 설정"""
        try:
            self.cache[key] = value
            if ttl:
                self._ttls[key] = datetime.utcnow() + timedelta(seconds=ttl)
            return True
        except Exception as e:
            logger.error(f"Local cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            if key in self.cache:
                del self.cache[key]
                if key in self._ttls:
                    del self._ttls[key]
                return True
            return False
        except Exception as e:
            logger.error(f"Local cache delete error: {e}")
            return False
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """캐시 클리어"""
        try:
            if pattern:
                keys_to_delete = [k for k in self.cache.keys() if k.startswith(pattern)]
                for key in keys_to_delete:
                    del self.cache[key]
                    if key in self._ttls:
                        del self._ttls[key]
                return len(keys_to_delete)
            else:
                count = len(self.cache)
                self.cache.clear()
                self._ttls.clear()
                return count
        except Exception as e:
            logger.error(f"Local cache clear error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return key in self.cache
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """TTL 확인"""
        if key in self._ttls:
            remaining = (self._ttls[key] - datetime.utcnow()).total_seconds()
            return int(remaining) if remaining > 0 else None
        return None
    
    async def close(self):
        """리소스 정리 (로컬 캐시는 정리할 것 없음)"""
        pass


class CacheManager:
    """캐시 관리자 - 전략 패턴 사용"""
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        self.settings = get_settings()
        self.backend = backend or self._create_backend()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
    
    def _create_backend(self) -> CacheBackend:
        """백엔드 생성"""
        if self.settings.redis_url:
            try:
                return RedisCache(self.settings.redis_url)
            except Exception as e:
                logger.warning(f"Redis 캐시 생성 실패: {e}, 로컬 캐시로 폴백")
        
        return LocalCache(
            max_size=self.settings.cache_max_size,
            default_ttl=self.settings.cache_ttl
        )
    
    def make_key(self, **kwargs) -> str:
        """캐시 키 생성"""
        # 키 정규화 및 해싱
        key_data = json.dumps(kwargs, sort_keys=True)
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        
        # 소스별 프리픽스 추가
        source = kwargs.get('source', 'general')
        return f"{source}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        try:
            value = await self.backend.get(key)
            if value is not None:
                self._stats['hits'] += 1
                logger.debug(f"캐시 히트: {key}")
            else:
                self._stats['misses'] += 1
                logger.debug(f"캐시 미스: {key}")
            return value
            
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"캐시 조회 오류: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        source: Optional[str] = None
    ) -> bool:
        """캐시에 값 설정"""
        try:
            # 기본 TTL 사용
            if ttl is None:
                ttl = self.settings.cache_ttl
            
            success = await self.backend.set(key, value, ttl)
            if success:
                self._stats['sets'] += 1
                logger.debug(f"캐시 설정: {key} (TTL: {ttl}초)")
            
            return success
            
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"캐시 설정 오류: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            success = await self.backend.delete(key)
            if success:
                self._stats['deletes'] += 1
                logger.debug(f"캐시 삭제: {key}")
            return success
            
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"캐시 삭제 오류: {e}")
            return False
    
    async def clear(self, source: Optional[str] = None) -> int:
        """캐시 클리어"""
        try:
            pattern = f"{source}:" if source else None
            count = await self.backend.clear(pattern)
            logger.info(f"캐시 클리어됨: {count}개 항목 (소스: {source or '전체'})")
            return count
            
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"캐시 클리어 오류: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 가져오기"""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self._stats,
            'total_requests': total_requests,
            'hit_rate': round(hit_rate, 2)
        }
    
    async def close(self):
        """리소스 정리"""
        await self.backend.close()


# 싱글톤 인스턴스
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """캐시 관리자 싱글톤 가져오기"""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager

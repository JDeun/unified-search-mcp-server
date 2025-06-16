# src/utils/rate_limiter.py
"""
Rate Limiting 유틸리티
Redis 기반 분산 rate limiting
"""
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

import redis.asyncio as redis

from ..config import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """분산 Rate Limiter"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.redis_url
        self._client: Optional[redis.Redis] = None
        self._local_cache: Dict[str, list] = {}  # 폴백용 로컬 캐시
        self._lock = asyncio.Lock()
    
    async def _get_client(self) -> Optional[redis.Redis]:
        """Redis 클라이언트 가져오기"""
        if not self.redis_url:
            return None
            
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        self._client = await redis.from_url(self.redis_url)
                        await self._client.ping()  # 연결 테스트
                    except Exception as e:
                        logger.warning(f"Redis 연결 실패: {e}")
                        return None
        
        return self._client
    
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        burst: Optional[int] = None
    ) -> tuple[bool, Optional[int]]:
        """
        Rate limit 체크
        
        Args:
            key: Rate limit 키 (예: "user:123:search")
            max_requests: 윈도우당 최대 요청 수
            window_seconds: 윈도우 크기 (초)
            burst: 순간 최대 허용량 (선택)
            
        Returns:
            (허용 여부, 재시도까지 남은 시간)
        """
        client = await self._get_client()
        
        if client:
            return await self._check_redis(client, key, max_requests, window_seconds, burst)
        else:
            return await self._check_local(key, max_requests, window_seconds, burst)
    
    async def _check_redis(
        self,
        client: redis.Redis,
        key: str,
        max_requests: int,
        window_seconds: int,
        burst: Optional[int]
    ) -> tuple[bool, Optional[int]]:
        """Redis 기반 rate limit 체크 (sliding window)"""
        now = time.time()
        window_start = now - window_seconds
        
        # Lua 스크립트로 원자적 실행
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        
        -- 오래된 항목 제거
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        
        -- 현재 카운트
        local current = redis.call('ZCARD', key)
        
        if current < max_requests then
            -- 새 요청 추가
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, ARGV[4])
            return {1, 0}
        else
            -- 가장 오래된 항목의 만료 시간 계산
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            if #oldest > 0 then
                local retry_after = math.ceil(oldest[2] + tonumber(ARGV[4]) - now)
                return {0, retry_after}
            else
                return {0, 1}
            end
        end
        """
        
        try:
            result = await client.eval(
                lua_script,
                1,
                f"rate_limit:{key}",
                str(now),
                str(window_start),
                str(max_requests),
                str(window_seconds)
            )
            
            allowed = bool(result[0])
            retry_after = int(result[1]) if result[1] else None
            
            return allowed, retry_after
            
        except Exception as e:
            logger.error(f"Redis rate limit 오류: {e}")
            return True, None  # 오류 시 허용
    
    async def _check_local(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        burst: Optional[int]
    ) -> tuple[bool, Optional[int]]:
        """로컬 메모리 기반 rate limit 체크 (간단한 구현)"""
        now = time.time()
        window_start = now - window_seconds
        
        # 요청 기록 가져오기
        if key not in self._local_cache:
            self._local_cache[key] = []
        
        requests = self._local_cache[key]
        
        # 오래된 요청 제거
        requests = [ts for ts in requests if ts > window_start]
        self._local_cache[key] = requests
        
        # 체크
        if len(requests) < max_requests:
            requests.append(now)
            return True, None
        else:
            # 가장 오래된 요청의 만료 시간
            oldest = min(requests)
            retry_after = int(oldest + window_seconds - now) + 1
            return False, retry_after
    
    async def reset_limit(self, key: str):
        """특정 키의 rate limit 리셋"""
        client = await self._get_client()
        
        if client:
            await client.delete(f"rate_limit:{key}")
        else:
            if key in self._local_cache:
                del self._local_cache[key]
    
    async def get_usage(self, key: str, window_seconds: int) -> Dict[str, Any]:
        """현재 사용량 조회"""
        client = await self._get_client()
        now = time.time()
        window_start = now - window_seconds
        
        if client:
            redis_key = f"rate_limit:{key}"
            await client.zremrangebyscore(redis_key, 0, window_start)
            count = await client.zcard(redis_key)
        else:
            if key in self._local_cache:
                requests = [ts for ts in self._local_cache[key] if ts > window_start]
                count = len(requests)
            else:
                count = 0
        
        return {
            "key": key,
            "current_usage": count,
            "window_seconds": window_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        """리소스 정리"""
        if self._client:
            await self._client.close()
            self._client = None


# 싱글톤 인스턴스
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Rate limiter 싱글톤"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# 데코레이터
def rate_limit(
    resource: str,
    max_requests: int = 100,
    window_seconds: int = 3600,
    burst: Optional[int] = None
):
    """Rate limit 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 클라이언트 ID 추출 (컨텍스트에서)
            from .logging import client_id_var
            client_id = client_id_var.get() or "anonymous"
            
            # Rate limit 키
            key = f"{client_id}:{resource}"
            
            # Rate limit 체크
            limiter = get_rate_limiter()
            allowed, retry_after = await limiter.check_rate_limit(
                key, max_requests, window_seconds, burst
            )
            
            if not allowed:
                from ..models import RateLimitError
                raise RateLimitError(
                    service=resource,
                    retry_after=retry_after
                )
            
            # 함수 실행
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

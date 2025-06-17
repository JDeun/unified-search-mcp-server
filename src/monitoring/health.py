# src/monitoring/health.py
"""
헬스 체크 및 준비 상태 확인
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import logging

from pydantic import BaseModel, Field

from ..config import get_settings
from ..cache import get_cache_manager

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """헬스 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """컴포넌트 헬스 정보"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckResult(BaseModel):
    """헬스 체크 결과"""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    environment: str
    uptime_seconds: float
    components: List[ComponentHealth] = Field(default_factory=list)


class HealthChecker:
    """헬스 체커"""
    
    def __init__(self):
        self.settings = get_settings()
        self.start_time = datetime.utcnow()
    
    async def check_health(self) -> HealthCheckResult:
        """전체 헬스 체크"""
        components = []
        
        # 캐시 헬스 체크
        cache_health = await self._check_cache_health()
        components.append(cache_health)
        
        # Redis 헬스 체크 (설정된 경우)
        if self.settings.redis_url:
            redis_health = await self._check_redis_health()
            components.append(redis_health)
        
        # 서비스 헬스 체크
        services_health = await self._check_services_health()
        components.extend(services_health)
        
        # 전체 상태 결정
        overall_status = self._determine_overall_status(components)
        
        # 업타임 계산
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return HealthCheckResult(
            status=overall_status,
            environment=self.settings.environment,
            uptime_seconds=uptime,
            components=components
        )
    
    async def _check_cache_health(self) -> ComponentHealth:
        """캐시 헬스 체크"""
        try:
            cache_manager = get_cache_manager()
            stats = cache_manager.get_stats()
            
            # 에러율 체크
            error_rate = (stats['errors'] / max(stats['total_requests'], 1)) * 100
            
            if error_rate > 10:
                status = HealthStatus.UNHEALTHY
                message = f"높은 에러율: {error_rate:.1f}%"
            elif error_rate > 5:
                status = HealthStatus.DEGRADED
                message = f"에러율 상승: {error_rate:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"정상 (히트율: {stats['hit_rate']:.1f}%)"
            
            return ComponentHealth(
                name="cache",
                status=status,
                message=message,
                metadata=stats
            )
            
        except Exception as e:
            logger.error(f"캐시 헬스 체크 실패: {e}")
            return ComponentHealth(
                name="cache",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    
    async def _check_redis_health(self) -> ComponentHealth:
        """Redis 헬스 체크"""
        try:
            from ..utils import get_rate_limiter
            rate_limiter = get_rate_limiter()
            
            # Redis 연결 테스트
            client = await rate_limiter._get_client()
            if client:
                await client.ping()
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="연결됨"
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    message="연결 실패 (로컬 폴백 사용 중)"
                )
                
        except Exception as e:
            logger.error(f"Redis 헬스 체크 실패: {e}")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    
    async def _check_services_health(self) -> List[ComponentHealth]:
        """서비스 헬스 체크"""
        services_health = []
        
        # 각 서비스 확인
        from ..services import get_unified_service
        unified_service = get_unified_service()
        
        service_status = await unified_service.get_service_status()
        
        for service_name, status in service_status.items():
            health_status = HealthStatus.HEALTHY
            if status['status'] == 'unhealthy':
                health_status = HealthStatus.UNHEALTHY
            elif status['status'] == 'error':
                health_status = HealthStatus.DEGRADED
            
            services_health.append(ComponentHealth(
                name=f"service_{service_name}",
                status=health_status,
                message=status.get('error'),
                metadata=status
            ))
        
        return services_health
    
    def _determine_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """전체 상태 결정"""
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            return HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in components):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY


class ReadinessChecker:
    """준비 상태 체커"""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def check_readiness(self) -> Dict[str, Any]:
        """준비 상태 확인"""
        checks = {
            "cache": await self._check_cache_ready(),
            "config": self._check_config_ready(),
            "services": await self._check_services_ready()
        }
        
        ready = all(checks.values())
        
        return {
            "ready": ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _check_cache_ready(self) -> bool:
        """캐시 준비 상태"""
        try:
            cache_manager = get_cache_manager()
            # 테스트 키로 읽기/쓰기 테스트
            test_key = "_readiness_test"
            await cache_manager.set(test_key, "test", ttl=10)
            value = await cache_manager.get(test_key)
            await cache_manager.delete(test_key)
            return value == "test"
        except Exception:
            return False
    
    def _check_config_ready(self) -> bool:
        """설정 준비 상태"""
        from ..config import get_security_config
        security_config = get_security_config()
        
        # 최소한 하나의 서비스는 사용 가능해야 함
        return any([
            True,  # Scholar는 항상 사용 가능
            (security_config.google_api_key and security_config.google_cse_id),
            security_config.youtube_api_key
        ])
    
    async def _check_services_ready(self) -> bool:
        """서비스 준비 상태"""
        try:
            from ..services import get_unified_service
            unified_service = get_unified_service()
            status = await unified_service.get_service_status()
            
            # 최소 하나의 서비스는 사용 가능해야 함
            return any(
                s.get('available', False) 
                for s in status.values()
            )
        except Exception:
            return False


# 싱글톤 인스턴스
_health_checker: Optional[HealthChecker] = None
_readiness_checker: Optional[ReadinessChecker] = None


def get_health_checker() -> HealthChecker:
    """헬스 체커 싱글톤"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def get_readiness_checker() -> ReadinessChecker:
    """준비 상태 체커 싱글톤"""
    global _readiness_checker
    if _readiness_checker is None:
        _readiness_checker = ReadinessChecker()
    return _readiness_checker

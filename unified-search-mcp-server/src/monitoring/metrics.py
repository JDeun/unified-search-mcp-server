# src/monitoring/metrics.py
"""
메트릭 수집 및 Prometheus 통합
"""
from typing import Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    REGISTRY, generate_latest,
    make_asgi_app
)
from prometheus_client.core import CollectorRegistry

from ..config import get_settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """메트릭 수집기"""
    
    # 검색 메트릭
    search_requests_total = Counter(
        'mcp_search_requests_total',
        'Total number of search requests',
        ['source', 'status']
    )
    
    search_duration_seconds = Histogram(
        'mcp_search_duration_seconds',
        'Search request duration in seconds',
        ['source'],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
    )
    
    # API 호출 메트릭
    api_calls_total = Counter(
        'mcp_api_calls_total',
        'Total number of API calls',
        ['api', 'endpoint', 'status']
    )
    
    api_call_duration_seconds = Histogram(
        'mcp_api_call_duration_seconds',
        'API call duration in seconds',
        ['api', 'endpoint'],
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )
    
    # 캐시 메트릭
    cache_hits_total = Counter(
        'mcp_cache_hits_total',
        'Total number of cache hits',
        ['source']
    )
    
    cache_misses_total = Counter(
        'mcp_cache_misses_total',
        'Total number of cache misses',
        ['source']
    )
    
    cache_size = Gauge(
        'mcp_cache_size',
        'Current cache size',
        ['source']
    )
    
    # Rate limit 메트릭
    rate_limit_requests_total = Counter(
        'mcp_rate_limit_requests_total',
        'Total number of rate limited requests',
        ['resource', 'status']
    )
    
    # 에러 메트릭
    errors_total = Counter(
        'mcp_errors_total',
        'Total number of errors',
        ['error_type', 'source']
    )
    
    # 시스템 정보
    system_info = Info(
        'mcp_system',
        'System information'
    )
    
    @classmethod
    def init_metrics(cls):
        """메트릭 초기화"""
        settings = get_settings()
        
        cls.system_info.info({
            'version': '1.0.0',
            'environment': settings.environment,
            'python_version': '3.10+'
        })
    
    @classmethod
    def record_search(cls, source: str, success: bool, duration: float):
        """검색 메트릭 기록"""
        status = 'success' if success else 'failure'
        cls.search_requests_total.labels(source=source, status=status).inc()
        if success:
            cls.search_duration_seconds.labels(source=source).observe(duration)
    
    @classmethod
    def record_api_call(
        cls, 
        api: str, 
        endpoint: str, 
        success: bool, 
        duration: float
    ):
        """API 호출 메트릭 기록"""
        status = 'success' if success else 'failure'
        cls.api_calls_total.labels(
            api=api, 
            endpoint=endpoint, 
            status=status
        ).inc()
        
        if success:
            cls.api_call_duration_seconds.labels(
                api=api,
                endpoint=endpoint
            ).observe(duration)
    
    @classmethod
    def record_cache_hit(cls, source: str):
        """캐시 히트 기록"""
        cls.cache_hits_total.labels(source=source).inc()
    
    @classmethod
    def record_cache_miss(cls, source: str):
        """캐시 미스 기록"""
        cls.cache_misses_total.labels(source=source).inc()
    
    @classmethod
    def update_cache_size(cls, source: str, size: int):
        """캐시 크기 업데이트"""
        cls.cache_size.labels(source=source).set(size)
    
    @classmethod
    def record_rate_limit(cls, resource: str, allowed: bool):
        """Rate limit 메트릭 기록"""
        status = 'allowed' if allowed else 'blocked'
        cls.rate_limit_requests_total.labels(
            resource=resource,
            status=status
        ).inc()
    
    @classmethod
    def record_error(cls, error_type: str, source: str):
        """에러 메트릭 기록"""
        cls.errors_total.labels(
            error_type=error_type,
            source=source
        ).inc()
    
    @classmethod
    def get_metrics(cls) -> bytes:
        """Prometheus 형식으로 메트릭 반환"""
        return generate_latest(REGISTRY)


class MetricsServer:
    """메트릭 서버"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self.app = make_asgi_app()
        self.server = None
        self.server_task = None
    
    async def start(self):
        """메트릭 서버 시작"""
        try:
            import uvicorn
            
            config = uvicorn.Config(
                app=self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="warning",
                access_log=False
            )
            
            self.server = uvicorn.Server(config)
            self.server_task = asyncio.create_task(self.server.serve())
            
            logger.info(f"메트릭 서버 시작됨: http://0.0.0.0:{self.port}/metrics")
            
        except Exception as e:
            logger.error(f"메트릭 서버 시작 실패: {e}")
    
    async def stop(self):
        """메트릭 서버 중지"""
        if self.server:
            self.server.should_exit = True
            if self.server_task:
                await self.server_task


# 싱글톤 인스턴스
_metrics_server: Optional[MetricsServer] = None


def get_metrics_server(port: int = 9090) -> MetricsServer:
    """메트릭 서버 싱글톤"""
    global _metrics_server
    if _metrics_server is None:
        _metrics_server = MetricsServer(port)
        MetricsCollector.init_metrics()
    return _metrics_server

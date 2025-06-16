# src/services/unified.py
"""
통합 검색 서비스
여러 소스에서 동시에 검색 수행
"""
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

from .base import ConcurrentSearchMixin
from .scholar import GoogleScholarService
from .web import GoogleWebService
from .youtube import YouTubeService
from ..models import (
    SearchSource, SearchRequest, SearchResponse,
    ScholarResult, WebResult, YouTubeResult,
    APIUsageStats
)
from ..config import get_settings
from ..cache import get_cache_manager, cached
from ..utils import PerformanceLogger, get_audit_logger
from ..monitoring import MetricsCollector

logger = logging.getLogger(__name__)


class UnifiedSearchService(ConcurrentSearchMixin):
    """통합 검색 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_manager = get_cache_manager()
        self.audit_logger = get_audit_logger()
        
        # 서비스 초기화
        self.services = {
            SearchSource.SCHOLAR: GoogleScholarService(),
            SearchSource.WEB: GoogleWebService(),
            SearchSource.YOUTUBE: YouTubeService()
        }
    
    @cached(ttl=1800, source="unified")  # 30분 캐시
    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        통합 검색 수행
        
        Args:
            request: 검색 요청 객체
            
        Returns:
            SearchResponse: 통합 검색 결과
        """
        start_time = datetime.utcnow()
        
        async with PerformanceLogger(
            "unified_search",
            logger
        ).add_context(
            query=request.query,
            sources=[s.value for s in request.sources]
        ):
            
            # 검색 작업 준비
            search_tasks = []
            for source in request.sources:
                if source in self.services:
                    search_tasks.append((
                        source,
                        self._search_source(source, request)
                    ))
            
            # 동시 검색 실행
            results_dict = await self.search_concurrently(
                search_tasks,
                max_concurrent=len(search_tasks)  # 모든 소스 동시 실행
            )
            
            # 결과 정리
            results: Dict[SearchSource, List[Union[ScholarResult, WebResult, YouTubeResult]]] = {}
            errors: Dict[SearchSource, str] = {}
            
            for source, result in results_dict.items():
                if isinstance(result, dict) and 'error' in result:
                    errors[source] = result['error']
                    results[source] = []
                else:
                    results[source] = result
            
            # 검색 시간 계산
            search_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 응답 생성
            response = SearchResponse(
                query=request.query,
                results=results,
                search_time=search_time,
                errors=errors,
                metadata={
                    'requested_sources': [s.value for s in request.sources],
                    'successful_sources': [s.value for s in results.keys() if s not in errors],
                    'cache_hit': False  # 캐시 데코레이터가 처리
                }
            )
            
            # 감사 로그
            self.audit_logger.log_search(
                query=request.query,
                source="unified",
                results_count=response.total_results,
                duration=search_time,
                metadata=response.metadata
            )
            
            # 메트릭 기록
            for source in request.sources:
                success = source not in errors
                MetricsCollector.record_search(
                    source=source.value,
                    success=success,
                    duration=search_time / len(request.sources)  # 평균 시간
                )
            
            return response
    
    async def _search_source(
        self,
        source: SearchSource,
        request: SearchRequest
    ) -> List[Union[ScholarResult, WebResult, YouTubeResult]]:
        """개별 소스 검색"""
        service = self.services[source]
        
        try:
            # 소스별 파라미터 준비
            if source == SearchSource.SCHOLAR:
                results = await service.search(
                    query=request.query,
                    num_results=request.num_results,
                    author=request.author,
                    year_start=request.year_start,
                    year_end=request.year_end
                )
            elif source == SearchSource.WEB:
                results = await service.search(
                    query=request.query,
                    num_results=request.num_results,
                    language=request.language,
                    safe_search=request.safe_search
                )
            elif source == SearchSource.YOUTUBE:
                results = await service.search(
                    query=request.query,
                    num_results=request.num_results,
                    video_duration=request.video_duration,
                    upload_date=request.upload_date,
                    order=request.sort_order
                )
            else:
                results = []
            
            return results
            
        except Exception as e:
            logger.error(f"{source.value} 검색 오류: {e}")
            raise
    
    async def get_api_usage_stats(self) -> APIUsageStats:
        """API 사용량 통계 조회"""
        stats = APIUsageStats()
        
        # 캐시 통계
        cache_stats = self.cache_manager.get_stats()
        for source in SearchSource:
            stats.cache_stats[source.value] = {
                'size': cache_stats.get('total_requests', 0),
                'hit_rate': cache_stats.get('hit_rate', 0)
            }
        
        # API 한도 정보
        stats.limits['google_web'] = {
            'daily_limit': self.settings.google_web_daily_limit,
            'used': stats.usage.get('google_web', 0),
            'remaining': max(0, self.settings.google_web_daily_limit - stats.usage.get('google_web', 0))
        }
        
        stats.limits['youtube'] = {
            'daily_limit': self.settings.youtube_daily_limit,
            'used': stats.usage.get('youtube', 0),
            'remaining': max(0, self.settings.youtube_daily_limit - stats.usage.get('youtube', 0))
        }
        
        return stats
    
    async def get_service_status(self) -> Dict[str, Any]:
        """서비스 상태 조회"""
        status = {}
        
        for source, service in self.services.items():
            try:
                # 서비스 헬스 체크
                is_healthy = await service.health_check() if hasattr(service, 'health_check') else True
                status[source.value] = {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'available': True
                }
            except Exception as e:
                status[source.value] = {
                    'status': 'error',
                    'available': False,
                    'error': str(e)
                }
        
        return status
    
    async def close(self):
        """리소스 정리"""
        # 모든 서비스 종료
        close_tasks = [
            service.close() 
            for service in self.services.values()
        ]
        await asyncio.gather(*close_tasks, return_exceptions=True)


# 싱글톤 인스턴스
_unified_service: Optional[UnifiedSearchService] = None


def get_unified_service() -> UnifiedSearchService:
    """통합 검색 서비스 싱글톤"""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedSearchService()
    return _unified_service

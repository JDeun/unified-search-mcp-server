# src/services/web.py
"""
Google Web 검색 서비스
Google Custom Search API를 사용한 웹 검색
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .base import BaseSearchService
from ..models import WebResult, SearchSource, SafeSearchLevel, ExternalAPIError
from ..cache import cached

logger = logging.getLogger(__name__)


class GoogleWebService(BaseSearchService[WebResult]):
    """Google Web 검색 서비스"""
    
    @property
    def service_name(self) -> str:
        return "google_web"
    
    @property
    def api_base_url(self) -> str:
        return "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self):
        super().__init__()
        
        # API 키 확인
        if not self.security_config.google_api_key:
            raise ValueError("Google API 키가 설정되지 않았습니다")
        
        if not self.security_config.google_cse_id:
            raise ValueError("Google Custom Search Engine ID가 설정되지 않았습니다")
        
        # API 키 복호화
        self._api_key = self.security_config.google_api_key
        self._cse_id = self.security_config.google_cse_id
    
    @cached(ttl=3600, source="web")  # 1시간 캐시
    async def search(
        self,
        query: str,
        num_results: int = 10,
        language: str = "en",
        safe_search: SafeSearchLevel = SafeSearchLevel.MEDIUM
    ) -> List[WebResult]:
        """
        Google 웹 검색
        
        Args:
            query: 검색어
            num_results: 결과 수 (최대 10)
            language: 언어 코드
            safe_search: 세이프서치 레벨
            
        Returns:
            검색 결과 리스트
        """
        # Google Custom Search는 한 번에 최대 10개
        num_results = min(num_results, 10)
        
        # API 파라미터
        params = {
            "key": self._api_key,
            "cx": self._cse_id,
            "q": query,
            "num": num_results,
            "lr": f"lang_{language}",
            "safe": safe_search.value
        }
        
        # API 호출
        response = await self._make_request("GET", self.api_base_url, params=params)
        data = response.json()
        
        # 결과 파싱
        results = []
        items = data.get("items", [])
        
        for item in items:
            try:
                result = self._parse_result(item)
                results.append(result)
            except Exception as e:
                logger.error(f"결과 파싱 오류: {e}")
                continue
        
        # 로깅
        self.log_search(
            query=query,
            results_count=len(results),
            duration=0,
            language=language,
            safe_search=safe_search.value
        )
        
        return results
    
    def _parse_result(self, item: Dict[str, Any]) -> WebResult:
        """검색 결과 파싱"""
        # 이미지 URL 추출
        image_url = None
        if "pagemap" in item and "cse_image" in item["pagemap"]:
            images = item["pagemap"]["cse_image"]
            if images and len(images) > 0:
                image_url = images[0].get("src")
        
        return WebResult(
            title=item.get("title", "No title"),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
            source=SearchSource.WEB,
            display_link=item.get("displayLink", ""),
            image_url=image_url
        )
    
    async def check_quota(self) -> Dict[str, Any]:
        """API 할당량 확인"""
        # Google Custom Search API는 직접적인 할당량 확인 API가 없음
        # 일일 한도와 사용량을 추적해야 함
        daily_limit = self.settings.google_web_daily_limit
        
        # 실제 구현에서는 Redis나 DB에서 사용량 추적
        used = 0  # TODO: 실제 사용량 조회
        
        return {
            "daily_limit": daily_limit,
            "used": used,
            "remaining": max(0, daily_limit - used),
            "reset_time": "00:00 UTC"
        }
    
    async def health_check(self) -> bool:
        """서비스 헬스 체크"""
        try:
            # 간단한 검색으로 테스트
            params = {
                "key": self._api_key,
                "cx": self._cse_id,
                "q": "test",
                "num": 1
            }
            
            response = await self._make_request("GET", self.api_base_url, params=params)
            return response.status_code == 200
        except Exception:
            return False

# src/services/scholar.py
"""
Google Scholar 검색 서비스
scholarly 라이브러리를 사용한 학술 검색
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from scholarly import scholarly, ProxyGenerator
from scholarly.publication import Publication
from scholarly.author import Author

from .base import BaseSearchService, RetryMixin
from ..models import ScholarResult, SearchSource, ServiceError, TimeoutError
from ..config import get_settings
from ..cache import cached, CacheKey

logger = logging.getLogger(__name__)


class GoogleScholarService(BaseSearchService[ScholarResult], RetryMixin):
    """Google Scholar 검색 서비스"""
    
    @property
    def service_name(self) -> str:
        return "google_scholar"
    
    @property
    def api_base_url(self) -> str:
        return "https://scholar.google.com"
    
    def __init__(self):
        super().__init__()
        self._setup_scholarly()
        self._semaphore = asyncio.Semaphore(1)  # Scholar는 순차 처리 필요
    
    def _setup_scholarly(self):
        """scholarly 설정"""
        # 프록시 설정 (필요한 경우)
        if self.settings.is_production():
            try:
                pg = ProxyGenerator()
                pg.ScraperAPI(self.security_config.scraper_api_key)
                scholarly.use_proxy(pg)
            except Exception as e:
                logger.warning(f"프록시 설정 실패: {e}")
    
    @cached(ttl=7200, source="scholar")  # 2시간 캐시
    async def search(
        self,
        query: str,
        num_results: int = 10,
        author: Optional[str] = None,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None
    ) -> List[ScholarResult]:
        """
        Google Scholar 검색
        
        Args:
            query: 검색어
            num_results: 결과 수
            author: 저자 필터
            year_start: 시작 연도
            year_end: 종료 연도
            
        Returns:
            검색 결과 리스트
        """
        async with self._semaphore:  # Rate limiting
            return await self.retry_with_backoff(
                lambda: self._search_impl(query, num_results, author, year_start, year_end),
                max_retries=self.settings.scholar_max_retries,
                initial_delay=self.settings.scholar_retry_delay
            )
    
    async def _search_impl(
        self,
        query: str,
        num_results: int,
        author: Optional[str],
        year_start: Optional[int],
        year_end: Optional[int]
    ) -> List[ScholarResult]:
        """실제 검색 구현"""
        # 쿼리 구성
        search_query = query
        if author:
            search_query = f'author:"{author}" {search_query}'
        
        # 검색 실행을 별도 스레드에서
        loop = asyncio.get_event_loop()
        
        def search_sync():
            results = []
            try:
                # scholarly 검색
                search_results = scholarly.search_pubs(search_query)
                
                for i, result in enumerate(search_results):
                    if i >= num_results:
                        break
                    
                    # 결과 파싱
                    try:
                        # 연도 필터
                        pub_year = result.get('bib', {}).get('pub_year')
                        if pub_year:
                            try:
                                year = int(pub_year)
                                if year_start and year < year_start:
                                    continue
                                if year_end and year > year_end:
                                    continue
                            except ValueError:
                                pass
                        
                        # ScholarResult 생성
                        scholar_result = self._parse_result(result)
                        results.append(scholar_result)
                        
                        # Rate limiting을 위한 지연
                        if i < num_results - 1:
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                asyncio.sleep(self.settings.scholar_rate_limit_delay)
                            )
                    
                    except Exception as e:
                        logger.error(f"결과 파싱 오류: {e}")
                        continue
                
                return results
                
            except Exception as e:
                logger.error(f"Scholar 검색 오류: {e}")
                raise ServiceError(
                    service="scholar",
                    message=f"검색 실패: {str(e)}",
                    user_message="학술 검색 중 오류가 발생했습니다."
                )
        
        # 동기 함수를 비동기로 실행
        results = await loop.run_in_executor(None, search_sync)
        
        # 로깅
        self.log_search(
            query=query,
            results_count=len(results),
            duration=0,  # scholarly는 시간 측정이 어려움
            author=author,
            year_range=f"{year_start}-{year_end}" if year_start or year_end else None
        )
        
        return results
    
    def _parse_result(self, pub_data: Dict[str, Any]) -> ScholarResult:
        """검색 결과 파싱"""
        bib = pub_data.get('bib', {})
        
        # 저자 처리
        authors = bib.get('author', '').split(' and ')
        if authors == ['']:
            authors = []
        
        # URL 처리
        url = pub_data.get('pub_url', '')
        if not url:
            url = pub_data.get('eprint_url', '')
        if not url:
            url = f"https://scholar.google.com/scholar?q={bib.get('title', '')}"
        
        # PDF URL
        pdf_url = pub_data.get('eprint_url')
        
        # 인용 수
        citations = pub_data.get('num_citations', 0)
        
        # 연도
        year = None
        pub_year = bib.get('pub_year')
        if pub_year:
            try:
                year = int(pub_year)
            except ValueError:
                pass
        
        return ScholarResult(
            title=bib.get('title', 'No title'),
            url=url,
            snippet=bib.get('abstract', ''),
            source=SearchSource.SCHOLAR,
            authors=authors,
            year=year,
            citations=citations,
            pdf_url=pdf_url,
            journal=bib.get('venue', '')
        )
    
    @cached(ttl=86400, source="scholar_author")  # 24시간 캐시
    async def get_author_info(self, author_name: str) -> Dict[str, Any]:
        """
        저자 정보 조회
        
        Args:
            author_name: 저자 이름
            
        Returns:
            저자 정보 딕셔너리
        """
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            
            def get_author_sync():
                try:
                    # 저자 검색
                    search_query = scholarly.search_author(author_name)
                    author = next(search_query, None)
                    
                    if not author:
                        return {"error": "저자를 찾을 수 없습니다."}
                    
                    # 상세 정보 조회
                    author = scholarly.fill(author)
                    
                    # 정보 추출
                    return {
                        "name": author.get("name", author_name),
                        "affiliation": author.get("affiliation", ""),
                        "email": author.get("email", ""),
                        "interests": author.get("interests", []),
                        "citedby": author.get("citedby", 0),
                        "publications": len(author.get("publications", [])),
                        "h_index": author.get("hindex", 0),
                        "i10_index": author.get("i10index", 0),
                        "url": author.get("url_picture", ""),
                        "homepage": author.get("homepage", "")
                    }
                    
                except Exception as e:
                    logger.error(f"저자 정보 조회 오류: {e}")
                    return {"error": str(e)}
            
            return await loop.run_in_executor(None, get_author_sync)
    
    async def health_check(self) -> bool:
        """서비스 헬스 체크"""
        try:
            # 간단한 검색으로 테스트
            results = await self.search("test", num_results=1)
            return True
        except Exception:
            return False
    
    async def close(self):
        """리소스 정리"""
        await super().close()

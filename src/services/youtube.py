# src/services/youtube.py
"""
YouTube 검색 서비스
YouTube Data API v3를 사용한 동영상 검색
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .base import BaseSearchService
from ..models import (
    YouTubeResult, SearchSource, 
    VideoDuration, UploadDate, SortOrder,
    ExternalAPIError
)
from ..cache import cached

logger = logging.getLogger(__name__)


class YouTubeService(BaseSearchService[YouTubeResult]):
    """YouTube 검색 서비스"""
    
    @property
    def service_name(self) -> str:
        return "youtube"
    
    @property
    def api_base_url(self) -> str:
        return "https://www.googleapis.com/youtube/v3"
    
    def __init__(self):
        super().__init__()
        
        # API 키 확인
        if not self.security_config.youtube_api_key:
            raise ValueError("YouTube API 키가 설정되지 않았습니다")
        
        self._api_key = self.security_config.youtube_api_key
    
    @cached(ttl=3600, source="youtube")  # 1시간 캐시
    async def search(
        self,
        query: str,
        num_results: int = 10,
        video_duration: Optional[VideoDuration] = None,
        upload_date: Optional[UploadDate] = None,
        order: SortOrder = SortOrder.RELEVANCE
    ) -> List[YouTubeResult]:
        """
        YouTube 동영상 검색
        
        Args:
            query: 검색어
            num_results: 결과 수 (최대 50)
            video_duration: 동영상 길이 필터
            upload_date: 업로드 날짜 필터
            order: 정렬 순서
            
        Returns:
            검색 결과 리스트
        """
        # YouTube API는 한 번에 최대 50개
        num_results = min(num_results, 50)
        
        # API 파라미터
        params = {
            "key": self._api_key,
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": num_results,
            "order": order.value
        }
        
        # 동영상 길이 필터
        if video_duration:
            params["videoDuration"] = video_duration.value
        
        # 업로드 날짜 필터
        if upload_date:
            published_after = self._calculate_published_after(upload_date)
            if published_after:
                params["publishedAfter"] = published_after
        
        # API 호출
        search_url = f"{self.api_base_url}/search"
        response = await self._make_request("GET", search_url, params=params)
        data = response.json()
        
        # 비디오 ID 수집
        video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
        
        if not video_ids:
            return []
        
        # 비디오 상세 정보 조회
        details = await self._get_video_details(video_ids)
        
        # 결과 파싱
        results = []
        for item, detail in zip(data.get("items", []), details):
            try:
                result = self._parse_result(item, detail)
                results.append(result)
            except Exception as e:
                logger.error(f"결과 파싱 오류: {e}")
                continue
        
        # 로깅
        self.log_search(
            query=query,
            results_count=len(results),
            duration=0,
            video_duration=video_duration.value if video_duration else None,
            upload_date=upload_date.value if upload_date else None,
            order=order.value
        )
        
        return results
    
    async def _get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """비디오 상세 정보 조회"""
        params = {
            "key": self._api_key,
            "part": "contentDetails,statistics",
            "id": ",".join(video_ids)
        }
        
        videos_url = f"{self.api_base_url}/videos"
        response = await self._make_request("GET", videos_url, params=params)
        data = response.json()
        
        return data.get("items", [])
    
    def _parse_result(
        self, 
        search_item: Dict[str, Any], 
        detail_item: Dict[str, Any]
    ) -> YouTubeResult:
        """검색 결과 파싱"""
        snippet = search_item["snippet"]
        video_id = search_item["id"]["videoId"]
        
        # 통계 정보
        statistics = detail_item.get("statistics", {})
        view_count = int(statistics.get("viewCount", 0))
        like_count = int(statistics.get("likeCount", 0))
        
        # 동영상 길이
        content_details = detail_item.get("contentDetails", {})
        duration = content_details.get("duration", "")
        
        # 발행일
        publish_date = None
        published_at = snippet.get("publishedAt")
        if published_at:
            try:
                publish_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except Exception:
                pass
        
        # 썸네일 URL (고화질 우선)
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url") or
            thumbnails.get("medium", {}).get("url") or
            thumbnails.get("default", {}).get("url")
        )
        
        return YouTubeResult(
            title=snippet.get("title", "No title"),
            url=f"https://www.youtube.com/watch?v={video_id}",
            snippet=snippet.get("description", ""),
            source=SearchSource.YOUTUBE,
            video_id=video_id,
            channel_name=snippet.get("channelTitle", ""),
            channel_id=snippet.get("channelId", ""),
            duration=self._format_duration(duration),
            view_count=view_count,
            like_count=like_count,
            publish_date=publish_date,
            thumbnail_url=thumbnail_url
        )
    
    def _calculate_published_after(self, upload_date: UploadDate) -> Optional[str]:
        """업로드 날짜 필터를 RFC3339 형식으로 변환"""
        now = datetime.utcnow()
        
        if upload_date == UploadDate.HOUR:
            date = now - timedelta(hours=1)
        elif upload_date == UploadDate.TODAY:
            date = now - timedelta(days=1)
        elif upload_date == UploadDate.WEEK:
            date = now - timedelta(weeks=1)
        elif upload_date == UploadDate.MONTH:
            date = now - timedelta(days=30)
        elif upload_date == UploadDate.YEAR:
            date = now - timedelta(days=365)
        else:
            return None
        
        return date.isoformat() + "Z"
    
    def _format_duration(self, iso_duration: str) -> str:
        """ISO 8601 duration을 읽기 쉬운 형식으로 변환"""
        if not iso_duration:
            return ""
        
        # PT15M33S -> 15:33
        # PT1H2M10S -> 1:02:10
        try:
            # 간단한 파싱 (완전하지 않음)
            duration = iso_duration.replace("PT", "")
            
            hours = 0
            minutes = 0
            seconds = 0
            
            if "H" in duration:
                hours_part = duration.split("H")[0]
                hours = int(hours_part)
                duration = duration.split("H")[1]
            
            if "M" in duration:
                minutes_part = duration.split("M")[0]
                minutes = int(minutes_part)
                duration = duration.split("M")[1]
            
            if "S" in duration:
                seconds_part = duration.split("S")[0]
                seconds = int(seconds_part)
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
                
        except Exception:
            return iso_duration
    
    async def check_quota(self) -> Dict[str, Any]:
        """API 할당량 확인"""
        # YouTube API는 일일 10,000 유닛
        # 검색은 100 유닛 소비
        daily_limit = self.settings.youtube_daily_limit
        units_per_search = 100
        
        # 실제 구현에서는 Redis나 DB에서 사용량 추적
        used = 0  # TODO: 실제 사용량 조회
        
        return {
            "daily_limit_searches": daily_limit,
            "daily_limit_units": daily_limit * units_per_search,
            "used_searches": used,
            "used_units": used * units_per_search,
            "remaining_searches": max(0, daily_limit - used),
            "remaining_units": max(0, (daily_limit - used) * units_per_search),
            "reset_time": "00:00 PT (Pacific Time)"
        }
    
    async def health_check(self) -> bool:
        """서비스 헬스 체크"""
        try:
            # API 키 확인을 위한 간단한 요청
            params = {
                "key": self._api_key,
                "part": "snippet",
                "q": "test",
                "type": "video",
                "maxResults": 1
            }
            
            search_url = f"{self.api_base_url}/search"
            response = await self._make_request("GET", search_url, params=params)
            return response.status_code == 200
        except Exception:
            return False

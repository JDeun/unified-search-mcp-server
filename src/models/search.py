# src/models/search.py
"""
Search models and data structures using Pydantic v2
"""
from enum import Enum
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, ConfigDict


class SearchSource(str, Enum):
    """Search source types"""
    SCHOLAR = "scholar"
    WEB = "web"
    YOUTUBE = "youtube"


class SafeSearchLevel(str, Enum):
    """Safe search levels for web search"""
    HIGH = "high"
    MEDIUM = "medium"
    OFF = "off"


class VideoDuration(str, Enum):
    """YouTube video duration filters"""
    SHORT = "short"  # < 4 minutes
    MEDIUM = "medium"  # 4-20 minutes
    LONG = "long"  # > 20 minutes


class UploadDate(str, Enum):
    """YouTube upload date filters"""
    HOUR = "hour"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class SortOrder(str, Enum):
    """YouTube sort order options"""
    RELEVANCE = "relevance"
    DATE = "date"
    RATING = "rating"
    VIEW_COUNT = "viewCount"


class BaseResult(BaseModel):
    """Base search result model"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True
    )
    
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1)
    snippet: str = Field(default="", max_length=2000)
    source: SearchSource
    search_date: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class ScholarResult(BaseResult):
    """Google Scholar search result"""
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    citations: Optional[int] = Field(default=None, ge=0)
    pdf_url: Optional[str] = None
    journal: Optional[str] = None
    
    @field_validator('pdf_url')
    @classmethod
    def validate_pdf_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('PDF URL must start with http:// or https://')
        return v


class WebResult(BaseResult):
    """Google Web search result"""
    display_link: Optional[str] = None
    image_url: Optional[str] = None
    
    @field_validator('image_url')
    @classmethod
    def validate_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Image URL must start with http:// or https://')
        return v


class YouTubeResult(BaseResult):
    """YouTube search result"""
    video_id: str = Field(..., min_length=1)
    channel_name: str = Field(..., min_length=1)
    channel_id: str = Field(..., min_length=1)
    duration: Optional[str] = None
    view_count: Optional[int] = Field(default=None, ge=0)
    like_count: Optional[int] = Field(default=None, ge=0)
    publish_date: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    
    @field_validator('thumbnail_url')
    @classmethod
    def validate_thumbnail_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Thumbnail URL must start with http:// or https://')
        return v


class SearchRequest(BaseModel):
    """Unified search request"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    query: str = Field(..., min_length=1, max_length=500)
    sources: List[SearchSource] = Field(default_factory=lambda: list(SearchSource))
    num_results: int = Field(default=10, ge=1, le=50)
    
    # Scholar-specific
    author: Optional[str] = Field(default=None, max_length=200)
    year_start: Optional[int] = Field(default=None, ge=1900, le=2100)
    year_end: Optional[int] = Field(default=None, ge=1900, le=2100)
    
    # Web-specific
    language: str = Field(default="en", min_length=2, max_length=5)
    safe_search: SafeSearchLevel = Field(default=SafeSearchLevel.MEDIUM)
    
    # YouTube-specific
    video_duration: Optional[VideoDuration] = None
    upload_date: Optional[UploadDate] = None
    sort_order: SortOrder = Field(default=SortOrder.RELEVANCE)
    
    @field_validator('year_end')
    @classmethod
    def validate_year_range(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and 'year_start' in info.data:
            year_start = info.data.get('year_start')
            if year_start and v < year_start:
                raise ValueError('year_end must be greater than or equal to year_start')
        return v


class SearchResponse(BaseModel):
    """Unified search response"""
    model_config = ConfigDict(populate_by_name=True)
    
    query: str
    results: Dict[SearchSource, List[Union[ScholarResult, WebResult, YouTubeResult]]] = Field(default_factory=dict)
    total_results: int = Field(default=0, ge=0)
    search_time: float = Field(default=0.0, ge=0.0)
    errors: Dict[SearchSource, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate total results
        self.total_results = sum(len(results) for results in self.results.values())


class APIUsageStats(BaseModel):
    """API usage statistics"""
    model_config = ConfigDict(populate_by_name=True)
    
    date: datetime = Field(default_factory=datetime.utcnow)
    usage: Dict[str, int] = Field(default_factory=dict)
    limits: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    cache_stats: Dict[str, Any] = Field(default_factory=dict)

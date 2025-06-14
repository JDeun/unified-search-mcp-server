# unified_search_server.py
from typing import Any, List, Dict, Optional, Union, Tuple
import asyncio
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
import json
import time
from collections import defaultdict

from fastmcp import FastMCP, Context
from scholarly import scholarly
import httpx
from cachetools import TTLCache
import aiohttp

# 로깅 설정 (상용 서비스 수준)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('unified_search.log', encoding='utf-8')
    ]
)

# FastMCP 서버 초기화
mcp = FastMCP("Unified Search Server 🔍")

# API 사용량 추적 (모니터링용)
api_usage = defaultdict(int)
api_errors = defaultdict(int)

# 설정
class SearchConfig:
    # API 키 (환경 변수로 설정)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID", "")  # Google Custom Search Engine ID (웹 검색용)
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    
    # Rate limiting - API 무료 할당량 고려
    RATE_LIMIT_DELAY = 1.0  # 초당 1회로 제한 (더 안전하게)
    
    # 캐시 설정
    CACHE_TTL = 3600  # 1시간
    CACHE_MAX_SIZE = 100
    
    # Google Scholar Rate Limit (scholarly 라이브러리)
    SCHOLAR_RATE_LIMIT_DELAY = 2.0  # Google Scholar는 더 엄격하게

# 캐시 초기화
scholar_cache = TTLCache(maxsize=SearchConfig.CACHE_MAX_SIZE, ttl=SearchConfig.CACHE_TTL)
web_cache = TTLCache(maxsize=SearchConfig.CACHE_MAX_SIZE, ttl=SearchConfig.CACHE_TTL)
youtube_cache = TTLCache(maxsize=SearchConfig.CACHE_MAX_SIZE, ttl=SearchConfig.CACHE_TTL)

# Rate limiting 데코레이터 (소스별로 다른 지연 시간 적용)
def rate_limit(delay: float = None):
    def decorator(func):
        last_call = [0]
        
        async def wrapper(*args, **kwargs):
            # 함수명에 따라 다른 delay 적용
            if delay is None:
                if 'scholar' in func.__name__:
                    actual_delay = SearchConfig.SCHOLAR_RATE_LIMIT_DELAY
                else:
                    actual_delay = SearchConfig.RATE_LIMIT_DELAY
            else:
                actual_delay = delay
                
            current_time = time.time()
            time_since_last_call = current_time - last_call[0]
            
            if time_since_last_call < actual_delay:
                await asyncio.sleep(actual_delay - time_since_last_call)
            
            last_call[0] = time.time()
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# 캐시 키 생성 헬퍼 함수
def create_cache_key(**kwargs) -> str:
    return json.dumps(kwargs, sort_keys=True)

# Google Scholar 검색 함수 (scholarly 라이브러리 사용)
async def search_google_scholar_internal(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """Google Scholar 내부 검색 함수"""
    try:
        # 재시도 로직 추가 (차단 대비)
        max_retries = 3
        retry_delay = 5.0
        
        for attempt in range(max_retries):
            try:
                search_query = scholarly.search_pubs(query)
                results = []
                
                for _ in range(num_results):
                    try:
                        article = await asyncio.to_thread(next, search_query)
                        result = {
                            'title': article.get('bib', {}).get('title', '제목 없음'),
                            'authors': ', '.join(article.get('bib', {}).get('author', [])),
                            'abstract': article.get('bib', {}).get('abstract', '초록 없음'),
                            'url': article.get('pub_url', 'URL 없음'),
                            'year': article.get('bib', {}).get('pub_year', '연도 미상'),
                            'citations': article.get('num_citations', 0),
                            'source': 'Google Scholar'
                        }
                        results.append(result)
                    except StopIteration:
                        break
                
                return results
                
            except Exception as e:
                if "429" in str(e) or "captcha" in str(e).lower():
                    # Rate limit 또는 CAPTCHA 감지
                    if attempt < max_retries - 1:
                        logging.warning(f"Google Scholar 차단 감지, {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                    else:
                        return [{
                            "error": "Google Scholar가 일시적으로 차단되었습니다. 잠시 후 다시 시도해주세요.",
                            "suggestion": "캐시된 결과를 사용하거나 다른 검색 소스를 이용해주세요."
                        }]
                else:
                    raise
                    
    except Exception as e:
        logging.error(f"Google Scholar 검색 오류: {str(e)}")
        return [{
            "error": f"Google Scholar 검색 실패: {str(e)}",
            "note": "Google Scholar는 공식 API가 없어 간헐적으로 실패할 수 있습니다."
        }]

async def advanced_scholar_search_internal(
    query: str, 
    author: Optional[str] = None, 
    year_range: Optional[Tuple[int, int]] = None, 
    num_results: int = 5
) -> List[Dict[str, Any]]:
    """Google Scholar 고급 검색 내부 함수"""
    try:
        # 검색 쿼리 구성
        search_terms = [query]
        if author:
            search_terms.append(f'author:"{author}"')
        
        full_query = ' '.join(search_terms)
        search_query = scholarly.search_pubs(full_query)
        
        results = []
        for _ in range(num_results * 2):  # 필터링을 위해 더 많은 결과 가져오기
            try:
                article = await asyncio.to_thread(next, search_query)
                
                # 연도 필터링
                if year_range:
                    pub_year = article.get('bib', {}).get('pub_year', '')
                    if pub_year and pub_year.isdigit():
                        year = int(pub_year)
                        if year < year_range[0] or year > year_range[1]:
                            continue
                
                result = {
                    'title': article.get('bib', {}).get('title', '제목 없음'),
                    'authors': ', '.join(article.get('bib', {}).get('author', [])),
                    'abstract': article.get('bib', {}).get('abstract', '초록 없음'),
                    'url': article.get('pub_url', 'URL 없음'),
                    'year': article.get('bib', {}).get('pub_year', '연도 미상'),
                    'citations': article.get('num_citations', 0),
                    'source': 'Google Scholar'
                }
                results.append(result)
                
                if len(results) >= num_results:
                    break
                    
            except StopIteration:
                break
                
        return results
    except Exception as e:
        logging.error(f"고급 Scholar 검색 오류: {str(e)}")
        raise

# Google Web Search (Custom Search API 사용)
async def search_google_web_internal(
    query: str, 
    num_results: int = 10,
    language: str = "en",
    safe_search: str = "medium"
) -> List[Dict[str, Any]]:
    """Google Custom Search API를 사용한 웹 검색 내부 함수"""
    if not SearchConfig.GOOGLE_API_KEY or not SearchConfig.GOOGLE_CSE_ID:
        return [{
            "error": "Google 웹 검색 API가 설정되지 않았습니다. GOOGLE_API_KEY와 GOOGLE_CUSTOM_SEARCH_ENGINE_ID 환경 변수를 설정하세요."
        }]
    
    try:
        async with httpx.AsyncClient() as client:
            params = {
                'key': SearchConfig.GOOGLE_API_KEY,
                'cx': SearchConfig.GOOGLE_CSE_ID,
                'q': query,
                'num': min(num_results, 10),  # API limit
                'lr': f'lang_{language}',
                'safe': safe_search
            }
            
            response = await client.get(
                'https://www.googleapis.com/customsearch/v1',
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                result = {
                    'title': item.get('title', '제목 없음'),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source': 'Google Web'
                }
                results.append(result)
                
            return results
            
    except Exception as e:
        logging.error(f"Google Web 검색 오류: {str(e)}")
        return [{"error": f"Google Web 검색 실패: {str(e)}"}]

# YouTube 검색 (YouTube Data API 사용)
async def search_youtube_internal(
    query: str,
    num_results: int = 10,
    video_duration: Optional[str] = None,  # short, medium, long
    upload_date: Optional[str] = None,    # hour, today, week, month, year
    order: str = "relevance"               # relevance, date, rating, viewCount
) -> List[Dict[str, Any]]:
    """YouTube Data API v3를 사용한 동영상 검색 내부 함수"""
    if not SearchConfig.YOUTUBE_API_KEY:
        return [{
            "error": "YouTube API 키가 설정되지 않았습니다. YOUTUBE_API_KEY 환경 변수를 설정하세요."
        }]
    
    try:
        async with httpx.AsyncClient() as client:
            params = {
                'part': 'snippet',
                'q': query,
                'key': SearchConfig.YOUTUBE_API_KEY,
                'maxResults': min(num_results, 50),  # API limit
                'type': 'video',
                'order': order
            }
            
            if video_duration:
                params['videoDuration'] = video_duration
                
            if upload_date:
                # upload_date에 따른 publishedAfter 계산
                now = datetime.utcnow()
                if upload_date == 'hour':
                    published_after = now - timedelta(hours=1)
                elif upload_date == 'today':
                    published_after = now - timedelta(days=1)
                elif upload_date == 'week':
                    published_after = now - timedelta(weeks=1)
                elif upload_date == 'month':
                    published_after = now - timedelta(days=30)
                elif upload_date == 'year':
                    published_after = now - timedelta(days=365)
                else:
                    published_after = None
                    
                if published_after:
                    params['publishedAfter'] = published_after.isoformat() + 'Z'
            
            response = await client.get(
                'https://www.googleapis.com/youtube/v3/search',
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                snippet = item.get('snippet', {})
                result = {
                    'title': snippet.get('title', '제목 없음'),
                    'channel': snippet.get('channelTitle', '알 수 없는 채널'),
                    'description': snippet.get('description', ''),
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    'published_at': snippet.get('publishedAt', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                    'source': 'YouTube'
                }
                results.append(result)
                
            return results
            
    except Exception as e:
        logging.error(f"YouTube 검색 오류: {str(e)}")
        return [{"error": f"YouTube 검색 실패: {str(e)}"}]

# MCP 도구 정의
@mcp.tool()
@rate_limit()  # Google Scholar는 자동으로 2초 지연
async def search_google_scholar(
    query: str, 
    num_results: int = 5,
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Search for academic papers on Google Scholar using keywords.
    
    Args:
        query: Search query string
        num_results: Number of results to return (default: 5)
        ctx: MCP context for logging
        
    Returns:
        List of dictionaries containing paper information
    """
    cache_key = create_cache_key(query=query, num_results=num_results)
    
    # 캐시 확인
    if cache_key in scholar_cache:
        await ctx.info(f"캐시된 Google Scholar 결과 반환: {query}")
        return scholar_cache[cache_key]
    
    await ctx.info(f"Google Scholar 검색 중: {query}")
    await ctx.report_progress(10, 100)
    
    try:
        results = await search_google_scholar_internal(query, num_results)
        
        # API 사용량 추적 (scholarly 라이브러리)
        if results and not (isinstance(results[0], dict) and 'error' in results[0]):
            api_usage["google_scholar"] += 1
            logging.info(f"Google Scholar 검색: {api_usage['google_scholar']}회")
        
        # 결과 캐싱
        scholar_cache[cache_key] = results
        
        await ctx.report_progress(100, 100)
        await ctx.info(f"{len(results)}개의 Google Scholar 결과 발견")
        return results
        
    except Exception as e:
        api_errors["google_scholar"] += 1
        await ctx.error(f"Google Scholar 검색 실패: {str(e)}")
        return [{"error": f"Google Scholar 검색 실패: {str(e)}"}]

@mcp.tool()
@rate_limit()  # Google Scholar는 자동으로 2초 지연
async def search_google_scholar_advanced(
    query: str,
    author: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    num_results: int = 5,
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Advanced search for academic papers on Google Scholar with filters.
    
    Args:
        query: General search query
        author: Author name to filter by
        year_start: Start year for publication date filter
        year_end: End year for publication date filter
        num_results: Number of results to return (default: 5)
        ctx: MCP context
        
    Returns:
        List of dictionaries containing paper information
    """
    year_range = None
    if year_start and year_end:
        year_range = (year_start, year_end)
    
    cache_key = create_cache_key(
        query=query, 
        author=author, 
        year_range=year_range, 
        num_results=num_results
    )
    
    # 캐시 확인
    if cache_key in scholar_cache:
        await ctx.info(f"캐시된 고급 Scholar 결과 반환")
        return scholar_cache[cache_key]
    
    await ctx.info(f"고급 Google Scholar 검색 수행 중")
    await ctx.report_progress(10, 100)
    
    try:
        results = await advanced_scholar_search_internal(
            query, author, year_range, num_results
        )
        
        # API 사용량 추적
        if results and not (isinstance(results[0], dict) and 'error' in results[0]):
            api_usage["google_scholar"] += 1
            logging.info(f"Google Scholar 고급 검색: {api_usage['google_scholar']}회")
        
        # 결과 캐싱
        scholar_cache[cache_key] = results
        
        await ctx.report_progress(100, 100)
        await ctx.info(f"{len(results)}개의 결과 발견")
        return results
        
    except Exception as e:
        api_errors["google_scholar"] += 1
        await ctx.error(f"고급 Scholar 검색 실패: {str(e)}")
        return [{"error": f"고급 Scholar 검색 실패: {str(e)}"}]

@mcp.tool()
@rate_limit()
async def search_google_web(
    query: str,
    num_results: int = 10,
    language: str = "en",
    safe_search: str = "medium",
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Search the web using Google Custom Search API.
    
    Args:
        query: Search query string
        num_results: Number of results (max 10 per API limits)
        language: Language code (e.g., 'en', 'ko', 'ja')
        safe_search: Safe search level ('high', 'medium', 'off')
        ctx: MCP context
        
    Returns:
        List of search results with title, URL, and snippet
    """
    cache_key = create_cache_key(
        query=query, 
        num_results=num_results, 
        language=language, 
        safe_search=safe_search
    )
    
    # 캐시 확인
    if cache_key in web_cache:
        await ctx.info(f"캐시된 웹 결과 반환: {query}")
        return web_cache[cache_key]
    
    await ctx.info(f"Google Web 검색 중: {query}")
    await ctx.report_progress(10, 100)
    
    try:
        results = await search_google_web_internal(query, num_results, language, safe_search)
        
        # API 사용량 추적
        if results and not (isinstance(results[0], dict) and 'error' in results[0]):
            api_usage["google_web"] += 1
            logging.info(f"Google Web API 사용: {api_usage['google_web']}/100")
        
        # 성공적인 경우 캐싱
        if results and not (isinstance(results[0], dict) and 'error' in results[0]):
            web_cache[cache_key] = results
    
        await ctx.report_progress(100, 100)
        await ctx.info(f"{len(results)}개의 웹 결과 발견")
        return results
    except Exception as e:
        api_errors["google_web"] += 1
        raise

@mcp.tool()
@rate_limit()
async def search_youtube(
    query: str,
    num_results: int = 10,
    video_duration: Optional[str] = None,
    upload_date: Optional[str] = None,
    order: str = "relevance",
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Search for videos on YouTube using YouTube Data API.
    
    Args:
        query: Search query string
        num_results: Number of results (max 50)
        video_duration: Duration filter ('short', 'medium', 'long')
        upload_date: Upload date filter ('hour', 'today', 'week', 'month', 'year')
        order: Sort order ('relevance', 'date', 'rating', 'viewCount')
        ctx: MCP context
        
    Returns:
        List of video information including title, URL, channel, description
    """
    cache_key = create_cache_key(
        query=query,
        num_results=num_results,
        video_duration=video_duration,
        upload_date=upload_date,
        order=order
    )
    
    # 캐시 확인
    if cache_key in youtube_cache:
        await ctx.info(f"캐시된 YouTube 결과 반환: {query}")
        return youtube_cache[cache_key]
    
    await ctx.info(f"YouTube 검색 중: {query}")
    await ctx.report_progress(10, 100)
    
    try:
        results = await search_youtube_internal(
            query, num_results, video_duration, upload_date, order
        )
        
        # API 사용량 추적
        if results and not (isinstance(results[0], dict) and 'error' in results[0]):
            api_usage["youtube"] += 1
            logging.info(f"YouTube API 사용: {api_usage['youtube']}/100")
        
        # 성공적인 경우 캐싱
        if results and not (isinstance(results[0], dict) and 'error' in results[0]):
            youtube_cache[cache_key] = results
        
        await ctx.report_progress(100, 100)
        await ctx.info(f"{len(results)}개의 YouTube 동영상 발견")
        return results
    except Exception as e:
        api_errors["youtube"] += 1
        raise

@mcp.tool()
async def unified_search(
    query: str,
    sources: List[str] = ["scholar", "web", "youtube"],
    num_results_per_source: int = 5,
    ctx: Context
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search across multiple sources simultaneously.
    
    Args:
        query: Search query string
        sources: List of sources to search ('scholar', 'web', 'youtube')
        num_results_per_source: Number of results per source
        ctx: MCP context
        
    Returns:
        Dictionary with results organized by source
    """
    await ctx.info(f"{len(sources)}개 소스에서 통합 검색 수행")
    
    results = {}
    tasks = []
    
    # 각 소스별 작업 생성
    if "scholar" in sources:
        tasks.append(("scholar", search_google_scholar_internal(query, num_results_per_source)))
    
    if "web" in sources:
        tasks.append(("web", search_google_web_internal(query, num_results_per_source)))
    
    if "youtube" in sources:
        tasks.append(("youtube", search_youtube_internal(query, num_results_per_source)))
    
    # 모든 검색을 동시에 실행
    total_tasks = len(tasks)
    completed = 0
    
    for source, task in tasks:
        try:
            await ctx.report_progress(completed * 100 // total_tasks, 100)
            results[source] = await task
            completed += 1
        except Exception as e:
            logging.error(f"{source} 검색 오류: {str(e)}")
            results[source] = [{"error": f"검색 실패: {str(e)}"}]
    
    await ctx.report_progress(100, 100)
    await ctx.info(f"통합 검색 완료: 총 {sum(len(r) for r in results.values())}개 결과")
    
    return results

@mcp.tool()
async def get_author_info(author_name: str, ctx: Context) -> Dict[str, Any]:
    """
    Get detailed information about an author from Google Scholar.
    
    Args:
        author_name: Name of the author to search for
        ctx: MCP context
        
    Returns:
        Dictionary containing author information including publications
    """
    await ctx.info(f"저자 정보 조회 중: {author_name}")
    
    try:
        search_query = scholarly.search_author(author_name)
        author = await asyncio.to_thread(next, search_query)
        filled_author = await asyncio.to_thread(scholarly.fill, author)
        
        # 관련 정보 추출
        author_info = {
            "name": filled_author.get("name", "N/A"),
            "affiliation": filled_author.get("affiliation", "N/A"),
            "interests": filled_author.get("interests", []),
            "citedby": filled_author.get("citedby", 0),
            "email": filled_author.get("email", "제공되지 않음"),
            "homepage": filled_author.get("homepage", "제공되지 않음"),
            "publications": [
                {
                    "title": pub.get("bib", {}).get("title", "N/A"),
                    "year": pub.get("bib", {}).get("pub_year", "N/A"),
                    "citations": pub.get("num_citations", 0),
                    "venue": pub.get("bib", {}).get("venue", "N/A")
                }
                for pub in filled_author.get("publications", [])[:10]  # 상위 10개 논문
            ],
            "source": "Google Scholar"
        }
        
        await ctx.info(f"저자 정보 조회 성공")
        return author_info
        
    except Exception as e:
        await ctx.error(f"저자 정보 조회 실패: {str(e)}")
        return {"error": f"저자 정보 조회 실패: {str(e)}"}

@mcp.tool()
async def clear_cache(source: Optional[str] = None, ctx: Context) -> Dict[str, str]:
    """
    Clear the cache for a specific source or all sources.
    
    Args:
        source: Source to clear cache for ('scholar', 'web', 'youtube', or None for all)
        ctx: MCP context
        
    Returns:
        Status message
    """
    if source == "scholar" or source is None:
        scholar_cache.clear()
        await ctx.info("Google Scholar 캐시 삭제됨")
    
    if source == "web" or source is None:
        web_cache.clear()
        await ctx.info("Google Web 캐시 삭제됨")
    
    if source == "youtube" or source is None:
        youtube_cache.clear()
        await ctx.info("YouTube 캐시 삭제됨")
    
    return {
        "status": "success",
        "message": f"캐시 삭제 완료: {source if source else '모든 소스'}"
    }

@mcp.tool()
async def get_api_usage_stats(ctx: Context) -> Dict[str, Any]:
    """
    Get API usage statistics for monitoring.
    
    Returns:
        Dictionary with usage stats and error counts
    """
    await ctx.info("API 사용량 통계 조회 중")
    
    # 현재 날짜의 통계만 반환 (일별 리셋 가정)
    today = datetime.now().strftime("%Y-%m-%d")
    
    stats = {
        "date": today,
        "usage": dict(api_usage),
        "errors": dict(api_errors),
        "cache_stats": {
            "scholar": {
                "size": len(scholar_cache),
                "max_size": SearchConfig.CACHE_MAX_SIZE
            },
            "web": {
                "size": len(web_cache),
                "max_size": SearchConfig.CACHE_MAX_SIZE
            },
            "youtube": {
                "size": len(youtube_cache),
                "max_size": SearchConfig.CACHE_MAX_SIZE
            }
        },
        "limits": {
            "google_web": {
                "free_quota": 100,
                "used": api_usage.get("google_web", 0),
                "remaining": max(0, 100 - api_usage.get("google_web", 0))
            },
            "youtube": {
                "free_quota": 100,  # 10000 units / 100 units per search
                "used": api_usage.get("youtube", 0),
                "remaining": max(0, 100 - api_usage.get("youtube", 0))
            }
        }
    }
    
    return stats

# 서버 시작 메시지
@mcp.prompt()
async def startup_info() -> str:
    """Get information about the Unified Search Server configuration."""
    config_status = []
    
    if SearchConfig.GOOGLE_API_KEY and SearchConfig.GOOGLE_CSE_ID:
        config_status.append("✅ Google Web Search: 설정됨")
    else:
        config_status.append("❌ Google Web Search: 미설정 (GOOGLE_API_KEY와 GOOGLE_CUSTOM_SEARCH_ENGINE_ID 설정 필요)")
    
    if SearchConfig.YOUTUBE_API_KEY:
        config_status.append("✅ YouTube Search: 설정됨")
    else:
        config_status.append("❌ YouTube Search: 미설정 (YOUTUBE_API_KEY 설정 필요)")
    
    config_status.append("✅ Google Scholar: 준비됨 (scholarly 라이브러리 사용)")
    
    return f"""
Unified Search MCP Server 🔍
===========================

설정 상태:
{chr(10).join(config_status)}

사용 가능한 도구:
- search_google_scholar: 학술 논문 검색
- search_google_scholar_advanced: 필터를 사용한 고급 학술 검색
- search_google_web: 웹 검색 (API 키 필요)
- search_youtube: YouTube 동영상 검색 (API 키 필요)
- unified_search: 모든 소스에서 동시 검색
- get_author_info: Google Scholar에서 저자 정보 조회
- clear_cache: 검색 결과 캐시 삭제
- get_api_usage_stats: API 사용량 및 상태 모니터링

캐시 설정:
- TTL: {SearchConfig.CACHE_TTL}초
- 최대 크기: 소스당 {SearchConfig.CACHE_MAX_SIZE}개 항목
"""

if __name__ == "__main__":
    import sys
    import os
    
    # Smithery 환경에서는 HTTP 모드로 실행
    if os.environ.get("SMITHERY_ENV") or "--transport" in sys.argv:
        mcp.run(transport="http", port=8000)
    else:
        # 로컬 개발시 stdio 모드
        mcp.run()

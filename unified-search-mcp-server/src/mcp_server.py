# src/mcp_server.py
"""
Main MCP Server
FastMCP-based unified search server using latest patterns
"""
import asyncio
import sys
import os
from typing import Optional, List, Dict, Any

from fastmcp import FastMCP

from .config import get_settings, get_security_config
from .utils import setup_logging, get_logger
from .services import (
    get_unified_service,
    create_scholar_service,
    create_web_search_service,
    create_youtube_service
)
from .models import (
    SearchSource, SearchRequest,
    SafeSearchLevel, VideoDuration, UploadDate, SortOrder,
    ValidationError, ServiceError
)

logger = get_logger(__name__)

# Initialize services at module level
_services: Dict[str, Any] = {}

def _initialize_services():
    """Initialize all services"""
    settings = get_settings()
    security_config = get_security_config()
    
    logger.info("Initializing services...")
    
    # Initialize unified service (always available)
    _services['unified'] = get_unified_service()
    logger.info("Unified search service initialized")
    
    # Initialize Google Scholar (no API key required)
    try:
        _services['scholar'] = create_scholar_service()
        logger.info("Scholar service initialized")
    except Exception as e:
        logger.warning(f"Scholar service initialization failed: {e}")
        _services['scholar'] = None
    
    # Initialize Google Web Search (requires API key)
    if security_config.google_api_key and security_config.google_cse_id:
        try:
            _services['web'] = create_web_search_service()
            logger.info("Web search service initialized")
        except Exception as e:
            logger.warning(f"Web search service initialization failed: {e}")
            _services['web'] = None
    else:
        logger.info("Google Web Search not configured (missing API key)")
        _services['web'] = None
    
    # Initialize YouTube Search (requires API key)
    if security_config.youtube_api_key:
        try:
            _services['youtube'] = create_youtube_service()
            logger.info("YouTube service initialized")
        except Exception as e:
            logger.warning(f"YouTube service initialization failed: {e}")
            _services['youtube'] = None
    else:
        logger.info("YouTube Search not configured (missing API key)")
        _services['youtube'] = None

# Create FastMCP server
mcp = FastMCP(
    name="Unified Search MCP Server",
    instructions="""
    Unified Search MCP Server - Search across Google Scholar, Google Web, and YouTube.
    
    Available tools:
    - unified_search: Search across all sources simultaneously
    - search_google_scholar: Search academic papers
    - search_google_web: Search the web (requires API key)
    - search_youtube: Search YouTube videos (requires API key)
    - get_author_info: Get author information from Scholar
    - clear_cache: Clear search result cache
    - get_api_usage_stats: View API usage and system status
    
    Use unified_search for comprehensive results across all sources.
    """
)


# Tools using latest FastMCP patterns
@mcp.tool
async def unified_search(
    query: str,
    sources: Optional[List[str]] = None,
    num_results: int = 10,
    # Scholar options
    author: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    # Web options
    language: str = "en",
    safe_search: str = "medium",
    # YouTube options
    video_duration: Optional[str] = None,
    upload_date: Optional[str] = None,
    sort_order: str = "relevance"
) -> Dict[str, Any]:
    """
    Search across multiple sources simultaneously.
    
    Args:
        query: Search query
        sources: List of sources ('scholar', 'web', 'youtube')
        num_results: Number of results per source
        author: Filter by author (Scholar only)
        year_start: Start year filter (Scholar only)
        year_end: End year filter (Scholar only)
        language: Language code (Web only)
        safe_search: Safe search level (Web only)
        video_duration: Video duration filter (YouTube only)
        upload_date: Upload date filter (YouTube only)
        sort_order: Sort order (YouTube only)
    """
    if not _services['unified']:
        raise ServiceError("Unified search service not available")
    
    # Parse sources
    if sources:
        try:
            search_sources = [SearchSource(s) for s in sources]
        except ValueError as e:
            raise ValidationError(f"Invalid source: {e}")
    else:
        # Default to available sources
        search_sources = []
        if _services['scholar']:
            search_sources.append(SearchSource.SCHOLAR)
        if _services['web']:
            search_sources.append(SearchSource.WEB)
        if _services['youtube']:
            search_sources.append(SearchSource.YOUTUBE)
    
    # Create request
    request = SearchRequest(
        query=query,
        sources=search_sources,
        num_results=num_results,
        author=author,
        year_start=year_start,
        year_end=year_end,
        language=language,
        safe_search=SafeSearchLevel(safe_search) if safe_search else SafeSearchLevel.MEDIUM,
        video_duration=VideoDuration(video_duration) if video_duration else None,
        upload_date=UploadDate(upload_date) if upload_date else None,
        sort_order=SortOrder(sort_order) if sort_order else SortOrder.RELEVANCE
    )
    
    # Perform search
    response = await _services['unified'].search(request)
    return response.model_dump()


@mcp.tool
async def search_google_scholar(
    query: str,
    num_results: int = 10,
    author: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Search Google Scholar for academic papers.
    
    Args:
        query: Search query
        num_results: Number of results (max 50)
        author: Filter by author name
        year_start: Start year for publication date
        year_end: End year for publication date
    """
    if not _services['scholar']:
        raise ServiceError("Scholar service not available")
    
    results = await _services['scholar'].search(
        query=query,
        num_results=num_results,
        author=author,
        year_start=year_start,
        year_end=year_end
    )
    
    return [r.model_dump() for r in results]


@mcp.tool
async def search_google_web(
    query: str,
    num_results: int = 10,
    language: str = "en",
    safe_search: str = "medium"
) -> List[Dict[str, Any]]:
    """
    Search the web using Google Custom Search API.
    
    Args:
        query: Search query
        num_results: Number of results (max 10)
        language: Language code ('en', 'ko', 'ja', etc.)
        safe_search: Safe search level ('high', 'medium', 'off')
    """
    if not _services['web']:
        raise ServiceError("Web search service not available. Please configure Google API key.")
    
    results = await _services['web'].search(
        query=query,
        num_results=num_results,
        language=language,
        safe_search=SafeSearchLevel(safe_search)
    )
    
    return [r.model_dump() for r in results]


@mcp.tool
async def search_youtube(
    query: str,
    num_results: int = 10,
    video_duration: Optional[str] = None,
    upload_date: Optional[str] = None,
    order: str = "relevance"
) -> List[Dict[str, Any]]:
    """
    Search YouTube videos.
    
    Args:
        query: Search query
        num_results: Number of results (max 50)
        video_duration: Duration filter ('short', 'medium', 'long')
        upload_date: Upload date filter ('hour', 'today', 'week', 'month', 'year')
        order: Sort order ('relevance', 'date', 'rating', 'viewCount')
    """
    if not _services['youtube']:
        raise ServiceError("YouTube service not available. Please configure YouTube API key.")
    
    results = await _services['youtube'].search(
        query=query,
        num_results=num_results,
        video_duration=VideoDuration(video_duration) if video_duration else None,
        upload_date=UploadDate(upload_date) if upload_date else None,
        order=SortOrder(order)
    )
    
    return [r.model_dump() for r in results]


@mcp.tool
async def get_author_info(author_name: str) -> Dict[str, Any]:
    """
    Get detailed information about an author from Google Scholar.
    
    Args:
        author_name: Name of the author
    """
    if not _services['scholar']:
        raise ServiceError("Scholar service not available")
    
    return await _services['scholar'].get_author_info(author_name)


@mcp.tool
async def clear_cache(source: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear search cache.
    
    Args:
        source: Source to clear ('scholar', 'web', 'youtube', or None for all)
    """
    from .cache import get_cache_manager
    
    cache_manager = get_cache_manager()
    
    if source:
        count = await cache_manager.clear(source=source)
        message = f"Cleared {count} items from {source} cache"
    else:
        count = await cache_manager.clear()
        message = f"Cleared {count} items from all caches"
    
    return {
        "status": "success",
        "message": message,
        "cleared_count": count
    }


@mcp.tool
async def get_api_usage_stats() -> Dict[str, Any]:
    """Get API usage statistics and system status."""
    if not _services['unified']:
        raise ServiceError("Unified service not available")
    
    stats = await _services['unified'].get_api_usage_stats()
    
    # Add health status
    from .monitoring import get_health_checker
    health_checker = get_health_checker()
    health_status = await health_checker.check_health()
    
    return {
        **stats.model_dump(),
        "health": health_status.model_dump(),
        "available_services": [
            name for name, service in _services.items() 
            if service is not None
        ]
    }


# Resources using latest patterns
@mcp.resource("health://status")
async def health_status() -> str:
    """Health check endpoint."""
    from .monitoring import get_health_checker
    health_checker = get_health_checker()
    result = await health_checker.check_health()
    
    return f"""
Health Status: {result.status.value}
Timestamp: {result.timestamp.isoformat()}
Uptime: {result.uptime_seconds:.2f}s

Components:
{chr(10).join(f"- {c.name}: {c.status.value} - {c.message or 'OK'}" for c in result.components)}
"""


@mcp.resource("metrics://stats")
async def metrics_stats() -> str:
    """Get current metrics."""
    from .cache import get_cache_manager
    
    cache_manager = get_cache_manager()
    cache_stats = cache_manager.get_stats()
    
    unified_service = get_unified_service()
    api_stats = await unified_service.get_api_usage_stats()
    
    return f"""
Cache Statistics:
- Total requests: {cache_stats.get('total_requests', 0)}
- Hit rate: {cache_stats.get('hit_rate', 0):.2f}%
- Hits: {cache_stats.get('hits', 0)}
- Misses: {cache_stats.get('misses', 0)}

API Usage:
- Google Web: {api_stats.usage.get('google_web', 0)}/100 daily
- YouTube: {api_stats.usage.get('youtube', 0)}/100 daily
"""


@mcp.prompt
async def system_info() -> str:
    """System information and configuration status"""
    settings = get_settings()
    security_config = get_security_config()
    
    config_status = []
    
    if security_config.google_api_key and security_config.google_cse_id:
        config_status.append("✅ Google Web Search: Configured")
    else:
        config_status.append("❌ Google Web Search: Not configured")
    
    if security_config.youtube_api_key:
        config_status.append("✅ YouTube Search: Configured")
    else:
        config_status.append("❌ YouTube Search: Not configured")
    
    config_status.append("✅ Google Scholar: Ready (no API key required)")
    
    return f"""
# Unified Search MCP Server 🔍

**Version**: 1.0.0
**Environment**: {settings.environment}
**Status**: Production-ready

## Configuration Status:
{chr(10).join(config_status)}

## Available Tools:
- `unified_search`: Search across all sources simultaneously
- `search_google_scholar`: Academic paper search
- `search_google_web`: Web search (requires API key)
- `search_youtube`: YouTube video search (requires API key)
- `get_author_info`: Get author information from Scholar
- `clear_cache`: Clear search result cache
- `get_api_usage_stats`: View API usage and system status

## Features:
- 🔒 Secure API key management
- 💾 Intelligent caching (TTL: {settings.cache_ttl}s)
- 🚦 Rate limiting protection
- 📊 Comprehensive monitoring
- 🛡️ Input validation and sanitization
- ⚡ Concurrent search execution
- 🔄 Automatic retry with backoff
- 📝 Structured logging

## Rate Limits:
- Google Scholar: 30 requests/minute
- Google Web: 100 requests/day
- YouTube: 100 searches/day

Ready to search! 🚀
"""


def run_server():
    """Run the server with proper transport configuration"""
    # Setup logging
    setup_logging()
    
    settings = get_settings()
    logger.info(f"Starting server in {settings.environment} mode")
    
    # Initialize services before running
    try:
        _initialize_services()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    # Determine transport mode
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport") + 1
        if idx < len(sys.argv):
            transport = sys.argv[idx]
            if transport == "streamable-http":
                mcp.run(transport="streamable-http", port=settings.port)
            elif transport == "sse":
                mcp.run(transport="sse", port=settings.port)
            else:
                mcp.run(transport=transport)
        else:
            mcp.run()
    elif os.environ.get("SMITHERY_ENV"):
        # Smithery deployment
        logger.info("Detected Smithery environment, running in HTTP mode")
        mcp.run(transport="streamable-http", port=settings.port)
    else:
        # Default stdio mode
        logger.info("Running in stdio mode")
        mcp.run()


if __name__ == "__main__":
    run_server()

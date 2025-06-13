# Unified Search MCP Server 🔍

A powerful MCP (Model Context Protocol) server that provides unified search capabilities across Google Scholar, Google Web Search, and YouTube. Built with performance and cost optimization in mind.

[한국어 README](README-ko.md)

## Features

- **🎓 Google Scholar Search**: Search academic papers with basic and advanced filtering
- **🌐 Google Web Search**: Search the web using Google Custom Search API
- **📺 YouTube Search**: Find videos with various filters (duration, upload date, etc.)
- **🔄 Unified Search**: Search across all sources simultaneously
- **💾 Smart Caching**: TTL-based caching to reduce API calls and improve performance
- **⚡ Rate Limiting**: Built-in rate limiting to respect API quotas
- **📊 Progress Reporting**: Real-time progress updates during searches
- **🔧 Fully Async**: Optimized asynchronous operations for better performance

## Key Improvements Over Original

1. **API-Based Searches**: Uses official APIs (Google Custom Search, YouTube Data API) instead of web scraping for better reliability and performance
2. **Caching System**: Implements TTL-based caching to reduce redundant API calls
3. **Rate Limiting**: Automatic rate limiting to prevent API quota exhaustion
4. **Concurrent Searches**: Unified search executes all searches in parallel
5. **Better Error Handling**: Comprehensive error handling with detailed error messages
6. **Context Integration**: Full integration with MCP Context for logging and progress reporting

## Installation

### Quick Install via Smithery (Recommended)

After publishing to Smithery, users will install it through the Smithery platform, which will automatically add the configuration to Claude Desktop.

### Manual Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd unified-search-mcp-server
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Set the following environment variables for API access:

```bash
# For Google Web Search
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_CSE_ID="your-custom-search-engine-id"

# For YouTube Search
export YOUTUBE_API_KEY="your-youtube-api-key"
```

### Getting API Keys

1. **Google Custom Search API** (for web search):
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing
   - Enable "Custom Search API"
   - Create credentials (API Key)
   - Create a Custom Search Engine at [cse.google.com](https://cse.google.com)
   - ⚠️ **Important**: This is for general web search, NOT Google Scholar!

2. **YouTube Data API v3**:
   - Same Google Cloud Console project
   - Enable "YouTube Data API v3"
   - Use the same API key or create a new one

3. **Google Scholar**:
   - No official API available
   - Free access through scholarly library
   - May be temporarily blocked with excessive use

## Usage

### Running the Server

```bash
python unified_search_server.py
```

Or use FastMCP CLI:
```bash
fastmcp run unified_search_server.py
```

### Installation in Claude Desktop

#### Option 1: Using Smithery (Recommended)
After publishing to Smithery, the configuration will be automatically added in this format:
```json
{
  "mcpServers": {
    "unified-search-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "@smithery/cli@latest",
        "run",
        "@JDeun/unified-search-mcp",
        "--key",
        "YOUR-SMITHERY-KEY"
      ]
    }
  }
}
```

#### Option 2: Manual Configuration

Add to `claude_desktop_config.json`:

**Windows:**
```json
{
  "mcpServers": {
    "unified-search": {
      "command": "C:\\Users\\YOUR\\PATH\\python.exe",
      "args": [
        "C:\\Users\\YOUR\\PATH\\unified_search_server.py"
      ],
      "env": {
        "GOOGLE_API_KEY": "your-key",
        "GOOGLE_CSE_ID": "your-cse-id",
        "YOUTUBE_API_KEY": "your-key"
      }
    }
  }
}
```

**Mac/Linux:**
```json
{
  "mcpServers": {
    "unified-search": {
      "command": "python",
      "args": [
        "/path/to/unified_search_server.py"
      ],
      "env": {
        "GOOGLE_API_KEY": "your-key",
        "GOOGLE_CSE_ID": "your-cse-id",
        "YOUTUBE_API_KEY": "your-key"
      }
    }
  }
}
```

## Available Tools

### 1. search_google_scholar
Basic keyword search for academic papers.
```python
result = await mcp.use_tool("search_google_scholar", {
    "query": "machine learning",
    "num_results": 5
})
```

### 2. search_google_scholar_advanced
Advanced search with author and year filters.
```python
result = await mcp.use_tool("search_google_scholar_advanced", {
    "query": "deep learning",
    "author": "Yann LeCun",
    "year_start": 2020,
    "year_end": 2024,
    "num_results": 10
})
```

### 3. search_google_web
Search the web using Google Custom Search API.
```python
result = await mcp.use_tool("search_google_web", {
    "query": "artificial intelligence news",
    "num_results": 10,
    "language": "en",
    "safe_search": "medium"
})
```

### 4. search_youtube
Search for YouTube videos with filters.
```python
result = await mcp.use_tool("search_youtube", {
    "query": "python tutorial",
    "num_results": 15,
    "video_duration": "medium",  # short, medium, long
    "upload_date": "month",      # hour, today, week, month, year
    "order": "viewCount"         # relevance, date, rating, viewCount
})
```

### 5. unified_search
Search across all sources simultaneously.
```python
result = await mcp.use_tool("unified_search", {
    "query": "climate change",
    "sources": ["scholar", "web", "youtube"],
    "num_results_per_source": 5
})
```

### 6. get_author_info
Get detailed author information from Google Scholar.
```python
result = await mcp.use_tool("get_author_info", {
    "author_name": "Geoffrey Hinton"
})
```

### 7. clear_cache
Clear cached search results.
```python
result = await mcp.use_tool("clear_cache", {
    "source": "web"  # scholar, web, youtube, or None for all
})
```

### 8. get_api_usage_stats
Monitor API usage and status.
```python
result = await mcp.use_tool("get_api_usage_stats", {})
# Returns: usage counts, error counts, cache status, remaining quotas
```

## Performance Optimizations

1. **Caching**: Results are cached for 1 hour (configurable) to reduce API calls
2. **Rate Limiting**: 0.5 seconds between API calls to prevent quota exhaustion
3. **Parallel Execution**: Unified search runs all searches concurrently
4. **Async Operations**: All I/O operations are asynchronous for better performance
5. **Smart Retries**: Failed searches don't affect other sources in unified search

## ⚠️ Important Notice

### About Google Scholar
- **No Official API**: Google Scholar does not provide an official API
- **Blocking Risk**: Excessive use may result in temporary IP blocking
- **Commercial Use Prohibited**: Check Google Scholar's terms of service
- **Alternative**: Consider official APIs like Semantic Scholar API for academic search

### About API Keys
- **GOOGLE_CUSTOM_SEARCH_ENGINE_ID**: For general web search (NOT Google Scholar)
- **Potential Costs**: Automatic billing may occur when exceeding free quotas
- **API Key Security**: Manage keys securely using environment variables

### For Production Use
- **Log Monitoring**: Regularly check `unified_search.log` file
- **API Usage Monitoring**: Track usage with `get_api_usage_stats` tool
- **Cache Management**: Adjust cache TTL as needed
- **Error Handling**: Designed so individual source failures don't affect overall service

### API Costs
1. **Google Scholar**: 
   - ✅ Free (using scholarly library)
   - ⚠️ Risk of temporary blocking with excessive use
   - 💡 Automatic 2-second rate limiting applied

2. **Google Custom Search (web search)**: 
   - Free: 100 queries/day
   - Paid: $5 per 1,000 queries (after 100 queries)
   - 💡 Caching prevents duplicate queries

3. **YouTube Data API**: 
   - Free: 10,000 units/day
   - Search operation: 100 units per search
   - 💡 Approximately 100 searches per day

### Stability Improvements
1. **Caching**: 1-hour result storage reduces API usage
2. **Rate Limiting**: 
   - Google Scholar: 2-second intervals
   - Other APIs: 1-second intervals
3. **Retry Logic**: Automatic retry on Google Scholar blocking
4. **Error Handling**: Independent error handling for each source

## Development

### Testing
```python
import asyncio
from fastmcp import Client

async def test():
    async with Client("unified_search_server.py") as client:
        # Test Google Scholar
        result = await client.call_tool("search_google_scholar", {
            "query": "quantum computing"
        })
        print(result)

asyncio.run(test())
```

### Adding New Search Sources

1. Create internal search function:
```python
async def search_new_source_internal(query: str, **kwargs) -> List[Dict]:
    # Implementation
    pass
```

2. Add MCP tool:
```python
@mcp.tool()
async def search_new_source(query: str, ctx: Context) -> List[Dict]:
    # Tool implementation with caching and rate limiting
    pass
```

3. Update unified_search to include new source

## Error Handling

The server handles various error scenarios:
- Missing API credentials
- API quota exceeded
- Network failures
- Invalid parameters
- Search timeouts

All errors are logged and returned in a consistent format.

## Troubleshooting

### API Key Issues
- Verify environment variables are set correctly
- Check API is enabled in Google Cloud Console
- Verify API key restrictions

### No Search Results
- Try simpler search queries
- Clear cache and retry
- Check logs for specific error messages

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Based on the original [Google Scholar MCP Server](https://github.com/DeadWaveWave/Google-Scholar-MCP-Server)
- Built with [FastMCP](https://github.com/jlowin/fastmcp)
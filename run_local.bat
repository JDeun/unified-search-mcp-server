@echo off
REM Local test script for MCP server on Windows

echo Starting local MCP server test...

REM Set test environment variables
set PORT=8080
set MCP_ENV=development
set MCP_LOG_LEVEL=DEBUG
set SMITHERY_ENV=true

REM Add your API keys here for testing
REM set GOOGLE_API_KEY=your-key
REM set GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-cse-id
REM set YOUTUBE_API_KEY=your-youtube-key

echo Starting server on port %PORT%...
python smithery_server.py

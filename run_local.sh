#!/bin/bash
# Local test script for MCP server

echo "Starting local MCP server test..."

# Set test environment variables
export PORT=8080
export MCP_ENV=development
export MCP_LOG_LEVEL=DEBUG
export SMITHERY_ENV=true

# Add your API keys here for testing
# export GOOGLE_API_KEY=your-key
# export GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-cse-id
# export YOUTUBE_API_KEY=your-youtube-key

echo "Starting server on port $PORT..."
python smithery_server.py

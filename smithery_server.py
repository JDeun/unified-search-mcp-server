#!/usr/bin/env python3
"""
Smithery-compatible MCP server wrapper using ASGI with configuration parsing
"""
import os
import sys
import logging
from urllib.parse import parse_qs

# Add src to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import after path setup
from src.mcp_server import mcp, _initialize_services
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SmitheryConfigMiddleware(BaseHTTPMiddleware):
    """Middleware to parse Smithery configuration from query parameters"""
    
    async def dispatch(self, request: Request, call_next):
        # Parse query parameters and set as environment variables
        if request.url.query:
            params = parse_qs(str(request.url.query))
            
            # Smithery sends config as dot-notation query params
            # Map common config patterns
            config_mapping = {
                'GOOGLE_API_KEY': ['GOOGLE_API_KEY', 'google_api_key', 'googleApiKey'],
                'GOOGLE_CUSTOM_SEARCH_ENGINE_ID': ['GOOGLE_CUSTOM_SEARCH_ENGINE_ID', 'google_cse_id', 'googleCseId'],
                'YOUTUBE_API_KEY': ['YOUTUBE_API_KEY', 'youtube_api_key', 'youtubeApiKey'],
                'MCP_LOG_LEVEL': ['MCP_LOG_LEVEL', 'log_level', 'logLevel']
            }
            
            for env_key, possible_params in config_mapping.items():
                for param in possible_params:
                    if param in params and params[param]:
                        os.environ[env_key] = params[param][0]
                        logger.info(f"Set {env_key} from query param {param}")
                        break
        
        response = await call_next(request)
        return response

# Initialize services at import time
try:
    _initialize_services()
    logger.info("Services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    raise

# Get ASGI app from FastMCP
base_app = mcp.http_app(path="/mcp")

# Create Starlette app with middleware
app = Starlette()
app.add_middleware(SmitheryConfigMiddleware)

# Mount the FastMCP app
app.mount("/", base_app)

# For running directly with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"  # Bind to all interfaces for container
    
    logger.info(f"Starting ASGI server on {host}:{port}")
    logger.info(f"MCP endpoint available at http://{host}:{port}/mcp")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

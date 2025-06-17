#!/usr/bin/env python3
"""
Smithery-compatible MCP server wrapper
Handles PORT environment variable and configuration parsing
"""
import os
import sys
from urllib.parse import parse_qs

# Add src to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp_server import run_server

def parse_smithery_config():
    """Parse Smithery configuration from query parameters"""
    # Smithery passes configuration as query parameters
    # This function would parse them if needed
    # For now, we use environment variables directly
    pass

if __name__ == "__main__":
    # Set PORT from environment variable if available
    if "PORT" in os.environ:
        # Override the default port setting
        os.environ["MCP_PORT"] = os.environ["PORT"]
    
    # Parse any Smithery-specific configuration
    parse_smithery_config()
    
    # Run the server
    run_server()

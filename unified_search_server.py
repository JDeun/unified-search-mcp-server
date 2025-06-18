#!/usr/bin/env python3
"""
Unified Search MCP Server for Smithery
"""
import sys
import os

# Smithery environment detection
if os.environ.get("SMITHERY_ENV"):
    # For Smithery deployment
    port = int(os.environ.get("PORT", 8080))
    transport = "streamable-http"
else:
    # For local development
    port = 8000
    transport = "stdio"

# Add src to Python path
sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_server import mcp, _initialize_services

if __name__ == "__main__":
    # Initialize services
    _initialize_services()
    
    # Run server
    mcp.run(transport=transport, port=port, host="0.0.0.0")

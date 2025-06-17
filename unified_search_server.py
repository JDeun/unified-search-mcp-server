#!/usr/bin/env python3
"""
Unified Search MCP Server
Main entry point for the MCP server
"""
import sys
import os
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.mcp_server import run_server

if __name__ == "__main__":
    # Check for Windows event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

# src/__init__.py
"""
Unified Search MCP Server
통합 검색 MCP 서버 - Google Scholar, Web, YouTube
"""

__version__ = "1.0.0"
__author__ = "JDeun"
__license__ = "MIT"

# 주요 컴포넌트 export
from .mcp_server import mcp, run_server

__all__ = [
    'mcp',
    'run_server',
    '__version__',
]

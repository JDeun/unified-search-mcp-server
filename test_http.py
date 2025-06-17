#!/usr/bin/env python3
"""
Test script to verify MCP server HTTP endpoints
"""
import asyncio
import httpx
import json

async def test_mcp_endpoints():
    """Test /mcp endpoint availability"""
    base_url = "http://localhost:8080"
    
    print("Testing MCP server endpoints...")
    
    async with httpx.AsyncClient() as client:
        # Test GET /mcp
        try:
            response = await client.get(f"{base_url}/mcp")
            print(f"GET /mcp: {response.status_code}")
            if response.status_code == 200:
                print("Response:", response.text[:200])
        except Exception as e:
            print(f"GET /mcp failed: {e}")
        
        # Test POST /mcp
        try:
            response = await client.post(
                f"{base_url}/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}
            )
            print(f"POST /mcp: {response.status_code}")
            if response.status_code == 200:
                print("Response:", response.text[:200])
        except Exception as e:
            print(f"POST /mcp failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_endpoints())

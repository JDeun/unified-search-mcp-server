#!/usr/bin/env python3
"""
Local test script for MCP server
"""
import asyncio
import httpx
import json
import os

async def test_mcp_server():
    """Test MCP server endpoints"""
    base_url = f"http://localhost:{os.environ.get('PORT', 8080)}"
    
    print(f"Testing MCP server at {base_url}/mcp")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test basic connection
        try:
            # Test if server is running
            response = await client.get(f"{base_url}/mcp")
            print(f"GET /mcp: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            # Test MCP initialize
            response = await client.post(
                f"{base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": "test-client",
                            "version": "0.1.0"
                        }
                    },
                    "id": 1
                },
                headers={"Content-Type": "application/json"}
            )
            print(f"\nPOST /mcp (initialize): {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            # Test list tools
            response = await client.post(
                f"{base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2
                },
                headers={"Content-Type": "application/json"}
            )
            print(f"\nPOST /mcp (tools/list): {response.status_code}")
            data = response.json()
            if "result" in data and "tools" in data["result"]:
                tools = data["result"]["tools"]
                print(f"Available tools: {[t['name'] for t in tools]}")
            else:
                print(f"Response: {json.dumps(data, indent=2)}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())

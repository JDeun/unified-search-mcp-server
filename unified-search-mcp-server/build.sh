#!/bin/bash
# Smithery Python MCP Server Build Script

echo "Building Python MCP Server..."

# Python 환경 확인
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed"
    exit 1
fi

# 의존성 설치
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Build completed successfully!"

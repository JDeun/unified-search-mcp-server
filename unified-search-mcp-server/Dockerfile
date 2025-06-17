FROM python:3.11-slim

WORKDIR /app

# 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# MCP 서버 실행
CMD ["python", "unified_search_server.py", "--transport", "streamable-http"]

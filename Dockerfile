FROM python:3.11-slim

WORKDIR /app

# 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# FastMCP의 HTTP transport를 위한 추가 패키지
RUN pip install --no-cache-dir uvicorn starlette

# 소스 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV MCP_ENV=production
ENV SMITHERY_ENV=true

# PORT 환경변수를 사용하도록 설정 (Smithery 요구사항)
EXPOSE 8080

# 서버 실행 - Smithery wrapper 사용
CMD ["python", "smithery_server.py", "--transport", "streamable-http"]

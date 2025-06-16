FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY unified_search_server.py .
COPY src/ ./src/

# 비루트 사용자 생성 및 전환
RUN useradd -m -u 1000 mcp && \
    chown -R mcp:mcp /app

USER mcp

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV MCP_ENV=production
ENV SMITHERY_ENV=true
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# 서버 실행
CMD ["python", "unified_search_server.py", "--transport", "streamable-http"]

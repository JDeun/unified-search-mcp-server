FROM python:3.11-slim

WORKDIR /app

# 의존성 파일 복사
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY unified_search_server.py .

# MCP 서버는 포트 8000에서 실행
EXPOSE 8000

# 서버 실행
CMD ["python", "unified_search_server.py"]

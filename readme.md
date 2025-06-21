# Unified Search MCP Server 🔍

**프로덕션 레벨** MCP (Model Context Protocol) 서버로 Google Scholar, Google Web Search, YouTube를 통합 검색할 수 있습니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![smithery badge](https://smithery.ai/badge/@JDeun/unified-search-mcp-server)](https://smithery.ai/server/@JDeun/unified-search-mcp-server)

## 🚀 주요 기능

### 핵심 검색 기능
- **🎓 Google Scholar**: 학술 논문 검색 (저자, 연도 필터링)
- **🌐 Google Web Search**: Google Custom Search API를 사용한 웹 검색
- **📺 YouTube Search**: 동영상 검색 (길이, 업로드 날짜, 정렬 옵션)
- **🔄 통합 검색**: 모든 소스에서 동시 검색

### 엔터프라이즈 기능
- **🔐 보안**: API 키 암호화, 입력값 검증, XSS/SQL 인젝션 방지
- **💾 분산 캐싱**: Redis 기반 캐싱 및 TTL 관리
- **⚡ Rate Limiting**: Redis 백엔드 기반 설정 가능한 rate limit
- **📊 모니터링**: Prometheus 메트릭, 헬스 체크, 구조화된 로깅
- **🔄 복원력**: 재시도 로직, 서킷 브레이커, 우아한 성능 저하
- **📝 감사 로깅**: 규정 준수를 위한 포괄적인 감사 추적

## 📋 요구 사항

- Python 3.11+
- Redis (선택사항, 분산 기능용)
- API 키:
  - Google Custom Search API (웹 검색용)
  - YouTube Data API v3 (YouTube 검색용)

## 🛠️ 설치

### Installing via Smithery

To install Unified Search MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@JDeun/unified-search-mcp-server):

```bash
npx -y @smithery/cli install @JDeun/unified-search-mcp-server --client claude
```

### Smithery를 통한 빠른 설치

Smithery 플랫폼을 통해 직접 배포하면 자동으로 설정됩니다.

### 수동 설치

1. 저장소 클론:
```bash
git clone https://github.com/JDeun/unified-search-mcp-server.git
cd unified-search-mcp-server
```

2. 가상 환경 생성:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치:
```bash
pip install -r requirements.txt
```

4. 환경 설정:
```bash
cp .env.example .env
# .env 파일을 편집하여 API 키와 설정 입력
```

## ⚙️ 설정

### 환경 변수

```env
# API 키
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-cse-id
YOUTUBE_API_KEY=your-youtube-api-key

# 보안
MCP_ENCRYPTION_KEY=your-256-bit-key
MCP_RATE_LIMIT_SECRET=your-secret

# Redis (선택사항)
MCP_REDIS_URL=redis://localhost:6379/0

# 설정
MCP_ENV=production
MCP_LOG_LEVEL=INFO
MCP_CACHE_TTL=3600
```

### API 키 발급 방법

1. **Google Custom Search API**:
   - [Google Cloud Console](https://console.cloud.google.com/) 접속
   - "Custom Search API" 활성화
   - 인증 정보 생성 (API 키)
   - [cse.google.com](https://cse.google.com/)에서 Custom Search Engine 생성

2. **YouTube Data API v3**:
   - 동일한 Google Cloud Console 프로젝트 사용
   - "YouTube Data API v3" 활성화
   - 동일한 API 키 사용 또는 새로 생성

## 🚀 사용법

### 서버 실행

```bash
# 개발 모드 (stdio)
python unified_search_server.py

# 프로덕션 모드 (HTTP)
python unified_search_server.py --transport streamable-http

# 커스텀 포트
MCP_PORT=8080 python unified_search_server.py --transport streamable-http
```

### Docker 배포

```bash
# 이미지 빌드
docker build -t unified-search-mcp .

# 컨테이너 실행
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your-key \
  -e GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-cse \
  -e YOUTUBE_API_KEY=your-key \
  unified-search-mcp
```

### Claude Desktop 통합

`claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "unified-search": {
      "command": "python",
      "args": ["/path/to/unified_search_server.py"],
      "env": {
        "GOOGLE_API_KEY": "your-key",
        "GOOGLE_CUSTOM_SEARCH_ENGINE_ID": "your-cse",
        "YOUTUBE_API_KEY": "your-key"
      }
    }
  }
}
```

## 📖 사용 가능한 도구

### unified_search
모든 소스에서 동시에 검색합니다.
```python
results = await unified_search(
    query="인공지능",
    sources=["scholar", "web", "youtube"],
    num_results=10
)
```

### search_google_scholar
학술 논문을 검색합니다.
```python
results = await search_google_scholar(
    query="머신러닝",
    author="Yann LeCun",
    year_start=2020,
    year_end=2024,
    num_results=10
)
```

### search_google_web
웹을 검색합니다.
```python
results = await search_google_web(
    query="ChatGPT",
    language="ko",
    safe_search="medium",
    num_results=10
)
```

### search_youtube
YouTube 동영상을 검색합니다.
```python
results = await search_youtube(
    query="파이썬 튜토리얼",
    video_duration="medium",
    upload_date="month",
    order="viewCount",
    num_results=20
)
```

### get_author_info
Google Scholar에서 저자 정보를 가져옵니다.
```python
info = await get_author_info("Geoffrey Hinton")
```

### clear_cache
캐시된 검색 결과를 삭제합니다.
```python
await clear_cache(source="web")  # 또는 None으로 전체 삭제
```

### get_api_usage_stats
API 사용량과 제한을 모니터링합니다.
```python
stats = await get_api_usage_stats()
```

## 🏗️ 아키텍처

### 모듈식 설계
```
src/
├── config/       # 설정 및 보안
├── models/       # 데이터 모델 및 검증
├── services/     # 검색 서비스 구현
├── cache/        # 캐싱 레이어
├── utils/        # 유틸리티 (로깅, rate limiting)
├── monitoring/   # 메트릭 및 헬스 체크
└── mcp_server.py # 메인 서버 구현
```

### 보안 레이어
- 입력값 검증 및 살균
- API 키 암호화 저장
- 클라이언트/엔드포인트별 rate limiting
- 규정 준수를 위한 감사 로깅
- CORS 및 요청 ID 추적

### 성능 최적화
- Redis 기반 분산 캐싱
- HTTP 클라이언트 연결 풀링
- 동시 검색 실행
- 지수 백오프를 통한 스마트 재시도
- 외부 API용 서킷 브레이커

## 📊 모니터링

### 헬스 체크 엔드포인트
```
리소스: health://status
```

### 메트릭 엔드포인트
```
리소스: metrics://stats
```

### 주요 메트릭
- 검색 요청 수 및 지연 시간
- 캐시 히트율
- API 할당량 사용량
- 소스별 오류율
- Rate limit 위반

## 🔒 보안

### 모범 사례
- 모든 API 키 Fernet으로 암호화
- XSS/SQL 인젝션 방지를 위한 입력 검증
- 남용 방지를 위한 rate limiting
- 민감한 데이터 없는 구조화된 로깅
- 정기적인 보안 업데이트

### 규정 준수
- PII 저장 없는 GDPR 준비
- 모든 검색에 대한 감사 추적
- 설정 가능한 데이터 보존
- API 사용량 추적

## 🧪 테스트

테스트 실행:
```bash
pytest tests/ -v --cov=src
```

## 🤝 기여

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing`)
3. 변경 사항 커밋 (`git commit -m 'Add feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing`)
5. Pull Request 열기

## 📝 라이선스

MIT 라이선스 - 자세한 내용은 [LICENSE](LICENSE) 파일 참조

## 🙏 감사의 말

- [FastMCP](https://github.com/jlowin/fastmcp)로 구축
- [scholarly](https://github.com/scholarly/scholarly)를 통한 Google Scholar 검색
- MCP 커뮤니티의 영감

## ⚠️ 중요 사항

### API 제한
- **Google Web Search**: 100 쿼리/일 (무료 티어)
- **YouTube API**: 10,000 유닛/일 (약 100 검색)
- **Google Scholar**: 공식 API 없음, rate 제한 있음

### 프로덕션 고려사항
- 분산 배포를 위해 Redis 사용
- 적절한 API 키 로테이션 설정
- Rate limit 및 할당량 모니터링
- API 오류에 대한 알림 설정
- 정기적인 설정 백업

## 📞 지원

문제 및 질문:
- GitHub Issues: [이슈 생성](https://github.com/JDeun/unified-search-mcp-server/issues)
- Smithery 지원: 배포 관련 문제

---

**MCP 커뮤니티를 위해 ❤️로 제작**

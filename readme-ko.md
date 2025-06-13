# Unified Search MCP Server 🔍

Google Scholar, Google Web Search, YouTube를 통합한 강력한 MCP (Model Context Protocol) 서버입니다. 성능과 비용 최적화를 염두에 두고 개발되었습니다.

[English README](README.md)

## 주요 기능

- **🎓 Google Scholar 검색**: 기본 및 고급 필터링으로 학술 논문 검색
- **🌐 Google Web 검색**: Google Custom Search API를 사용한 웹 검색
- **📺 YouTube 검색**: 다양한 필터(재생 시간, 업로드 날짜 등)로 동영상 검색
- **🔄 통합 검색**: 모든 소스에서 동시 검색
- **💾 스마트 캐싱**: API 호출을 줄이고 성능을 향상시키는 TTL 기반 캐싱
- **⚡ Rate Limiting**: API 할당량을 준수하는 내장 속도 제한
- **📊 진행률 보고**: 검색 중 실시간 진행률 업데이트
- **🔧 완전 비동기**: 더 나은 성능을 위한 최적화된 비동기 작업

## 기존 대비 주요 개선사항

1. **API 기반 검색**: 웹 스크래핑 대신 공식 API(Google Custom Search, YouTube Data API) 사용으로 안정성과 성능 향상
2. **캐싱 시스템**: 중복 API 호출을 줄이는 TTL 기반 캐싱 구현
3. **Rate Limiting**: API 할당량 소진을 방지하는 자동 속도 제한
4. **동시 검색**: 통합 검색이 모든 검색을 병렬로 실행
5. **향상된 오류 처리**: 상세한 오류 메시지와 포괄적인 오류 처리
6. **Context 통합**: 로깅 및 진행률 보고를 위한 MCP Context 완전 통합

## 설치

### 1. 저장소 복제
```bash
git clone <your-repo-url>
cd unified-search-mcp-server
```

### 2. 가상 환경 생성
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

## 설정

### 환경 변수 설정

API 접근을 위해 다음 환경 변수를 설정하세요:

```bash
# Google Web Search용
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_CSE_ID="your-custom-search-engine-id"

# YouTube Search용
export YOUTUBE_API_KEY="your-youtube-api-key"
```

### API 키 발급 방법

1. **Google Custom Search API** (웹 검색용):
   - [Google Cloud Console](https://console.cloud.google.com) 접속
   - 새 프로젝트 생성 또는 기존 프로젝트 선택
   - "Custom Search API" 활성화
   - 자격 증명 생성 (API 키)
   - [cse.google.com](https://cse.google.com)에서 Custom Search Engine 생성
   - ⚠️ **중요**: 이것은 일반 웹 검색용입니다. Google Scholar와는 무관합니다!

2. **YouTube Data API v3**:
   - 동일한 Google Cloud Console 프로젝트 사용
   - "YouTube Data API v3" 활성화
   - 동일한 API 키 사용 또는 새로 생성

3. **Google Scholar**:
   - 공식 API가 없습니다
   - scholarly 라이브러리를 통한 무료 접근
   - 과도한 사용 시 일시적 차단 가능

## 사용법

### 서버 실행

```bash
python unified_search_server.py
```

또는 FastMCP CLI 사용:
```bash
fastmcp run unified_search_server.py
```

### Claude Desktop에 설치

#### 방법 1: Smithery를 통한 자동 설치 (권장)
Smithery에 게시한 후, 자동으로 다음과 같은 형식으로 설정이 추가됩니다:
```json
{
  "mcpServers": {
    "unified-search-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "@smithery/cli@latest",
        "run",
        "@JDeun/unified-search-mcp",
        "--key",
        "YOUR-SMITHERY-KEY"
      ]
    }
  }
}
```

#### 방법 2: 수동 설정

`claude_desktop_config.json` 파일에 다음 내용 추가:

**Windows:**
```json
{
  "mcpServers": {
    "unified-search": {
      "command": "C:\\Users\\YOUR\\PATH\\python.exe",
      "args": [
        "C:\\Users\\YOUR\\PATH\\unified_search_server.py"
      ],
      "env": {
        "GOOGLE_API_KEY": "your-key",
        "GOOGLE_CSE_ID": "your-cse-id",
        "YOUTUBE_API_KEY": "your-key"
      }
    }
  }
}
```

**Mac/Linux:**
```json
{
  "mcpServers": {
    "unified-search": {
      "command": "python",
      "args": [
        "/path/to/unified_search_server.py"
      ],
      "env": {
        "GOOGLE_API_KEY": "your-key",
        "GOOGLE_CSE_ID": "your-cse-id",
        "YOUTUBE_API_KEY": "your-key"
      }
    }
  }
}
```

### Cursor에 설치

```json
{
  "mcpServers": {
    "unified-search": {
      "command": "python",
      "args": [
        "/path/to/unified_search_server.py"
      ],
      "env": {
        "GOOGLE_API_KEY": "your-key",
        "GOOGLE_CSE_ID": "your-cse-id",
        "YOUTUBE_API_KEY": "your-key"
      }
    }
  }
}
```

## 사용 가능한 도구

### 1. search_google_scholar
학술 논문을 위한 기본 키워드 검색
```python
result = await mcp.use_tool("search_google_scholar", {
    "query": "machine learning",
    "num_results": 5
})
```

### 2. search_google_scholar_advanced
저자 및 연도 필터를 사용한 고급 검색
```python
result = await mcp.use_tool("search_google_scholar_advanced", {
    "query": "deep learning",
    "author": "Yann LeCun",
    "year_start": 2020,
    "year_end": 2024,
    "num_results": 10
})
```

### 3. search_google_web
Google Custom Search API를 사용한 웹 검색
```python
result = await mcp.use_tool("search_google_web", {
    "query": "인공지능 뉴스",
    "num_results": 10,
    "language": "ko",
    "safe_search": "medium"
})
```

### 4. search_youtube
필터를 사용한 YouTube 동영상 검색
```python
result = await mcp.use_tool("search_youtube", {
    "query": "파이썬 튜토리얼",
    "num_results": 15,
    "video_duration": "medium",  # short, medium, long
    "upload_date": "month",      # hour, today, week, month, year
    "order": "viewCount"         # relevance, date, rating, viewCount
})
```

### 5. unified_search
모든 소스에서 동시 검색
```python
result = await mcp.use_tool("unified_search", {
    "query": "기후 변화",
    "sources": ["scholar", "web", "youtube"],
    "num_results_per_source": 5
})
```

### 6. get_author_info
Google Scholar에서 상세한 저자 정보 조회
```python
result = await mcp.use_tool("get_author_info", {
    "author_name": "Geoffrey Hinton"
})
```

### 7. clear_cache
캐시된 검색 결과 삭제
```python
result = await mcp.use_tool("clear_cache", {
    "source": "web"  # scholar, web, youtube, 또는 None (전체)
})
```

### 8. get_api_usage_stats
API 사용량 및 상태 모니터링
```python
result = await mcp.use_tool("get_api_usage_stats", {})
# 반환값: 사용량, 오류 횟수, 캐시 상태, 남은 할당량 등
```

## 성능 최적화

1. **캐싱**: 결과는 1시간(설정 가능) 동안 캐시되어 API 호출 감소
2. **Rate Limiting**: API 호출 간 0.5초 간격으로 할당량 소진 방지
3. **병렬 실행**: 통합 검색이 모든 검색을 동시에 실행
4. **비동기 작업**: 모든 I/O 작업이 비동기로 처리되어 성능 향상
5. **스마트 재시도**: 실패한 검색이 통합 검색의 다른 소스에 영향을 주지 않음

## ⚠️ 중요 공지사항

### Google Scholar 관련
- **공식 API 없음**: Google Scholar는 공식 API를 제공하지 않습니다
- **차단 위험**: 과도한 사용 시 IP가 일시적으로 차단될 수 있습니다
- **상업적 사용 금지**: Google Scholar의 이용약관을 확인하세요
- **대안**: 학술 검색이 중요한 경우 Semantic Scholar API 등 공식 API 사용을 고려하세요

### API 키 관련
- **GOOGLE_CUSTOM_SEARCH_ENGINE_ID**: 일반 웹 검색용 (Google Scholar와 무관)
- **비용 발생 가능**: 무료 할당량 초과 시 자동으로 과금될 수 있습니다
- **API 키 보안**: 환경 변수나 안전한 방법으로 관리하세요

### 프로덕션 사용 시
- **로깅 모니터링**: `unified_search.log` 파일을 정기적으로 확인
- **API 사용량 모니터링**: `get_api_usage_stats` 도구로 사용량 추적
- **캐시 관리**: 필요에 따라 캐시 TTL 조정
- **에러 처리**: 각 소스의 실패가 전체 서비스에 영향을 주지 않도록 설계됨

### API 비용
1. **Google Scholar**: 
   - ✅ 무료 (scholarly 라이브러리 사용)
   - ⚠️ 과도한 사용 시 일시적 차단 위험
   - 💡 2초 간격 자동 rate limiting 적용

2. **Google Custom Search (웹 검색)**: 
   - 무료: 100 쿼리/일
   - 유료: $5 per 1,000 쿼리 (100 쿼리 초과 시)
   - 💡 캐싱으로 중복 쿼리 방지

3. **YouTube Data API**: 
   - 무료: 10,000 유닛/일
   - 검색 작업: 100 유닛 소비
   - 💡 하루 약 100회 검색 가능

### 안정성 개선 사항
1. **캐싱**: 1시간 동안 결과 저장으로 API 사용량 감소
2. **Rate Limiting**: 
   - Google Scholar: 2초 간격
   - 기타 API: 1초 간격
3. **재시도 로직**: Google Scholar 차단 시 자동 재시도
4. **오류 처리**: 각 소스별 독립적 오류 처리

## 개발

### 테스트
```python
import asyncio
from fastmcp import Client

async def test():
    async with Client("unified_search_server.py") as client:
        # Google Scholar 테스트
        result = await client.call_tool("search_google_scholar", {
            "query": "양자 컴퓨팅"
        })
        print(result)

asyncio.run(test())
```

### 새로운 검색 소스 추가

1. 내부 검색 함수 생성:
```python
async def search_new_source_internal(query: str, **kwargs) -> List[Dict]:
    # 구현
    pass
```

2. MCP 도구 추가:
```python
@mcp.tool()
async def search_new_source(query: str, ctx: Context) -> List[Dict]:
    # 캐싱과 rate limiting을 포함한 도구 구현
    pass
```

3. unified_search 업데이트하여 새 소스 포함

## 오류 처리

서버는 다양한 오류 시나리오를 처리합니다:
- API 자격 증명 누락
- API 할당량 초과
- 네트워크 장애
- 잘못된 매개변수
- 검색 시간 초과

모든 오류는 로깅되고 일관된 형식으로 반환됩니다.

## 문제 해결

### API 키 관련 문제
- 환경 변수가 올바르게 설정되었는지 확인
- Google Cloud Console에서 API가 활성화되었는지 확인
- API 키의 사용 제한 확인

### 검색 결과가 없을 때
- 검색어를 단순하게 변경해보기
- 캐시를 지우고 다시 시도 (`clear_cache` 도구 사용)
- 로그에서 구체적인 오류 메시지 확인

## 라이선스

MIT License

## 기여

기여를 환영합니다! Pull Request를 자유롭게 제출해주세요.

## 감사의 말

- 원본 [Google Scholar MCP Server](https://github.com/DeadWaveWave/Google-Scholar-MCP-Server) 기반
- [FastMCP](https://github.com/jlowin/fastmcp)로 구축됨
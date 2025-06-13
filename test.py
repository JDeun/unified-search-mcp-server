"""
Unified Search MCP Server 기본 테스트 스크립트
Basic test script for Unified Search MCP Server
"""
import asyncio
import sys
from fastmcp import Client
import json


async def test_basic_functionality():
    """Unified Search MCP Server의 기본 기능 테스트"""
    
    print("🔧 Unified Search MCP Server 테스트 중...")
    print("-" * 50)
    
    try:
        # 서버 연결
        async with Client("unified_search_server.py") as client:
            print("✅ 서버 연결 성공")
            
            # 사용 가능한 도구 목록
            tools = await client.list_tools()
            print(f"\n📋 사용 가능한 도구: {len(tools)}개")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:50]}...")
            
            # 테스트 1: Google Scholar 검색
            print("\n🎓 Google Scholar 검색 테스트...")
            try:
                result = await client.call_tool("search_google_scholar", {
                    "query": "artificial intelligence",
                    "num_results": 3
                })
                print(f"  {len(result)}개 결과 발견")
                if result and isinstance(result[0], dict):
                    if 'error' not in result[0]:
                        print(f"  첫 번째 결과: {result[0].get('title', '제목 없음')[:60]}...")
                    else:
                        print(f"  ⚠️  {result[0]['error']}")
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
            
            # 테스트 2: Google Web 검색 (API 키 없으면 실패할 수 있음)
            print("\n🌐 Google Web 검색 테스트...")
            try:
                result = await client.call_tool("search_google_web", {
                    "query": "Python programming",
                    "num_results": 3
                })
                if result and isinstance(result[0], dict):
                    if 'error' in result[0]:
                        print(f"  ⚠️  예상된 오류: {result[0]['error']}")
                        print("     💡 팁: GOOGLE_API_KEY와 GOOGLE_CUSTOM_SEARCH_ENGINE_ID를 설정하세요")
                    else:
                        print(f"  {len(result)}개 결과 발견")
                        print(f"  첫 번째 결과: {result[0].get('title', '제목 없음')[:60]}...")
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
            
            # 테스트 3: YouTube 검색 (API 키 없으면 실패할 수 있음)
            print("\n📺 YouTube 검색 테스트...")
            try:
                result = await client.call_tool("search_youtube", {
                    "query": "MCP tutorial",
                    "num_results": 3
                })
                if result and isinstance(result[0], dict):
                    if 'error' in result[0]:
                        print(f"  ⚠️  예상된 오류: {result[0]['error']}")
                    else:
                        print(f"  {len(result)}개 결과 발견")
                        print(f"  첫 번째 동영상: {result[0].get('title', '제목 없음')[:60]}...")
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
            
            # 테스트 4: 통합 검색
            print("\n🔄 통합 검색 테스트...")
            try:
                result = await client.call_tool("unified_search", {
                    "query": "machine learning",
                    "sources": ["scholar"],  # API 키 문제를 피하기 위해 scholar만 사용
                    "num_results_per_source": 2
                })
                for source, items in result.items():
                    print(f"  {source}: {len(items)}개 결과")
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
            
            # 테스트 5: 저자 정보
            print("\n👤 저자 정보 조회 테스트...")
            try:
                result = await client.call_tool("get_author_info", {
                    "author_name": "Geoffrey Hinton"
                })
                if isinstance(result, dict) and 'error' not in result:
                    print(f"  이름: {result.get('name', 'N/A')}")
                    print(f"  소속: {result.get('affiliation', 'N/A')}")
                    print(f"  인용수: {result.get('citedby', 0)}")
                    print(f"  논문수: {len(result.get('publications', []))}")
                else:
                    print(f"  ⚠️  {result.get('error', '알 수 없는 오류')}")
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
            
            # 테스트 6: 캐시 삭제
            print("\n🗑️  캐시 삭제 테스트...")
            try:
                result = await client.call_tool("clear_cache", {})
                print(f"  {result.get('message', '캐시 삭제됨')}")
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
            
            # 테스트 7: API 사용량 통계
            print("\n📊 API 사용량 통계 테스트...")
            try:
                result = await client.call_tool("get_api_usage_stats", {})
                print(f"  검색 횟수: Scholar={result['usage'].get('google_scholar', 0)}, "
                      f"Web={result['usage'].get('google_web', 0)}, "
                      f"YouTube={result['usage'].get('youtube', 0)}")
                print(f"  캐시 상태: Scholar={result['cache_stats']['scholar']['size']}/{result['cache_stats']['scholar']['max_size']}")
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
            
            print("\n✅ 모든 테스트 완료!")
            
    except Exception as e:
        print(f"\n❌ 서버 연결 실패: {str(e)}")
        print("\n서버가 설치되고 접근 가능한지 확인하세요.")
        sys.exit(1)


async def test_with_api_keys():
    """API 키가 필요한 기능 테스트"""
    print("\n🔑 API 키를 사용한 테스트...")
    print("-" * 50)
    
    async with Client("unified_search_server.py") as client:
        # 전체 통합 검색
        print("\n🔄 전체 통합 검색 테스트 (모든 소스)...")
        try:
            result = await client.call_tool("unified_search", {
                "query": "climate change solutions",
                "sources": ["scholar", "web", "youtube"],
                "num_results_per_source": 3
            })
            
            for source, items in result.items():
                print(f"\n{source.upper()} 결과:")
                if items and isinstance(items[0], dict) and 'error' in items[0]:
                    print(f"  ⚠️  {items[0]['error']}")
                else:
                    for i, item in enumerate(items[:2], 1):
                        title = item.get('title', '제목 없음')
                        print(f"  {i}. {title[:60]}...")
        except Exception as e:
            print(f"  ❌ 오류: {str(e)}")


async def main():
    """모든 테스트 실행"""
    # 기본 테스트 (API 키 없이도 작동)
    await test_basic_functionality()
    
    # API 키가 필요한 테스트 옵션
    print("\n" + "="*50)
    response = input("\nAPI 키가 필요한 기능을 테스트하시겠습니까? (y/n): ")
    if response.lower() == 'y':
        await test_with_api_keys()
    
    print("\n🎉 테스트 완료!")


if __name__ == "__main__":
    # 서버 파일 존재 확인
    import os
    if not os.path.exists("unified_search_server.py"):
        print("❌ 오류: unified_search_server.py 파일을 찾을 수 없습니다!")
        print("올바른 디렉토리에서 이 테스트를 실행하고 있는지 확인하세요.")
        sys.exit(1)
    
    asyncio.run(main())
#!/usr/bin/env python3
"""
Unified Search MCP Server 설치 스크립트
Installation script for Unified Search MCP Server
"""
import os
import sys
import json
import platform
import subprocess
import shutil
from pathlib import Path


def get_claude_config_path():
    """Claude Desktop 설정 파일 경로 반환"""
    system = platform.system()
    
    if system == "Windows":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    else:
        raise Exception(f"지원되지 않는 운영체제: {system}")


def get_python_path():
    """현재 Python 실행 파일 경로 반환"""
    return sys.executable


def install_dependencies():
    """필요한 패키지 설치"""
    print("📦 의존성 패키지 설치 중...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ 패키지 설치 완료")
        return True
    except subprocess.CalledProcessError:
        print("❌ 패키지 설치 실패")
        return False


def setup_api_keys():
    """API 키 설정"""
    print("\n🔑 API 키 설정")
    print("-" * 50)
    
    env_vars = {}
    
    # Google API 설정
    print("\n1. Google Custom Search API (일반 웹 검색용)")
    print("   ⚠️  주의: 이것은 Google Scholar가 아닌 일반 웹 검색을 위한 API입니다!")
    print("   - https://console.cloud.google.com 에서 API 키 발급")
    print("   - https://cse.google.com 에서 Custom Search Engine ID 생성")
    print("   - 무료: 100 쿼리/일, 초과 시 유료 ($5/1000 쿼리)")
    google_api = input("   Google API Key (선택사항, Enter로 건너뛰기): ").strip()
    google_cse = input("   Google Custom Search Engine ID (선택사항, Enter로 건너뛰기): ").strip()
    
    if google_api:
        env_vars["GOOGLE_API_KEY"] = google_api
    if google_cse:
        env_vars["GOOGLE_CUSTOM_SEARCH_ENGINE_ID"] = google_cse
    
    # YouTube API 설정
    print("\n2. YouTube Data API v3")
    print("   - Google Cloud Console에서 YouTube Data API v3 활성화")
    print("   - 무료: 10,000 유닛/일 (검색당 100 유닛)")
    youtube_api = input("   YouTube API Key (선택사항, Enter로 건너뛰기): ").strip()
    
    if youtube_api:
        env_vars["YOUTUBE_API_KEY"] = youtube_api
    
    print("\n3. Google Scholar")
    print("   ✅ API 키 불필요 (scholarly 라이브러리 사용)")
    print("   ⚠️  과도한 사용 시 일시적 차단 가능")
    
    return env_vars


def update_claude_config(env_vars):
    """Claude Desktop 설정 파일 업데이트"""
    config_path = get_claude_config_path()
    python_path = get_python_path()
    server_path = os.path.abspath("unified_search_server.py")
    
    print(f"\n📝 Claude Desktop 설정 업데이트 중...")
    print(f"   설정 파일: {config_path}")
    
    # 설정 디렉토리 생성
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 기존 설정 읽기
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {}
    else:
        config = {}
    
    # mcpServers 섹션 확인
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Unified Search 서버 설정 추가
    config["mcpServers"]["unified-search"] = {
        "command": python_path,
        "args": [server_path],
        "env": env_vars if env_vars else {}
    }
    
    # 설정 저장
    try:
        # 백업 생성
        if config_path.exists():
            backup_path = config_path.with_suffix('.json.bak')
            shutil.copy(config_path, backup_path)
            print(f"   백업 생성: {backup_path}")
        
        # 새 설정 저장
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("✅ Claude Desktop 설정 업데이트 완료")
        return True
    except Exception as e:
        print(f"❌ 설정 업데이트 실패: {e}")
        return False


def test_installation():
    """설치 테스트"""
    print("\n🧪 설치 테스트 중...")
    try:
        # 서버 시작 테스트
        process = subprocess.Popen(
            [sys.executable, "unified_search_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 잠시 대기
        import time
        time.sleep(2)
        
        # 프로세스 종료
        process.terminate()
        
        print("✅ 서버 실행 테스트 성공")
        return True
    except Exception as e:
        print(f"❌ 서버 실행 테스트 실패: {e}")
        return False


def main():
    """메인 설치 프로세스"""
    print("🚀 Unified Search MCP Server 설치 시작")
    print("=" * 50)
    
    # 현재 디렉토리 확인
    if not os.path.exists("unified_search_server.py"):
        print("❌ unified_search_server.py 파일을 찾을 수 없습니다.")
        print("   프로젝트 디렉토리에서 이 스크립트를 실행하세요.")
        sys.exit(1)
    
    # 1. 의존성 설치
    if not install_dependencies():
        print("\n설치를 중단합니다.")
        sys.exit(1)
    
    # 2. API 키 설정
    env_vars = setup_api_keys()
    
    # 3. Claude Desktop 설정 업데이트
    if not update_claude_config(env_vars):
        print("\n설치를 중단합니다.")
        sys.exit(1)
    
    # 4. 설치 테스트
    test_installation()
    
    # 완료 메시지
    print("\n" + "=" * 50)
    print("🎉 설치 완료!")
    print("\n다음 단계:")
    print("1. Claude Desktop을 재시작하세요")
    print("2. Claude에서 다음과 같이 테스트해보세요:")
    print('   "search_google_scholar 도구를 사용해서 machine learning 관련 논문을 찾아줘"')
    
    if not env_vars:
        print("\n⚠️  API 키를 설정하지 않았습니다.")
        print("   Google Scholar는 API 키 없이도 작동하지만,")
        print("   Google Web과 YouTube 검색을 사용하려면 API 키가 필요합니다.")
        print(f"   나중에 {get_claude_config_path()} 파일을 편집하여 추가할 수 있습니다.")


if __name__ == "__main__":
    main()
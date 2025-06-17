# tests/conftest.py
"""
pytest 설정 및 공통 fixture
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
import os

# 환경 변수 설정
os.environ['MCP_ENV'] = 'test'
os.environ['MCP_LOG_LEVEL'] = 'ERROR'  # 테스트 중 로그 최소화


@pytest.fixture(scope='session')
def event_loop():
    """이벤트 루프 fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_singletons():
    """싱글톤 리셋"""
    # 각 테스트 전에 싱글톤 초기화
    # 싱글톤 리셋을 위한 모듈 import
    import src.config.settings as settings_module
    if hasattr(settings_module, '_settings'):
        settings_module._settings = None
    
    import src.cache.manager as cache_module
    if hasattr(cache_module, '_cache_manager'):
        cache_module._cache_manager = None
    
    import src.services.unified as unified_module
    if hasattr(unified_module, '_unified_service'):
        unified_module._unified_service = None


@pytest.fixture
def mock_redis():
    """Redis 모킹"""
    with patch('redis.asyncio.from_url') as mock:
        redis_client = Mock()
        mock.return_value = redis_client
        yield redis_client


@pytest.fixture
def mock_cache_manager():
    """캐시 관리자 모킹"""
    with patch('src.cache.get_cache_manager') as mock:
        cache = Mock()
        cache.get = Mock(return_value=None)  # 캐시 미스
        cache.set = Mock(return_value=True)
        cache.delete = Mock(return_value=True)
        cache.clear = Mock(return_value=10)
        cache.get_stats = Mock(return_value={
            'hits': 100,
            'misses': 50,
            'hit_rate': 66.67
        })
        mock.return_value = cache
        yield cache

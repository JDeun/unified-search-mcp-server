# tests/test_basic.py
"""
기본 테스트
서버가 정상적으로 시작되는지 확인
"""
import pytest
import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import get_settings
from src.config.security import InputSanitizer
from src.models import SearchSource, ValidationError


def test_settings():
    """설정 로드 테스트"""
    settings = get_settings()
    assert settings is not None
    assert settings.environment in ['development', 'staging', 'production']


def test_input_sanitizer():
    """입력 검증 테스트"""
    # 정상 쿼리
    clean_query = InputSanitizer.sanitize_query("test query")
    assert clean_query == "test query"
    
    # XSS 시도
    xss_query = InputSanitizer.sanitize_query("<script>alert('xss')</script>test")
    assert "<script>" not in xss_query
    assert "alert" not in xss_query
    
    # 길이 제한
    long_query = InputSanitizer.sanitize_query("a" * 1000, max_length=100)
    assert len(long_query) == 100


def test_numeric_validation():
    """숫자 검증 테스트"""
    # 정상 값
    result = InputSanitizer.validate_numeric_param(5, min_val=1, max_val=10)
    assert result == 5
    
    # 범위 초과
    with pytest.raises(ValueError):
        InputSanitizer.validate_numeric_param(15, min_val=1, max_val=10)
    
    # 범위 미만
    with pytest.raises(ValueError):
        InputSanitizer.validate_numeric_param(0, min_val=1, max_val=10)


def test_enum_validation():
    """열거형 검증 테스트"""
    # 정상 값
    result = InputSanitizer.validate_enum_param(
        "scholar", 
        ["scholar", "web", "youtube"]
    )
    assert result == "scholar"
    
    # 잘못된 값
    with pytest.raises(ValueError):
        InputSanitizer.validate_enum_param(
            "invalid", 
            ["scholar", "web", "youtube"]
        )


def test_search_source_enum():
    """검색 소스 열거형 테스트"""
    assert SearchSource.SCHOLAR.value == "scholar"
    assert SearchSource.WEB.value == "web"
    assert SearchSource.YOUTUBE.value == "youtube"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

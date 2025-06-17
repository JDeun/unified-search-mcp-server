# src/utils/logging.py
"""
로깅 유틸리티
구조화된 로깅 및 감사 로깅
"""
import logging
import logging.config
import json
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar
import sys

from ..config import get_settings

# 요청 컨텍스트
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
client_id_var: ContextVar[Optional[str]] = ContextVar('client_id', default=None)


class ContextFilter(logging.Filter):
    """컨텍스트 정보를 로그에 추가하는 필터"""
    
    def filter(self, record):
        record.request_id = request_id_var.get() or 'no-request-id'
        record.client_id = client_id_var.get() or 'anonymous'
        return True


class AuditLogger:
    """감사 로깅"""
    
    def __init__(self, name: str = "audit"):
        self.logger = logging.getLogger(f"{name}.audit")
    
    def log_search(
        self,
        query: str,
        source: str,
        results_count: int,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """검색 로그"""
        self.logger.info(
            "search_performed",
            extra={
                'event_type': 'search',
                'query': query,
                'source': source,
                'results_count': results_count,
                'duration': duration,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def log_api_call(
        self,
        api: str,
        endpoint: str,
        status: int,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """API 호출 로그"""
        self.logger.info(
            "api_call",
            extra={
                'event_type': 'api_call',
                'api': api,
                'endpoint': endpoint,
                'status': status,
                'duration': duration,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """에러 로그"""
        self.logger.error(
            "error_occurred",
            extra={
                'event_type': 'error',
                'error_type': error_type,
                'error_message': error_message,
                'source': source,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """보안 이벤트 로그"""
        self.logger.warning(
            "security_event",
            extra={
                'event_type': 'security',
                'security_event_type': event_type,
                'description': description,
                'severity': severity,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow().isoformat()
            }
        )


class PerformanceLogger:
    """성능 로깅을 위한 컨텍스트 매니저"""
    
    def __init__(self, operation: str, logger: logging.Logger):
        self.operation = operation
        self.logger = logger
        self.start_time = None
        self.context = {}
    
    def add_context(self, **kwargs):
        """컨텍스트 추가"""
        self.context.update(kwargs)
        return self
    
    async def __aenter__(self):
        self.start_time = datetime.utcnow()
        self.logger.debug(f"{self.operation} 시작", extra=self.context)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"{self.operation} 실패",
                extra={
                    **self.context,
                    'duration': duration,
                    'error': str(exc_val)
                }
            )
        else:
            self.logger.info(
                f"{self.operation} 완료",
                extra={
                    **self.context,
                    'duration': duration
                }
            )


def setup_logging():
    """로깅 설정"""
    settings = get_settings()
    log_config = settings.get_log_config()
    
    # 컨텍스트 필터 추가
    for handler in log_config.get('handlers', {}).values():
        if 'filters' not in handler:
            handler['filters'] = []
        handler['filters'].append('context_filter')
    
    # 필터 설정 추가
    if 'filters' not in log_config:
        log_config['filters'] = {}
    
    log_config['filters']['context_filter'] = {
        '()': ContextFilter
    }
    
    # 로깅 설정 적용
    logging.config.dictConfig(log_config)
    
    # 외부 라이브러리 로깅 레벨 조정
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('scholarly').setLevel(logging.WARNING)
    logging.getLogger('redis').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """로거 가져오기"""
    return logging.getLogger(name)


def set_request_context(request_id: Optional[str] = None, client_id: Optional[str] = None):
    """요청 컨텍스트 설정"""
    if request_id:
        request_id_var.set(request_id)
    if client_id:
        client_id_var.set(client_id)


def clear_request_context():
    """요청 컨텍스트 클리어"""
    request_id_var.set(None)
    client_id_var.set(None)


# 싱글톤 감사 로거
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """감사 로거 가져오기"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

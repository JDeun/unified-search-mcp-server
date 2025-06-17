# src/models/errors.py
"""
Error models and exception handling using Pydantic v2
"""
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response"""
    model_config = ConfigDict(populate_by_name=True)
    
    error_code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    user_message: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return self.model_dump(exclude_none=True)


class ValidationError(Exception):
    """Input validation error"""
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        self.user_message = f"Invalid input: {message}"
        super().__init__(self.message)
    
    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert to error response"""
        details = {}
        if self.field:
            details['field'] = self.field
        if self.value is not None:
            details['value'] = str(self.value)
        
        return ErrorResponse(
            error_code="VALIDATION_ERROR",
            message=self.message,
            user_message=self.user_message,
            request_id=request_id,
            details=details if details else None
        )


class ServiceError(Exception):
    """Service-level error"""
    def __init__(
        self,
        error_code: str = "SERVICE_ERROR",
        message: str = "Service error occurred",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.user_message = user_message or message
        self.details = details
        super().__init__(self.message)
    
    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert to error response"""
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            user_message=self.user_message,
            request_id=request_id,
            details=self.details
        )
    
    def log_error(self, request_id: Optional[str] = None):
        """Log the error"""
        logger.error(
            f"ServiceError [{self.error_code}]: {self.message}",
            extra={
                'error_code': self.error_code,
                'request_id': request_id,
                'details': self.details
            }
        )


class ExternalAPIError(ServiceError):
    """External API error"""
    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_code = f"EXTERNAL_API_ERROR_{service.upper()}"
        user_message = f"External service error: {service} is currently unavailable"
        
        error_details = {'service': service}
        if status_code:
            error_details['status_code'] = status_code
        if details:
            error_details.update(details)
        
        super().__init__(
            error_code=error_code,
            message=message,
            user_message=user_message,
            details=error_details
        )


class RateLimitError(ServiceError):
    """Rate limit exceeded error"""
    def __init__(
        self,
        service: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {'service': service}
        if retry_after:
            error_details['retry_after'] = retry_after
        if details:
            error_details.update(details)
        
        super().__init__(
            error_code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded for {service}",
            user_message=f"Too many requests. Please try again in {retry_after or 60} seconds.",
            details=error_details
        )


class TimeoutError(ServiceError):
    """Request timeout error"""
    def __init__(
        self,
        service: str,
        timeout: int,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {
            'service': service,
            'timeout': timeout
        }
        if details:
            error_details.update(details)
        
        super().__init__(
            error_code="REQUEST_TIMEOUT",
            message=f"Request to {service} timed out after {timeout}s",
            user_message="Request timed out. Please try again.",
            details=error_details
        )


class CacheError(ServiceError):
    """Cache-related error"""
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {}
        if operation:
            error_details['operation'] = operation
        if details:
            error_details.update(details)
        
        super().__init__(
            error_code="CACHE_ERROR",
            message=message,
            user_message="Cache operation failed. The service is still available.",
            details=error_details if error_details else None
        )


def handle_unexpected_error(
    error: Exception,
    request_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """Handle unexpected errors"""
    # Log the full traceback
    logger.exception(
        "Unexpected error occurred",
        extra={
            'request_id': request_id,
            'context': context
        }
    )
    
    # Create user-friendly response
    return ErrorResponse(
        error_code="INTERNAL_ERROR",
        message=str(error),
        user_message="An unexpected error occurred. Please try again later.",
        request_id=request_id,
        details={
            'type': type(error).__name__,
            'traceback': traceback.format_exc() if logger.isEnabledFor(logging.DEBUG) else None
        }
    )

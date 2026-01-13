"""
Centralized error handling for consistent API responses.

Features:
- Standardized error response format
- Proper HTTP status codes
- No internal error details exposed to clients
- Structured logging of errors
"""

from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional
from utils.logger import get_logger

logger = get_logger("backend.core.error_handler")


class ErrorResponse(BaseModel):
    """Standardized error response format"""
    error: str  # Short error code/type (e.g., "NOT_FOUND", "UNAUTHORIZED")
    detail: str  # User-friendly error message
    request_id: Optional[str] = None  # For debugging/correlation


class ErrorHandler:
    """Helper class for consistent error handling"""
    
    @staticmethod
    def not_found(detail: str = "Resource not found") -> HTTPException:
        """Return a 404 Not Found error"""
        return HTTPException(status_code=404, detail=detail)
    
    @staticmethod
    def unauthorized(detail: str = "Authentication required") -> HTTPException:
        """Return a 401 Unauthorized error"""
        return HTTPException(status_code=401, detail=detail)
    
    @staticmethod
    def forbidden(detail: str = "Access denied") -> HTTPException:
        """Return a 403 Forbidden error"""
        return HTTPException(status_code=403, detail=detail)
    
    @staticmethod
    def bad_request(detail: str = "Invalid request") -> HTTPException:
        """Return a 400 Bad Request error"""
        return HTTPException(status_code=400, detail=detail)
    
    @staticmethod
    def conflict(detail: str = "Resource conflict") -> HTTPException:
        """Return a 409 Conflict error"""
        return HTTPException(status_code=409, detail=detail)
    
    @staticmethod
    def rate_limited(detail: str = "Rate limit exceeded") -> HTTPException:
        """Return a 429 Too Many Requests error"""
        return HTTPException(status_code=429, detail=detail)
    
    @staticmethod
    def internal_error(detail: str = "Internal server error") -> HTTPException:
        """
        Return a 500 Internal Server Error.
        Always log the full error details (internal error is logged, user only sees generic message).
        """
        logger.error(f"Internal server error: {detail}")
        return HTTPException(
            status_code=500, 
            detail="An internal error occurred. Please try again later."
        )
    
    @staticmethod
    def service_unavailable(detail: str = "Service temporarily unavailable") -> HTTPException:
        """Return a 503 Service Unavailable error"""
        logger.warning(f"Service unavailable: {detail}")
        return HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again later."
        )

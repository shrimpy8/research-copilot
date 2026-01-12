"""
Standardized API responses for Research Copilot.

Per PRD §6 - Stripe-style API response wrapper with metadata.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Optional, TypeVar

from src.models import ApiResponse, ApiError, ResponseMeta

T = TypeVar("T")


def success_response(
    data: T,
    request_id: Optional[str] = None,
    start_time: Optional[float] = None,
) -> ApiResponse:
    """Create a standardized success response."""
    duration_ms = int((time.time() - start_time) * 1000) if start_time else 0
    return ApiResponse(
        success=True,
        data=data,
        error=None,
        meta=ResponseMeta(
            request_id=request_id or f"req_{uuid.uuid4().hex[:16]}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            duration_ms=duration_ms,
        ),
    )


def error_response(
    code: str,
    message: str,
    error_type: str,
    param: Optional[str] = None,
    details: Optional[dict] = None,
    suggestion: Optional[str] = None,
    request_id: Optional[str] = None,
) -> ApiResponse:
    """Create a standardized error response."""
    return ApiResponse(
        success=False,
        data=None,
        error=ApiError(
            code=code,
            message=message,
            type=error_type,
            param=param,
            details=details,
            suggestion=suggestion,
        ),
        meta=ResponseMeta(
            request_id=request_id or f"req_{uuid.uuid4().hex[:16]}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            duration_ms=0,
        ),
    )

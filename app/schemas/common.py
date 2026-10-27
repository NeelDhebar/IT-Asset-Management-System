"""Common Pydantic Schemas and Response Wrappers."""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper."""
    success: bool = True
    message: str = "Operation completed successfully."
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """Standardized API error response."""
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

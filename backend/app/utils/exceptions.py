"""Custom Exception Hierarchy for Smart IT Asset & Support Ticket Management System.

Demonstrates:
- Clean OOP exception inheritance hierarchy
- Domain-specific error codes and HTTP mapping hints
- Custom exception handling for business logic and data layers
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception for all domain and service errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception data to a structured dictionary for JSON responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


# Asset Exceptions
class InvalidAssetError(AppException):
    """Raised when asset validation fails or invalid operations are attempted."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, status_code=400, details=details)


class AssetNotFoundError(AppException):
    """Raised when an asset is not found in the repository."""

    def __init__(self, asset_id: str) -> None:
        super().__init__(
            message=f"Asset with ID '{asset_id}' was not found.",
            status_code=404,
            details={"asset_id": asset_id},
        )


# Ticket Exceptions
class InvalidTicketError(AppException):
    """Raised when a support ticket payload or operation is invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, status_code=400, details=details)


class TicketNotFoundError(AppException):
    """Raised when a ticket is not found."""

    def __init__(self, ticket_id: str) -> None:
        super().__init__(
            message=f"Ticket with ID '{ticket_id}' was not found.",
            status_code=404,
            details={"ticket_id": ticket_id},
        )


class InvalidStatusTransitionError(AppException):
    """Raised when a ticket or asset status change violates the allowed workflow state machine."""

    def __init__(self, current_status: str, target_status: str, entity: str = "Ticket") -> None:
        message = (
            f"Invalid {entity} status transition from '{current_status}' to '{target_status}'."
        )
        super().__init__(
            message=message,
            status_code=422,
            details={
                "entity": entity,
                "current_status": current_status,
                "target_status": target_status,
            },
        )


# SLA Exceptions
class SLAConfigurationError(AppException):
    """Raised when SLA priority or rule configuration is missing or malformed."""

    def __init__(self, priority: str) -> None:
        super().__init__(
            message=f"Invalid SLA configuration for priority '{priority}'.",
            status_code=400,
            details={"priority": priority},
        )


# File Processing Exceptions
class FileProcessingError(AppException):
    """Raised when parsing, reading, writing, or archiving text data files fails."""

    def __init__(self, filename: str, reason: str) -> None:
        super().__init__(
            message=f"File processing failed for '{filename}': {reason}",
            status_code=400,
            details={"filename": filename, "reason": reason},
        )


# Database Exceptions
class DatabaseConnectionError(AppException):
    """Raised when relational database connectivity or transaction fails."""

    def __init__(self, message: str = "Database connection or transaction failure occurred.") -> None:
        super().__init__(message=message, status_code=503)


# Security Exceptions
class AuthenticationError(AppException):
    """Raised when user credentials or JWT token is invalid or expired."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message=message, status_code=401)


class AuthorizationError(AppException):
    """Raised when authenticated user lacks permissions for the requested resource."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message=message, status_code=403)


class DuplicateRecordError(AppException):
    """Raised when attempting to insert a record with a unique constraint violation."""

    def __init__(self, field: str, value: Any) -> None:
        super().__init__(
            message=f"Record with {field}='{value}' already exists.",
            status_code=409,
            details={"field": field, "value": value},
        )

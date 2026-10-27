"""Unit Tests for Custom Python Decorators."""

import pytest
from app.models.enums import UserRole
from app.utils.decorators import (
    measure_execution_time,
    log_activity,
    login_required,
    admin_required,
)
from app.utils.exceptions import AuthenticationError, AuthorizationError


def test_measure_execution_time_sync():
    """Verify @measure_execution_time preserves return value."""
    @measure_execution_time
    def add(a: int, b: int) -> int:
        return a + b

    result = add(5, 7)
    assert result == 12


def test_log_activity_decorator():
    """Verify @log_activity executes and preserves exceptions."""
    @log_activity("TEST_OPERATION")
    def multiply(a: int, b: int) -> int:
        return a * b

    assert multiply(3, 4) == 12


def test_login_required_decorator_guard():
    """Verify @login_required raises AuthenticationError if current_user missing."""
    @login_required
    def secured_action(current_user=None):
        return "Access Granted"

    # Missing user raises AuthenticationError
    with pytest.raises(AuthenticationError):
        secured_action(current_user=None)

    # Valid user passes
    assert secured_action(current_user={"user_id": "EMP-101"}) == "Access Granted"


def test_admin_required_decorator_guard():
    """Verify @admin_required enforces ADMIN role."""
    @admin_required
    def admin_action(current_user=None):
        return "Admin Cleared"

    # Employee attempting admin action raises AuthorizationError
    with pytest.raises(AuthorizationError):
        admin_action(current_user={"user_id": "EMP-101", "role": "EMPLOYEE"})

    # Admin passes
    assert admin_action(current_user={"user_id": "ADM-001", "role": "ADMIN"}) == "Admin Cleared"

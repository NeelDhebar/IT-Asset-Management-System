"""Custom Python Decorators.

Demonstrates:
- Function decorators with *args and **kwargs
- functools.wraps preserving function metadata
- Performance measurement decorator (@measure_execution_time)
- Structured activity logging decorator (@log_activity)
- Role and Authentication enforcement decorators (@login_required, @admin_required)
"""

import time
import functools
import inspect
from typing import Any, Callable, List
from app.utils.logger import get_logger
from app.utils.exceptions import AuthenticationError, AuthorizationError
from app.models.enums import UserRole

logger = get_logger()


def measure_execution_time(func: Callable) -> Callable:
    """Decorator to measure and log execution duration of synchronous and asynchronous functions."""
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                logger.info(
                    "Execution metrics: [async] %s executed in %.2f ms",
                    func.__qualname__,
                    duration_ms,
                )
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                logger.info(
                    "Execution metrics: [sync] %s executed in %.2f ms",
                    func.__qualname__,
                    duration_ms,
                )
        return sync_wrapper


def log_activity(action_name: str) -> Callable:
    """Decorator to automatically log business actions and identify caller parameters."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info("Activity Started: [%s] via %s", action_name, func.__name__)
            try:
                result = func(*args, **kwargs)
                logger.info("Activity Completed Successfully: [%s]", action_name)
                return result
            except Exception as exc:
                logger.error("Activity Failed: [%s] with error: %s", action_name, str(exc))
                raise
        return wrapper
    return decorator


def login_required(func: Callable) -> Callable:
    """Decorator that verifies user authentication context exists in kwargs."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        current_user = kwargs.get("current_user")
        if not current_user:
            raise AuthenticationError("User authentication is required to access this resource.")
        return func(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles: UserRole) -> Callable:
    """Decorator that verifies the user possesses one of the authorized roles."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_user = kwargs.get("current_user")
            if not current_user:
                raise AuthenticationError("Authentication required.")
            user_role = getattr(current_user, "role", None) or (
                current_user.get("role") if isinstance(current_user, dict) else None
            )
            if isinstance(user_role, str):
                try:
                    user_role = UserRole(user_role)
                except ValueError:
                    user_role = None

            if user_role not in allowed_roles:
                allowed_str = ", ".join(r.value for r in allowed_roles)
                raise AuthorizationError(
                    f"Access restricted. Required role: {allowed_str}. Your role: {user_role}."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(func: Callable) -> Callable:
    """Shortcut decorator for Admin-only operations."""
    return role_required(UserRole.ADMIN)(func)

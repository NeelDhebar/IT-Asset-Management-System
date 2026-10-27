"""Authentication & RBAC Security Router.

Demonstrates:
- JWT Bearer Token Authentication
- Role-Based Access Control (ADMIN, SUPPORT, EMPLOYEE)
- FastAPI Dependency Injection (Depends)
- Password hashing verification
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.repositories import UserRepository, ActivityLogRepository
from app.models.enums import UserRole
from app.models.orm import UserModel
from app.schemas.user import UserCreate, UserResponse, LoginRequest, Token
from app.schemas.common import APIResponse
from app.utils.security import hash_password, verify_password, create_access_token, decode_access_token
from app.utils.exceptions import AuthenticationError, AuthorizationError
from app.utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """Dependency extracting and validating current user from JWT Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token payload missing subject.")

        user_repo = UserRepository(db)
        user = user_repo.get_by_user_id(user_id)
        if not user:
            raise AuthenticationError("User associated with token no longer exists.")
        if not user.is_active:
            raise AuthenticationError("User account is inactive.")

        return user
    except AuthenticationError as auth_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_err.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(*allowed_roles: UserRole):
    """Factory dependency for role-based access control (RBAC)."""
    def role_checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        user_role = UserRole(current_user.role)
        if user_role not in allowed_roles:
            logger.warning(
                "Access forbidden: User %s (Role %s) attempted to access resource requiring %s",
                current_user.user_id,
                user_role.value,
                [r.value for r in allowed_roles],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden. Required role: {[r.value for r in allowed_roles]}",
            )
        return current_user
    return role_checker


@router.post("/register", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> APIResponse[UserResponse]:
    """Register a new user account."""
    user_repo = UserRepository(db)
    hashed_pwd = hash_password(user_in.password)

    created_user = user_repo.create({
        "user_id": user_in.user_id,
        "email": user_in.email,
        "hashed_password": hashed_pwd,
        "full_name": user_in.full_name,
        "role": user_in.role.value,
        "department": user_in.department,
        "is_active": True,
    })

    ActivityLogRepository(db).log(
        user_id=created_user.user_id,
        action="USER_REGISTERED",
        entity_type="User",
        entity_id=created_user.user_id,
    )

    return APIResponse(message="User registered successfully.", data=UserResponse.model_validate(created_user))


@router.post("/login", response_model=APIResponse[Token])
def login(login_req: LoginRequest, db: Session = Depends(get_db)) -> APIResponse[Token]:
    """Authenticate user with email/password and issue JWT access token."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(login_req.email)

    if not user or not verify_password(login_req.password, user.hashed_password):
        logger.warning("Failed login attempt for email: %s", login_req.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    token_data = {
        "sub": user.user_id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
    }
    access_token = create_access_token(token_data)

    ActivityLogRepository(db).log(
        user_id=user.user_id,
        action="USER_LOGIN",
        entity_type="User",
        entity_id=user.user_id,
    )

    token_payload = Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
    return APIResponse(message="Login successful.", data=token_payload)


@router.get("/me", response_model=APIResponse[UserResponse])
def get_current_profile(current_user: UserModel = Depends(get_current_user)) -> APIResponse[UserResponse]:
    """Retrieve details of the currently authenticated session user."""
    return APIResponse(data=UserResponse.model_validate(current_user))


@router.post("/logout", response_model=APIResponse[None])
def logout(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)) -> APIResponse[None]:
    """Logs out user session and records security activity event."""
    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="USER_LOGOUT",
        entity_type="User",
        entity_id=current_user.user_id,
    )
    return APIResponse(message="Logged out successfully.")

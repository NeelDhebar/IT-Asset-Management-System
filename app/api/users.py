"""Users Management Router.

Demonstrates:
- RESTful CRUD endpoints for users
- Role-based authorization guarding user operations
- Pydantic models for validation and responses
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.repositories import UserRepository, ActivityLogRepository
from app.models.enums import UserRole
from app.models.orm import UserModel
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import APIResponse
from app.api.auth import get_current_user, require_roles
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=APIResponse[List[UserResponse]])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
) -> APIResponse[List[UserResponse]]:
    """List all users in system (Admin & IT Support)."""
    user_repo = UserRepository(db)
    users = user_repo.list_all(skip=skip, limit=limit)
    return APIResponse(data=[UserResponse.model_validate(u) for u in users])


@router.get("/{user_id}", response_model=APIResponse[UserResponse])
def get_user_by_id(
    user_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[UserResponse]:
    """Retrieve user details by user_id (Self, Admin, or IT Support)."""
    if current_user.role == UserRole.EMPLOYEE.value and current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other employee profiles.")

    user_repo = UserRepository(db)
    user = user_repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")
    return APIResponse(data=UserResponse.model_validate(user))


@router.post("", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> APIResponse[UserResponse]:
    """Admin-only: Create a new user with specific role."""
    user_repo = UserRepository(db)
    hashed_pwd = hash_password(payload.password)

    user = user_repo.create({
        "user_id": payload.user_id,
        "email": payload.email,
        "hashed_password": hashed_pwd,
        "full_name": payload.full_name,
        "role": payload.role.value,
        "department": payload.department,
        "is_active": True,
    })

    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="ADMIN_CREATE_USER",
        entity_type="User",
        entity_id=user.user_id,
    )
    return APIResponse(message="User created successfully.", data=UserResponse.model_validate(user))


@router.put("/{user_id}", response_model=APIResponse[UserResponse])
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> APIResponse[UserResponse]:
    """Admin-only: Update user details."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email.lower().strip()
    if payload.role is not None:
        user.role = payload.role.value
    if payload.department is not None:
        user.department = payload.department
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)

    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="ADMIN_UPDATE_USER",
        entity_type="User",
        entity_id=user.user_id,
    )
    return APIResponse(message="User updated successfully.", data=UserResponse.model_validate(user))


@router.delete("/{user_id}", response_model=APIResponse[None])
def delete_user(
    user_id: str,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> APIResponse[None]:
    """Admin-only: Soft deactivate user account."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    user.is_active = False
    db.commit()

    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="ADMIN_DEACTIVATE_USER",
        entity_type="User",
        entity_id=user.user_id,
    )
    return APIResponse(message=f"User '{user_id}' deactivated successfully.")

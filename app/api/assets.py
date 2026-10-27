"""IT Asset Management Router.

Demonstrates:
- REST endpoints for assets
- Assign and return lifecycle transitions
- Role authorization (Admin creates/assigns/retires, Support/Employee views)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.repositories import ActivityLogRepository
from app.models.enums import UserRole
from app.models.orm import UserModel
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetAssignRequest,
    BatchAssetReturnRequest,
    AssetResponse,
)
from app.schemas.common import APIResponse
from app.services.asset_service import AssetService
from app.api.auth import get_current_user, require_roles

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=APIResponse[List[Dict[str, Any]]])
def list_assets(
    status_filter: Optional[str] = None,
    asset_type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[Dict[str, Any]]]:
    """List assets. Employees see their own assigned assets unless viewing available assets."""
    service = AssetService(db)
    if current_user.role == UserRole.EMPLOYEE.value:
        if status_filter != "AVAILABLE":
            assigned_to = current_user.user_id

    assets = service.list_assets(status=status_filter, asset_type=asset_type, assigned_to=assigned_to)
    return APIResponse(data=assets)


@router.get("/{asset_id}", response_model=APIResponse[Dict[str, Any]])
def get_asset(
    asset_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Retrieve full polymorphic details and specs of an asset."""
    service = AssetService(db)
    asset_data = service.get_asset(asset_id)

    # If employee, ensure they are assigned this asset
    if current_user.role == UserRole.EMPLOYEE.value and asset_data.get("assigned_to") != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to unassigned asset.")

    return APIResponse(data=asset_data)


@router.post("", response_model=APIResponse[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Admin/Support: Register a new IT asset."""
    service = AssetService(db)
    created = service.create_asset(payload.model_dump())

    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="CREATE_ASSET",
        entity_type="Asset",
        entity_id=payload.asset_id,
    )
    return APIResponse(message="Asset registered successfully.", data=created)


@router.post("/{asset_id}/assign", response_model=APIResponse[Dict[str, Any]])
def assign_asset(
    asset_id: str,
    payload: AssetAssignRequest,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Admin/Support: Assign an available asset to an employee."""
    service = AssetService(db)
    assigned = service.assign_asset(asset_id, payload.user_id, payload.notes)

    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="ASSIGN_ASSET",
        entity_type="Asset",
        entity_id=asset_id,
        details={"assigned_to": payload.user_id},
    )
    return APIResponse(message=f"Asset '{asset_id}' assigned to '{payload.user_id}'.", data=assigned)


@router.post("/return-batch", response_model=APIResponse[Dict[str, Any]])
def return_assets_batch(
    payload: BatchAssetReturnRequest,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT, UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Process batch return of multiple assigned assets."""
    service = AssetService(db)
    returned_ids: List[str] = []
    errors: List[str] = []

    for asset_id in payload.asset_ids:
        try:
            asset_data = service.get_asset(asset_id)
            if current_user.role == UserRole.EMPLOYEE.value and asset_data.get("assigned_to") != current_user.user_id:
                errors.append(f"Asset '{asset_id}' is not assigned to you.")
                continue

            service.return_asset(asset_id)
            ActivityLogRepository(db).log(
                user_id=current_user.user_id,
                action="RETURN_ASSET",
                entity_type="Asset",
                entity_id=asset_id,
            )
            returned_ids.append(asset_id)
        except Exception as exc:
            errors.append(f"{asset_id}: {str(exc)}")

    if not returned_ids and errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    return APIResponse(
        message=f"Successfully returned {len(returned_ids)} asset(s)." + (f" ({len(errors)} failed)" if errors else ""),
        data={"returned_ids": returned_ids, "errors": errors},
    )


@router.post("/{asset_id}/return", response_model=APIResponse[Dict[str, Any]])
def return_asset(
    asset_id: str,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT, UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Admin/Support: Process the return of an assigned asset. Employee: Return own assigned asset."""
    service = AssetService(db)
    asset_data = service.get_asset(asset_id)
    if current_user.role == UserRole.EMPLOYEE.value and asset_data.get("assigned_to") != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot return an asset not assigned to you.")

    returned = service.return_asset(asset_id)

    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="RETURN_ASSET",
        entity_type="Asset",
        entity_id=asset_id,
    )
    return APIResponse(message=f"Asset '{asset_id}' returned to available pool.", data=returned)


@router.delete("/{asset_id}", response_model=APIResponse[None])
def retire_asset(
    asset_id: str,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> APIResponse[None]:
    """Admin-only: Retire/decommission an asset."""
    service = AssetService(db)
    asset_orm = service.asset_repo.get_by_asset_id(asset_id)
    if not asset_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset '{asset_id}' not found.")

    asset_orm.status = "RETIRED"
    asset_orm.assigned_to = None
    db.commit()

    ActivityLogRepository(db).log(
        user_id=current_user.user_id,
        action="RETIRE_ASSET",
        entity_type="Asset",
        entity_id=asset_id,
    )
    return APIResponse(message=f"Asset '{asset_id}' decommissioned and retired.")

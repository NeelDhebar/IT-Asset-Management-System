"""Reports and Analytical Stream Router.

Demonstrates:
- Memory-efficient data streaming via FastAPI StreamingResponse and Python generators (yield)
- SLA metrics computation across enterprise tickets
- CSV exports
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.enums import UserRole
from app.models.orm import UserModel
from app.schemas.common import APIResponse
from app.services.report_service import ReportService
from app.api.auth import require_roles

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/tickets")
def get_tickets_report(
    format: str = Query("json", description="'json' summary or 'csv' stream"),
    status: str = Query(None, description="Optional status filter"),
    priority: str = Query(None, description="Optional priority filter"),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
):
    """Retrieve tickets report.

    If format='csv', returns a generator StreamingResponse with O(1) memory consumption.
    """
    service = ReportService(db)
    if format.lower() == "csv":
        stream_gen = service.stream_tickets_csv(status_filter=status, priority_filter=priority)
        return StreamingResponse(
            stream_gen,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tickets_report.csv"},
        )

    # JSON response
    tickets = service.ticket_repo.list_all(status=status, priority=priority)
    return APIResponse(
        data=[
            {
                "ticket_id": t.ticket_id,
                "title": t.title,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "created_by": t.created_by,
                "assigned_to": t.assigned_to,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "sla_deadline": t.sla_deadline.isoformat() if t.sla_deadline else None,
            }
            for t in tickets
        ]
    )


@router.get("/assets")
def get_assets_report(
    format: str = Query("json", description="'json' summary or 'csv' stream"),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
):
    """Retrieve assets report with calculated depreciation.

    If format='csv', returns a generator StreamingResponse.
    """
    service = ReportService(db)
    if format.lower() == "csv":
        stream_gen = service.stream_assets_csv()
        return StreamingResponse(
            stream_gen,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=assets_inventory_report.csv"},
        )

    assets = service.asset_repo.list_all()
    return APIResponse(
        data=[
            {
                "asset_id": a.asset_id,
                "type": a.asset_type,
                "brand": a.brand,
                "model": a.model,
                "status": a.status,
                "assigned_to": a.assigned_to,
                "purchase_cost": a.purchase_cost,
            }
            for a in assets
        ]
    )


@router.get("/sla", response_model=APIResponse[Dict[str, Any]])
def get_sla_report(
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Retrieve SLA compliance analytics: breach percentages, resolution durations, and status counts."""
    service = ReportService(db)
    summary = service.get_sla_report_summary()
    return APIResponse(data=summary)

"""Support Tickets API Router.

Demonstrates:
- Ticket creation with automatic rule-based classification
- Ticket assignment, progression, resolution, and closure
- Real-time WebSocket event publishing on ticket state changes
- SLA calculation metrics endpoint
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.enums import UserRole
from app.models.orm import UserModel
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketAssignRequest,
    TicketResolveRequest,
    TicketResponse,
    SLAMetricsResponse,
)
from app.schemas.common import APIResponse
from app.services.ticket_service import TicketService
from app.api.auth import get_current_user, require_roles
from app.api.websocket import ws_manager

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("", response_model=APIResponse[List[TicketResponse]])
def list_tickets(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[TicketResponse]]:
    """List tickets. Employees only see their own tickets; Support only see tickets assigned to them; Admin sees all."""
    service = TicketService(db)
    created_by = None
    assigned_to = None

    if current_user.role == UserRole.EMPLOYEE.value:
        created_by = current_user.user_id
    elif current_user.role == UserRole.SUPPORT.value:
        assigned_to = current_user.user_id

    tickets = service.ticket_repo.list_all(
        status=status_filter,
        priority=priority_filter,
        created_by=created_by,
        assigned_to=assigned_to,
    )
    return APIResponse(data=[TicketResponse.model_validate(t) for t in tickets])


@router.get("/{ticket_id}", response_model=APIResponse[TicketResponse])
def get_ticket(
    ticket_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TicketResponse]:
    """Retrieve full ticket details."""
    service = TicketService(db)
    ticket = service.ticket_repo.get_by_ticket_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket '{ticket_id}' not found.")

    if current_user.role == UserRole.EMPLOYEE.value and ticket.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other employee tickets.")

    if current_user.role == UserRole.SUPPORT.value and ticket.assigned_to != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access tickets assigned to another support agent.")

    return APIResponse(data=TicketResponse.model_validate(ticket))


@router.get("/{ticket_id}/sla", response_model=APIResponse[Dict[str, Any]])
def get_ticket_sla(
    ticket_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Retrieve live SLA status and remaining minutes for a ticket."""
    service = TicketService(db)
    metrics = service.get_ticket_sla_metrics(ticket_id)
    return APIResponse(data=metrics)


@router.post("", response_model=APIResponse[TicketResponse], status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TicketResponse]:
    """Create a new support ticket. Automatic classification applies if category/priority not passed."""
    service = TicketService(db)
    ticket = service.create_ticket(
        title=payload.title,
        description=payload.description,
        created_by=current_user.user_id,
        category=payload.category,
        priority=payload.priority,
    )

    ticket_response = TicketResponse.model_validate(ticket)

    # Real-time WebSocket broadcast to all connected dashboard clients
    await ws_manager.broadcast_event(
        "TICKET_CREATED",
        {
            "ticket_id": ticket.ticket_id,
            "title": ticket.title,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_by": ticket.created_by,
        },
    )

    return APIResponse(message="Ticket created successfully.", data=ticket_response)


@router.put("/{ticket_id}", response_model=APIResponse[TicketResponse])
def update_ticket_details(
    ticket_id: str,
    payload: TicketUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TicketResponse]:
    """Update title/description of a ticket."""
    service = TicketService(db)
    ticket = service.ticket_repo.get_by_ticket_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket '{ticket_id}' not found.")

    if current_user.role == UserRole.EMPLOYEE.value and ticket.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit tickets belonging to others.")

    if payload.title is not None:
        ticket.title = payload.title
    if payload.description is not None:
        ticket.description = payload.description
    if payload.category is not None:
        ticket.category = payload.category.value
    if payload.priority is not None:
        ticket.priority = payload.priority.value

    db.commit()
    db.refresh(ticket)
    return APIResponse(message="Ticket updated.", data=TicketResponse.model_validate(ticket))


@router.post("/{ticket_id}/assign", response_model=APIResponse[TicketResponse])
async def assign_ticket(
    ticket_id: str,
    payload: TicketAssignRequest,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
) -> APIResponse[TicketResponse]:
    """Assign ticket to an IT Support engineer."""
    service = TicketService(db)
    updated = service.assign_ticket(
        ticket_id=ticket_id,
        support_user_id=payload.assigned_to,
        actor_id=current_user.user_id,
        comments=payload.comments,
    )

    await ws_manager.broadcast_event(
        "TICKET_ASSIGNED",
        {"ticket_id": ticket_id, "assigned_to": payload.assigned_to, "status": updated.status},
    )
    return APIResponse(message=f"Ticket assigned to {payload.assigned_to}.", data=TicketResponse.model_validate(updated))


@router.post("/{ticket_id}/progress", response_model=APIResponse[TicketResponse])
async def start_progress(
    ticket_id: str,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
) -> APIResponse[TicketResponse]:
    """Transition ticket to IN_PROGRESS."""
    service = TicketService(db)
    ticket = service.ticket_repo.get_by_ticket_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket '{ticket_id}' not found.")

    if current_user.role == UserRole.SUPPORT.value and ticket.assigned_to != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot progress tickets assigned to another support agent.")

    updated = service.start_progress(ticket_id=ticket_id, actor_id=current_user.user_id)

    await ws_manager.broadcast_event(
        "TICKET_STATUS_CHANGED",
        {"ticket_id": ticket_id, "status": updated.status},
    )
    return APIResponse(message="Ticket work marked in progress.", data=TicketResponse.model_validate(updated))


@router.post("/{ticket_id}/resolve", response_model=APIResponse[TicketResponse])
async def resolve_ticket(
    ticket_id: str,
    payload: TicketResolveRequest,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db),
) -> APIResponse[TicketResponse]:
    """Resolve ticket with resolution summary."""
    service = TicketService(db)
    ticket = service.ticket_repo.get_by_ticket_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket '{ticket_id}' not found.")

    if current_user.role == UserRole.SUPPORT.value and ticket.assigned_to != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot resolve tickets assigned to another support agent.")

    updated = service.resolve_ticket(
        ticket_id=ticket_id,
        resolution=payload.resolution,
        actor_id=current_user.user_id,
        comments=payload.comments,
    )

    await ws_manager.broadcast_event(
        "TICKET_RESOLVED",
        {"ticket_id": ticket_id, "status": updated.status, "resolution": payload.resolution},
    )
    return APIResponse(message="Ticket resolved successfully.", data=TicketResponse.model_validate(updated))


@router.post("/{ticket_id}/close", response_model=APIResponse[TicketResponse])
async def close_ticket(
    ticket_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TicketResponse]:
    """Close ticket (Employee who created it or Admin/assigned Support)."""
    service = TicketService(db)
    ticket = service.ticket_repo.get_by_ticket_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket '{ticket_id}' not found.")

    if current_user.role == UserRole.EMPLOYEE.value and ticket.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot close another user's ticket.")

    if current_user.role == UserRole.SUPPORT.value and ticket.assigned_to != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot close tickets assigned to another support agent.")

    updated = service.close_ticket(ticket_id=ticket_id, actor_id=current_user.user_id)

    await ws_manager.broadcast_event(
        "TICKET_CLOSED",
        {"ticket_id": ticket_id, "status": updated.status},
    )
    return APIResponse(message="Ticket closed.", data=TicketResponse.model_validate(updated))

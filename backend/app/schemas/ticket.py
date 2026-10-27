"""Pydantic schemas for Support Ticket management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import TicketCategory, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None


class TicketAssignRequest(BaseModel):
    assigned_to: str
    comments: Optional[str] = "Assigned to specialist"


class TicketResolveRequest(BaseModel):
    resolution: str = Field(..., min_length=5)
    comments: Optional[str] = None


class TicketResponse(BaseModel):
    id: int
    ticket_id: str
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    created_by: str
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    sla_deadline: datetime
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SLAMetricsResponse(BaseModel):
    ticket_id: str
    priority: TicketPriority
    sla_deadline: datetime
    is_breached: bool
    remaining_minutes: float
    status_label: str
    resolution_minutes: Optional[float] = None

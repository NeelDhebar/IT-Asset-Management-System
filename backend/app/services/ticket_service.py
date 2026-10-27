"""Support Ticket Management Service Layer.

Demonstrates:
- Automatic ticket classification integration
- SLA deadline computation & SLA metric evaluations
- Ticket workflow state machine validation
- Real-time WebSocket event dispatching
- Audit trail management
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database.repositories import TicketRepository, UserRepository
from app.models.enums import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
    ALLOWED_TICKET_TRANSITIONS,
)
from app.models.orm import TicketModel
from app.services.classifier_service import auto_classify_ticket
from app.services.sla_service import SLAService
from app.utils.exceptions import (
    InvalidTicketError,
    TicketNotFoundError,
    InvalidStatusTransitionError,
)
from app.utils.logger import get_logger

logger = get_logger()


class TicketService:
    """Service encapsulating the complete support ticket lifecycle."""

    def __init__(self, db: Session) -> None:
        self.ticket_repo = TicketRepository(db)
        self.user_repo = UserRepository(db)

    def create_ticket(
        self,
        title: str,
        description: str,
        created_by: str,
        category: Optional[TicketCategory] = None,
        priority: Optional[TicketPriority] = None,
    ) -> TicketModel:
        """Creates a ticket, applying rule-based auto-classification if needed and SLA calculation."""
        # 1. Rule-based Auto-Classification if fields omitted
        auto_cat, auto_prio, matched_keywords = auto_classify_ticket(title, description)

        final_category = category or auto_cat
        final_priority = priority or auto_prio

        logger.info(
            "Ticket Auto-Classifier Result: category=%s, priority=%s, keywords=%s",
            final_category.value,
            final_priority.value,
            matched_keywords,
        )

        # 2. SLA Deadline calculation
        created_time = datetime.now(timezone.utc)
        sla_deadline = SLAService.calculate_deadline(created_time, final_priority)

        # 3. Generate Unique Ticket ID (e.g. INC-XXXX)
        short_id = uuid.uuid4().hex[:6].upper()
        ticket_id = f"INC-{short_id}"

        # 4. Atomic Database Transaction (Atomicity)
        ticket_data = {
            "ticket_id": ticket_id,
            "title": title.strip(),
            "description": description.strip(),
            "category": final_category.value,
            "priority": final_priority.value,
            "status": TicketStatus.OPEN.value,
            "created_by": created_by,
            "sla_deadline": sla_deadline,
        }

        created_ticket = self.ticket_repo.create_atomic(ticket_data, actor_user_id=created_by)
        return created_ticket

    def assign_ticket(self, ticket_id: str, support_user_id: str, actor_id: str, comments: Optional[str] = None) -> TicketModel:
        """Assigns ticket to an IT Support engineer."""
        support_user = self.user_repo.get_by_user_id(support_user_id)
        if not support_user:
            raise InvalidTicketError(f"IT Support user '{support_user_id}' does not exist.")

        ticket = self.ticket_repo.get_by_ticket_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id)

        current_status = TicketStatus(ticket.status)
        target_status = TicketStatus.ASSIGNED

        if target_status not in ALLOWED_TICKET_TRANSITIONS.get(current_status, []):
            raise InvalidStatusTransitionError(current_status.value, target_status.value, "Ticket")

        updated = self.ticket_repo.update_status_atomic(
            ticket_id=ticket_id,
            new_status=target_status.value,
            actor_user_id=actor_id,
            comments=comments or f"Ticket assigned to {support_user.full_name} ({support_user_id})",
            assigned_to=support_user_id,
        )
        return updated

    def start_progress(self, ticket_id: str, actor_id: str) -> TicketModel:
        """Transitions ticket to IN_PROGRESS."""
        ticket = self.ticket_repo.get_by_ticket_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id)

        current_status = TicketStatus(ticket.status)
        target_status = TicketStatus.IN_PROGRESS

        if target_status not in ALLOWED_TICKET_TRANSITIONS.get(current_status, []):
            raise InvalidStatusTransitionError(current_status.value, target_status.value, "Ticket")

        return self.ticket_repo.update_status_atomic(
            ticket_id=ticket_id,
            new_status=target_status.value,
            actor_user_id=actor_id,
            comments="Work commenced on ticket resolution.",
        )

    def resolve_ticket(self, ticket_id: str, resolution: str, actor_id: str, comments: Optional[str] = None) -> TicketModel:
        """Transitions ticket to RESOLVED with required resolution details."""
        if not resolution or len(resolution.strip()) < 5:
            raise InvalidTicketError("A descriptive resolution explanation (at least 5 chars) is mandatory.")

        ticket = self.ticket_repo.get_by_ticket_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id)

        current_status = TicketStatus(ticket.status)
        target_status = TicketStatus.RESOLVED

        if target_status not in ALLOWED_TICKET_TRANSITIONS.get(current_status, []):
            raise InvalidStatusTransitionError(current_status.value, target_status.value, "Ticket")

        return self.ticket_repo.update_status_atomic(
            ticket_id=ticket_id,
            new_status=target_status.value,
            actor_user_id=actor_id,
            comments=comments or "Ticket marked as resolved.",
            resolution=resolution.strip(),
        )

    def close_ticket(self, ticket_id: str, actor_id: str, comments: Optional[str] = None) -> TicketModel:
        """Closes ticket (terminal state)."""
        ticket = self.ticket_repo.get_by_ticket_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id)

        current_status = TicketStatus(ticket.status)
        target_status = TicketStatus.CLOSED

        if target_status not in ALLOWED_TICKET_TRANSITIONS.get(current_status, []):
            raise InvalidStatusTransitionError(current_status.value, target_status.value, "Ticket")

        return self.ticket_repo.update_status_atomic(
            ticket_id=ticket_id,
            new_status=target_status.value,
            actor_user_id=actor_id,
            comments=comments or "Ticket closed by user/admin.",
        )

    def get_ticket_sla_metrics(self, ticket_id: str) -> Dict[str, Any]:
        """Calculates current live SLA countdown and metrics for a ticket."""
        ticket = self.ticket_repo.get_by_ticket_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id)

        metrics = SLAService.check_sla_status(
            created_at=ticket.created_at,
            priority=TicketPriority(ticket.priority),
            closed_at=ticket.closed_at,
        )
        return {
            "ticket_id": ticket.ticket_id,
            "priority": ticket.priority,
            "status": ticket.status,
            **metrics,
        }

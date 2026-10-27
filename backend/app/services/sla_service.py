"""SLA (Service Level Agreement) Management Engine.

Demonstrates:
- datetime and timedelta arithmetic
- Deadline forecasting and remaining duration computation
- Breach detection
- Resolution time metrics and dataset averaging
- Custom SLA exceptions
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from app.models.enums import TicketPriority
from app.utils.exceptions import SLAConfigurationError


class SLAService:
    """Manages ticket SLA rules, deadlines, and breach calculations."""

    # SLA Windows in hours per priority
    SLA_HOURS_MAP: Dict[TicketPriority, int] = {
        TicketPriority.CRITICAL: 2,
        TicketPriority.HIGH: 4,
        TicketPriority.MEDIUM: 8,
        TicketPriority.LOW: 24,
    }

    @classmethod
    def get_sla_window(cls, priority: TicketPriority) -> timedelta:
        """Retrieve timedelta duration window for given priority."""
        if priority not in cls.SLA_HOURS_MAP:
            raise SLAConfigurationError(priority.value if hasattr(priority, "value") else str(priority))
        return timedelta(hours=cls.SLA_HOURS_MAP[priority])

    @classmethod
    def calculate_deadline(cls, created_at: datetime, priority: TicketPriority) -> datetime:
        """Calculate SLA resolution deadline by adding SLA window to creation timestamp."""
        window = cls.get_sla_window(priority)
        return created_at + window

    @classmethod
    def check_sla_status(
        cls,
        created_at: datetime,
        priority: TicketPriority,
        closed_at: Optional[datetime] = None,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Compute full SLA health metrics for a ticket.

        Returns:
            Dictionary containing deadline, is_breached, remaining_minutes, status_label.
        """
        now = reference_time or datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        deadline = cls.calculate_deadline(created_at, priority)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        # If already resolved/closed
        if closed_at:
            if closed_at.tzinfo is None:
                closed_at = closed_at.replace(tzinfo=timezone.utc)
            is_breached = closed_at > deadline
            resolution_duration = closed_at - created_at
            resolution_minutes = round(resolution_duration.total_seconds() / 60, 1)

            return {
                "deadline": deadline.isoformat(),
                "is_breached": is_breached,
                "remaining_minutes": 0,
                "status_label": "RESOLVED_BREACHED" if is_breached else "RESOLVED_WITHIN_SLA",
                "resolution_minutes": resolution_minutes,
            }

        # Active ticket
        remaining_duration = deadline - now
        remaining_minutes = round(remaining_duration.total_seconds() / 60, 1)
        is_breached = remaining_duration.total_seconds() < 0

        status_label = "SLA BREACHED" if is_breached else "SLA ACTIVE"

        return {
            "deadline": deadline.isoformat(),
            "is_breached": is_breached,
            "remaining_minutes": remaining_minutes,
            "status_label": status_label,
            "resolution_minutes": None,
        }

    @classmethod
    def calculate_average_resolution_time(cls, closed_tickets: List[Dict[str, Any]]) -> float:
        """Calculate average resolution time in hours for resolved/closed tickets."""
        if not closed_tickets:
            return 0.0

        durations_seconds: List[float] = []
        for t in closed_tickets:
            created = t.get("created_at")
            closed = t.get("closed_at")
            if created and closed:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                if isinstance(closed, str):
                    closed = datetime.fromisoformat(closed)
                diff = (closed - created).total_seconds()
                if diff >= 0:
                    durations_seconds.append(diff)

        if not durations_seconds:
            return 0.0

        avg_seconds = sum(durations_seconds) / len(durations_seconds)
        return round(avg_seconds / 3600.0, 2)  # In hours

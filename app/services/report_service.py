"""Report Generation Service using Generators for Memory-Efficient Streaming.

Demonstrates:
- Generators (yield) preventing in-memory dataset bloat
- Streaming CSV reports directly to clients
- SLA metrics calculation and aggregation
"""

from typing import Any, Dict, Generator, List, Optional
from sqlalchemy.orm import Session
from app.database.repositories import TicketRepository, AssetRepository
from app.models.enums import TicketPriority
from app.services.sla_service import SLAService
from app.utils.generators import (
    ticket_generator,
    asset_depreciation_generator,
    stream_csv_rows,
)


class ReportService:
    """Generates analytical reports and streams large tabular datasets."""

    def __init__(self, db: Session) -> None:
        self.ticket_repo = TicketRepository(db)
        self.asset_repo = AssetRepository(db)

    def stream_tickets_csv(
        self,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Streams tickets report as CSV lines without buffering entire dataset in memory."""
        orm_tickets = self.ticket_repo.list_all(status=status_filter, priority=priority_filter)

        # Convert ORM to generator of dictionaries
        ticket_dicts = (
            {
                "ticket_id": t.ticket_id,
                "title": t.title,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "created_by": t.created_by,
                "assigned_to": t.assigned_to or "Unassigned",
                "created_at": t.created_at.isoformat() if t.created_at else "",
                "sla_deadline": t.sla_deadline.isoformat() if t.sla_deadline else "",
                "closed_at": t.closed_at.isoformat() if t.closed_at else "",
            }
            for t in orm_tickets
        )

        gen = ticket_generator(
            ticket_dicts,
            status_filter=status_filter,
            priority_filter=priority_filter,
        )

        fieldnames = [
            "ticket_id", "title", "category", "priority", "status",
            "created_by", "assigned_to", "created_at", "sla_deadline", "closed_at"
        ]
        return stream_csv_rows(gen, fieldnames)

    def stream_assets_csv(self) -> Generator[str, None, None]:
        """Streams asset inventory with calculated depreciation using generators."""
        orm_assets = self.asset_repo.list_all()
        asset_dicts = (
            {
                "asset_id": a.asset_id,
                "asset_type": a.asset_type,
                "brand": a.brand,
                "model": a.model,
                "serial_number": a.serial_number,
                "purchase_date": a.purchase_date,
                "purchase_cost": a.purchase_cost,
                "status": a.status,
                "assigned_to": a.assigned_to or "Unassigned",
            }
            for a in orm_assets
        )

        gen = asset_depreciation_generator(asset_dicts)
        fieldnames = [
            "asset_id", "asset_type", "brand", "model", "serial_number",
            "purchase_date", "purchase_cost", "status", "assigned_to", "age_years", "depreciated_value"
        ]
        return stream_csv_rows(gen, fieldnames)

    def get_sla_report_summary(self) -> Dict[str, Any]:
        """Aggregates enterprise SLA metrics: breach rates, resolution times, and compliance %."""
        tickets = self.ticket_repo.list_all()
        total_tickets = len(tickets)

        if total_tickets == 0:
            return {
                "total_tickets": 0,
                "active_tickets": 0,
                "resolved_tickets": 0,
                "breached_count": 0,
                "compliance_rate_percent": 100.0,
                "average_resolution_hours": 0.0,
                "priority_breakdown": {},
            }

        breached_count = 0
        resolved_tickets = []
        active_tickets = 0
        priority_counts: Dict[str, int] = {}

        for t in tickets:
            prio = t.priority
            priority_counts[prio] = priority_counts.get(prio, 0) + 1

            status_metrics = SLAService.check_sla_status(
                created_at=t.created_at,
                priority=TicketPriority(t.priority),
                closed_at=t.closed_at,
            )

            if status_metrics["is_breached"]:
                breached_count += 1

            if t.status in ("RESOLVED", "CLOSED"):
                resolved_tickets.append({
                    "created_at": t.created_at,
                    "closed_at": t.closed_at,
                })
            else:
                active_tickets += 1

        avg_resolution_hours = SLAService.calculate_average_resolution_time(resolved_tickets)
        compliance_rate = round(((total_tickets - breached_count) / total_tickets) * 100.0, 1)

        return {
            "total_tickets": total_tickets,
            "active_tickets": active_tickets,
            "resolved_tickets": len(resolved_tickets),
            "breached_count": breached_count,
            "compliance_rate_percent": compliance_rate,
            "average_resolution_hours": avg_resolution_hours,
            "priority_breakdown": priority_counts,
        }

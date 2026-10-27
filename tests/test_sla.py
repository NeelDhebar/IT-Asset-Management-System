"""Unit Tests for SLA Management Subsystem."""

import pytest
from datetime import datetime, timedelta, timezone
from app.models.enums import TicketPriority
from app.services.sla_service import SLAService
from app.utils.exceptions import SLAConfigurationError


def test_sla_deadline_calculation_hours():
    """Verify SLA windows: Critical=2h, High=4h, Medium=8h, Low=24h."""
    now = datetime(2025, 4, 10, 10, 0, tzinfo=timezone.utc)

    crit_deadline = SLAService.calculate_deadline(now, TicketPriority.CRITICAL)
    assert crit_deadline == now + timedelta(hours=2)

    high_deadline = SLAService.calculate_deadline(now, TicketPriority.HIGH)
    assert high_deadline == now + timedelta(hours=4)

    med_deadline = SLAService.calculate_deadline(now, TicketPriority.MEDIUM)
    assert med_deadline == now + timedelta(hours=8)

    low_deadline = SLAService.calculate_deadline(now, TicketPriority.LOW)
    assert low_deadline == now + timedelta(hours=24)


def test_sla_active_status_and_remaining():
    """Verify SLA status calculation when deadline is in the future."""
    created = datetime(2025, 4, 10, 10, 0, tzinfo=timezone.utc)
    current = datetime(2025, 4, 10, 13, 30, tzinfo=timezone.utc)

    # High priority SLA deadline is 14:00. At 13:30, 30 mins remaining
    metrics = SLAService.check_sla_status(
        created_at=created,
        priority=TicketPriority.HIGH,
        reference_time=current,
    )
    assert metrics["is_breached"] is False
    assert metrics["remaining_minutes"] == 30.0
    assert metrics["status_label"] == "SLA ACTIVE"


def test_sla_breach_detection():
    """Verify SLA breach detection when current time exceeds deadline."""
    created = datetime(2025, 4, 10, 10, 0, tzinfo=timezone.utc)
    current = datetime(2025, 4, 10, 15, 0, tzinfo=timezone.utc)

    # High priority deadline was 14:00. At 15:00, breached by 60 mins
    metrics = SLAService.check_sla_status(
        created_at=created,
        priority=TicketPriority.HIGH,
        reference_time=current,
    )
    assert metrics["is_breached"] is True
    assert metrics["status_label"] == "SLA BREACHED"
    assert metrics["remaining_minutes"] < 0


def test_average_resolution_time_calculation():
    """Verify average resolution time calculation across closed tickets."""
    t1_created = datetime(2025, 4, 10, 10, 0, tzinfo=timezone.utc)
    t1_closed = t1_created + timedelta(hours=2)

    t2_created = datetime(2025, 4, 10, 10, 0, tzinfo=timezone.utc)
    t2_closed = t2_created + timedelta(hours=4)

    closed_tickets = [
        {"created_at": t1_created, "closed_at": t1_closed},
        {"created_at": t2_created, "closed_at": t2_closed},
    ]

    avg_hours = SLAService.calculate_average_resolution_time(closed_tickets)
    # (2 + 4) / 2 = 3.0 hours
    assert avg_hours == 3.0

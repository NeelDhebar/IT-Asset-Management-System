"""Unit Tests for Rule-Based Ticket Classification Engine."""

import pytest
from app.models.enums import TicketCategory, TicketPriority
from app.services.classifier_service import auto_classify_ticket


def test_classify_hardware_high_priority():
    """Verify example from requirement: 'My laptop is not starting' -> Hardware / HIGH."""
    category, priority, keywords = auto_classify_ticket(
        title="My laptop is not starting",
        description="I press the power button and the screen stays black with no lights.",
    )
    assert category == TicketCategory.HARDWARE
    assert priority == TicketPriority.HIGH
    assert "laptop" in [k.lower() for k in keywords]


def test_classify_network_critical_priority():
    """Verify critical network outage detection."""
    category, priority, keywords = auto_classify_ticket(
        title="Office VPN outage",
        description="The entire floor cannot connect to production cluster, blocked all work emergency.",
    )
    assert category == TicketCategory.NETWORK
    assert priority == TicketPriority.CRITICAL


def test_classify_access_request():
    """Verify access and credential classification."""
    category, priority, keywords = auto_classify_ticket(
        title="Password reset for Active Directory",
        description="Account locked after too many attempts, need OTP reset.",
    )
    assert category == TicketCategory.ACCESS


def test_classify_software_medium_priority():
    """Verify software classification with performance keywords."""
    category, priority, keywords = auto_classify_ticket(
        title="Microsoft Excel slow performance",
        description="Excel formulas are intermittent and freeze when opening large financial models.",
    )
    assert category == TicketCategory.SOFTWARE
    assert priority == TicketPriority.MEDIUM

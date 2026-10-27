"""Domain Enumerations for Smart IT Asset & Support Ticket Management System."""

from enum import Enum


class UserRole(str, Enum):
    """System user authorization roles."""
    ADMIN = "ADMIN"
    SUPPORT = "SUPPORT"
    EMPLOYEE = "EMPLOYEE"


class AssetType(str, Enum):
    """Categorization of IT physical assets."""
    LAPTOP = "Laptop"
    MONITOR = "Monitor"
    KEYBOARD = "Keyboard"
    MOUSE = "Mouse"
    PRINTER = "Printer"


class AssetStatus(str, Enum):
    """Lifecycle status of an IT asset."""
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    UNDER_REPAIR = "UNDER_REPAIR"
    RETIRED = "RETIRED"
    LOST = "LOST"


class TicketCategory(str, Enum):
    """Category classification for support tickets."""
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    NETWORK = "Network"
    ACCESS = "Access"
    OTHER = "Other"


class TicketPriority(str, Enum):
    """Urgency / SLA tier for support tickets."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    """State machine progression for support tickets."""
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# Valid Ticket state transitions
ALLOWED_TICKET_TRANSITIONS = {
    TicketStatus.OPEN: [TicketStatus.ASSIGNED, TicketStatus.CLOSED],
    TicketStatus.ASSIGNED: [TicketStatus.IN_PROGRESS, TicketStatus.OPEN],
    TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED, TicketStatus.ASSIGNED],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.IN_PROGRESS],
    TicketStatus.CLOSED: [],  # Terminal state
}

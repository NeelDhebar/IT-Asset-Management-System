"""SQLAlchemy Relational ORM Models.

Demonstrates:
- Relational Database Normalization
- Table relationships (1-to-many, foreign keys)
- Primary keys, Unique constraints, NOT NULL constraints, Indexes
- Cascades and timestamps
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from app.database.connection import Base


def utc_now() -> datetime:
    """Helper for generating timezone-aware UTC timestamps."""
    return datetime.now(timezone.utc)


class UserModel(Base):
    """User entity representing Employees, IT Support, and Admins."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., EMP-101, ADM-001
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="EMPLOYEE")  # ADMIN, SUPPORT, EMPLOYEE
    department = Column(String(100), nullable=False, default="General")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    assigned_assets = relationship("AssetModel", back_populates="assignee", foreign_keys="AssetModel.assigned_to")
    created_tickets = relationship("TicketModel", back_populates="creator", foreign_keys="TicketModel.created_by")
    assigned_tickets = relationship("TicketModel", back_populates="assignee", foreign_keys="TicketModel.assigned_to")
    assignments = relationship("AssetAssignmentModel", back_populates="user")


class AssetModel(Base):
    """IT Hardware Asset entity."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., LAP-1023
    asset_type = Column(String(50), nullable=False, index=True)  # Laptop, Monitor, Keyboard, Mouse, Printer
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False, index=True)
    purchase_date = Column(String(20), nullable=False)  # ISO string YYYY-MM-DD
    purchase_cost = Column(Float, default=0.0, nullable=False)
    status = Column(String(30), nullable=False, default="AVAILABLE", index=True)  # AVAILABLE, ASSIGNED, etc.
    assigned_to = Column(String(50), ForeignKey("users.user_id"), nullable=True)
    specs_json = Column(Text, nullable=True)  # Serialized hardware specs
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    assignee = relationship("UserModel", back_populates="assigned_assets", foreign_keys=[assigned_to])
    assignment_history = relationship("AssetAssignmentModel", back_populates="asset", cascade="all, delete-orphan")


class AssetAssignmentModel(Base):
    """History log of asset assignments to employees."""

    __tablename__ = "asset_assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(50), ForeignKey("assets.asset_id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    assigned_date = Column(DateTime, default=utc_now, nullable=False)
    returned_date = Column(DateTime, nullable=True)
    notes = Column(String(255), nullable=True)

    # Relationships
    asset = relationship("AssetModel", back_populates="assignment_history")
    user = relationship("UserModel", back_populates="assignments")


class TicketModel(Base):
    """Support Ticket entity."""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., INC-1001
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="Hardware", index=True)
    priority = Column(String(20), nullable=False, default="MEDIUM", index=True)
    status = Column(String(30), nullable=False, default="OPEN", index=True)
    created_by = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    assigned_to = Column(String(50), ForeignKey("users.user_id"), nullable=True, index=True)
    resolution = Column(Text, nullable=True)
    sla_deadline = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("UserModel", back_populates="created_tickets", foreign_keys=[created_by])
    assignee = relationship("UserModel", back_populates="assigned_tickets", foreign_keys=[assigned_to])
    history = relationship("TicketHistoryModel", back_populates="ticket", cascade="all, delete-orphan")


class TicketHistoryModel(Base):
    """Audit trail for ticket state transitions and comments."""

    __tablename__ = "ticket_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id = Column(String(50), ForeignKey("tickets.ticket_id"), nullable=False, index=True)
    changed_by = Column(String(50), nullable=False)
    old_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)
    comments = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    ticket = relationship("TicketModel", back_populates="history")


class ActivityLogModel(Base):
    """System-wide operational activity audit log."""

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


# Explicit composite indexes for high-throughput queries
Index("idx_ticket_status_priority", TicketModel.status, TicketModel.priority)
Index("idx_asset_status_type", AssetModel.status, AssetModel.asset_type)

"""Repository Pattern Implementation.

Demonstrates:
- Decoupling data access logic from business services (Dependency Inversion & Layered Architecture)
- ACID Transaction Management (Atomicity, Consistency, Isolation, Durability)
- Multi-operation atomic transactions with automatic rollback on error
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.orm import (
    UserModel,
    AssetModel,
    AssetAssignmentModel,
    TicketModel,
    TicketHistoryModel,
    ActivityLogModel,
)
from app.utils.exceptions import (
    AssetNotFoundError,
    TicketNotFoundError,
    DuplicateRecordError,
    DatabaseConnectionError,
)
from app.utils.logger import get_logger

logger = get_logger()


class UserRepository:
    """Data access repository for User entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_id(self, user_id: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.user_id == user_id)
        return self.db.scalars(stmt).first()

    def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email.lower().strip())
        return self.db.scalars(stmt).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        stmt = select(UserModel).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, user_data: Dict[str, Any]) -> UserModel:
        if self.get_by_user_id(user_data["user_id"]):
            raise DuplicateRecordError("user_id", user_data["user_id"])
        if self.get_by_email(user_data["email"]):
            raise DuplicateRecordError("email", user_data["email"])

        user = UserModel(
            user_id=user_data["user_id"],
            email=user_data["email"].lower().strip(),
            hashed_password=user_data["hashed_password"],
            full_name=user_data["full_name"],
            role=user_data.get("role", "EMPLOYEE"),
            department=user_data.get("department", "General"),
            is_active=user_data.get("is_active", True),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


class AssetRepository:
    """Data access repository for Asset and Asset Assignment entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_asset_id(self, asset_id: str) -> Optional[AssetModel]:
        stmt = select(AssetModel).where(AssetModel.asset_id == asset_id)
        return self.db.scalars(stmt).first()

    def list_all(
        self,
        status: Optional[str] = None,
        asset_type: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> List[AssetModel]:
        stmt = select(AssetModel)
        if status:
            stmt = stmt.where(AssetModel.status == status)
        if asset_type:
            stmt = stmt.where(AssetModel.asset_type == asset_type)
        if assigned_to:
            stmt = stmt.where(AssetModel.assigned_to == assigned_to)
        return list(self.db.scalars(stmt).all())

    def create(self, asset_data: Dict[str, Any]) -> AssetModel:
        if self.get_by_asset_id(asset_data["asset_id"]):
            raise DuplicateRecordError("asset_id", asset_data["asset_id"])

        asset = AssetModel(
            asset_id=asset_data["asset_id"],
            asset_type=asset_data["asset_type"],
            brand=asset_data["brand"],
            model=asset_data["model"],
            serial_number=asset_data["serial_number"],
            purchase_date=asset_data["purchase_date"],
            purchase_cost=asset_data.get("purchase_cost", 0.0),
            status=asset_data.get("status", "AVAILABLE"),
            assigned_to=asset_data.get("assigned_to"),
            specs_json=json.dumps(asset_data.get("specs", {})),
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def assign_asset(self, asset_id: str, user_id: str, notes: Optional[str] = None) -> AssetModel:
        """Atomic transaction: update asset status + record assignment history."""
        asset = self.get_by_asset_id(asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        try:
            asset.status = "ASSIGNED"
            asset.assigned_to = user_id

            assignment = AssetAssignmentModel(
                asset_id=asset_id,
                user_id=user_id,
                assigned_date=datetime.now(timezone.utc),
                notes=notes,
            )
            self.db.add(assignment)
            self.db.commit()
            self.db.refresh(asset)
            return asset
        except Exception as exc:
            self.db.rollback()
            logger.error("Failed assigning asset %s: %s", asset_id, exc)
            raise DatabaseConnectionError("Failed to persist asset assignment.")

    def return_asset(self, asset_id: str) -> AssetModel:
        """Atomic transaction: mark asset returned and close assignment history record."""
        asset = self.get_by_asset_id(asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        try:
            previous_user = asset.assigned_to
            asset.status = "AVAILABLE"
            asset.assigned_to = None

            # Close open assignment record
            stmt = (
                select(AssetAssignmentModel)
                .where(AssetAssignmentModel.asset_id == asset_id)
                .where(AssetAssignmentModel.returned_date.is_(None))
                .order_by(desc(AssetAssignmentModel.assigned_date))
            )
            assignment = self.db.scalars(stmt).first()
            if assignment:
                assignment.returned_date = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(asset)
            return asset
        except Exception as exc:
            self.db.rollback()
            logger.error("Failed returning asset %s: %s", asset_id, exc)
            raise DatabaseConnectionError("Failed to update asset return.")


class TicketRepository:
    """Data access repository for Support Tickets and Audit History."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_ticket_id(self, ticket_id: str) -> Optional[TicketModel]:
        stmt = select(TicketModel).where(TicketModel.ticket_id == ticket_id)
        return self.db.scalars(stmt).first()

    def list_all(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        created_by: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> List[TicketModel]:
        stmt = select(TicketModel)
        if status:
            stmt = stmt.where(TicketModel.status == status)
        if priority:
            stmt = stmt.where(TicketModel.priority == priority)
        if created_by:
            stmt = stmt.where(TicketModel.created_by == created_by)
        if assigned_to:
            stmt = stmt.where(TicketModel.assigned_to == assigned_to)
        stmt = stmt.order_by(desc(TicketModel.created_at))
        return list(self.db.scalars(stmt).all())

    def create_atomic(
        self,
        ticket_data: Dict[str, Any],
        actor_user_id: str,
    ) -> TicketModel:
        """Demonstrates ACID Atomicity.

        Executes 3 operations within a single database transaction:
        1. Insert into tickets
        2. Insert into ticket_history (initial entry)
        3. Insert into activity_logs
        If any step fails, the entire transaction rolls back completely!
        """
        if self.get_by_ticket_id(ticket_data["ticket_id"]):
            raise DuplicateRecordError("ticket_id", ticket_data["ticket_id"])

        try:
            # 1. Create Ticket
            ticket = TicketModel(
                ticket_id=ticket_data["ticket_id"],
                title=ticket_data["title"],
                description=ticket_data["description"],
                category=ticket_data["category"],
                priority=ticket_data["priority"],
                status=ticket_data.get("status", "OPEN"),
                created_by=ticket_data["created_by"],
                assigned_to=ticket_data.get("assigned_to"),
                sla_deadline=ticket_data["sla_deadline"],
            )
            self.db.add(ticket)

            # 2. Audit in TicketHistory
            history = TicketHistoryModel(
                ticket_id=ticket_data["ticket_id"],
                changed_by=actor_user_id,
                old_status="NONE",
                new_status=ticket_data.get("status", "OPEN"),
                comments="Ticket created in system.",
            )
            self.db.add(history)

            # 3. System Activity Log
            activity = ActivityLogModel(
                user_id=actor_user_id,
                action="CREATE_TICKET",
                entity_type="Ticket",
                entity_id=ticket_data["ticket_id"],
                details_json=json.dumps({"title": ticket_data["title"], "priority": ticket_data["priority"]}),
            )
            self.db.add(activity)

            # Commit all operations atomically
            self.db.commit()
            self.db.refresh(ticket)
            return ticket
        except Exception as exc:
            self.db.rollback()
            logger.error("ACID Transaction rollback during ticket creation: %s", exc)
            raise DatabaseConnectionError(f"Atomic ticket creation failed: {exc}")

    def update_status_atomic(
        self,
        ticket_id: str,
        new_status: str,
        actor_user_id: str,
        comments: Optional[str] = None,
        resolution: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> TicketModel:
        """Atomic status update with ticket history and activity log creation."""
        ticket = self.get_by_ticket_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id)

        old_status = ticket.status

        try:
            ticket.status = new_status
            if resolution:
                ticket.resolution = resolution
            if assigned_to:
                ticket.assigned_to = assigned_to
            if new_status in ("RESOLVED", "CLOSED") and ticket.closed_at is None:
                ticket.closed_at = datetime.now(timezone.utc)

            # Audit history
            history = TicketHistoryModel(
                ticket_id=ticket_id,
                changed_by=actor_user_id,
                old_status=old_status,
                new_status=new_status,
                comments=comments or f"Status changed from {old_status} to {new_status}",
            )
            self.db.add(history)

            # Activity log
            activity = ActivityLogModel(
                user_id=actor_user_id,
                action=f"TRANSITION_{new_status}",
                entity_type="Ticket",
                entity_id=ticket_id,
                details_json=json.dumps({"old_status": old_status, "new_status": new_status, "resolution": resolution}),
            )
            self.db.add(activity)

            self.db.commit()
            self.db.refresh(ticket)
            return ticket
        except Exception as exc:
            self.db.rollback()
            logger.error("Rollback on ticket status update (%s): %s", ticket_id, exc)
            raise DatabaseConnectionError(f"Failed to update ticket status: {exc}")


class ActivityLogRepository:
    """Data access repository for system-wide activity logs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, limit: int = 100) -> List[ActivityLogModel]:
        stmt = select(ActivityLogModel).order_by(desc(ActivityLogModel.created_at)).limit(limit)
        return list(self.db.scalars(stmt).all())

    def log(self, user_id: str, action: str, entity_type: str, entity_id: str, details: Optional[Dict] = None) -> None:
        activity = ActivityLogModel(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details_json=json.dumps(details or {}),
        )
        self.db.add(activity)
        self.db.commit()

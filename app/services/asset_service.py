"""Asset Management Service Layer.

Demonstrates:
- Business logic separation from API controllers and Database repositories (MVC / Layered Architecture)
- Bridge between OOP domain models (Laptop, Monitor, etc.) and ORM persistence models
- Polymorphic depreciation and specs evaluation
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database.repositories import AssetRepository, UserRepository
from app.models.enums import AssetStatus, AssetType
from app.models.domain_assets import (
    Asset,
    Laptop,
    Monitor,
    Keyboard,
    Mouse,
    Printer,
    Warranty,
)
from app.utils.exceptions import InvalidAssetError, AssetNotFoundError
from app.utils.logger import get_logger

logger = get_logger()


class AssetService:
    """Service handling asset lifecycle, inventory verification, and domain model mapping."""

    def __init__(self, db: Session) -> None:
        self.asset_repo = AssetRepository(db)
        self.user_repo = UserRepository(db)

    @staticmethod
    def domain_asset_factory(asset_data: Dict[str, Any]) -> Asset:
        """Factory Method pattern instantiating the appropriate polymorphic OOP Asset class."""
        asset_type = asset_data.get("asset_type")
        purchase_date_val = asset_data["purchase_date"]
        if isinstance(purchase_date_val, str):
            parsed_date = date.fromisoformat(purchase_date_val[:10])
        else:
            parsed_date = purchase_date_val

        specs = asset_data.get("specs", {})
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except Exception:
                specs = {}

        common_args = {
            "asset_id": asset_data["asset_id"],
            "brand": asset_data["brand"],
            "model": asset_data["model"],
            "serial_number": asset_data["serial_number"],
            "purchase_date": parsed_date,
            "purchase_cost": float(asset_data.get("purchase_cost", 0.0)),
            "status": AssetStatus(asset_data.get("status", AssetStatus.AVAILABLE)),
            "assigned_to": asset_data.get("assigned_to"),
        }

        if asset_type == AssetType.LAPTOP or asset_type == "Laptop":
            return Laptop(
                **common_args,
                processor=specs.get("processor", "Intel Core i7"),
                ram_gb=int(specs.get("ram_gb", 16)),
                storage_gb=int(specs.get("storage_gb", 512)),
                battery_health_percent=int(specs.get("battery_health_percent", 100)),
            )
        elif asset_type == AssetType.MONITOR or asset_type == "Monitor":
            return Monitor(
                **common_args,
                screen_size_inches=float(specs.get("screen_size_inches", 27.0)),
                resolution=specs.get("resolution", "2560x1440"),
                refresh_rate_hz=int(specs.get("refresh_rate_hz", 75)),
            )
        elif asset_type == AssetType.KEYBOARD or asset_type == "Keyboard":
            return Keyboard(
                **common_args,
                connectivity=specs.get("connectivity", "Wireless"),
                switch_type=specs.get("switch_type", "Mechanical Brown"),
            )
        elif asset_type == AssetType.MOUSE or asset_type == "Mouse":
            return Mouse(
                **common_args,
                dpi=int(specs.get("dpi", 1600)),
                is_wireless=bool(specs.get("is_wireless", True)),
            )
        elif asset_type == AssetType.PRINTER or asset_type == "Printer":
            return Printer(
                **common_args,
                print_technology=specs.get("print_technology", "Laser"),
                pages_per_minute=int(specs.get("pages_per_minute", 35)),
                is_color=bool(specs.get("is_color", True)),
            )
        else:
            raise InvalidAssetError(f"Unsupported asset type: {asset_type}")

    def create_asset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validates domain constraints and saves a new asset."""
        # Instantiate domain object to run domain invariants
        domain_obj = self.domain_asset_factory(payload)

        # Persist through repository
        created = self.asset_repo.create({
            "asset_id": domain_obj.asset_id,
            "asset_type": domain_obj.asset_type.value,
            "brand": domain_obj.brand,
            "model": domain_obj.model,
            "serial_number": domain_obj.serial_number,
            "purchase_date": domain_obj.purchase_date.isoformat(),
            "purchase_cost": domain_obj.purchase_cost,
            "status": domain_obj.status.value,
            "assigned_to": domain_obj.assigned_to,
            "specs": domain_obj.get_specs_summary(),
        })

        return domain_obj.to_dict()

    def get_asset(self, asset_id: str) -> Dict[str, Any]:
        """Retrieves asset and transforms into polymorphic domain model summary."""
        orm_asset = self.asset_repo.get_by_asset_id(asset_id)
        if not orm_asset:
            raise AssetNotFoundError(asset_id)

        domain_obj = self.domain_asset_factory({
            "asset_id": orm_asset.asset_id,
            "asset_type": orm_asset.asset_type,
            "brand": orm_asset.brand,
            "model": orm_asset.model,
            "serial_number": orm_asset.serial_number,
            "purchase_date": orm_asset.purchase_date,
            "purchase_cost": orm_asset.purchase_cost,
            "status": orm_asset.status,
            "assigned_to": orm_asset.assigned_to,
            "specs": orm_asset.specs_json,
        })
        return domain_obj.to_dict()

    def assign_asset(self, asset_id: str, user_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Assign an available asset to a user."""
        user = self.user_repo.get_by_user_id(user_id)
        if not user:
            raise InvalidAssetError(f"Assignee user '{user_id}' does not exist.")

        orm_asset = self.asset_repo.get_by_asset_id(asset_id)
        if not orm_asset:
            raise AssetNotFoundError(asset_id)

        if orm_asset.status != AssetStatus.AVAILABLE.value:
            raise InvalidAssetError(
                f"Asset '{asset_id}' is not available (current status: {orm_asset.status})."
            )

        updated = self.asset_repo.assign_asset(asset_id, user_id, notes)
        return self.get_asset(asset_id)

    def return_asset(self, asset_id: str) -> Dict[str, Any]:
        """Return an assigned asset back into inventory."""
        orm_asset = self.asset_repo.get_by_asset_id(asset_id)
        if not orm_asset:
            raise AssetNotFoundError(asset_id)

        if orm_asset.status != AssetStatus.ASSIGNED.value:
            raise InvalidAssetError(
                f"Cannot return asset '{asset_id}' because it is not currently assigned (status: {orm_asset.status})."
            )

        self.asset_repo.return_asset(asset_id)
        return self.get_asset(asset_id)

    def list_assets(
        self,
        status: Optional[str] = None,
        asset_type: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List assets converted to domain summary format."""
        orm_assets = self.asset_repo.list_all(status=status, asset_type=asset_type, assigned_to=assigned_to)
        results = []
        for a in orm_assets:
            domain_obj = self.domain_asset_factory({
                "asset_id": a.asset_id,
                "asset_type": a.asset_type,
                "brand": a.brand,
                "model": a.model,
                "serial_number": a.serial_number,
                "purchase_date": a.purchase_date,
                "purchase_cost": a.purchase_cost,
                "status": a.status,
                "assigned_to": a.assigned_to,
                "specs": a.specs_json,
            })
            results.append(domain_obj.to_dict())
        return results

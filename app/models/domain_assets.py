"""Object-Oriented Programming (OOP) Domain Hierarchy for IT Assets.

Demonstrates:
- Inheritance (Base class Asset with derived specialized hardware classes)
- Encapsulation (Protected attributes, property getters/setters, state guard invariants)
- Polymorphism (Overridden methods: get_specs_summary, is_portable, calculate_depreciation)
- Composition (HardwareSpec and Warranty objects composed within Asset instances)
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, Optional
from app.models.enums import AssetStatus, AssetType
from app.utils.exceptions import InvalidAssetError


class Warranty:
    """Demonstrates Composition: Warranty component encapsulated within an Asset."""

    def __init__(self, provider: str, start_date: date, duration_months: int) -> None:
        self.provider = provider
        self.start_date = start_date
        self.duration_months = duration_months

    @property
    def is_active(self) -> bool:
        """Calculate warranty validity relative to current date."""
        today = date.today()
        months_passed = (today.year - self.start_date.year) * 12 + (today.month - self.start_date.month)
        return months_passed < self.duration_months

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "start_date": self.start_date.isoformat(),
            "duration_months": self.duration_months,
            "is_active": self.is_active,
        }


class Asset(ABC):
    """Base class for all IT Assets.

    Demonstrates Encapsulation via private/protected fields and validation methods.
    """

    def __init__(
        self,
        asset_id: str,
        asset_type: AssetType,
        brand: str,
        model: str,
        serial_number: str,
        purchase_date: date,
        purchase_cost: float = 0.0,
        status: AssetStatus = AssetStatus.AVAILABLE,
        assigned_to: Optional[str] = None,
        warranty: Optional[Warranty] = None,
    ) -> None:
        self._asset_id = asset_id
        self._asset_type = asset_type
        self._brand = brand
        self._model = model
        self._serial_number = serial_number
        self._purchase_date = purchase_date
        self._purchase_cost = max(0.0, float(purchase_cost))
        self._status = status
        self._assigned_to = assigned_to
        # Composition: Warranty object composed within Asset
        self._warranty = warranty

    # --- Encapsulation: Property Getters ---
    @property
    def asset_id(self) -> str:
        return self._asset_id

    @property
    def asset_type(self) -> AssetType:
        return self._asset_type

    @property
    def brand(self) -> str:
        return self._brand

    @property
    def model(self) -> str:
        return self._model

    @property
    def serial_number(self) -> str:
        return self._serial_number

    @property
    def purchase_date(self) -> date:
        return self._purchase_date

    @property
    def purchase_cost(self) -> float:
        return self._purchase_cost

    @property
    def status(self) -> AssetStatus:
        return self._status

    @property
    def assigned_to(self) -> Optional[str]:
        return self._assigned_to

    @property
    def warranty(self) -> Optional[Warranty]:
        return self._warranty

    # --- Domain Business Methods (Encapsulation invariants) ---
    def assign_to(self, employee_id: str) -> None:
        """Assign asset to an employee if currently available."""
        if self._status != AssetStatus.AVAILABLE:
            raise InvalidAssetError(
                f"Asset '{self._asset_id}' cannot be assigned because its status is {self._status.value}."
            )
        if not employee_id or not employee_id.strip():
            raise InvalidAssetError("Employee ID must be provided to assign an asset.")
        self._status = AssetStatus.ASSIGNED
        self._assigned_to = employee_id.strip()

    def return_asset(self) -> None:
        """Mark asset returned and available for reallocation."""
        if self._status != AssetStatus.ASSIGNED:
            raise InvalidAssetError(
                f"Asset '{self._asset_id}' is not currently assigned (status: {self._status.value})."
            )
        self._status = AssetStatus.AVAILABLE
        self._assigned_to = None

    def mark_under_repair(self) -> None:
        """Transition asset to repair status."""
        self._status = AssetStatus.UNDER_REPAIR

    def retire(self) -> None:
        """Decommission asset from inventory."""
        self._status = AssetStatus.RETIRED
        self._assigned_to = None

    # --- Polymorphic Methods (Overridden by Child Classes) ---
    @abstractmethod
    def get_specs_summary(self) -> Dict[str, Any]:
        """Polymorphic summary of device-specific technical specs."""
        pass

    @abstractmethod
    def is_portable(self) -> bool:
        """Polymorphic determination of physical portability."""
        pass

    def calculate_depreciation(self, current_year: Optional[int] = None) -> float:
        """Polymorphic base straight-line annual depreciation calculation (20% per year)."""
        year = current_year or datetime.now().year
        age_years = max(0, year - self._purchase_date.year)
        depreciation_rate = 0.20
        depreciated_value = self._purchase_cost * max(0.0, (1.0 - (depreciation_rate * age_years)))
        return round(depreciated_value, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize domain asset object to dictionary."""
        return {
            "asset_id": self._asset_id,
            "type": self._asset_type.value,
            "brand": self._brand,
            "model": self._model,
            "serial_number": self._serial_number,
            "purchase_date": self._purchase_date.isoformat(),
            "purchase_cost": self._purchase_cost,
            "status": self._status.value,
            "assigned_to": self._assigned_to,
            "is_portable": self.is_portable(),
            "specs": self.get_specs_summary(),
            "warranty": self._warranty.to_dict() if self._warranty else None,
        }


# =====================================================================
# Child Classes Demonstrating Inheritance & Polymorphism
# =====================================================================

class Laptop(Asset):
    """Laptop asset with processor, RAM, and battery characteristics."""

    def __init__(
        self,
        asset_id: str,
        brand: str,
        model: str,
        serial_number: str,
        purchase_date: date,
        processor: str = "Intel Core i7",
        ram_gb: int = 16,
        storage_gb: int = 512,
        battery_health_percent: int = 100,
        purchase_cost: float = 1200.0,
        status: AssetStatus = AssetStatus.AVAILABLE,
        assigned_to: Optional[str] = None,
        warranty: Optional[Warranty] = None,
    ) -> None:
        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.LAPTOP,
            brand=brand,
            model=model,
            serial_number=serial_number,
            purchase_date=purchase_date,
            purchase_cost=purchase_cost,
            status=status,
            assigned_to=assigned_to,
            warranty=warranty,
        )
        self.processor = processor
        self.ram_gb = ram_gb
        self.storage_gb = storage_gb
        self.battery_health_percent = battery_health_percent

    def is_portable(self) -> bool:
        return True

    def get_specs_summary(self) -> Dict[str, Any]:
        return {
            "processor": self.processor,
            "ram_gb": self.ram_gb,
            "storage_gb": self.storage_gb,
            "battery_health": f"{self.battery_health_percent}%",
        }

    def calculate_depreciation(self, current_year: Optional[int] = None) -> float:
        # Laptops depreciate slightly faster (25% per year)
        year = current_year or datetime.now().year
        age_years = max(0, year - self._purchase_date.year)
        depreciated_value = self._purchase_cost * max(0.0, (1.0 - (0.25 * age_years)))
        return round(depreciated_value, 2)


class Monitor(Asset):
    """Monitor display asset with screen size, resolution, and refresh rate."""

    def __init__(
        self,
        asset_id: str,
        brand: str,
        model: str,
        serial_number: str,
        purchase_date: date,
        screen_size_inches: float = 27.0,
        resolution: str = "2560x1440",
        refresh_rate_hz: int = 75,
        purchase_cost: float = 300.0,
        status: AssetStatus = AssetStatus.AVAILABLE,
        assigned_to: Optional[str] = None,
        warranty: Optional[Warranty] = None,
    ) -> None:
        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.MONITOR,
            brand=brand,
            model=model,
            serial_number=serial_number,
            purchase_date=purchase_date,
            purchase_cost=purchase_cost,
            status=status,
            assigned_to=assigned_to,
            warranty=warranty,
        )
        self.screen_size_inches = screen_size_inches
        self.resolution = resolution
        self.refresh_rate_hz = refresh_rate_hz

    def is_portable(self) -> bool:
        return False

    def get_specs_summary(self) -> Dict[str, Any]:
        return {
            "screen_size_inches": self.screen_size_inches,
            "resolution": self.resolution,
            "refresh_rate_hz": self.refresh_rate_hz,
        }


class Keyboard(Asset):
    """Keyboard peripheral asset with connectivity and switch type."""

    def __init__(
        self,
        asset_id: str,
        brand: str,
        model: str,
        serial_number: str,
        purchase_date: date,
        connectivity: str = "Wireless",
        switch_type: str = "Mechanical Brown",
        purchase_cost: float = 80.0,
        status: AssetStatus = AssetStatus.AVAILABLE,
        assigned_to: Optional[str] = None,
        warranty: Optional[Warranty] = None,
    ) -> None:
        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.KEYBOARD,
            brand=brand,
            model=model,
            serial_number=serial_number,
            purchase_date=purchase_date,
            purchase_cost=purchase_cost,
            status=status,
            assigned_to=assigned_to,
            warranty=warranty,
        )
        self.connectivity = connectivity
        self.switch_type = switch_type

    def is_portable(self) -> bool:
        return True

    def get_specs_summary(self) -> Dict[str, Any]:
        return {
            "connectivity": self.connectivity,
            "switch_type": self.switch_type,
        }


class Mouse(Asset):
    """Mouse peripheral asset with sensor DPI and ergonomic profile."""

    def __init__(
        self,
        asset_id: str,
        brand: str,
        model: str,
        serial_number: str,
        purchase_date: date,
        dpi: int = 1600,
        is_wireless: bool = True,
        purchase_cost: float = 40.0,
        status: AssetStatus = AssetStatus.AVAILABLE,
        assigned_to: Optional[str] = None,
        warranty: Optional[Warranty] = None,
    ) -> None:
        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.MOUSE,
            brand=brand,
            model=model,
            serial_number=serial_number,
            purchase_date=purchase_date,
            purchase_cost=purchase_cost,
            status=status,
            assigned_to=assigned_to,
            warranty=warranty,
        )
        self.dpi = dpi
        self.is_wireless = is_wireless

    def is_portable(self) -> bool:
        return True

    def get_specs_summary(self) -> Dict[str, Any]:
        return {
            "dpi": self.dpi,
            "is_wireless": self.is_wireless,
        }


class Printer(Asset):
    """Network/office printer asset with printing technology and PPM."""

    def __init__(
        self,
        asset_id: str,
        brand: str,
        model: str,
        serial_number: str,
        purchase_date: date,
        print_technology: str = "Laser",
        pages_per_minute: int = 35,
        is_color: bool = True,
        purchase_cost: float = 500.0,
        status: AssetStatus = AssetStatus.AVAILABLE,
        assigned_to: Optional[str] = None,
        warranty: Optional[Warranty] = None,
    ) -> None:
        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.PRINTER,
            brand=brand,
            model=model,
            serial_number=serial_number,
            purchase_date=purchase_date,
            purchase_cost=purchase_cost,
            status=status,
            assigned_to=assigned_to,
            warranty=warranty,
        )
        self.print_technology = print_technology
        self.pages_per_minute = pages_per_minute
        self.is_color = is_color

    def is_portable(self) -> bool:
        return False

    def get_specs_summary(self) -> Dict[str, Any]:
        return {
            "print_technology": self.print_technology,
            "pages_per_minute": self.pages_per_minute,
            "is_color": self.is_color,
        }

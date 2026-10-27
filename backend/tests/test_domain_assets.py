"""Unit Tests for Object-Oriented Asset Hierarchy.

Tests:
- Inheritance from base Asset
- Encapsulation invariants (assign, return, state checks)
- Polymorphism (specs summary, portability, depreciation)
- Composition (Warranty component)
- Custom exceptions (InvalidAssetError)
"""

import pytest
from datetime import date
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
from app.utils.exceptions import InvalidAssetError


def test_warranty_composition():
    """Verify composition: Warranty object inside Asset and active check."""
    w = Warranty(provider="Dell Care", start_date=date.today(), duration_months=24)
    assert w.is_active is True
    data = w.to_dict()
    assert data["provider"] == "Dell Care"
    assert data["duration_months"] == 24


def test_laptop_polymorphism_and_specs():
    """Verify Laptop child class inheritance and polymorphic behavior."""
    lap = Laptop(
        asset_id="LAP-1001",
        brand="Dell",
        model="Latitude 5440",
        serial_number="SN-12345",
        purchase_date=date(2024, 1, 1),
        processor="Intel Core i7",
        ram_gb=32,
        storage_gb=1024,
        purchase_cost=1500.0,
    )
    assert lap.asset_type == AssetType.LAPTOP
    assert lap.is_portable() is True
    specs = lap.get_specs_summary()
    assert specs["processor"] == "Intel Core i7"
    assert specs["ram_gb"] == 32
    assert specs["storage_gb"] == 1024


def test_monitor_polymorphism_and_specs():
    """Verify Monitor child class behavior (not portable, resolution specs)."""
    mon = Monitor(
        asset_id="MON-2001",
        brand="Dell",
        model="UltraSharp",
        serial_number="SN-MON-99",
        purchase_date=date(2024, 5, 1),
        screen_size_inches=27.0,
        resolution="3840x2160",
        purchase_cost=500.0,
    )
    assert mon.asset_type == AssetType.MONITOR
    assert mon.is_portable() is False
    assert mon.get_specs_summary()["resolution"] == "3840x2160"


def test_encapsulation_asset_assignment_guard():
    """Verify Encapsulation: cannot assign an asset that is not AVAILABLE."""
    lap = Laptop(
        asset_id="LAP-1002",
        brand="Lenovo",
        model="ThinkPad",
        serial_number="SN-LEN-01",
        purchase_date=date(2025, 1, 1),
        status=AssetStatus.AVAILABLE,
    )
    # Valid assignment
    lap.assign_to("EMP-101")
    assert lap.status == AssetStatus.ASSIGNED
    assert lap.assigned_to == "EMP-101"

    # Invalid re-assignment when already assigned raises InvalidAssetError
    with pytest.raises(InvalidAssetError):
        lap.assign_to("EMP-102")


def test_encapsulation_asset_return_guard():
    """Verify Encapsulation: cannot return an unassigned asset."""
    mon = Monitor(
        asset_id="MON-2002",
        brand="HP",
        model="E24",
        serial_number="SN-HP-02",
        purchase_date=date(2025, 1, 1),
        status=AssetStatus.AVAILABLE,
    )
    # Returning an asset that is not ASSIGNED raises InvalidAssetError
    with pytest.raises(InvalidAssetError):
        mon.return_asset()

    # Assign then return works properly
    mon.assign_to("EMP-105")
    mon.return_asset()
    assert mon.status == AssetStatus.AVAILABLE
    assert mon.assigned_to is None


def test_polymorphic_depreciation_calculation():
    """Verify calculation of depreciation values over years."""
    lap = Laptop(
        asset_id="LAP-1003",
        brand="Apple",
        model="MacBook",
        serial_number="SN-APL-01",
        purchase_date=date(2023, 1, 1),
        purchase_cost=2000.0,
    )
    # Laptop depreciates 25% per year. After 2 years (2025), value = 2000 * 0.50 = 1000
    depreciated = lap.calculate_depreciation(current_year=2025)
    assert depreciated == 1000.0

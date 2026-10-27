"""Unit Tests for Generator Processing Functions."""

import inspect
from app.utils.generators import ticket_generator, asset_depreciation_generator, stream_csv_rows


def test_ticket_generator_is_generator():
    """Verify ticket_generator is a Python generator object and yields lazily."""
    dataset = [
        {"ticket_id": "INC-01", "status": "OPEN", "priority": "HIGH"},
        {"ticket_id": "INC-02", "status": "CLOSED", "priority": "LOW"},
    ]
    gen = ticket_generator(dataset, status_filter="OPEN")
    assert inspect.isgenerator(gen)

    # Yield first item
    first_item = next(gen)
    assert first_item["ticket_id"] == "INC-01"

    # No more open items
    assert list(gen) == []


def test_asset_depreciation_generator():
    """Verify asset_depreciation_generator enriches assets with calculated depreciation."""
    assets = [
        {"asset_id": "LAP-01", "purchase_cost": 1000.0, "purchase_date": "2023-01-01"},
    ]
    gen = asset_depreciation_generator(assets, current_year=2025)
    results = list(gen)
    assert len(results) == 1
    # 2 years * 20% = 40% depreciation -> remaining 60% of 1000 = 600
    assert results[0]["depreciated_value"] == 600.0


def test_stream_csv_rows():
    """Verify streaming CSV generator produces header then rows."""
    def sample_gen():
        yield {"id": "1", "name": "Alice"}
        yield {"id": "2", "name": "Bob"}

    csv_lines = list(stream_csv_rows(sample_gen(), fieldnames=["id", "name"]))
    assert len(csv_lines) == 3  # Header + 2 rows
    assert "id,name" in csv_lines[0]
    assert "1,Alice" in csv_lines[1]
    assert "2,Bob" in csv_lines[2]

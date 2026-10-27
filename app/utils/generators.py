"""Generator-Based Data Processing Utilities.

Demonstrates:
- Memory-efficient processing using `yield`
- Generator iterators that avoid loading entire datasets into RAM
- Streaming report transformations
- Lazy evaluation for large CSV/JSON payloads
"""

import io
import csv
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional
from datetime import datetime


def ticket_generator(
    tickets_dataset: Iterable[Dict[str, Any]],
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Generator that lazily filters and yields tickets one-by-one.

    Memory Benefit:
    Instead of building an in-memory filtered list of 50,000+ items (O(N) RAM),
    this generator processes items one at a time with O(1) auxiliary memory footprint.
    """
    for ticket in tickets_dataset:
        if status_filter and ticket.get("status") != status_filter:
            continue
        if priority_filter and ticket.get("priority") != priority_filter:
            continue
        yield ticket


def asset_depreciation_generator(
    assets_dataset: Iterable[Dict[str, Any]],
    current_year: Optional[int] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Generator that streams assets enriched with calculated depreciation values."""
    eval_year = current_year or datetime.now().year
    depreciation_rate = 0.20

    for asset in assets_dataset:
        purchase_year = eval_year
        purchase_date = asset.get("purchase_date")
        if purchase_date:
            try:
                purchase_year = int(str(purchase_date)[:4])
            except (ValueError, TypeError):
                purchase_year = eval_year

        age_years = max(0, eval_year - purchase_year)
        cost = float(asset.get("purchase_cost", 0.0))
        current_value = round(cost * max(0.0, (1.0 - (depreciation_rate * age_years))), 2)

        # Yield enriched record without modifying source dataset
        yield {
            **asset,
            "age_years": age_years,
            "depreciated_value": current_value,
        }


def stream_csv_rows(
    data_generator: Generator[Dict[str, Any], None, None],
    fieldnames: List[str],
) -> Generator[str, None, None]:
    """Streams CSV-formatted rows lazily from a generator.

    Ideal for FastAPI StreamingResponse to export multi-megabyte reports without memory spikes.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")

    # Yield header first
    writer.writeheader()
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    # Yield row-by-row
    for row in data_generator:
        writer.writerow(row)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

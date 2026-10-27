"""File Processing & External API Integration Router.

Demonstrates:
- File I/O analysis: line, word, character counts
- Batch record parsing and duplicate elimination
- Archiving files using the os module
- External API calls via requests library demonstrating network failure states
"""

import os
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.enums import UserRole
from app.models.orm import UserModel
from app.schemas.common import APIResponse
from app.services.file_service import FileProcessorService
from app.services.external_api import ExternalAPIService
from app.api.auth import require_roles

router = APIRouter(prefix="/files", tags=["File Processing & External APIs"])


@router.get("/list", response_model=APIResponse[Dict[str, List[str]]])
def list_files(
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
) -> APIResponse[Dict[str, List[str]]]:
    """Lists all files in data/ and data/archive/ directories using the os module."""
    service = FileProcessorService()
    listing = service.list_data_files()
    return APIResponse(data=listing)


@router.get("/metrics/{filename}", response_model=APIResponse[Dict[str, Any]])
def analyze_file(
    filename: str,
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
) -> APIResponse[Dict[str, Any]]:
    """Calculates lines, words, characters, and byte size of a file in the data directory."""
    service = FileProcessorService()
    filepath = os.path.join(service.base_data_dir, filename)
    metrics = service.analyze_file_metrics(filepath)
    return APIResponse(data=metrics)


@router.post("/process/{file_type}", response_model=APIResponse[Dict[str, Any]])
def process_data_file(
    file_type: str,  # 'employees' | 'assets' | 'tickets'
    archive_after: bool = Query(True, description="Whether to archive after processing"),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> APIResponse[Dict[str, Any]]:
    """Parses, deduplicates, and optionally archives an input data file."""
    service = FileProcessorService()
    filename_map = {
        "employees": ("employees.txt", ["user_id", "email", "full_name", "role", "department"], "user_id"),
        "assets": ("assets.txt", ["asset_id", "asset_type", "brand", "model", "serial_number", "purchase_date", "purchase_cost"], "asset_id"),
        "tickets": ("tickets.txt", ["ticket_id", "title", "category", "priority", "created_by"], "ticket_id"),
    }

    if file_type not in filename_map:
        return APIResponse(
            success=False,
            message=f"Unsupported file type '{file_type}'. Supported: 'employees', 'assets', 'tickets'.",
        )

    target_file, expected_fields, key_field = filename_map[file_type]
    filepath = os.path.join(service.base_data_dir, target_file)

    metrics = service.analyze_file_metrics(filepath)
    records = service.read_and_parse_records(filepath, delimiter="|", expected_fields=expected_fields)
    deduped_records, duplicates_count = service.deduplicate_records(records, key_field=key_field)

    archived_path = None
    if archive_after and os.path.exists(filepath):
        archived_path = service.archive_file(filepath)

    result_summary = {
        "file_type": file_type,
        "original_file": target_file,
        "metrics": metrics,
        "total_records_parsed": len(records),
        "duplicates_removed": duplicates_count,
        "unique_records_count": len(deduped_records),
        "archived_destination": archived_path,
        "sample_records": deduped_records[:5],
    }
    return APIResponse(message=f"Processed and parsed {file_type} file successfully.", data=result_summary)


@router.get("/external-sync", response_model=APIResponse[Dict[str, Any]])
def external_api_health_check(
    override_url: str = Query(None, description="Optional URL to test error states or timeouts"),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
) -> APIResponse[Dict[str, Any]]:
    """Invokes external API integration via requests.

    Demonstrates handling of:
    - 200 OK
    - Timeout
    - Connection error
    - HTTP error
    - Malformed response
    """
    ext_service = ExternalAPIService()
    result = ext_service.fetch_time_sync(endpoint_url=override_url)
    return APIResponse(message="External API request evaluated.", data=result)

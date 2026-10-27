"""Unit Tests for File I/O and OS Processing."""

import os
import pytest
from app.services.file_service import FileProcessorService
from app.utils.exceptions import FileProcessingError


@pytest.fixture
def temp_file_service(tmp_path):
    """Fixture providing an isolated FileProcessorService with temporary directories."""
    data_dir = tmp_path / "data"
    archive_dir = tmp_path / "data" / "archive"
    service = FileProcessorService(
        base_data_dir=str(data_dir),
        archive_dir=str(archive_dir),
    )
    return service, str(data_dir), str(archive_dir)


def test_file_metrics_counting(temp_file_service):
    """Verify counting lines, words, characters, and byte sizes."""
    service, data_dir, _ = temp_file_service
    test_file = os.path.join(data_dir, "test_metrics.txt")

    content = "Hello world\nThis is line two\nThree words here\n"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)

    metrics = service.analyze_file_metrics(test_file)
    assert metrics["line_count"] == 3
    # "Hello world" (2) + "This is line two" (4) + "Three words here" (3) = 9 words
    assert metrics["word_count"] == 9
    assert metrics["char_count"] == len(content)


def test_read_and_deduplicate_records(temp_file_service):
    """Verify parsing pipe-delimited records and removing duplicate records."""
    service, data_dir, _ = temp_file_service
    test_file = os.path.join(data_dir, "test_dupes.txt")

    content = (
        "EMP-101|alice@company.com|Alice\n"
        "EMP-102|bob@company.com|Bob\n"
        "EMP-101|alice@company.com|Alice Duplicate\n"
    )
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)

    fields = ["user_id", "email", "name"]
    records = service.read_and_parse_records(test_file, delimiter="|", expected_fields=fields)
    assert len(records) == 3

    deduped, removed_count = service.deduplicate_records(records, key_field="user_id")
    assert len(deduped) == 2
    assert removed_count == 1
    assert deduped[0]["user_id"] == "EMP-101"
    assert deduped[1]["user_id"] == "EMP-102"


def test_archive_file_with_os(temp_file_service):
    """Verify moving/archiving file using os module."""
    service, data_dir, archive_dir = temp_file_service
    test_file = os.path.join(data_dir, "archive_me.txt")

    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Some data to archive")

    archived_path = service.archive_file(test_file)

    # Original file is gone
    assert not os.path.exists(test_file)
    # Archived file exists in archive folder
    assert os.path.exists(archived_path)
    assert archive_dir in archived_path


def test_nonexistent_file_exception(temp_file_service):
    """Verify FileProcessingError is raised for nonexistent file."""
    service, data_dir, _ = temp_file_service
    fake_path = os.path.join(data_dir, "does_not_exist.txt")

    with pytest.raises(FileProcessingError):
        service.analyze_file_metrics(fake_path)

"""File I/O and OS Module Processing Subsystem.

Demonstrates:
- Context manager `with open(...)` for safe file I/O (read, write, append)
- Text analysis: counting lines, words, characters
- Record parsing and schema transformation
- In-memory duplicate removal
- `os` module: directory creation, existence checks, directory listings, archiving/moving
- Custom exception handling (FileProcessingError)
"""

import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.utils.exceptions import FileProcessingError
from app.utils.logger import get_logger

logger = get_logger()


class FileProcessorService:
    """Service to process raw text files (employees.txt, assets.txt, tickets.txt)."""

    def __init__(self, base_data_dir: str = "data", archive_dir: str = "data/archive") -> None:
        self.base_data_dir = base_data_dir
        self.archive_dir = archive_dir
        # Ensure directories exist using os module
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create necessary data and archive directories using os.makedirs."""
        if not os.path.exists(self.base_data_dir):
            os.makedirs(self.base_data_dir, exist_ok=True)
            logger.info("Created base data directory: %s", self.base_data_dir)

        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir, exist_ok=True)
            logger.info("Created archive directory: %s", self.archive_dir)

    def analyze_file_metrics(self, filepath: str) -> Dict[str, Any]:
        """Calculates line count, word count, character count, and byte size.

        Demonstrates core file reading and string operations.
        """
        if not os.path.exists(filepath):
            raise FileProcessingError(filepath, "File does not exist.")

        line_count = 0
        word_count = 0
        char_count = 0

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                for line in file:
                    line_count += 1
                    char_count += len(line)
                    # Count words using string split
                    word_count += len(line.split())

            byte_size = os.path.getsize(filepath)

            return {
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "line_count": line_count,
                "word_count": word_count,
                "char_count": char_count,
                "byte_size": byte_size,
            }
        except (IOError, OSError) as exc:
            raise FileProcessingError(filepath, f"Failed to read file metrics: {exc}")

    def read_and_parse_records(
        self,
        filepath: str,
        delimiter: str = "|",
        expected_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Reads pipe-delimited records and converts each line into a mapped dictionary."""
        if not os.path.exists(filepath):
            raise FileProcessingError(filepath, "File does not exist on disk.")

        records: List[Dict[str, str]] = []
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, start=1):
                    cleaned = line.strip()
                    # Skip empty lines and comment lines
                    if not cleaned or cleaned.startswith("#"):
                        continue

                    parts = [p.strip() for p in cleaned.split(delimiter)]
                    if expected_fields:
                        if len(parts) != len(expected_fields):
                            logger.warning(
                                "Line %d in %s has %d columns, expected %d. Skipping.",
                                line_num,
                                filepath,
                                len(parts),
                                len(expected_fields),
                            )
                            continue
                        record_dict = dict(zip(expected_fields, parts))
                    else:
                        record_dict = {f"col_{i}": val for i, val in enumerate(parts)}

                    records.append(record_dict)

            return records
        except (IOError, OSError) as exc:
            raise FileProcessingError(filepath, f"Error parsing records: {exc}")

    def deduplicate_records(
        self, records: List[Dict[str, str]], key_field: str
    ) -> Tuple[List[Dict[str, str]], int]:
        """Removes duplicate records based on a unique key field while preserving order.

        Returns:
            Tuple of (deduplicated_list, duplicate_count)
        """
        seen_keys = set()
        deduped: List[Dict[str, str]] = []
        duplicates_removed = 0

        for record in records:
            unique_val = record.get(key_field)
            if unique_val is None:
                deduped.append(record)
                continue

            if unique_val in seen_keys:
                duplicates_removed += 1
            else:
                seen_keys.add(unique_val)
                deduped.append(record)

        return deduped, duplicates_removed

    def append_record(self, filepath: str, record_line: str) -> None:
        """Appends a new record line to the file."""
        try:
            with open(filepath, "a", encoding="utf-8") as file:
                file.write(record_line.rstrip() + "\n")
        except (IOError, OSError) as exc:
            raise FileProcessingError(filepath, f"Failed appending record: {exc}")

    def archive_file(self, filepath: str) -> str:
        """Moves and renames a processed file into the archive folder using the os module."""
        if not os.path.exists(filepath):
            raise FileProcessingError(filepath, "Cannot archive nonexistent file.")

        self._ensure_directories()
        base_name = os.path.basename(filepath)
        name, ext = os.path.splitext(base_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived_name = f"{name}_archived_{timestamp}{ext}"
        destination = os.path.join(self.archive_dir, archived_name)

        try:
            # Use os.replace / shutil.move for atomic move
            shutil.move(filepath, destination)
            logger.info("Archived file '%s' to '%s'", filepath, destination)
            return destination
        except (IOError, OSError) as exc:
            raise FileProcessingError(filepath, f"Failed archiving file: {exc}")

    def list_data_files(self) -> Dict[str, List[str]]:
        """Lists files in data directory and archive directory using os.listdir."""
        self._ensure_directories()
        active_files = [
            f for f in os.listdir(self.base_data_dir)
            if os.path.isfile(os.path.join(self.base_data_dir, f))
        ]
        archived_files = [
            f for f in os.listdir(self.archive_dir)
            if os.path.isfile(os.path.join(self.archive_dir, f))
        ]
        return {
            "active_files": active_files,
            "archived_files": archived_files,
        }

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_DOCX_UNZIPPED_BYTES = 200 * 1024 * 1024
MAX_DOCX_ENTRIES = 5000


@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None
    file_type: str | None = None
    size_bytes: int | None = None


REQUIRED_DOCX_PARTS = {"[Content_Types].xml", "word/document.xml"}


def validate_docx(path: Path) -> ValidationResult:
    if not path.exists() or not path.is_file():
        return ValidationResult(False, "file_not_found")
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        return ValidationResult(False, "file_too_large", "docx", size)
    with path.open("rb") as handle:
        magic = handle.read(2)
    if magic != b"PK":
        return ValidationResult(False, "invalid_magic", "docx", size)
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_DOCX_ENTRIES:
                return ValidationResult(False, "too_many_entries", "docx", size)
            total_uncompressed = sum(info.file_size for info in infos)
            if total_uncompressed > MAX_DOCX_UNZIPPED_BYTES:
                return ValidationResult(False, "uncompressed_limit", "docx", size)
            names = {info.filename for info in infos}
            if not REQUIRED_DOCX_PARTS.issubset(names):
                return ValidationResult(False, "missing_required_parts", "docx", size)
    except zipfile.BadZipFile:
        return ValidationResult(False, "invalid_zip", "docx", size)
    return ValidationResult(True, None, "docx", size)


def validate_txt(path: Path) -> ValidationResult:
    if not path.exists() or not path.is_file():
        return ValidationResult(False, "file_not_found")
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        return ValidationResult(False, "file_too_large", "txt", size)
    try:
        with path.open("rb") as handle:
            handle.read(4096)
    except OSError:
        return ValidationResult(False, "read_error", "txt", size)
    return ValidationResult(True, None, "txt", size)

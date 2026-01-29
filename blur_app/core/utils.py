from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str, max_length: int = 255) -> str:
    sanitized = SAFE_FILENAME_PATTERN.sub("_", name.strip())
    if not sanitized:
        sanitized = "file"
    return sanitized[:max_length]


def compute_sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def safe_write_atomic(target_path: Path, data: bytes) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(target_path.parent)) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name
    os.replace(temp_name, target_path)


def iter_chunks(data: bytes, chunk_size: int = 1024 * 1024) -> Iterable[bytes]:
    for idx in range(0, len(data), chunk_size):
        yield data[idx : idx + chunk_size]


def decode_text_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "cp1251", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def encode_text(text: str) -> bytes:
    return text.encode("utf-8")

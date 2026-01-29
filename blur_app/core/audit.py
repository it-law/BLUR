from __future__ import annotations

import getpass
import sqlite3
from pathlib import Path
from typing import Any

from .utils import now_utc_iso, sanitize_filename


SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    os_username TEXT NOT NULL,
    input_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    playbook_name TEXT NOT NULL,
    playbook_version TEXT NOT NULL,
    dry_run INTEGER NOT NULL,
    total_matches INTEGER NOT NULL,
    matches_by_category TEXT NOT NULL,
    sha256_input TEXT NOT NULL,
    sha256_output TEXT
);
"""


class AuditLogger:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(SCHEMA)

    def log(
        self,
        *,
        input_filename: str,
        file_type: str,
        playbook_name: str,
        playbook_version: str,
        dry_run: bool,
        total_matches: int,
        matches_by_category: dict[str, int],
        sha256_input: str,
        sha256_output: str | None,
    ) -> None:
        payload = (
            now_utc_iso(),
            getpass.getuser(),
            sanitize_filename(input_filename),
            file_type,
            playbook_name,
            playbook_version,
            1 if dry_run else 0,
            total_matches,
            str(matches_by_category),
            sha256_input,
            sha256_output,
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    timestamp_utc,
                    os_username,
                    input_filename,
                    file_type,
                    playbook_name,
                    playbook_version,
                    dry_run,
                    total_matches,
                    matches_by_category,
                    sha256_input,
                    sha256_output
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            conn.commit()

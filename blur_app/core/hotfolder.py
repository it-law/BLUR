from __future__ import annotations

import fnmatch
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .audit import AuditLogger
from .file_validation import validate_docx, validate_txt
from .playbooks import Playbook
from .processor_docx import process_docx
from .processor_txt import process_txt
from .utils import sanitize_filename


@dataclass
class HotFolderConfig:
    enabled: bool = False
    input_dir: Path | None = None
    output_dir: Path | None = None
    error_dir: Path | None = None
    processed_dir: Path | None = None
    selected_playbook: str | None = None
    file_types: tuple[str, ...] = ("docx", "txt")
    naming_scheme: str = "suffix"
    max_concurrency: int = 1
    stable_file_wait_ms: int = 1500
    ignore_patterns: tuple[str, ...] = ("~$*", "*.tmp", ".DS_Store")


@dataclass
class HotFolderStatus:
    last_processed: str | None = None
    success_count: int = 0
    failure_count: int = 0
    running: bool = False


class HotFolderManager:
    def __init__(
        self,
        config: HotFolderConfig,
        playbook_loader: Callable[[str], Playbook],
        audit_logger: AuditLogger,
        poll_interval: float = 1.0,
    ) -> None:
        self.config = config
        self.playbook_loader = playbook_loader
        self.audit_logger = audit_logger
        self.poll_interval = poll_interval
        self.status = HotFolderStatus()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.status.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.status.running = False

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.process_once()
            time.sleep(self.poll_interval)

    def process_once(self) -> None:
        if not self.config.enabled:
            return
        input_dir = self.config.input_dir
        output_dir = self.config.output_dir
        if not input_dir or not output_dir:
            return
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.config.error_dir:
            self.config.error_dir.mkdir(parents=True, exist_ok=True)
        if self.config.processed_dir:
            self.config.processed_dir.mkdir(parents=True, exist_ok=True)

        for path in sorted(input_dir.iterdir()):
            if not path.is_file():
                continue
            if self._is_ignored(path.name):
                continue
            if not _is_stable(path, self.config.stable_file_wait_ms):
                continue
            processing_path = _acquire_processing_lock(path)
            if not processing_path:
                continue
            try:
                self._process_file(processing_path, output_dir)
                self.status.success_count += 1
                self.status.last_processed = processing_path.name
                if self.config.processed_dir:
                    _move_file(processing_path, self.config.processed_dir / sanitize_filename(path.name))
                else:
                    _move_file(processing_path, input_dir / sanitize_filename(path.name))
            except Exception:
                self.status.failure_count += 1
                self.status.last_processed = processing_path.name
                if self.config.error_dir:
                    _move_file(processing_path, self.config.error_dir / sanitize_filename(path.name))
                else:
                    _move_file(processing_path, input_dir / sanitize_filename(path.name))

    def _process_file(self, path: Path, output_dir: Path) -> None:
        suffix = path.suffix.lower()
        playbook = self.playbook_loader(self.config.selected_playbook or "")
        if suffix == ".docx" and "docx" in self.config.file_types:
            validation = validate_docx(path)
            if validation.valid:
                process_docx(
                    input_path=path,
                    output_dir=output_dir,
                    playbook=playbook,
                    audit_logger=self.audit_logger,
                    dry_run=False,
                )
        elif suffix == ".txt" and "txt" in self.config.file_types:
            validation = validate_txt(path)
            if validation.valid:
                process_txt(
                    input_path=path,
                    output_dir=output_dir,
                    playbook=playbook,
                    audit_logger=self.audit_logger,
                    dry_run=False,
                )

    def _is_ignored(self, name: str) -> bool:
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.config.ignore_patterns)


def _is_stable(path: Path, wait_ms: int) -> bool:
    try:
        first_stat = path.stat()
    except OSError:
        return False
    time.sleep(wait_ms / 1000)
    try:
        second_stat = path.stat()
    except OSError:
        return False
    return first_stat.st_size == second_stat.st_size and first_stat.st_mtime == second_stat.st_mtime


def _acquire_processing_lock(path: Path) -> Path | None:
    processing_name = f".processing_{path.name}"
    processing_path = path.with_name(processing_name)
    try:
        os.replace(path, processing_path)
    except OSError:
        return None
    return processing_path


def _move_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dst)

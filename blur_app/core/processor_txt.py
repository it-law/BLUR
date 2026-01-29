from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .audit import AuditLogger
from .playbooks import Playbook
from .rules import RuleMatchReport, apply_rules
from .utils import compute_sha256_bytes, decode_text_bytes, encode_text, safe_write_atomic, sanitize_filename


@dataclass
class TextProcessResult:
    output_path: Path | None
    report: RuleMatchReport
    output_bytes: bytes | None


def process_txt(
    *,
    input_path: Path,
    output_dir: Path,
    playbook: Playbook,
    audit_logger: AuditLogger,
    dry_run: bool = False,
) -> TextProcessResult:
    input_bytes = input_path.read_bytes()
    text = decode_text_bytes(input_bytes)
    redacted_text, report = apply_rules(text, playbook, dry_run=dry_run)
    output_bytes = None
    output_path = None
    if not dry_run:
        output_bytes = encode_text(redacted_text)
        output_name = f"{sanitize_filename(input_path.stem)}_blurred{input_path.suffix}"
        output_path = output_dir / output_name
        safe_write_atomic(output_path, output_bytes)

    audit_logger.log(
        input_filename=input_path.name,
        file_type="txt",
        playbook_name=playbook.name,
        playbook_version=playbook.version,
        dry_run=dry_run,
        total_matches=report.total_matches,
        matches_by_category=report.matches_by_rule_type,
        sha256_input=compute_sha256_bytes(input_bytes),
        sha256_output=compute_sha256_bytes(output_bytes) if output_bytes else None,
    )
    return TextProcessResult(output_path, report, output_bytes)

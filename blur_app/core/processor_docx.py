from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from .audit import AuditLogger
from .cleaner_docx import clean_docx_parts
from .playbooks import Playbook
from .rules import RuleMatchReport, apply_rules
from .utils import compute_sha256_bytes, safe_write_atomic, sanitize_filename


WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": WORD_NAMESPACE}


@dataclass
class DocxProcessResult:
    output_path: Path | None
    report: RuleMatchReport
    output_bytes: bytes | None


def process_docx(
    *,
    input_path: Path,
    output_dir: Path,
    playbook: Playbook,
    audit_logger: AuditLogger,
    dry_run: bool = False,
) -> DocxProcessResult:
    input_bytes = input_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(input_bytes)) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    cleaned_parts = clean_docx_parts(parts)
    updated_parts, report = _apply_rules_to_parts(cleaned_parts, playbook, dry_run=dry_run)

    output_bytes = None
    output_path = None
    if not dry_run:
        output_stream = io.BytesIO()
        with zipfile.ZipFile(output_stream, "w", compression=zipfile.ZIP_DEFLATED) as output_zip:
            for name, data in updated_parts.items():
                output_zip.writestr(name, data)
        output_bytes = output_stream.getvalue()
        output_name = f"{sanitize_filename(input_path.stem)}_blurred{input_path.suffix}"
        output_path = output_dir / output_name
        safe_write_atomic(output_path, output_bytes)

    audit_logger.log(
        input_filename=input_path.name,
        file_type="docx",
        playbook_name=playbook.name,
        playbook_version=playbook.version,
        dry_run=dry_run,
        total_matches=report.total_matches,
        matches_by_category=report.matches_by_rule_type,
        sha256_input=compute_sha256_bytes(input_bytes),
        sha256_output=compute_sha256_bytes(output_bytes) if output_bytes else None,
    )

    return DocxProcessResult(output_path, report, output_bytes)


def _apply_rules_to_parts(
    parts: dict[str, bytes],
    playbook: Playbook,
    dry_run: bool,
) -> tuple[dict[str, bytes], RuleMatchReport]:
    updated_parts = dict(parts)
    aggregate = RuleMatchReport()
    for name, data in parts.items():
        if not name.startswith("word/") or not name.endswith(".xml"):
            continue
        try:
            tree = etree.fromstring(data)
        except etree.XMLSyntaxError:
            continue
        modified = False
        for text_node in tree.xpath(".//w:t", namespaces=NSMAP):
            if text_node.text is None:
                continue
            redacted_text, report = apply_rules(text_node.text, playbook, dry_run=dry_run)
            _merge_reports(aggregate, report)
            if not dry_run and redacted_text != text_node.text:
                text_node.text = redacted_text
                modified = True
        if modified:
            updated_parts[name] = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")
    return updated_parts, aggregate


def _merge_reports(target: RuleMatchReport, report: RuleMatchReport) -> None:
    target.total_matches += report.total_matches
    for key, value in report.matches_by_rule_type.items():
        target.matches_by_rule_type[key] = target.matches_by_rule_type.get(key, 0) + value
    for key, value in report.matches_by_rule_id.items():
        target.matches_by_rule_id[key] = target.matches_by_rule_id.get(key, 0) + value

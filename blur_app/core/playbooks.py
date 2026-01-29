from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


ALLOWED_PLAYBOOK_KEYS = {
    "name",
    "version",
    "updated_at",
    "updated_by",
    "description",
    "redaction_mode",
    "mask_char",
    "rules",
}

ALLOWED_RULE_KEYS = {
    "id",
    "name",
    "type",
    "enabled",
    "priority",
    "action",
    "replacement_template",
    "scope",
    "patterns",
    "phrases",
    "case_insensitive",
    "dictionary",
    "keywords",
}

RULE_TYPES = {
    "allowlist",
    "dictionary_entities",
    "regex_patterns",
    "keyword_list",
}

ACTIONS = {"MASK", "REPLACE", "REMOVE"}


@dataclass
class Rule:
    rule_id: str
    name: str
    rule_type: str
    enabled: bool = True
    priority: int = 100
    action: str = "MASK"
    replacement_template: str | None = None
    scope: list[str] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    dictionary: dict[str, str] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    case_insensitive: bool = False


@dataclass
class Playbook:
    name: str
    version: str
    redaction_mode: str = "FIXED_TOKEN"
    mask_char: str = "*"
    rules: list[Rule] = field(default_factory=list)
    description: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None


class PlaybookError(ValueError):
    pass


def _validate_keys(data: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = set(data.keys()) - allowed
    if unknown:
        raise PlaybookError(f"Unknown keys in {context}: {sorted(unknown)}")


def _parse_rule(raw: dict[str, Any]) -> Rule:
    _validate_keys(raw, ALLOWED_RULE_KEYS, "rule")
    rule_type = raw.get("type")
    if rule_type not in RULE_TYPES:
        raise PlaybookError(f"Invalid rule type: {rule_type}")
    action = raw.get("action", "MASK")
    if action not in ACTIONS:
        raise PlaybookError(f"Invalid action: {action}")
    return Rule(
        rule_id=str(raw.get("id")),
        name=str(raw.get("name")),
        rule_type=rule_type,
        enabled=bool(raw.get("enabled", True)),
        priority=int(raw.get("priority", 100)),
        action=action,
        replacement_template=raw.get("replacement_template"),
        scope=list(raw.get("scope", []) or []),
        patterns=list(raw.get("patterns", []) or []),
        phrases=list(raw.get("phrases", []) or []),
        dictionary=dict(raw.get("dictionary", {}) or {}),
        keywords=list(raw.get("keywords", []) or []),
        case_insensitive=bool(raw.get("case_insensitive", False)),
    )


def load_playbook(path: Path) -> Playbook:
    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    if not isinstance(data, dict):
        raise PlaybookError("Playbook must be a mapping")
    _validate_keys(data, ALLOWED_PLAYBOOK_KEYS, "playbook")
    name = data.get("name")
    version = data.get("version")
    if not name or not version:
        raise PlaybookError("Playbook requires name and version")
    rules_raw = data.get("rules", [])
    if not isinstance(rules_raw, list):
        raise PlaybookError("Rules must be a list")
    rules = [_parse_rule(rule) for rule in rules_raw]
    return Playbook(
        name=str(name),
        version=str(version),
        redaction_mode=str(data.get("redaction_mode", "FIXED_TOKEN")),
        mask_char=str(data.get("mask_char", "*")),
        rules=rules,
        description=data.get("description"),
        updated_at=data.get("updated_at"),
        updated_by=data.get("updated_by"),
    )


def list_playbooks(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.yaml"))

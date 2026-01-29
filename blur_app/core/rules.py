from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .playbooks import Playbook, Rule


PLACEHOLDER_PREFIX = "__BLUR_ALLOWLIST_"


@dataclass
class RuleMatchReport:
    total_matches: int = 0
    matches_by_rule_type: dict[str, int] = field(default_factory=dict)
    matches_by_rule_id: dict[str, int] = field(default_factory=dict)


def apply_rules(text: str, playbook: Playbook, dry_run: bool = False) -> tuple[str, RuleMatchReport]:
    report = RuleMatchReport()
    placeholders: dict[str, str] = {}

    allowlist_rules = _rules_by_type(playbook, "allowlist")
    protected_text = _apply_allowlist(text, allowlist_rules, placeholders)

    for rule_type in ("dictionary_entities", "regex_patterns", "keyword_list"):
        for rule in _rules_by_type(playbook, rule_type):
            protected_text = _apply_rule(
                protected_text,
                rule,
                playbook,
                report,
                dry_run=dry_run,
            )

    restored = protected_text
    for placeholder, original in placeholders.items():
        restored = restored.replace(placeholder, original)

    return restored, report


def _rules_by_type(playbook: Playbook, rule_type: str) -> list[Rule]:
    rules = [rule for rule in playbook.rules if rule.rule_type == rule_type and rule.enabled]
    return sorted(rules, key=lambda rule: rule.priority)


def _apply_allowlist(text: str, rules: Iterable[Rule], placeholders: dict[str, str]) -> str:
    protected = text
    counter = 0
    for rule in rules:
        for phrase in rule.phrases:
            counter += 1
            placeholder = f"{PLACEHOLDER_PREFIX}{counter}__"
            placeholders[placeholder] = phrase
            protected = protected.replace(phrase, placeholder)
        for pattern_entry in rule.patterns:
            pattern = pattern_entry.get("pattern")
            flags = 0
            if rule.case_insensitive or pattern_entry.get("case_insensitive"):
                flags |= re.IGNORECASE
            if not pattern:
                continue

            def _replacement(match: re.Match[str]) -> str:
                nonlocal counter
                counter += 1
                placeholder = f"{PLACEHOLDER_PREFIX}{counter}__"
                placeholders[placeholder] = match.group(0)
                return placeholder

            protected = re.sub(pattern, _replacement, protected, flags=flags)
    return protected


def _apply_rule(
    text: str,
    rule: Rule,
    playbook: Playbook,
    report: RuleMatchReport,
    dry_run: bool = False,
) -> str:
    if rule.rule_type == "dictionary_entities":
        return _apply_dictionary(text, rule, playbook, report, dry_run)
    if rule.rule_type == "regex_patterns":
        return _apply_regex_patterns(text, rule, playbook, report, dry_run)
    if rule.rule_type == "keyword_list":
        return _apply_keywords(text, rule, playbook, report, dry_run)
    return text


def _register_match(report: RuleMatchReport, rule: Rule, count: int) -> None:
    if count <= 0:
        return
    report.total_matches += count
    report.matches_by_rule_type[rule.rule_type] = report.matches_by_rule_type.get(rule.rule_type, 0) + count
    report.matches_by_rule_id[rule.rule_id] = report.matches_by_rule_id.get(rule.rule_id, 0) + count


def _replacement_for_match(match_text: str, rule: Rule, playbook: Playbook) -> str:
    if rule.action == "REMOVE":
        return ""
    if rule.action == "REPLACE":
        template = rule.replacement_template or "[BLURRED:{rule_name}]"
        return template.format(rule_name=rule.name, rule_id=rule.rule_id)
    if playbook.redaction_mode == "SAME_LENGTH_MASK":
        mask_char = playbook.mask_char or "*"
        return mask_char * len(match_text)
    return rule.replacement_template or "[BLURRED]"


def _apply_dictionary(
    text: str,
    rule: Rule,
    playbook: Playbook,
    report: RuleMatchReport,
    dry_run: bool,
) -> str:
    updated = text
    for target, replacement in rule.dictionary.items():
        if rule.case_insensitive:
            pattern = re.compile(re.escape(target), re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(target))
        matches = list(pattern.finditer(updated))
        if matches:
            _register_match(report, rule, len(matches))
            if dry_run:
                continue
            if rule.action == "REMOVE":
                updated = pattern.sub("", updated)
            elif rule.action == "REPLACE":
                updated = pattern.sub(replacement, updated)
            else:
                updated = pattern.sub(lambda m: _replacement_for_match(m.group(0), rule, playbook), updated)
    return updated


def _apply_regex_patterns(
    text: str,
    rule: Rule,
    playbook: Playbook,
    report: RuleMatchReport,
    dry_run: bool,
) -> str:
    updated = text
    for entry in rule.patterns:
        pattern = entry.get("pattern")
        if not pattern:
            continue
        flags = 0
        if rule.case_insensitive or entry.get("case_insensitive"):
            flags |= re.IGNORECASE
        compiled = re.compile(pattern, flags)
        matches = list(compiled.finditer(updated))
        if matches:
            _register_match(report, rule, len(matches))
            if dry_run:
                continue
            updated = compiled.sub(lambda m: _replacement_for_match(m.group(0), rule, playbook), updated)
    return updated


def _apply_keywords(
    text: str,
    rule: Rule,
    playbook: Playbook,
    report: RuleMatchReport,
    dry_run: bool,
) -> str:
    updated = text
    if not rule.keywords:
        return updated
    escaped = [re.escape(keyword) for keyword in rule.keywords]
    pattern = "|".join(escaped)
    flags = re.IGNORECASE if rule.case_insensitive else 0
    compiled = re.compile(pattern, flags)
    matches = list(compiled.finditer(updated))
    if matches:
        _register_match(report, rule, len(matches))
        if not dry_run:
            updated = compiled.sub(lambda m: _replacement_for_match(m.group(0), rule, playbook), updated)
    return updated

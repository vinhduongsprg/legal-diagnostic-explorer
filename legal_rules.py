"""Data model and loading helpers for the synthetic legal rules."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


VALID_ACTIONS = {
    "permit",
    "prohibit",
    "require_license",
    "require_registration",
    "require_inspection",
    "restrict",
}
VALID_SCOPES = {"local", "national", "temporary", "permanent"}
RULE_FIELDS = ("id", "authority", "subject", "condition", "action", "scope")


@dataclass(frozen=True)
class Rule:
    id: str
    authority: str
    subject: str
    condition: str
    action: str
    scope: str


@dataclass(frozen=True)
class CoverageCase:
    subject: str
    condition: str


def _require_text_fields(record: Any, fields: tuple[str, ...], label: str) -> None:
    if not isinstance(record, dict):
        raise ValueError(f"{label} must be a JSON object.")

    unexpected_fields = set(record) - set(fields)
    if unexpected_fields:
        names = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"{label} has unexpected field(s): {names}.")

    for field in fields:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must have a non-empty string '{field}'.")


def load_dataset(
    path: Path | None = None,
) -> tuple[list[Rule], list[CoverageCase]]:
    """Load rules and the predefined subject/condition cases used for gap checks."""
    dataset_path = path or Path(__file__).parent / "data" / "synthetic_rules.json"
    with dataset_path.open(encoding="utf-8") as dataset_file:
        data = json.load(dataset_file)

    if not isinstance(data, dict):
        raise ValueError("The dataset root must be a JSON object.")

    raw_rules = data.get("rules")
    raw_cases = data.get("coverage_cases")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ValueError("The dataset must contain a non-empty 'rules' list.")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("The dataset must contain a non-empty 'coverage_cases' list.")

    rules: list[Rule] = []
    for index, record in enumerate(raw_rules, start=1):
        label = f"Rule at index {index}"
        _require_text_fields(record, RULE_FIELDS, label)
        rules.append(Rule(**{field: record[field] for field in RULE_FIELDS}))

    coverage_cases: list[CoverageCase] = []
    for index, record in enumerate(raw_cases, start=1):
        label = f"Coverage case at index {index}"
        fields = ("subject", "condition")
        _require_text_fields(record, fields, label)
        coverage_cases.append(CoverageCase(**{field: record[field] for field in fields}))

    return rules, coverage_cases


def validate_dataset(
    rules: Iterable[Rule], coverage_cases: Iterable[CoverageCase]
) -> list[str]:
    """Return all structural and vocabulary problems found in the loaded dataset."""
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, rule in enumerate(rules, start=1):
        for field in RULE_FIELDS:
            value = getattr(rule, field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Rule at index {index} has an empty or invalid '{field}'.")

        if rule.id in seen_ids:
            errors.append(f"Duplicate rule ID: {rule.id}.")
        seen_ids.add(rule.id)

        if rule.action not in VALID_ACTIONS:
            errors.append(f"Rule {rule.id} has unsupported action '{rule.action}'.")
        if rule.scope not in VALID_SCOPES:
            errors.append(f"Rule {rule.id} has unsupported scope '{rule.scope}'.")

    seen_cases: set[tuple[str, str]] = set()
    for case in coverage_cases:
        key = (case.subject, case.condition)
        if not case.subject.strip() or not case.condition.strip():
            errors.append("Coverage cases must have non-empty subjects and conditions.")
        if key in seen_cases:
            errors.append(
                f"Duplicate coverage case: {case.subject} + {case.condition}."
            )
        seen_cases.add(key)

    return errors

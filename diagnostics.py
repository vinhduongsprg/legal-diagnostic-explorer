"""Structural diagnostics for a deliberately simplified, synthetic rule system."""

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from legal_rules import CoverageCase, Rule


INCOMPATIBLE_ACTION_PAIRS = {
    frozenset(("permit", "prohibit")),
}


@dataclass(frozen=True)
class RulePairFinding:
    rule_a: str
    rule_b: str
    subject: str
    condition: str
    action_a: str
    action_b: str
    authority_a: str
    authority_b: str


@dataclass(frozen=True)
class PotentialGap:
    subject: str
    condition: str


@dataclass(frozen=True)
class AuthorityInteraction:
    authority_a: str
    authority_b: str
    overlaps: int
    conflicts: int
    shared_subjects: tuple[str, ...]


@dataclass(frozen=True)
class AuthoritySummary:
    authority: str
    subjects_regulated: int
    overlap_interactions: int
    conflict_interactions: int


def find_overlaps(rules: Iterable[Rule]) -> list[RulePairFinding]:
    """Find rule pairs sharing a subject and exact condition.

    Scope is retained in each rule but deliberately not interpreted in this
    first-pass comparison; a shared subject and condition are only a signal
    for review, not a conclusion that the rules are inconsistent.
    """
    findings: list[RulePairFinding] = []
    for rule_a, rule_b in combinations(rules, 2):
        if (rule_a.subject, rule_a.condition) != (rule_b.subject, rule_b.condition):
            continue
        findings.append(
            RulePairFinding(
                rule_a=rule_a.id,
                rule_b=rule_b.id,
                subject=rule_a.subject,
                condition=rule_a.condition,
                action_a=rule_a.action,
                action_b=rule_b.action,
                authority_a=rule_a.authority,
                authority_b=rule_b.authority,
            )
        )
    return findings


def find_potential_conflicts(
    overlaps: Iterable[RulePairFinding],
) -> list[RulePairFinding]:
    """Flag shared-subject/condition pairs with explicitly incompatible actions."""
    return [
        finding
        for finding in overlaps
        if frozenset((finding.action_a, finding.action_b)) in INCOMPATIBLE_ACTION_PAIRS
    ]


def find_potential_gaps(
    rules: Iterable[Rule], coverage_cases: Iterable[CoverageCase]
) -> list[PotentialGap]:
    """Find predefined subject/condition cases with no modeled rule."""
    covered_cases = {(rule.subject, rule.condition) for rule in rules}
    return [
        PotentialGap(case.subject, case.condition)
        for case in coverage_cases
        if (case.subject, case.condition) not in covered_cases
    ]


def analyze_authorities(
    rules: Iterable[Rule],
    overlaps: Iterable[RulePairFinding],
    conflicts: Iterable[RulePairFinding],
) -> tuple[list[AuthoritySummary], list[AuthorityInteraction]]:
    """Summarize subject coverage and cross-authority rule relationships."""
    rules = list(rules)
    overlaps = list(overlaps)
    conflict_ids = {(finding.rule_a, finding.rule_b) for finding in conflicts}

    subjects_by_authority: dict[str, set[str]] = defaultdict(set)
    for rule in rules:
        subjects_by_authority[rule.authority].add(rule.subject)

    interaction_counts: dict[tuple[str, str], dict[str, set]] = defaultdict(
        lambda: {"overlaps": set(), "conflicts": set(), "subjects": set()}
    )
    for finding in overlaps:
        if finding.authority_a == finding.authority_b:
            continue
        pair = tuple(sorted((finding.authority_a, finding.authority_b)))
        counts = interaction_counts[pair]
        rule_pair = (finding.rule_a, finding.rule_b)
        counts["overlaps"].add(rule_pair)
        counts["subjects"].add(finding.subject)
        if rule_pair in conflict_ids:
            counts["conflicts"].add(rule_pair)

    interactions = [
        AuthorityInteraction(
            authority_a=pair[0],
            authority_b=pair[1],
            overlaps=len(counts["overlaps"]),
            conflicts=len(counts["conflicts"]),
            shared_subjects=tuple(sorted(counts["subjects"])),
        )
        for pair, counts in sorted(interaction_counts.items())
    ]

    overlap_count_by_authority: dict[str, int] = defaultdict(int)
    conflict_count_by_authority: dict[str, int] = defaultdict(int)
    for interaction in interactions:
        overlap_count_by_authority[interaction.authority_a] += interaction.overlaps
        overlap_count_by_authority[interaction.authority_b] += interaction.overlaps
        conflict_count_by_authority[interaction.authority_a] += interaction.conflicts
        conflict_count_by_authority[interaction.authority_b] += interaction.conflicts

    summaries = [
        AuthoritySummary(
            authority=authority,
            subjects_regulated=len(subjects),
            overlap_interactions=overlap_count_by_authority[authority],
            conflict_interactions=conflict_count_by_authority[authority],
        )
        for authority, subjects in sorted(subjects_by_authority.items())
    ]
    return summaries, interactions

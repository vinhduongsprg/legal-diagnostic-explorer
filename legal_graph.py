"""NetworkX representation of the synthetic legal system."""

import networkx as nx

from diagnostics import RulePairFinding
from legal_rules import Rule


def build_legal_graph(
    rules: list[Rule], overlaps: list[RulePairFinding], conflicts: list[RulePairFinding]
) -> nx.MultiDiGraph:
    """Build a typed graph of authorities, rules, subjects, and diagnostics."""
    graph = nx.MultiDiGraph()

    for rule in rules:
        authority_node = f"authority::{rule.authority}"
        rule_node = f"rule::{rule.id}"
        subject_node = f"subject::{rule.subject}"

        graph.add_node(
            authority_node, kind="authority", label=rule.authority
        )
        graph.add_node(
            rule_node,
            kind="rule",
            label=f"{rule.id}\n{rule.action}",
            rule_id=rule.id,
            condition=rule.condition,
            scope=rule.scope,
        )
        graph.add_node(subject_node, kind="subject", label=rule.subject)
        graph.add_edge(authority_node, rule_node, relation="creates")
        graph.add_edge(rule_node, subject_node, relation="regulates")

    for finding in overlaps:
        graph.add_edge(
            f"rule::{finding.rule_a}",
            f"rule::{finding.rule_b}",
            relation="overlaps",
            subject=finding.subject,
            condition=finding.condition,
        )

    for finding in conflicts:
        graph.add_edge(
            f"rule::{finding.rule_a}",
            f"rule::{finding.rule_b}",
            relation="potentially_conflicts_with",
            subject=finding.subject,
            condition=finding.condition,
        )

    return graph

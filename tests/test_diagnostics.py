import unittest
from dataclasses import replace
from pathlib import Path

from diagnostics import (
    analyze_authorities,
    find_overlaps,
    find_potential_conflicts,
    find_potential_gaps,
)
from legal_graph import build_legal_graph
from legal_rules import load_dataset, validate_dataset


class SyntheticDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules, cls.coverage_cases = load_dataset()
        cls.overlaps = find_overlaps(cls.rules)
        cls.conflicts = find_potential_conflicts(cls.overlaps)
        cls.gaps = find_potential_gaps(cls.rules, cls.coverage_cases)

    def test_dataset_is_valid_and_has_expected_size(self) -> None:
        self.assertEqual(validate_dataset(self.rules, self.coverage_cases), [])
        self.assertEqual(len(self.rules), 24)

    def test_validation_reports_duplicate_ids_and_invalid_vocabulary(self) -> None:
        malformed_rule = replace(self.rules[0], action="advise")
        errors = validate_dataset(
            [self.rules[0], malformed_rule], self.coverage_cases
        )
        self.assertTrue(any("Duplicate rule ID" in error for error in errors))
        self.assertTrue(any("unsupported action" in error for error in errors))

    def test_known_overlap_is_detected_without_becoming_a_conflict(self) -> None:
        overlap_pairs = {(item.rule_a, item.rule_b) for item in self.overlaps}
        conflict_pairs = {(item.rule_a, item.rule_b) for item in self.conflicts}
        self.assertIn(("R01", "R14"), overlap_pairs)
        self.assertNotIn(("R01", "R14"), conflict_pairs)

    def test_known_potential_conflict_is_detected(self) -> None:
        conflict_pairs = {(item.rule_a, item.rule_b) for item in self.conflicts}
        self.assertIn(("R03", "R17"), conflict_pairs)

    def test_known_gap_is_detected(self) -> None:
        gap_cases = {(item.subject, item.condition) for item in self.gaps}
        self.assertIn(("restaurant", "unregistered"), gap_cases)

    def test_synthetic_diagnostic_totals_are_stable(self) -> None:
        self.assertEqual(len(self.overlaps), 17)
        self.assertEqual(len(self.conflicts), 1)
        self.assertEqual(len(self.gaps), 4)

    def test_authority_interactions_include_cross_authority_conflict(self) -> None:
        summaries, interactions = analyze_authorities(
            self.rules, self.overlaps, self.conflicts
        )
        municipal_safety = next(
            item
            for item in interactions
            if item.authority_a == "Municipal Regulation"
            and item.authority_b == "Public Safety Regulation"
        )
        self.assertGreater(municipal_safety.overlaps, 0)
        self.assertEqual(municipal_safety.conflicts, 1)
        self.assertTrue(summaries)

    def test_graph_contains_expected_entities_and_relationships(self) -> None:
        graph = build_legal_graph(self.rules, self.overlaps, self.conflicts)
        self.assertEqual(
            sum(data["kind"] == "authority" for _, data in graph.nodes(data=True)),
            5,
        )
        self.assertEqual(
            sum(data["kind"] == "rule" for _, data in graph.nodes(data=True)),
            24,
        )
        self.assertEqual(
            sum(data["kind"] == "subject" for _, data in graph.nodes(data=True)),
            10,
        )
        relations = {data["relation"] for _, _, data in graph.edges(data=True)}
        self.assertEqual(
            relations,
            {"creates", "regulates", "overlaps", "potentially_conflicts_with"},
        )


if __name__ == "__main__":
    unittest.main()

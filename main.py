"""Run diagnostics and generate visual summaries of the synthetic system."""

from collections import Counter
from pathlib import Path

from diagnostics import (
    analyze_authorities,
    find_overlaps,
    find_potential_conflicts,
    find_potential_gaps,
)
from legal_graph import build_legal_graph
from legal_rules import load_dataset, validate_dataset
from visualization import (
    create_authority_interactions,
    create_diagnostic_summary,
    create_legal_system_graph,
)


def main() -> None:
    rules, coverage_cases = load_dataset()
    errors = validate_dataset(rules, coverage_cases)
    if errors:
        raise ValueError("Dataset validation failed:\n" + "\n".join(errors))

    overlaps = find_overlaps(rules)
    conflicts = find_potential_conflicts(overlaps)
    gaps = find_potential_gaps(rules, coverage_cases)
    authority_summaries, authority_interactions = analyze_authorities(
        rules, overlaps, conflicts
    )
    graph = build_legal_graph(rules, overlaps, conflicts)

    results_dir = Path(__file__).parent / "results"
    create_legal_system_graph(graph, rules, results_dir / "legal_system_graph.png")
    create_diagnostic_summary(
        overlaps, conflicts, len(gaps), results_dir / "diagnostic_summary.png"
    )
    create_authority_interactions(
        [summary.authority for summary in authority_summaries],
        authority_interactions,
        results_dir / "authority_interactions.png",
    )

    print("=" * 72)
    print("COMPUTATIONAL LEGAL DIAGNOSTIC - SYNTHETIC DATA")
    print("=" * 72)
    print(f"Rules analyzed:       {len(rules)}")
    print(f"Authorities:           {len(authority_summaries)}")
    subject_counts = Counter(rule.subject for rule in rules)
    print(f"Subjects:              {len(subject_counts)}")
    most_regulated_count = max(subject_counts.values())
    most_regulated_subjects = sorted(
        subject
        for subject, count in subject_counts.items()
        if count == most_regulated_count
    )
    print(
        f"Most regulated subject(s): {', '.join(most_regulated_subjects)} "
        f"({most_regulated_count} rules each)"
    )
    print(f"Potential overlaps:    {len(overlaps)}")
    print(f"Potential conflicts:   {len(conflicts)}")
    print(f"Potential gaps:        {len(gaps)}")
    print()
    print("NOTE: These diagnostics identify structural patterns in synthetic")
    print("norms. They do not establish legal conclusions; human interpretation")
    print("and review are required.")
    print(f"\nVisualizations saved in: {results_dir}")

    print("\nPOTENTIAL OVERLAPS")
    for finding in overlaps:
        print(
            f"{finding.rule_a} <-> {finding.rule_b} | "
            f"{finding.subject} + {finding.condition} | "
            f"{finding.action_a} / {finding.action_b}"
        )

    print("\nPOTENTIAL CONFLICTS")
    for finding in conflicts:
        print(
            f"{finding.rule_a} <-> {finding.rule_b} | "
            f"{finding.subject} + {finding.condition} | "
            f"{finding.action_a} / {finding.action_b}"
        )

    print("\nPOTENTIAL GAPS IN THE MODELED SYSTEM")
    for gap in gaps:
        print(f"{gap.subject} + {gap.condition} | no modeled rule applies")

    print("\nAUTHORITY COVERAGE")
    most_subjects = max(summary.subjects_regulated for summary in authority_summaries)
    for summary in authority_summaries:
        marker = " (most subjects)" if summary.subjects_regulated == most_subjects else ""
        print(
            f"{summary.authority}: {summary.subjects_regulated} subjects; "
            f"{summary.overlap_interactions} cross-authority overlaps; "
            f"{summary.conflict_interactions} potential conflicts{marker}"
        )

    print("\nAUTHORITY INTERACTIONS")
    for interaction in authority_interactions:
        print(
            f"{interaction.authority_a} <-> {interaction.authority_b}: "
            f"{interaction.overlaps} overlap(s), "
            f"{interaction.conflicts} potential conflict(s)"
        )

    if authority_interactions:
        most_interactive_pair = max(
            authority_interactions,
            key=lambda interaction: (interaction.overlaps, interaction.conflicts),
        )
        print(
            "\nAuthority pair with most interactions: "
            f"{most_interactive_pair.authority_a} <-> "
            f"{most_interactive_pair.authority_b} "
            f"({most_interactive_pair.overlaps} overlap(s))"
        )

    if authority_interactions:
        partners_by_authority: dict[str, set[str]] = {}
        for interaction in authority_interactions:
            partners_by_authority.setdefault(interaction.authority_a, set()).add(
                interaction.authority_b
            )
            partners_by_authority.setdefault(interaction.authority_b, set()).add(
                interaction.authority_a
            )
        most_connected_authority, partners = max(
            partners_by_authority.items(), key=lambda item: len(item[1])
        )
        print(
            "Most connected authority by distinct authority relationships: "
            f"{most_connected_authority} ({len(partners)} partner(s))"
        )


if __name__ == "__main__":
    main()

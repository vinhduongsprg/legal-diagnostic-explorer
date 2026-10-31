"""Create reproducible visual summaries of the synthetic diagnostic results."""

from collections import defaultdict
from pathlib import Path
from textwrap import fill

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from diagnostics import AuthorityInteraction, RulePairFinding
from legal_rules import Rule


AUTHORITY_COLOR = "#315C8A"
RULE_COLOR = "#E8B44A"
SUBJECT_COLOR = "#78A88A"
OVERLAP_COLOR = "#D28B2C"
CONFLICT_COLOR = "#B64242"
NEUTRAL_COLOR = "#AAB4BF"


def _graph_positions(
    rules: list[Rule], authorities: list[str], subjects: list[str]
) -> dict[str, tuple[float, float]]:
    ordered_rules = sorted(rules, key=lambda rule: (rule.authority, rule.id))
    row_by_rule = {
        rule.id: len(ordered_rules) - index - 1
        for index, rule in enumerate(ordered_rules)
    }
    rows_by_authority: dict[str, list[int]] = defaultdict(list)
    for rule in ordered_rules:
        rows_by_authority[rule.authority].append(row_by_rule[rule.id])

    positions: dict[str, tuple[float, float]] = {
        f"authority::{authority}": (
            0.0,
            sum(rows) / len(rows),
        )
        for authority, rows in rows_by_authority.items()
    }
    positions.update(
        {
            f"rule::{rule.id}": (1.6, row_by_rule[rule.id])
            for rule in ordered_rules
        }
    )
    positions.update(
        {
            f"subject::{subject}": (
                3.2,
                (len(subjects) - index - 1)
                * (len(ordered_rules) - 1)
                / max(1, len(subjects) - 1),
            )
            for index, subject in enumerate(sorted(subjects))
        }
    )
    return positions


def create_legal_system_graph(
    graph: nx.MultiDiGraph, rules: list[Rule], output_path: Path
) -> None:
    """Render a three-layer authority/rule/subject graph with diagnostic links."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    authorities = sorted(
        label
        for _, data in graph.nodes(data=True)
        if data["kind"] == "authority"
        for label in [data["label"]]
    )
    subjects = sorted(
        label
        for _, data in graph.nodes(data=True)
        if data["kind"] == "subject"
        for label in [data["label"]]
    )
    positions = _graph_positions(rules, authorities, subjects)
    fig, ax = plt.subplots(figsize=(15, max(11, len(rules) * 0.48)))
    ax.set_title("Synthetic Legal System: Authorities, Rules, and Subjects", fontsize=17)

    authority_nodes = [
        node for node, data in graph.nodes(data=True) if data["kind"] == "authority"
    ]
    rule_nodes = [node for node, data in graph.nodes(data=True) if data["kind"] == "rule"]
    subject_nodes = [
        node for node, data in graph.nodes(data=True) if data["kind"] == "subject"
    ]
    create_edges = [
        (source, target)
        for source, target, data in graph.edges(data=True)
        if data["relation"] == "creates"
    ]
    regulate_edges = [
        (source, target)
        for source, target, data in graph.edges(data=True)
        if data["relation"] == "regulates"
    ]
    overlap_edges = [
        (source, target)
        for source, target, data in graph.edges(data=True)
        if data["relation"] == "overlaps"
    ]
    conflict_edges = [
        (source, target)
        for source, target, data in graph.edges(data=True)
        if data["relation"] == "potentially_conflicts_with"
    ]

    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=create_edges,
        ax=ax,
        edge_color=NEUTRAL_COLOR,
        arrows=True,
        arrowsize=12,
        width=1.0,
        alpha=0.65,
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=regulate_edges,
        ax=ax,
        edge_color=NEUTRAL_COLOR,
        arrows=True,
        arrowsize=12,
        width=1.0,
        alpha=0.65,
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=overlap_edges,
        ax=ax,
        edge_color=OVERLAP_COLOR,
        style="dashed",
        arrows=True,
        arrowstyle="-",
        arrowsize=8,
        width=1.2,
        alpha=0.48,
        connectionstyle="arc3,rad=0.18",
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=conflict_edges,
        ax=ax,
        edge_color=CONFLICT_COLOR,
        style="solid",
        arrows=True,
        arrowstyle="-",
        arrowsize=8,
        width=3.0,
        alpha=0.95,
        connectionstyle="arc3,rad=-0.2",
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=authority_nodes,
        node_shape="o",
        node_color=AUTHORITY_COLOR,
        node_size=1750,
        ax=ax,
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=rule_nodes,
        node_shape="s",
        node_color=RULE_COLOR,
        node_size=480,
        ax=ax,
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=subject_nodes,
        node_shape="D",
        node_color=SUBJECT_COLOR,
        node_size=1350,
        ax=ax,
    )
    nx.draw_networkx_labels(
        graph,
        positions,
        labels={
            node: data.get("rule_id", data["label"])
            for node, data in graph.nodes(data=True)
        },
        font_size=8,
        font_weight="normal",
        ax=ax,
    )

    legend = [
        Patch(facecolor=AUTHORITY_COLOR, label="Authority"),
        Patch(facecolor=RULE_COLOR, label="Rule"),
        Patch(facecolor=SUBJECT_COLOR, label="Subject"),
        Line2D([0], [0], color=NEUTRAL_COLOR, label="Creates / regulates"),
        Line2D([0], [0], color=OVERLAP_COLOR, linestyle="--", label="Potential overlap"),
        Line2D([0], [0], color=CONFLICT_COLOR, linewidth=3, label="Potential conflict"),
    ]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=3)
    ax.text(
        0.5,
        -0.17,
        "Rule labels are IDs; diagnostic links are structural signals, not legal conclusions.",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color="#4F5964",
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_diagnostic_summary(
    overlaps: list[RulePairFinding],
    conflicts: list[RulePairFinding],
    gap_count: int,
    output_path: Path,
) -> None:
    """Render the counts of overlaps, potential conflicts, and modeled gaps."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels = ["Potential overlaps", "Potential conflicts", "Potential gaps"]
    values = [len(overlaps), len(conflicts), gap_count]
    colors = [OVERLAP_COLOR, CONFLICT_COLOR, SUBJECT_COLOR]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.barh(labels, values, color=colors, height=0.58)
    ax.invert_yaxis()
    ax.set_xlabel("Number of findings")
    ax.set_title("Diagnostic Summary (Synthetic Model)")
    ax.set_xlim(0, max(values, default=0) + 2)
    ax.grid(axis="x", alpha=0.22)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values):
        ax.text(value + 0.2, bar.get_y() + bar.get_height() / 2, str(value), va="center")
    fig.text(
        0.5,
        0.01,
        "Gaps are absent subject/condition cases from a predefined checklist.",
        ha="center",
        fontsize=9,
        color="#4F5964",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_authority_interactions(
    authorities: list[str],
    interactions: list[AuthorityInteraction],
    output_path: Path,
) -> None:
    """Render cross-authority overlaps and potential conflicts as a small network."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph = nx.Graph()
    graph.add_nodes_from(authorities)
    for interaction in interactions:
        graph.add_edge(
            interaction.authority_a,
            interaction.authority_b,
            overlaps=interaction.overlaps,
            conflicts=interaction.conflicts,
        )

    positions = nx.circular_layout(graph)
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_title("Cross-Authority Interactions in the Synthetic Model", fontsize=14)
    nx.draw_networkx_nodes(
        graph,
        positions,
        node_color=AUTHORITY_COLOR,
        node_size=5000,
        ax=ax,
    )
    wrapped_labels = {
        authority: fill(authority, width=14) for authority in authorities
    }
    nx.draw_networkx_labels(
        graph,
        positions,
        labels=wrapped_labels,
        font_color="white",
        font_size=7.2,
        font_weight="bold",
        ax=ax,
    )

    for source, target, data in graph.edges(data=True):
        conflict = data["conflicts"] > 0
        nx.draw_networkx_edges(
            graph,
            positions,
            edgelist=[(source, target)],
            edge_color=CONFLICT_COLOR if conflict else OVERLAP_COLOR,
            width=1.5 + min(data["overlaps"], 8) * 0.55,
            style="solid" if conflict else "dashed",
            ax=ax,
        )
        midpoint = (
            (positions[source][0] + positions[target][0]) / 2,
            (positions[source][1] + positions[target][1]) / 2,
        )
        ax.text(
            midpoint[0],
            midpoint[1],
            f"{data['overlaps']} overlap(s)\n{data['conflicts']} conflict(s)",
            ha="center",
            va="center",
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.9},
        )

    ax.legend(
        handles=[
            Line2D([0], [0], color=OVERLAP_COLOR, linestyle="--", label="Overlap only"),
            Line2D([0], [0], color=CONFLICT_COLOR, label="Includes potential conflict"),
        ],
        loc="lower right",
        bbox_to_anchor=(0.98, 0.03),
        ncol=1,
    )
    ax.text(
        0.5,
        -0.12,
        "Line width reflects overlap count; labels show overlap and conflict counts.",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color="#4F5964",
    )
    ax.margins(0.25)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

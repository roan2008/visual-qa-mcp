from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from .chart_generator import write_json
from .flowchart_generator import DEFAULT_WIDTH, render_flowchart_diagram

RED = [214, 48, 49]
BLUE = [9, 132, 227]
ORANGE = [230, 126, 34]
GREEN = [0, 148, 50]
PURPLE = [142, 68, 173]

NODE_SIZE = [140, 80]
CENTER_X = DEFAULT_WIDTH / 2

FLOWCHART_CHECKS: list[dict[str, Any]] = [
    {
        "id": "node-count-matches",
        "type": "node_count_matches",
        "severity": "high",
        "description": "The number of detected nodes should match the declared nodes.",
    },
    {
        "id": "required-nodes-present",
        "type": "required_nodes_present",
        "severity": "critical",
        "description": "Every required node must be present with its declared color identity.",
        "params": {"color_match_distance": 60.0},
    },
    {
        "id": "node-shape-correct",
        "type": "node_shape_correct",
        "severity": "critical",
        "description": "Each node must render with its declared shape (rectangle or diamond).",
        "params": {"color_match_distance": 60.0},
    },
]

LABEL_CHECK: dict[str, Any] = {
    "id": "node-label-correct",
    "type": "node_label_correct",
    "severity": "high",
    "description": "Each labeled node's decoded text must match its declared label.",
    "params": {"color_match_distance": 60.0},
}

CONNECTOR_CHECK: dict[str, Any] = {
    "id": "connector-links-correct",
    "type": "connector_links_correct",
    "severity": "critical",
    "description": "Every declared directed connector must be found in the rendered arrow evidence.",
    "params": {"color_match_distance": 60.0},
}


def _five_node_chain() -> list[dict[str, Any]]:
    y_centers = [80, 220, 360, 500, 640]
    return [
        {"id": "start", "name": "Start", "shape": "rectangle", "rgb": RED, "label_text": "Start", "y": y_centers[0]},
        {"id": "input", "name": "Input", "shape": "rectangle", "rgb": BLUE, "label_text": "Input", "y": y_centers[1]},
        {"id": "decision", "name": "Decision", "shape": "diamond", "rgb": ORANGE, "label_text": "Decision", "y": y_centers[2]},
        {"id": "process", "name": "Process", "shape": "rectangle", "rgb": GREEN, "label_text": "Process", "y": y_centers[3]},
        {"id": "end", "name": "End", "shape": "rectangle", "rgb": PURPLE, "label_text": "End", "y": y_centers[4]},
    ]


def _five_node_edges() -> list[tuple[str, str]]:
    return [("start", "input"), ("input", "decision"), ("decision", "process"), ("process", "end")]


BRANCH_WIDTH = 620
BRANCH_CENTER_X = BRANCH_WIDTH / 2


def _branching_diagram() -> list[dict[str, Any]]:
    return [
        {"id": "start", "name": "Start", "shape": "rectangle", "rgb": RED, "label_text": "Start", "x": BRANCH_CENTER_X, "y": 90},
        {"id": "decision", "name": "Decision", "shape": "diamond", "rgb": ORANGE, "label_text": "Decision", "x": BRANCH_CENTER_X, "y": 320},
        {"id": "left", "name": "Left branch", "shape": "rectangle", "rgb": GREEN, "label_text": "Output", "x": BRANCH_CENTER_X - 140, "y": 590},
        {"id": "right", "name": "Right branch", "shape": "rectangle", "rgb": PURPLE, "label_text": "End", "x": BRANCH_CENTER_X + 140, "y": 590},
    ]


def _branching_edges() -> list[tuple[str, str]]:
    return [("start", "decision"), ("decision", "left"), ("decision", "right")]


def _three_node_chain() -> list[dict[str, Any]]:
    y_centers = [110, 360, 610]
    return [
        {"id": "start", "name": "Start", "shape": "rectangle", "rgb": RED, "y": y_centers[0]},
        {"id": "decision", "name": "Decision", "shape": "diamond", "rgb": ORANGE, "y": y_centers[1]},
        {"id": "end", "name": "End", "shape": "rectangle", "rgb": PURPLE, "y": y_centers[2]},
    ]


def _spec_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spec_nodes = []
    for node in nodes:
        entry = {"id": node["id"], "name": node["name"], "rgb": node["rgb"], "shape": node["shape"]}
        if node.get("label_text"):
            entry["label_text"] = node["label_text"]
        spec_nodes.append(entry)
    return spec_nodes


def _render_nodes(
    nodes: list[dict[str, Any]],
    node_overrides: dict[str, dict[str, Any]] | None = None,
    drop_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    overrides = node_overrides or {}
    drop = set(drop_ids or [])
    rendered = []
    for node in nodes:
        if node["id"] in drop:
            continue
        item = {
            "id": node["id"],
            "shape": node["shape"],
            "rgb": node["rgb"],
            "center_px": [node.get("x", CENTER_X), node["y"]],
            "size_px": NODE_SIZE,
        }
        if node.get("label_text"):
            item["label_text"] = node["label_text"]
        item.update(overrides.get(node["id"], {}))
        rendered.append(item)
    return rendered


def _base_spec(
    case_id: str,
    nodes: list[dict[str, Any]],
    edges: list[tuple[str, str]] | None,
    include_label_check: bool,
) -> dict[str, Any]:
    source_reference: dict[str, Any] = {"nodes": _spec_nodes(nodes)}
    checks = deepcopy(FLOWCHART_CHECKS)
    if include_label_check:
        checks.append(deepcopy(LABEL_CHECK))
    if edges is not None:
        source_reference["connectors"] = [{"from_id": from_id, "to_id": to_id} for from_id, to_id in edges]
        checks.append(deepcopy(CONNECTOR_CHECK))
    return {
        "id": f"flowchart-{case_id}",
        "domain": "computer_science",
        "risk_level": "medium",
        "learning_objective": (
            "Read a vertical-chain flowchart where each node has the correct shape, color "
            "identity, and label, and each directed connector links the declared nodes."
        ),
        "source_reference": source_reference,
        "required_elements": [
            {"id": "nodes", "kind": "node", "name": "flowchart nodes", "count": len(nodes)},
        ],
        "labels": [],
        "relations": [],
        "checks": checks,
    }


def _case(
    case_id: str,
    title: str,
    kind: str,
    nodes: list[dict[str, Any]],
    edges: list[tuple[str, str]] | None,
    expected_report: dict[str, Any],
    defect_type: str | None = None,
    include_label_check: bool = True,
    node_overrides: dict[str, dict[str, Any]] | None = None,
    drop_render_node_ids: list[str] | None = None,
    extra_render_nodes: list[dict[str, Any]] | None = None,
    render_edges: list[tuple[str, str]] | None = None,
    render_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    render_nodes = _render_nodes(nodes, node_overrides, drop_render_node_ids)
    if extra_render_nodes:
        render_nodes = render_nodes + deepcopy(extra_render_nodes)

    rendered_ids = {node["id"] for node in render_nodes}
    edge_source = render_edges if render_edges is not None else (edges or [])
    render_connectors = [
        {"from_id": from_id, "to_id": to_id}
        for from_id, to_id in edge_source
        if from_id in rendered_ids and to_id in rendered_ids
    ]

    expected_report = deepcopy(expected_report)
    expected_report.setdefault("expected_evidence", {"node_count": None})
    return {
        "case_id": case_id,
        "title": title,
        "kind": kind,
        "defect_type": defect_type,
        "spec_nodes": nodes,
        "edges": edges,
        "include_label_check": include_label_check,
        "render_nodes": render_nodes,
        "render_connectors": render_connectors,
        "render_options": render_options or {},
        "expected_report": expected_report,
    }


def dataset_cases() -> list[dict[str, Any]]:
    def golden(node_count: int) -> dict[str, Any]:
        return {"verdict": "pass", "expected_finding_types": [], "expected_evidence": {"node_count": node_count}}

    five_nodes = _five_node_chain()
    five_edges = _five_node_edges()
    three_nodes = _three_node_chain()

    return [
        _case(
            "golden-01",
            "Five-node chain with labels and connectors, all correct",
            "golden",
            five_nodes,
            five_edges,
            golden(5),
        ),
        _case(
            "golden-02",
            "Three-node chain, no labels or connector check declared",
            "golden",
            three_nodes,
            None,
            golden(3),
            include_label_check=False,
        ),
        _case(
            "mutated-01",
            "A declared node is missing entirely",
            "mutated",
            five_nodes,
            five_edges,
            {
                "verdict": "fail",
                "expected_finding_types": ["node_count_mismatch", "missing_node"],
                "expected_evidence": {"node_count": 4},
            },
            defect_type="missing_node",
            drop_render_node_ids=["process"],
        ),
        _case(
            "mutated-02",
            "An undeclared extra node is rendered",
            "mutated",
            five_nodes,
            five_edges,
            {
                "verdict": "fail",
                "expected_finding_types": ["node_count_mismatch", "extra_node"],
                "expected_evidence": {"node_count": 6},
            },
            defect_type="extra_node",
            extra_render_nodes=[
                {"id": "extra", "shape": "rectangle", "rgb": [40, 200, 200], "center_px": [40, 640], "size_px": [60, 40]}
            ],
        ),
        _case(
            "mutated-03",
            "The decision node renders as a rectangle instead of a diamond",
            "mutated",
            five_nodes,
            five_edges,
            {
                "verdict": "fail",
                "expected_finding_types": ["node_shape_wrong"],
                "expected_evidence": {"node_count": 5},
            },
            defect_type="node_shape_wrong",
            node_overrides={"decision": {"shape": "rectangle"}},
        ),
        _case(
            "mutated-04",
            "The decision node's label text is wrong",
            "mutated",
            five_nodes,
            five_edges,
            {
                "verdict": "fail",
                "expected_finding_types": ["node_label_wrong"],
                "expected_evidence": {"node_count": 5},
            },
            defect_type="node_label_wrong",
            node_overrides={"decision": {"label_text": "Process"}},
        ),
        _case(
            "mutated-05",
            "A declared connector is missing from the rendered image",
            "mutated",
            five_nodes,
            five_edges,
            {
                "verdict": "fail",
                "expected_finding_types": ["missing_connector"],
                "expected_evidence": {"node_count": 5},
            },
            defect_type="missing_connector",
            render_edges=[("start", "input"), ("input", "decision"), ("process", "end")],
        ),
        _case(
            "mutated-06",
            "An extra undeclared connector is rendered",
            "mutated",
            five_nodes,
            [("start", "input"), ("input", "decision"), ("process", "end")],
            {
                "verdict": "fail",
                "expected_finding_types": ["extra_connector"],
                "expected_evidence": {"node_count": 5},
            },
            defect_type="extra_connector",
            render_edges=five_edges,
        ),
        _case(
            "mutated-07",
            "Two nodes share an ambiguous color",
            "mutated",
            five_nodes,
            five_edges,
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"node_count": 5},
            },
            defect_type="ambiguous_node_colors",
            node_overrides={"process": {"rgb": RED}},
        ),
        _case(
            "mutated-08",
            "A node is too small to classify its shape",
            "mutated",
            five_nodes,
            five_edges,
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"node_count": 5},
            },
            defect_type="degenerate_node_geometry",
            node_overrides={"end": {"size_px": [12, 8]}},
        ),
        _case(
            "golden-03",
            "Branching diagram: one decision node with two diagonal out-edges, all correct",
            "golden",
            _branching_diagram(),
            _branching_edges(),
            golden(4),
            render_options={"width": BRANCH_WIDTH},
        ),
        _case(
            "mutated-09",
            "Branching diagram, one of the two diagonal branch connectors is missing",
            "mutated",
            _branching_diagram(),
            _branching_edges(),
            {
                "verdict": "fail",
                "expected_finding_types": ["missing_connector"],
                "expected_evidence": {"node_count": 4},
            },
            defect_type="missing_connector",
            render_edges=[("start", "decision"), ("decision", "left")],
            render_options={"width": BRANCH_WIDTH},
        ),
    ]


def build_flowchart_dataset(output_root: Path) -> None:
    build_flowchart_cases_dataset(output_root, dataset_cases(), dataset_track="controlled")


def build_flowchart_cases_dataset(
    output_root: Path,
    cases: list[dict[str, Any]],
    dataset_track: str = "controlled",
) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    for case in cases:
        case_dir = output_root / case["kind"] / case["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)

        spec = _base_spec(case["case_id"], case["spec_nodes"], case["edges"], case["include_label_check"])
        metadata = {
            "case_id": case["case_id"],
            "title": case["title"],
            "kind": case["kind"],
            "defect_type": case["defect_type"],
            "scenario": "flowchart",
            "dataset_track": dataset_track,
            "image_id": case["case_id"],
            "diagram_version": "flowchart-v1",
            "render_options": case["render_options"],
            "renderer": "pillow",
        }

        write_json(case_dir / "visual_spec.json", spec)
        write_json(case_dir / "metadata.json", metadata)
        write_json(case_dir / "expected_report.json", case["expected_report"])
        render_flowchart_diagram(
            image_path=case_dir / "image.png",
            nodes=case["render_nodes"],
            connectors=case["render_connectors"],
            render_options=case["render_options"],
        )

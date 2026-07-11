from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_qa_mcp.claim_graph import build_flowchart_claim_graph
from visual_qa_mcp.flowchart_dataset import build_flowchart_dataset
from visual_qa_mcp.flowchart_extractor import extract_flowchart_evidence
from visual_qa_mcp.flowchart_generator import render_flowchart_diagram
from visual_qa_mcp.flowchart_rules import run_flowchart_claims
from visual_qa_mcp.primitive_evidence import extract_primitive_evidence, primitive_graph_from_flowchart
from visual_qa_mcp.service import run_flowchart_verification, write_verification_artifacts
from visual_qa_mcp.validation import (
    discover_flowchart_cases,
    load_schema,
    summarize_flowchart_validation_results,
    validate_json,
)

ROOT = Path(__file__).resolve().parents[2]

RED = [214, 48, 49]
BLUE = [9, 132, 227]
ORANGE = [230, 126, 34]
GREEN = [0, 148, 50]
PURPLE = [142, 68, 173]

NODES = [
    {"id": "start", "name": "Start", "shape": "rectangle", "rgb": RED, "label_text": "Start", "center_px": [210, 80]},
    {"id": "input", "name": "Input", "shape": "rectangle", "rgb": BLUE, "label_text": "Input", "center_px": [210, 220]},
    {"id": "decision", "name": "Decision", "shape": "diamond", "rgb": ORANGE, "label_text": "Decision", "center_px": [210, 360]},
    {"id": "end", "name": "End", "shape": "rectangle", "rgb": PURPLE, "label_text": "End", "center_px": [210, 500]},
]
EDGES = [("start", "input"), ("input", "decision"), ("decision", "end")]


def _render(
    tmp_path: Path,
    nodes: list[dict],
    edges: list[tuple[str, str]],
    name: str = "image.png",
    render_options: dict | None = None,
) -> Path:
    image_path = tmp_path / name
    render_nodes = [
        {"id": n["id"], "shape": n["shape"], "rgb": n["rgb"], "center_px": n["center_px"], "size_px": [140, 80], "label_text": n.get("label_text")}
        for n in nodes
    ]
    connectors = [{"from_id": f, "to_id": t} for f, t in edges]
    render_flowchart_diagram(image_path, render_nodes, connectors, render_options=render_options)
    return image_path


BRANCH_NODES = [
    {"id": "start", "name": "Start", "shape": "rectangle", "rgb": RED, "label_text": "Start", "center_px": [310, 90]},
    {"id": "decision", "name": "Decision", "shape": "diamond", "rgb": ORANGE, "label_text": "Decision", "center_px": [310, 320]},
    {"id": "left", "name": "Left branch", "shape": "rectangle", "rgb": GREEN, "label_text": "Output", "center_px": [170, 590]},
    {"id": "right", "name": "Right branch", "shape": "rectangle", "rgb": PURPLE, "label_text": "End", "center_px": [450, 590]},
]
BRANCH_EDGES = [("start", "decision"), ("decision", "left"), ("decision", "right")]


def _spec(
    tmp_path: Path,
    nodes: list[dict],
    edges: list[tuple[str, str]] | None = None,
    include_label_check: bool = True,
    checks_extra: list[dict] | None = None,
) -> Path:
    source_reference: dict = {
        "nodes": [
            {"id": n["id"], "name": n["name"], "rgb": n["rgb"], "shape": n["shape"], **({"label_text": n["label_text"]} if n.get("label_text") else {})}
            for n in nodes
        ]
    }
    checks = [
        {"id": "node-count-matches", "type": "node_count_matches", "severity": "high"},
        {"id": "required-nodes-present", "type": "required_nodes_present", "severity": "critical"},
        {"id": "node-shape-correct", "type": "node_shape_correct", "severity": "critical"},
    ]
    if include_label_check:
        checks.append({"id": "node-label-correct", "type": "node_label_correct", "severity": "high"})
    if edges is not None:
        source_reference["connectors"] = [{"from_id": f, "to_id": t} for f, t in edges]
        checks.append({"id": "connector-links-correct", "type": "connector_links_correct", "severity": "critical"})
    spec = {
        "id": "flowchart-test-spec",
        "domain": "computer_science",
        "risk_level": "medium",
        "learning_objective": "Test flowchart-v1 verification.",
        "source_reference": source_reference,
        "required_elements": [{"id": "nodes", "kind": "node", "name": "flowchart nodes", "count": len(nodes)}],
        "labels": [],
        "relations": [],
        "checks": checks + (checks_extra or []),
    }
    spec_path = tmp_path / "visual_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def test_extractor_detects_nodes_and_connectors(tmp_path: Path) -> None:
    image_path = _render(tmp_path, NODES, EDGES)
    evidence = extract_flowchart_evidence(image_path)
    assert len(evidence.nodes) == 4
    assert not evidence.gaps
    shapes_by_rgb = {tuple(n.rgb): n.shape for n in evidence.nodes}
    assert shapes_by_rgb[tuple(ORANGE)] == "diamond"
    assert shapes_by_rgb[tuple(RED)] == "rectangle"
    assert len(evidence.connectors) == 3


def test_extractor_decodes_node_labels(tmp_path: Path) -> None:
    image_path = _render(tmp_path, NODES, EDGES)
    evidence = extract_flowchart_evidence(image_path)
    labels_by_rgb = {tuple(n.rgb): n.label_text for n in evidence.nodes}
    assert labels_by_rgb[tuple(RED)] == "Start"
    assert labels_by_rgb[tuple(ORANGE)] == "Decision"


def test_extractor_evidence_matches_schema(tmp_path: Path) -> None:
    image_path = _render(tmp_path, NODES, EDGES)
    evidence = extract_flowchart_evidence(image_path)
    schema = load_schema(ROOT / "specs" / "flowchart-evidence-graph.schema.json")
    assert validate_json(schema, evidence.to_dict()) == []


def test_golden_diagram_passes(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    image_path = _render(tmp_path, NODES, EDGES)
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "pass"
    assert result.report.findings == []


def test_branching_diagram_with_diagonal_connectors_passes(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, BRANCH_NODES, BRANCH_EDGES)
    image_path = _render(tmp_path, BRANCH_NODES, BRANCH_EDGES, render_options={"width": 620})
    evidence = extract_flowchart_evidence(image_path)
    assert len(evidence.connectors) == 3
    assert not evidence.gaps
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "pass"
    assert result.report.findings == []


def test_branching_diagram_reports_missing_branch_connector(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, BRANCH_NODES, BRANCH_EDGES)
    image_path = _render(
        tmp_path,
        BRANCH_NODES,
        [("start", "decision"), ("decision", "left")],
        render_options={"width": 620},
    )
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    types = {finding.type for finding in result.report.findings}
    assert types == {"missing_connector"}
    finding = next(f for f in result.report.findings if f.type == "missing_connector")
    assert finding.evidence["expected_edge"] == ["decision", "right"]


def test_missing_node_reports_missing_and_count(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    image_path = _render(tmp_path, NODES[:3], EDGES[:2])
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert {"missing_node", "node_count_mismatch"}.issubset(types)
    assert result.report.verdict == "fail"


def test_extra_node_reports_extra_and_count(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    extra = NODES + [{"id": "extra", "name": "Extra", "shape": "rectangle", "rgb": [40, 200, 200], "center_px": [380, 80]}]
    image_path = _render(tmp_path, extra, EDGES)
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert {"extra_node", "node_count_mismatch"}.issubset(types)
    assert result.report.verdict == "fail"


def test_node_shape_wrong_reports_finding(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    wrong_shape = [dict(n) for n in NODES]
    wrong_shape[2] = {**wrong_shape[2], "shape": "rectangle"}
    image_path = _render(tmp_path, wrong_shape, EDGES)
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "node_shape_wrong" in types
    assert result.report.verdict == "fail"


def test_node_label_wrong_reports_finding(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    wrong_label = [dict(n) for n in NODES]
    wrong_label[2] = {**wrong_label[2], "label_text": "Process"}
    image_path = _render(tmp_path, wrong_label, EDGES)
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "node_label_wrong" in types
    assert result.report.verdict == "fail"


def test_missing_connector_reports_finding(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    image_path = _render(tmp_path, NODES, EDGES[:2])  # drop decision->end
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "missing_connector" in types
    assert result.report.verdict == "fail"
    assert "connector-links-correct" in result.report.checks_run


def test_missing_node_does_not_force_needs_review_via_connectors(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    image_path = _render(tmp_path, NODES[:2], EDGES[:1])  # decision, end missing
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    assert "connector-links-correct" in result.report.checks_run
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "connector-links-correct" not in skipped_ids


def test_extra_connector_reports_finding(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES[:2])  # declare only start->input, input->decision
    image_path = _render(tmp_path, NODES, EDGES)  # render all three
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "extra_connector" in types
    assert result.report.verdict == "fail"


def test_ambiguous_node_colors_guarded_as_needs_review(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    colliding = [dict(n) for n in NODES]
    colliding[3] = {**colliding[3], "rgb": RED}  # end collides with start
    image_path = _render(tmp_path, colliding, EDGES)
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "needs_review"
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "required-nodes-present" in skipped_ids


def test_degenerate_node_guarded_as_needs_review(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    image_path = tmp_path / "image.png"
    render_nodes = [
        {"id": n["id"], "shape": n["shape"], "rgb": n["rgb"], "center_px": n["center_px"], "size_px": [140, 80], "label_text": n.get("label_text")}
        for n in NODES
    ]
    render_nodes[3]["size_px"] = [12, 8]
    connectors = [{"from_id": f, "to_id": t} for f, t in EDGES]
    render_flowchart_diagram(image_path, render_nodes, connectors)
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "needs_review"


def test_unknown_check_becomes_claim_gap_and_needs_review(tmp_path: Path) -> None:
    spec_path = _spec(
        tmp_path,
        NODES,
        checks_extra=[{"id": "swimlane-correct", "type": "swimlane_correct", "severity": "high"}],
    )
    claim_graph = build_flowchart_claim_graph(spec_path)
    assert any(gap.check_id == "swimlane-correct" for gap in claim_graph.gaps)
    image_path = _render(tmp_path, NODES, [])
    evidence = extract_flowchart_evidence(image_path)
    report = run_flowchart_claims(claim_graph, evidence)
    assert report.verdict == "needs_review"


def test_label_check_without_declared_labels_is_gapped(tmp_path: Path) -> None:
    unlabeled = [{**n, "label_text": None} for n in NODES]
    spec_path = _spec(tmp_path, unlabeled, include_label_check=True)
    claim_graph = build_flowchart_claim_graph(spec_path)
    assert any(
        gap.check_id == "node-label-correct" and gap.code == "labels_not_declared" for gap in claim_graph.gaps
    )


def test_connectors_declared_without_check_is_gapped(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, include_label_check=False)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["source_reference"]["connectors"] = [{"from_id": "start", "to_id": "input"}]
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    claim_graph = build_flowchart_claim_graph(spec_path)
    assert any(
        gap.check_id == "connector-links-correct" and gap.code == "connectors_without_links_check"
        for gap in claim_graph.gaps
    )


def test_connector_check_without_declared_connectors_is_gapped(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, include_label_check=False)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["checks"].append({"id": "connector-links-correct", "type": "connector_links_correct", "severity": "critical"})
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    claim_graph = build_flowchart_claim_graph(spec_path)
    assert any(
        gap.check_id == "connector-links-correct" and gap.code == "connectors_not_declared"
        for gap in claim_graph.gaps
    )


def test_artifact_writing_for_flowchart_verification(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, NODES, EDGES)
    image_path = _render(tmp_path, NODES, EDGES)
    result = run_flowchart_verification(image_path=image_path, spec_path=spec_path)
    paths = write_verification_artifacts(result, tmp_path / "out")
    assert paths.report_path.exists()
    assert paths.evidence_graph_path.exists()
    assert paths.claim_graph_path.exists()
    assert paths.overlay_path.exists()
    assert paths.primitive_evidence_graph_path is not None
    assert paths.primitive_evidence_graph_path.exists()
    report_payload = json.loads(paths.report_path.read_text(encoding="utf-8"))
    assert report_payload["claim_graph_path"] == str(paths.claim_graph_path)


def test_primitive_evidence_adapter_produces_nodes_and_connectors(tmp_path: Path) -> None:
    image_path = _render(tmp_path, NODES, EDGES)
    evidence = extract_flowchart_evidence(image_path)
    graph = primitive_graph_from_flowchart(evidence, image_path)
    rectangle_primitives = [p for p in graph.primitives if p.type == "rectangle"]
    symbol_primitives = [p for p in graph.primitives if p.type == "symbol"]
    arrow_primitives = [p for p in graph.primitives if p.type == "arrow"]
    assert len(rectangle_primitives) == 3
    assert len(symbol_primitives) == 1
    assert len(arrow_primitives) == 3
    assert graph.profile == "flowchart-v1"


def test_extract_primitive_evidence_dispatches_flowchart_profile(tmp_path: Path) -> None:
    image_path = _render(tmp_path, NODES, EDGES)
    graph = extract_primitive_evidence(image_path, "flowchart-v1")
    assert graph.profile == "flowchart-v1"


@pytest.fixture(scope="module")
def flowchart_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset_root = tmp_path_factory.mktemp("flowchart-v1")
    build_flowchart_dataset(dataset_root)
    return dataset_root


def test_flowchart_dataset_structure(flowchart_dataset: Path) -> None:
    cases = discover_flowchart_cases(flowchart_dataset)
    assert len(cases) == 12
    assert sum(1 for case in cases if case.kind == "golden") == 3
    assert sum(1 for case in cases if case.kind == "mutated") == 9


def test_flowchart_dataset_validation_summary(flowchart_dataset: Path) -> None:
    summary = summarize_flowchart_validation_results(flowchart_dataset)
    assert summary["total_cases"] == 12
    assert summary["typed_mutated_cases"] == 7
    assert summary["typed_mutated_hits"] == 7
    assert summary["critical_error_recall"] == 1.0
    assert summary["ambiguous_cases"] == 2
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_failures"] == 0
    assert summary["golden_non_passes"] == 0
    assert summary["verdict_mismatches"] == 0

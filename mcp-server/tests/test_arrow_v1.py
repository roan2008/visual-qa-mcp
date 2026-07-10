from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_qa_mcp.arrow_dataset import build_arrow_dataset
from visual_qa_mcp.arrow_extractor import extract_arrow_evidence
from visual_qa_mcp.arrow_generator import render_arrow_diagram
from visual_qa_mcp.arrow_rules import run_arrow_claims
from visual_qa_mcp.claim_graph import build_arrow_claim_graph
from visual_qa_mcp.service import run_arrow_verification, write_verification_artifacts
from visual_qa_mcp.validation import (
    discover_arrow_cases,
    load_schema,
    summarize_arrow_validation_results,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

BASIC_ARROWS = [
    {"rgb": [214, 48, 49], "anchor": "bottom_center", "angle_degrees": 270, "length_px": 90},
    {"rgb": [9, 132, 227], "anchor": "top_center", "angle_degrees": 90, "length_px": 90},
    {"rgb": [0, 148, 50], "anchor": "right_center", "angle_degrees": 0, "length_px": 90},
    {"rgb": [230, 126, 34], "anchor": "left_center", "angle_degrees": 180, "length_px": 90},
]


def _basic_spec(
    tmp_path: Path,
    checks_extra: list[dict] | None = None,
    scenario_type: str | None = None,
) -> Path:
    source_reference: dict = {
        "arrows": [
                {"id": "weight", "name": "Weight (W)", "rgb": [214, 48, 49], "direction_degrees": 270, "target": "object"},
                {"id": "normal", "name": "Normal (N)", "rgb": [9, 132, 227], "direction_degrees": 90, "target": "object"},
                {"id": "applied", "name": "Applied (F)", "rgb": [0, 148, 50], "direction_degrees": 0, "target": "object"},
                {"id": "friction", "name": "Friction (f)", "rgb": [230, 126, 34], "direction_degrees": 180, "target": "object"},
        ],
        "object": {"kind": "box"},
    }
    if scenario_type is not None:
        source_reference["scenario_type"] = scenario_type
    spec = {
        "id": "arrow-test-spec",
        "domain": "physics",
        "risk_level": "medium",
        "learning_objective": "Test free-body arrow verification.",
        "source_reference": source_reference,
        "required_elements": [
            {"id": "object", "kind": "box", "name": "object", "count": 1},
            {"id": "arrows", "kind": "arrow", "name": "force arrows", "count": 4},
        ],
        "labels": [],
        "relations": [],
        "checks": [
            {"id": "arrow-count-matches", "type": "arrow_count_matches", "severity": "high"},
            {"id": "required-arrows-present", "type": "required_arrows_present", "severity": "critical"},
            {"id": "arrow-directions-correct", "type": "arrow_directions_correct", "severity": "critical", "params": {"angle_tolerance_degrees": 15.0}},
            {"id": "arrow-anchors-object", "type": "arrow_anchors_object", "severity": "high"},
        ]
        + (checks_extra or []),
    }
    spec_path = tmp_path / "visual_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def _render(tmp_path: Path, arrows: list[dict], name: str = "image.png") -> Path:
    image_path = tmp_path / name
    render_arrow_diagram(image_path, arrows)
    return image_path


def test_extractor_detects_four_arrows_and_directions(tmp_path: Path) -> None:
    image_path = _render(tmp_path, BASIC_ARROWS)
    evidence = extract_arrow_evidence(image_path)
    assert len(evidence.arrows) == 4
    assert not evidence.gaps
    detected_angles = sorted(arrow.angle_degrees for arrow in evidence.arrows)
    for detected, expected in zip(detected_angles, [0.0, 90.0, 180.0, 270.0], strict=True):
        assert abs(detected - expected) <= 6.0
    assert evidence.regions and evidence.regions[0].region_id == "object"


def test_extractor_evidence_matches_schema(tmp_path: Path) -> None:
    image_path = _render(tmp_path, BASIC_ARROWS)
    evidence = extract_arrow_evidence(image_path)
    schema = load_schema(REPO_ROOT / "specs" / "arrow-evidence-graph.schema.json")
    errors = [error.message for error in schema.iter_errors(evidence.to_dict())]
    assert errors == []


def test_golden_diagram_passes(tmp_path: Path) -> None:
    spec_path = _basic_spec(tmp_path)
    image_path = _render(tmp_path, BASIC_ARROWS)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "pass"
    assert result.report.findings == []


def test_reversed_arrow_reports_direction_finding(tmp_path: Path) -> None:
    arrows = [dict(arrow) for arrow in BASIC_ARROWS]
    arrows[3]["angle_degrees"] = 0  # friction reversed
    spec_path = _basic_spec(tmp_path)
    image_path = _render(tmp_path, arrows)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    types = {finding.type for finding in result.report.findings}
    assert "arrow_direction_wrong" in types


def test_missing_arrow_reports_missing_and_count(tmp_path: Path) -> None:
    spec_path = _basic_spec(tmp_path)
    image_path = _render(tmp_path, BASIC_ARROWS[:3])
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert {"arrow_missing", "arrow_count_mismatch"}.issubset(types)
    assert result.report.verdict == "fail"


def test_detached_arrow_reports_anchor_finding(tmp_path: Path) -> None:
    arrows = [dict(arrow) for arrow in BASIC_ARROWS]
    arrows[0]["tail_offset"] = [90, 40]  # weight floats away from the object
    spec_path = _basic_spec(tmp_path)
    image_path = _render(tmp_path, arrows)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "arrow_anchor_detached" in types


def test_duplicate_colors_guarded_as_needs_review(tmp_path: Path) -> None:
    arrows = [dict(arrow) for arrow in BASIC_ARROWS]
    arrows[3]["rgb"] = [0, 148, 50]  # friction same color as applied
    spec_path = _basic_spec(tmp_path)
    image_path = _render(tmp_path, arrows)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "needs_review"
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "required-arrows-present" in skipped_ids
    assert "arrow-directions-correct" in skipped_ids


def test_unknown_check_becomes_claim_gap_and_needs_review(tmp_path: Path) -> None:
    spec_path = _basic_spec(
        tmp_path,
        checks_extra=[{"id": "torque-balance", "type": "torque_balance", "severity": "high"}],
    )
    claim_graph = build_arrow_claim_graph(spec_path)
    assert any(gap.check_id == "torque-balance" for gap in claim_graph.gaps)
    image_path = _render(tmp_path, BASIC_ARROWS)
    evidence = extract_arrow_evidence(image_path)
    report = run_arrow_claims(claim_graph, evidence)
    assert report.verdict == "needs_review"


def test_artifact_writing_for_arrow_verification(tmp_path: Path) -> None:
    spec_path = _basic_spec(tmp_path)
    image_path = _render(tmp_path, BASIC_ARROWS)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    paths = write_verification_artifacts(result, tmp_path / "out")
    assert paths.report_path.exists()
    assert paths.evidence_graph_path.exists()
    assert paths.claim_graph_path.exists()
    assert paths.overlay_path.exists()
    report_payload = json.loads(paths.report_path.read_text(encoding="utf-8"))
    assert report_payload["claim_graph_path"] == str(paths.claim_graph_path)


LABELED_ARROWS = [
    {"rgb": [214, 48, 49], "anchor": "bottom_center", "angle_degrees": 270, "length_px": 90, "label_text": "W"},
    {"rgb": [9, 132, 227], "anchor": "top_center", "angle_degrees": 90, "length_px": 90, "label_text": "N"},
    {"rgb": [0, 148, 50], "anchor": "right_center", "angle_degrees": 0, "length_px": 90, "label_text": "F"},
    {"rgb": [230, 126, 34], "anchor": "left_center", "angle_degrees": 180, "length_px": 90, "label_text": "f"},
]


def _labeled_spec(tmp_path: Path) -> Path:
    spec = {
        "id": "arrow-test-labeled-spec",
        "domain": "physics",
        "risk_level": "medium",
        "learning_objective": "Test label-based arrow identity resolution.",
        "source_reference": {
            "arrows": [
                {"id": "weight", "name": "Weight (W)", "rgb": [214, 48, 49], "direction_degrees": 270, "label_text": "W", "target": "object"},
                {"id": "normal", "name": "Normal (N)", "rgb": [9, 132, 227], "direction_degrees": 90, "label_text": "N", "target": "object"},
                {"id": "applied", "name": "Applied (F)", "rgb": [0, 148, 50], "direction_degrees": 0, "label_text": "F", "target": "object"},
                {"id": "friction", "name": "Friction (f)", "rgb": [230, 126, 34], "direction_degrees": 180, "label_text": "f", "target": "object"},
            ],
            "object": {"kind": "box"},
        },
        "required_elements": [
            {"id": "object", "kind": "box", "name": "object", "count": 1},
            {"id": "arrows", "kind": "arrow", "name": "force arrows", "count": 4},
        ],
        "labels": [],
        "relations": [],
        "checks": [
            {"id": "arrow-count-matches", "type": "arrow_count_matches", "severity": "high"},
            {"id": "required-arrows-present", "type": "required_arrows_present", "severity": "critical"},
            {"id": "arrow-directions-correct", "type": "arrow_directions_correct", "severity": "critical", "params": {"angle_tolerance_degrees": 15.0}},
            {"id": "arrow-anchors-object", "type": "arrow_anchors_object", "severity": "high"},
        ],
    }
    spec_path = tmp_path / "visual_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def test_extractor_decodes_arrow_labels(tmp_path: Path) -> None:
    image_path = _render(tmp_path, LABELED_ARROWS)
    evidence = extract_arrow_evidence(image_path)
    decoded = {arrow.label_text for arrow in evidence.arrows}
    assert decoded == {"W", "N", "F", "f"}
    assert not evidence.gaps


def test_labels_resolve_color_collision_into_typed_defect(tmp_path: Path) -> None:
    arrows = [dict(arrow) for arrow in LABELED_ARROWS]
    arrows[3]["rgb"] = [0, 148, 50]  # friction now shares applied's color
    arrows[3]["angle_degrees"] = 220  # and points the wrong way (still outward, away from the object)
    spec_path = _labeled_spec(tmp_path)
    image_path = _render(tmp_path, arrows)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    types = {finding.type for finding in result.report.findings}
    assert "arrow_direction_wrong" in types
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "required-arrows-present" not in skipped_ids


BALANCE_CHECK = {
    "id": "force-balance-correct",
    "type": "force_balance_correct",
    "severity": "critical",
    "params": {"resultant_ratio_tolerance": 0.15},
}


def test_declared_equilibrium_with_balanced_forces_passes(tmp_path: Path) -> None:
    spec_path = _basic_spec(tmp_path, checks_extra=[dict(BALANCE_CHECK)], scenario_type="equilibrium")
    image_path = _render(tmp_path, BASIC_ARROWS)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "pass"
    assert "force-balance-correct" in result.report.checks_run


def test_shortened_arrow_violates_declared_equilibrium(tmp_path: Path) -> None:
    arrows = [dict(arrow) for arrow in BASIC_ARROWS]
    arrows[0]["length_px"] = 50  # weight too short: same direction and anchor, wrong magnitude
    spec_path = _basic_spec(tmp_path, checks_extra=[dict(BALANCE_CHECK)], scenario_type="equilibrium")
    image_path = _render(tmp_path, arrows)
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    types = {finding.type for finding in result.report.findings}
    assert types == {"force_balance_violation"}
    finding = result.report.findings[0]
    assert finding.evidence["resultant_ratio"] > finding.evidence["resultant_ratio_tolerance"]
    assert set(finding.evidence["arrow_vectors_px"]) == {"weight", "normal", "applied", "friction"}


def test_balance_check_without_scenario_declaration_is_gapped(tmp_path: Path) -> None:
    spec_path = _basic_spec(tmp_path, checks_extra=[dict(BALANCE_CHECK)])
    claim_graph = build_arrow_claim_graph(spec_path)
    assert any(
        gap.check_id == "force-balance-correct" and gap.code == "scenario_type_not_declared"
        for gap in claim_graph.gaps
    )
    image_path = _render(tmp_path, BASIC_ARROWS)
    evidence = extract_arrow_evidence(image_path)
    report = run_arrow_claims(claim_graph, evidence)
    assert report.verdict == "needs_review"


def test_scenario_without_balance_check_is_gapped(tmp_path: Path) -> None:
    spec_path = _basic_spec(tmp_path, scenario_type="equilibrium")
    claim_graph = build_arrow_claim_graph(spec_path)
    assert any(
        gap.check_id == "force-balance-correct" and gap.code == "scenario_without_balance_check"
        for gap in claim_graph.gaps
    )


def test_balance_check_refuses_partial_force_set(tmp_path: Path) -> None:
    spec_path = _basic_spec(tmp_path, checks_extra=[dict(BALANCE_CHECK)], scenario_type="equilibrium")
    image_path = _render(tmp_path, BASIC_ARROWS[:3])  # friction arrow never drawn
    result = run_arrow_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "arrow_missing" in types
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "force-balance-correct" in skipped_ids
    assert "force_balance_violation" not in types


@pytest.fixture(scope="module")
def arrow_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset_root = tmp_path_factory.mktemp("arrow-v1")
    build_arrow_dataset(dataset_root)
    return dataset_root


def test_arrow_dataset_structure(arrow_dataset: Path) -> None:
    cases = discover_arrow_cases(arrow_dataset)
    assert len(cases) == 17
    assert sum(1 for case in cases if case.kind == "golden") == 6
    assert sum(1 for case in cases if case.kind == "mutated") == 11


def test_arrow_dataset_validation_summary(arrow_dataset: Path) -> None:
    summary = summarize_arrow_validation_results(arrow_dataset)
    assert summary["total_cases"] == 17
    assert summary["typed_mutated_cases"] == 8
    assert summary["typed_mutated_hits"] == 8
    assert summary["critical_error_recall"] == 1.0
    assert summary["ambiguous_cases"] == 3
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_failures"] == 0
    assert summary["golden_non_passes"] == 0
    assert summary["verdict_mismatches"] == 0
    assert summary["force_balance_metrics"] == {
        "typed_cases": 1,
        "typed_hits": 1,
        "typed_hit_rate": 1.0,
    }

from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_qa_mcp.claim_graph import build_coordinate_claim_graph
from visual_qa_mcp.coordinate_dataset import build_coordinate_dataset, build_noisy_coordinate_dataset
from visual_qa_mcp.coordinate_extractor import extract_coordinate_evidence
from visual_qa_mcp.coordinate_generator import (
    DEFAULT_PLOT_BOX,
    render_coordinate_diagram,
    x_value_to_pixel,
    y_value_to_pixel,
)
from visual_qa_mcp.coordinate_rules import run_coordinate_claims
from visual_qa_mcp.primitive_evidence import (
    extract_primitive_evidence,
    primitive_graph_from_coordinates,
)
from visual_qa_mcp.service import run_coordinate_verification, write_verification_artifacts
from visual_qa_mcp.validation import (
    discover_coordinate_cases,
    load_schema,
    summarize_coordinate_validation_results,
    validate_json,
)

ROOT = Path(__file__).resolve().parents[2]

X_AXIS = {"min": 0, "max": 100, "step": 20}
Y_AXIS = {"min": 0, "max": 50, "step": 10}
POINTS = [
    {"id": "p1", "name": "Point 1", "rgb": [214, 48, 49], "x": 10, "y": 5},
    {"id": "p2", "name": "Point 2", "rgb": [9, 132, 227], "x": 40, "y": 15},
    {"id": "p3", "name": "Point 3", "rgb": [0, 148, 50], "x": 70, "y": 35},
    {"id": "p4", "name": "Point 4", "rgb": [142, 68, 173], "x": 95, "y": 48},
]


def _ticks(axis: dict) -> list[dict]:
    return [{"value": value} for value in range(axis["min"], axis["max"] + 1, axis["step"])]


def _render(
    tmp_path: Path,
    points: list[dict],
    polyline_ids: list[str] | None,
    name: str = "image.png",
    series: list[list[str]] | None = None,
) -> Path:
    image_path = tmp_path / name
    rendered_points = [
        {
            "id": point["id"],
            "center_px": [
                x_value_to_pixel(float(point["x"]), X_AXIS, DEFAULT_PLOT_BOX),
                y_value_to_pixel(float(point["y"]), Y_AXIS, DEFAULT_PLOT_BOX),
            ],
            "rgb": point["rgb"],
            **({"label_text": point["label_text"]} if "label_text" in point else {}),
        }
        for point in points
    ]
    render_coordinate_diagram(
        image_path,
        rendered_points,
        polyline_ids,
        {**X_AXIS, "ticks": _ticks(X_AXIS)},
        {**Y_AXIS, "ticks": _ticks(Y_AXIS)},
        polylines=series,
    )
    return image_path


def _spec(
    tmp_path: Path,
    points: list[dict],
    polyline_ids: list[str] | None = None,
    checks_extra: list[dict] | None = None,
    series: list[dict] | None = None,
) -> Path:
    source_reference: dict = {
        "x_axis": {"min": X_AXIS["min"], "max": X_AXIS["max"]},
        "y_axis": {"min": Y_AXIS["min"], "max": Y_AXIS["max"]},
        "points": [
            {
                "id": p["id"],
                "name": p["name"],
                "rgb": p["rgb"],
                "x": p["x"],
                "y": p["y"],
                "label_text": p.get("label_text"),
            }
            for p in points
        ],
    }
    checks = [
        {"id": "point-count-matches", "type": "point_count_matches", "severity": "high"},
        {"id": "required-points-present", "type": "required_points_present", "severity": "critical"},
        {"id": "point-positions-correct", "type": "point_positions_correct", "severity": "critical"},
        {"id": "axis-scale-correct", "type": "axis_scale_correct", "severity": "critical"},
    ]
    if series is not None:
        source_reference["polylines"] = series
        checks.append(
            {"id": "polyline-connections-correct", "type": "polyline_connections_correct", "severity": "high"}
        )
    elif polyline_ids is not None:
        source_reference["polyline"] = {"ordered_point_ids": polyline_ids}
        checks.append(
            {"id": "polyline-connections-correct", "type": "polyline_connections_correct", "severity": "high"}
        )
    spec = {
        "id": "coordinate-test-spec",
        "domain": "mathematics",
        "risk_level": "medium",
        "learning_objective": "Test coordinate-graph-v1 verification.",
        "source_reference": source_reference,
        "required_elements": [{"id": "points", "kind": "point", "name": "scatter points", "count": len(points)}],
        "labels": [],
        "relations": [],
        "checks": checks + (checks_extra or []),
    }
    spec_path = tmp_path / "visual_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def test_extractor_detects_four_points_and_axes(tmp_path: Path) -> None:
    image_path = _render(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    evidence = extract_coordinate_evidence(image_path)
    assert len(evidence.points) == 4
    assert not evidence.gaps
    assert evidence.x_axis.mapping is not None
    assert evidence.y_axis.mapping is not None
    assert evidence.x_axis.mapping.min_value == 0.0
    assert evidence.x_axis.mapping.max_value == 100.0
    assert evidence.y_axis.mapping.min_value == 0.0
    assert evidence.y_axis.mapping.max_value == 50.0


def test_dual_axis_round_trip_error_is_small(tmp_path: Path) -> None:
    image_path = _render(tmp_path, POINTS, None)
    evidence = extract_coordinate_evidence(image_path)
    by_rgb = {tuple(point.rgb): point for point in evidence.points}
    for point in POINTS:
        detected = by_rgb[tuple(point["rgb"])]
        assert detected.data_xy is not None
        assert abs(detected.data_xy[0] - point["x"]) < 0.5
        assert abs(detected.data_xy[1] - point["y"]) < 0.5


def test_extractor_evidence_matches_schema(tmp_path: Path) -> None:
    image_path = _render(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    evidence = extract_coordinate_evidence(image_path)
    schema = load_schema(ROOT / "specs" / "coordinate-evidence-graph.schema.json")
    assert validate_json(schema, evidence.to_dict()) == []


def test_golden_diagram_passes(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    image_path = _render(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "pass"
    assert result.report.findings == []


def test_missing_point_reports_missing_and_count(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    image_path = _render(tmp_path, POINTS[:3], ["p1", "p2", "p3"])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert {"missing_point", "point_count_mismatch"}.issubset(types)
    assert result.report.verdict == "fail"


def test_extra_point_reports_extra_and_count(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    extra_points = POINTS + [{"id": "extra", "name": "Extra", "rgb": [230, 126, 34], "x": 50, "y": 25}]
    image_path = _render(tmp_path, extra_points, ["p1", "p2", "p3", "p4"])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert {"extra_point", "point_count_mismatch"}.issubset(types)
    assert result.report.verdict == "fail"


def test_point_position_wrong_reports_finding(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS)
    moved = [dict(point) for point in POINTS]
    moved[1]["x"] = 85.0  # p2 rendered far from its declared x
    image_path = _render(tmp_path, moved, None)
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "point_position_wrong" in types
    assert result.report.verdict == "fail"


def test_axis_scale_misread_reports_finding(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS)
    image_path = tmp_path / "image.png"
    rendered_points = [
        {
            "id": point["id"],
            "center_px": [
                x_value_to_pixel(float(point["x"]), X_AXIS, DEFAULT_PLOT_BOX),
                y_value_to_pixel(float(point["y"]), Y_AXIS, DEFAULT_PLOT_BOX),
            ],
            "rgb": point["rgb"],
        }
        for point in POINTS
    ]
    shifted_y_ticks = [{"value": value, "label_text": str(value + 10)} for value in range(Y_AXIS["min"], Y_AXIS["max"] + 1, Y_AXIS["step"])]
    render_coordinate_diagram(
        image_path,
        rendered_points,
        None,
        {**X_AXIS, "ticks": _ticks(X_AXIS)},
        {**Y_AXIS, "ticks": shifted_y_ticks},
    )
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "axis_scale_misread" in types
    assert result.report.verdict == "fail"


def test_polyline_connection_wrong_reports_finding(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    image_path = _render(tmp_path, POINTS, ["p1", "p2", "p4"])  # skips p3
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    types = {finding.type for finding in result.report.findings}
    assert "polyline_connection_wrong" in types
    assert result.report.verdict == "fail"
    assert "polyline-connections-correct" in result.report.checks_run


def test_missing_point_does_not_force_needs_review_via_polyline(tmp_path: Path) -> None:
    # A plain missing-point defect must resolve to "fail" (a real finding),
    # not "needs_review" - the polyline check should skip judging only the
    # affected edges rather than discarding the whole check.
    spec_path = _spec(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    image_path = _render(tmp_path, POINTS[:3], ["p1", "p2"])  # p4 missing entirely
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    assert "polyline-connections-correct" in result.report.checks_run
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "polyline-connections-correct" not in skipped_ids


def test_ambiguous_point_colors_guarded_as_needs_review(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    colliding = [dict(point) for point in POINTS]
    colliding[2]["rgb"] = [9, 132, 227]  # p3 collides with p2's color
    image_path = _render(tmp_path, colliding, ["p1", "p2", "p3", "p4"])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "needs_review"
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "required-points-present" in skipped_ids
    assert "point-positions-correct" in skipped_ids


def test_labeled_points_pass_when_correct(tmp_path: Path) -> None:
    labeled = [dict(point) for point in POINTS]
    for point, label in zip(labeled, ("A", "B", "C", "D")):
        point["label_text"] = label
    spec_path = _spec(tmp_path, labeled, ["p1", "p2", "p3", "p4"])
    image_path = _render(tmp_path, labeled, ["p1", "p2", "p3", "p4"])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "pass"


def test_label_resolves_color_collision_and_position_defect_surfaces(tmp_path: Path) -> None:
    labeled = [dict(point) for point in POINTS]
    for point, label in zip(labeled, ("A", "B", "C", "D")):
        point["label_text"] = label
    spec_path = _spec(tmp_path, labeled, ["p1", "p2", "p3", "p4"])
    colliding = [dict(point) for point in labeled]
    colliding[2]["rgb"] = [9, 132, 227]  # p3 collides with p2's color but keeps a distinct label
    colliding[2]["x"] = 85  # actual rendered position diverges from the declared 70
    image_path = _render(tmp_path, colliding, ["p1", "p2", "p3", "p4"])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    types = {finding.type for finding in result.report.findings}
    assert types == {"point_position_wrong"}
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "required-points-present" not in skipped_ids


def test_multi_series_polylines_pass_when_both_correct(tmp_path: Path) -> None:
    series = [
        {"series_id": "series-1", "ordered_point_ids": ["p1", "p2"]},
        {"series_id": "series-2", "ordered_point_ids": ["p3", "p4"]},
    ]
    spec_path = _spec(tmp_path, POINTS, series=series)
    image_path = _render(tmp_path, POINTS, None, series=[["p1", "p2"], ["p3", "p4"]])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "pass"


def test_multi_series_reports_series_scoped_connection_failure(tmp_path: Path) -> None:
    series = [
        {"series_id": "series-1", "ordered_point_ids": ["p1", "p2"]},
        {"series_id": "series-2", "ordered_point_ids": ["p3", "p4"]},
    ]
    spec_path = _spec(tmp_path, POINTS, series=series)
    image_path = _render(tmp_path, POINTS, None, series=[["p1", "p2"], ["p3"]])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "fail"
    types = {finding.type for finding in result.report.findings}
    assert types == {"polyline_connection_wrong"}
    finding = next(f for f in result.report.findings if f.type == "polyline_connection_wrong")
    assert finding.evidence["series_id"] == "series-2"


def test_unreadable_axis_guarded_as_needs_review(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS)
    image_path = tmp_path / "image.png"
    rendered_points = [
        {
            "id": point["id"],
            "center_px": [
                x_value_to_pixel(float(point["x"]), X_AXIS, DEFAULT_PLOT_BOX),
                y_value_to_pixel(float(point["y"]), Y_AXIS, DEFAULT_PLOT_BOX),
            ],
            "rgb": point["rgb"],
        }
        for point in POINTS
    ]
    render_coordinate_diagram(
        image_path,
        rendered_points,
        None,
        {**X_AXIS, "ticks": _ticks(X_AXIS)},
        {**Y_AXIS, "ticks": [{"value": 0}]},  # only one Y tick: unreadable
    )
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    assert result.report.verdict == "needs_review"
    skipped_ids = {item["check_id"] for item in result.report.checks_skipped}
    assert "point-positions-correct" in skipped_ids
    assert "axis-scale-correct" in skipped_ids


def test_unknown_check_becomes_claim_gap_and_needs_review(tmp_path: Path) -> None:
    spec_path = _spec(
        tmp_path,
        POINTS,
        checks_extra=[{"id": "curve-fit-correct", "type": "curve_fit_correct", "severity": "high"}],
    )
    claim_graph = build_coordinate_claim_graph(spec_path)
    assert any(gap.check_id == "curve-fit-correct" for gap in claim_graph.gaps)
    image_path = _render(tmp_path, POINTS, None)
    evidence = extract_coordinate_evidence(image_path)
    report = run_coordinate_claims(claim_graph, evidence)
    assert report.verdict == "needs_review"


def test_polyline_declared_without_check_is_gapped(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["source_reference"]["polyline"] = {"ordered_point_ids": ["p1", "p2", "p3", "p4"]}
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    claim_graph = build_coordinate_claim_graph(spec_path)
    assert any(
        gap.check_id == "polyline-connections-correct" and gap.code == "polyline_without_connections_check"
        for gap in claim_graph.gaps
    )


def test_polyline_check_without_declared_polyline_is_gapped(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["checks"].append(
        {"id": "polyline-connections-correct", "type": "polyline_connections_correct", "severity": "high"}
    )
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    claim_graph = build_coordinate_claim_graph(spec_path)
    assert any(
        gap.check_id == "polyline-connections-correct" and gap.code == "polyline_not_declared"
        for gap in claim_graph.gaps
    )


def test_artifact_writing_for_coordinate_verification(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    image_path = _render(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    result = run_coordinate_verification(image_path=image_path, spec_path=spec_path)
    paths = write_verification_artifacts(result, tmp_path / "out")
    assert paths.report_path.exists()
    assert paths.evidence_graph_path.exists()
    assert paths.claim_graph_path.exists()
    assert paths.overlay_path.exists()
    assert paths.primitive_evidence_graph_path is not None
    assert paths.primitive_evidence_graph_path.exists()
    report_payload = json.loads(paths.report_path.read_text(encoding="utf-8"))
    assert report_payload["claim_graph_path"] == str(paths.claim_graph_path)


def test_primitive_evidence_adapter_produces_points_and_axes(tmp_path: Path) -> None:
    image_path = _render(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    evidence = extract_coordinate_evidence(image_path)
    graph = primitive_graph_from_coordinates(evidence, image_path)
    point_primitives = [p for p in graph.primitives if p.type == "point"]
    line_primitives = [p for p in graph.primitives if p.type == "line"]
    assert len(point_primitives) == 4
    assert len(line_primitives) == 2
    assert graph.profile == "coordinate-graph-v1"


def test_extract_primitive_evidence_dispatches_coordinate_profile(tmp_path: Path) -> None:
    image_path = _render(tmp_path, POINTS, ["p1", "p2", "p3", "p4"])
    graph = extract_primitive_evidence(image_path, "coordinate-graph-v1")
    assert graph.profile == "coordinate-graph-v1"


@pytest.fixture(scope="module")
def coordinate_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset_root = tmp_path_factory.mktemp("coordinate-v1")
    build_coordinate_dataset(dataset_root)
    return dataset_root


def test_coordinate_dataset_structure(coordinate_dataset: Path) -> None:
    cases = discover_coordinate_cases(coordinate_dataset)
    assert len(cases) == 15
    assert sum(1 for case in cases if case.kind == "golden") == 6
    assert sum(1 for case in cases if case.kind == "mutated") == 9


def test_coordinate_dataset_validation_summary(coordinate_dataset: Path) -> None:
    summary = summarize_coordinate_validation_results(coordinate_dataset)
    assert summary["total_cases"] == 15
    assert summary["typed_mutated_cases"] == 7
    assert summary["typed_mutated_hits"] == 7
    assert summary["critical_error_recall"] == 1.0
    assert summary["ambiguous_cases"] == 2
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_failures"] == 0
    assert summary["golden_non_passes"] == 0
    assert summary["verdict_mismatches"] == 0


@pytest.fixture(scope="module")
def coordinate_noisy_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset_root = tmp_path_factory.mktemp("coordinate-v1-noisy")
    build_noisy_coordinate_dataset(dataset_root)
    return dataset_root


def test_coordinate_noisy_dataset_structure(coordinate_noisy_dataset: Path) -> None:
    cases = discover_coordinate_cases(coordinate_noisy_dataset)
    assert len(cases) == 6
    assert sum(1 for case in cases if case.kind == "golden") == 2
    assert sum(1 for case in cases if case.kind == "mutated") == 4
    assert all(case.dataset_track == "noisy" for case in cases)


def test_coordinate_noisy_dataset_validation_summary(coordinate_noisy_dataset: Path) -> None:
    summary = summarize_coordinate_validation_results(coordinate_noisy_dataset)
    assert summary["total_cases"] == 6
    assert summary["typed_mutated_cases"] == 4
    assert summary["typed_mutated_hits"] == 4
    assert summary["critical_error_recall"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_failures"] == 0
    assert summary["golden_non_passes"] == 0
    assert summary["verdict_mismatches"] == 0

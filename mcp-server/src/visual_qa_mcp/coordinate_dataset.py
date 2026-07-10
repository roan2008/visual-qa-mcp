from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from .chart_generator import write_json
from .coordinate_generator import (
    DEFAULT_PLOT_BOX,
    render_coordinate_diagram,
    x_value_to_pixel,
    y_value_to_pixel,
)

RED = [214, 48, 49]
BLUE = [9, 132, 227]
GREEN = [0, 148, 50]
PURPLE = [142, 68, 173]
ORANGE = [230, 126, 34]

COORDINATE_CHECKS: list[dict[str, Any]] = [
    {
        "id": "point-count-matches",
        "type": "point_count_matches",
        "severity": "high",
        "description": "The number of detected scatter points should match the declared points.",
    },
    {
        "id": "required-points-present",
        "type": "required_points_present",
        "severity": "critical",
        "description": "Every required point must be present with its declared color identity.",
        "params": {"color_match_distance": 60.0},
    },
    {
        "id": "point-positions-correct",
        "type": "point_positions_correct",
        "severity": "critical",
        "description": (
            "Each point's data-space position, derived from independent X/Y axis scales, "
            "must match its declared position within tolerance."
        ),
        "params": {"color_match_distance": 60.0},
    },
    {
        "id": "axis-scale-correct",
        "type": "axis_scale_correct",
        "severity": "critical",
        "description": "The displayed X and Y axis ranges must match the declared spec ranges.",
        "params": {"axis_value_tolerance": 0.5},
    },
]

POLYLINE_CHECK: dict[str, Any] = {
    "id": "polyline-connections-correct",
    "type": "polyline_connections_correct",
    "severity": "high",
    "description": (
        "The declared ordered polyline must connect its points in the declared order, "
        "verified against rendered line-pixel evidence."
    ),
    "params": {"color_match_distance": 60.0},
}


def _spec_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"id": point["id"], "name": point.get("name", point["id"]), "rgb": point["rgb"], "x": point["x"], "y": point["y"]}
        for point in points
    ]


def _ticks(axis: dict[str, Any], text_offset: int = 0) -> list[dict[str, Any]]:
    values = range(int(axis["min"]), int(axis["max"]) + 1, int(axis["step"]))
    return [
        {"value": value, "label_text": str(value + text_offset)} if text_offset else {"value": value}
        for value in values
    ]


def _render_points(
    points: list[dict[str, Any]],
    x_axis: dict[str, Any],
    y_axis: dict[str, Any],
    plot_box: list[float],
    render_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    overrides = render_overrides or {}
    rendered = []
    for point in points:
        center_px = [
            x_value_to_pixel(float(point["x"]), x_axis, plot_box),
            y_value_to_pixel(float(point["y"]), y_axis, plot_box),
        ]
        item = {"id": point["id"], "center_px": center_px, "rgb": point["rgb"]}
        item.update(overrides.get(point["id"], {}))
        rendered.append(item)
    return rendered


def _base_spec(
    case_id: str,
    points: list[dict[str, Any]],
    x_axis: dict[str, Any],
    y_axis: dict[str, Any],
    ordered_point_ids: list[str] | None,
) -> dict[str, Any]:
    source_reference: dict[str, Any] = {
        "x_axis": {"min": x_axis["min"], "max": x_axis["max"]},
        "y_axis": {"min": y_axis["min"], "max": y_axis["max"]},
        "points": _spec_points(points),
    }
    checks = deepcopy(COORDINATE_CHECKS)
    if ordered_point_ids is not None:
        source_reference["polyline"] = {"ordered_point_ids": ordered_point_ids}
        checks.append(deepcopy(POLYLINE_CHECK))
    return {
        "id": f"coordinate-{case_id}",
        "domain": "mathematics",
        "risk_level": "medium",
        "learning_objective": (
            "Read a coordinate plane where each scatter point has the correct position and "
            "color identity, and the connecting polyline links the declared points in order."
        ),
        "source_reference": source_reference,
        "required_elements": [
            {"id": "points", "kind": "point", "name": "scatter points", "count": len(points)},
        ],
        "labels": [],
        "relations": [],
        "checks": checks,
    }


def _case(
    case_id: str,
    title: str,
    kind: str,
    points: list[dict[str, Any]],
    x_axis: dict[str, Any],
    y_axis: dict[str, Any],
    expected_report: dict[str, Any],
    defect_type: str | None = None,
    ordered_point_ids: list[str] | None = None,
    render_ordered_point_ids: list[str] | None = None,
    render_overrides: dict[str, dict[str, Any]] | None = None,
    extra_render_points: list[dict[str, Any]] | None = None,
    drop_render_point_ids: list[str] | None = None,
    x_tick_text_offset: int = 0,
    y_tick_text_offset: int = 0,
    render_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plot_box = [float(value) for value in (render_options or {}).get("plot_box", DEFAULT_PLOT_BOX)]
    render_source = points
    if drop_render_point_ids:
        render_source = [point for point in render_source if point["id"] not in drop_render_point_ids]
    rendered_points = _render_points(render_source, x_axis, y_axis, plot_box, render_overrides)
    if extra_render_points:
        rendered_points.extend(deepcopy(extra_render_points))

    render_x_axis = {**x_axis, "ticks": _ticks(x_axis, x_tick_text_offset)}
    render_y_axis = {**y_axis, "ticks": _ticks(y_axis, y_tick_text_offset)}
    render_polyline_ids = (
        render_ordered_point_ids if render_ordered_point_ids is not None else ordered_point_ids
    )

    expected_report = deepcopy(expected_report)
    expected_report.setdefault("expected_evidence", {"point_count": None})
    return {
        "case_id": case_id,
        "title": title,
        "kind": kind,
        "defect_type": defect_type,
        "spec_points": points,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "ordered_point_ids": ordered_point_ids,
        "render_points": rendered_points,
        "render_x_axis": render_x_axis,
        "render_y_axis": render_y_axis,
        "render_polyline_ids": render_polyline_ids,
        "render_options": render_options or {},
        "expected_report": expected_report,
    }


def _linear_points() -> list[dict[str, Any]]:
    return [
        {"id": "p1", "name": "Point 1", "rgb": RED, "x": 10, "y": 5},
        {"id": "p2", "name": "Point 2", "rgb": BLUE, "x": 40, "y": 15},
        {"id": "p3", "name": "Point 3", "rgb": GREEN, "x": 70, "y": 35},
        {"id": "p4", "name": "Point 4", "rgb": PURPLE, "x": 95, "y": 48},
    ]


ZERO_BASELINE_X = {"min": 0, "max": 100, "step": 20}
ZERO_BASELINE_Y = {"min": 0, "max": 50, "step": 10}


def dataset_cases() -> list[dict[str, Any]]:
    def golden(point_count: int) -> dict[str, Any]:
        return {
            "verdict": "pass",
            "expected_finding_types": [],
            "expected_evidence": {"point_count": point_count},
        }

    non_zero_x = {"min": 20, "max": 120, "step": 10}
    non_zero_y = {"min": 30, "max": 90, "step": 10}
    non_zero_points = [
        {"id": "p1", "name": "Point 1", "rgb": RED, "x": 25, "y": 35},
        {"id": "p2", "name": "Point 2", "rgb": BLUE, "x": 60, "y": 55},
        {"id": "p3", "name": "Point 3", "rgb": GREEN, "x": 90, "y": 70},
        {"id": "p4", "name": "Point 4", "rgb": PURPLE, "x": 115, "y": 88},
    ]

    # Signed axis with X-scale != Y-scale: a naive extractor that reused one
    # axis's pixels-per-unit for both axes, or an identity pixel-to-data
    # mapping, would silently place every point at a detectably wrong
    # position here (X spans 200 units over ~560 px = 2.8 px/unit while Y
    # spans 100 units over ~420 px = 4.2 px/unit).
    dual_scale_x = {"min": -100, "max": 100, "step": 40}
    dual_scale_y = {"min": -50, "max": 50, "step": 20}
    dual_scale_points = [
        {"id": "p1", "name": "Point 1", "rgb": RED, "x": -90, "y": -45},
        {"id": "p2", "name": "Point 2", "rgb": BLUE, "x": -30, "y": -10},
        {"id": "p3", "name": "Point 3", "rgb": GREEN, "x": 20, "y": 15},
        {"id": "p4", "name": "Point 4", "rgb": PURPLE, "x": 85, "y": 40},
    ]

    small_x = {"min": 0, "max": 60, "step": 10}
    small_y = {"min": 0, "max": 30, "step": 5}
    small_points = [
        {"id": "p1", "name": "Point 1", "rgb": RED, "x": 5, "y": 25},
        {"id": "p2", "name": "Point 2", "rgb": BLUE, "x": 30, "y": 10},
        {"id": "p3", "name": "Point 3", "rgb": GREEN, "x": 55, "y": 28},
    ]

    return [
        _case(
            "golden-01",
            "Zero-baseline dual axis, four points on a polyline",
            "golden",
            _linear_points(),
            ZERO_BASELINE_X,
            ZERO_BASELINE_Y,
            golden(4),
            ordered_point_ids=["p1", "p2", "p3", "p4"],
        ),
        _case(
            "golden-02",
            "Non-zero-minimum dual axis, four points on a polyline",
            "golden",
            non_zero_points,
            non_zero_x,
            non_zero_y,
            golden(4),
            ordered_point_ids=["p1", "p2", "p3", "p4"],
        ),
        _case(
            "golden-03",
            "Signed axis with mismatched X/Y scale, four points on a polyline",
            "golden",
            dual_scale_points,
            dual_scale_x,
            dual_scale_y,
            golden(4),
            ordered_point_ids=["p1", "p2", "p3", "p4"],
        ),
        _case(
            "golden-04",
            "Three points, no polyline check requested",
            "golden",
            small_points,
            small_x,
            small_y,
            golden(3),
        ),
        _case(
            "mutated-01",
            "Missing declared point",
            "mutated",
            _linear_points(),
            ZERO_BASELINE_X,
            ZERO_BASELINE_Y,
            {
                "verdict": "fail",
                "expected_finding_types": ["point_count_mismatch", "missing_point"],
                "expected_evidence": {"point_count": 3},
            },
            defect_type="missing_point",
            ordered_point_ids=["p1", "p2", "p3", "p4"],
            drop_render_point_ids=["p3"],
            render_ordered_point_ids=["p1", "p2", "p4"],
        ),
        _case(
            "mutated-02",
            "Extra undeclared point",
            "mutated",
            _linear_points(),
            ZERO_BASELINE_X,
            ZERO_BASELINE_Y,
            {
                "verdict": "fail",
                "expected_finding_types": ["point_count_mismatch", "extra_point"],
                "expected_evidence": {"point_count": 5},
            },
            defect_type="extra_point",
            ordered_point_ids=["p1", "p2", "p3", "p4"],
            extra_render_points=[{"id": "extra", "center_px": [300, 100], "rgb": ORANGE}],
        ),
        _case(
            "mutated-03",
            "Point rendered at the wrong position",
            "mutated",
            _linear_points(),
            ZERO_BASELINE_X,
            ZERO_BASELINE_Y,
            {
                "verdict": "fail",
                "expected_finding_types": ["point_position_wrong"],
                "expected_evidence": {"point_count": 4},
            },
            defect_type="point_position_wrong",
            ordered_point_ids=["p1", "p2", "p3", "p4"],
            render_overrides={
                "p2": {
                    "center_px": [
                        x_value_to_pixel(85.0, ZERO_BASELINE_X, DEFAULT_PLOT_BOX),
                        y_value_to_pixel(15.0, ZERO_BASELINE_Y, DEFAULT_PLOT_BOX),
                    ]
                }
            },
            render_ordered_point_ids=["p1", "p3", "p4"],
        ),
        _case(
            "mutated-04",
            "Y-axis tick labels shifted, misreading the scale",
            "mutated",
            _linear_points(),
            ZERO_BASELINE_X,
            ZERO_BASELINE_Y,
            {
                "verdict": "fail",
                "expected_finding_types": ["axis_scale_misread"],
                "expected_evidence": {"point_count": 4},
            },
            defect_type="axis_scale_misread",
            ordered_point_ids=["p1", "p2", "p3", "p4"],
            y_tick_text_offset=10,
        ),
        _case(
            "mutated-05",
            "Polyline skips a declared point",
            "mutated",
            _linear_points(),
            ZERO_BASELINE_X,
            ZERO_BASELINE_Y,
            {
                "verdict": "fail",
                "expected_finding_types": ["polyline_connection_wrong"],
                "expected_evidence": {"point_count": 4},
            },
            defect_type="polyline_skips_point",
            ordered_point_ids=["p1", "p2", "p3", "p4"],
            render_ordered_point_ids=["p1", "p2", "p4"],
        ),
        _case(
            "mutated-06",
            "Two points share an ambiguous color",
            "mutated",
            _linear_points(),
            ZERO_BASELINE_X,
            ZERO_BASELINE_Y,
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"point_count": 4},
            },
            defect_type="ambiguous_point_colors",
            ordered_point_ids=["p1", "p2", "p3", "p4"],
            render_overrides={"p3": {"rgb": BLUE}},
        ),
        _case(
            "mutated-07",
            "Y-axis ticks removed, scale unreadable",
            "mutated",
            _linear_points(),
            ZERO_BASELINE_X,
            {**ZERO_BASELINE_Y, "step": 1000},
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"point_count": 4},
            },
            defect_type="unreadable_axis",
            ordered_point_ids=["p1", "p2", "p3", "p4"],
        ),
    ]


def build_coordinate_dataset(output_root: Path) -> None:
    build_coordinate_cases_dataset(output_root, dataset_cases(), dataset_track="controlled")


def build_coordinate_cases_dataset(
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

        spec = _base_spec(
            case["case_id"],
            case["spec_points"],
            case["x_axis"],
            case["y_axis"],
            ordered_point_ids=case["ordered_point_ids"],
        )
        metadata = {
            "case_id": case["case_id"],
            "title": case["title"],
            "kind": case["kind"],
            "defect_type": case["defect_type"],
            "scenario": "coordinate_plane",
            "dataset_track": dataset_track,
            "image_id": case["case_id"],
            "diagram_version": "coordinate-graph-v1",
            "render_options": case["render_options"],
            "renderer": "pillow",
        }

        write_json(case_dir / "visual_spec.json", spec)
        write_json(case_dir / "metadata.json", metadata)
        write_json(case_dir / "expected_report.json", case["expected_report"])
        render_coordinate_diagram(
            image_path=case_dir / "image.png",
            points=case["render_points"],
            polyline_point_ids=case["render_polyline_ids"],
            x_axis=case["render_x_axis"],
            y_axis=case["render_y_axis"],
            render_options=case["render_options"],
        )

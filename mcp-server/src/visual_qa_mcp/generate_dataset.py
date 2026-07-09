from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from .chart_generator import render_chart_image, write_json

BASE_MONTHS = ["Jan", "Feb", "Mar"]


def _source_data(values: list[float]) -> list[dict[str, Any]]:
    return [
        {"month": month, "rainfall_mm": value}
        for month, value in zip(BASE_MONTHS, values, strict=True)
    ]


def _render_data(labels: list[str], values: list[float]) -> list[dict[str, Any]]:
    return [{"label": label, "value": value} for label, value in zip(labels, values, strict=True)]


def _checks(axis_mode: str) -> list[dict[str, Any]]:
    checks = [
        {
            "id": "bar-values-match-data",
            "type": "chart_value_consistency",
            "severity": "critical",
            "description": "Bar heights should match the source data within tolerance.",
            "params": {"relative_tolerance": 0.05},
        },
        {
            "id": "axis-label-present",
            "type": "label_present",
            "severity": "high",
            "description": "The y-axis label must be visible.",
        },
        {
            "id": "axis-unit-present",
            "type": "axis_unit_present",
            "severity": "high",
            "description": "The y-axis unit must match the expected unit.",
        },
        {
            "id": "bar-count-matches",
            "type": "bar_count_matches",
            "severity": "high",
            "description": "The number of bars should match the source data.",
        },
        {
            "id": "axis-scale-readable",
            "type": "axis_scale_readable",
            "severity": "high",
            "description": "The chart must expose enough readable tick evidence to derive a stable numeric scale.",
        },
        {
            "id": "axis-scale-monotonic",
            "type": "axis_scale_monotonic",
            "severity": "high",
            "description": "Tick values must be monotonic and internally consistent.",
        },
    ]
    if axis_mode == "signed":
        checks.append(
            {
                "id": "axis-zero-line-resolved",
                "type": "axis_zero_line_resolved",
                "severity": "high",
                "description": "Signed charts must expose a resolvable zero line.",
            }
        )
    return checks


def _base_spec(
    case_id: str,
    source_reference: list[dict[str, Any]],
    axis_mode: str,
    expected_y_label: str,
    axis_min: float,
    axis_max: float,
) -> dict[str, Any]:
    labels = [{"text": item["month"], "target": "bars"} for item in source_reference]
    labels.append({"text": expected_y_label, "target": "y_axis"})
    return {
        "id": f"chart-{case_id}",
        "domain": "chart",
        "risk_level": "medium",
        "learning_objective": "Compare rainfall across months using a numerically correct bar chart.",
        "source_reference": {
            "data": source_reference,
            "axis": {
                "expected_scale_mode": axis_mode,
                "expected_min_value": axis_min,
                "expected_max_value": axis_max,
            },
        },
        "required_elements": [
            {"id": "x_axis", "kind": "axis", "name": "month axis", "count": 1},
            {"id": "y_axis", "kind": "axis", "name": "rainfall axis", "count": 1},
            {"id": "bars", "kind": "bar", "name": "rainfall bars", "count": len(source_reference)},
        ],
        "labels": labels,
        "relations": [],
        "checks": _checks(axis_mode),
    }


def _case(
    case_id: str,
    title: str,
    kind: str,
    axis_mode: str,
    source_values: list[float],
    render_labels: list[str],
    render_values: list[float],
    axis_config: dict[str, Any],
    expected_report: dict[str, Any],
    defect_type: str | None = None,
    spec_y_label: str = "Rainfall (mm)",
    display_y_label: str | None = None,
    render_options: dict[str, Any] | None = None,
    backend: str = "template",
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "title": title,
        "kind": kind,
        "axis_mode": axis_mode,
        "defect_type": defect_type,
        "source_data": _source_data(source_values),
        "render_data": _render_data(render_labels, render_values),
        "spec_y_label": spec_y_label,
        "axis_config": {
            "bar_axis": dict(axis_config["bar_axis"]),
            "display_ticks": list(axis_config["display_ticks"]),
            "y_label": display_y_label or spec_y_label,
        },
        "expected_report": expected_report,
        "render_options": render_options or {},
        "backend": backend,
    }


def dataset_cases() -> list[dict[str, Any]]:
    return [
        _case(
            "golden-01",
            "Zero baseline basic",
            "golden",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "pass", "expected_finding_types": []},
        ),
        _case(
            "golden-02",
            "Zero baseline layout variation",
            "golden",
            "zero_baseline",
            [30, 90, 60],
            BASE_MONTHS,
            [30, 90, 60],
            {"bar_axis": {"min": 0, "max": 120}, "display_ticks": [0, 30, 60, 90, 120]},
            {"verdict": "pass", "expected_finding_types": []},
            render_options={
                "layout_overrides": {
                    "width": 760,
                    "height": 540,
                    "margin_left": 144,
                    "margin_bottom": 122,
                    "axis_label_box": [210, 28, 700, 62],
                },
                "tick_font_size": 16,
                "x_label_font_size": 15,
            },
        ),
        _case(
            "golden-03",
            "Zero baseline color variation",
            "golden",
            "zero_baseline",
            [25, 50, 85],
            BASE_MONTHS,
            [25, 50, 85],
            {"bar_axis": {"min": 0, "max": 100}, "display_ticks": [0, 25, 50, 75, 100]},
            {"verdict": "pass", "expected_finding_types": []},
            render_options={"bar_fill": [45, 104, 230], "grid_fill": [230, 232, 238]},
        ),
        _case(
            "golden-04",
            "Non-zero minimum basic",
            "golden",
            "non_zero_min",
            [35, 65, 50],
            BASE_MONTHS,
            [35, 65, 50],
            {"bar_axis": {"min": 20, "max": 80}, "display_ticks": [20, 35, 50, 65, 80]},
            {"verdict": "pass", "expected_finding_types": []},
        ),
        _case(
            "golden-05",
            "Non-zero minimum layout variation",
            "golden",
            "non_zero_min",
            [25, 55, 40],
            BASE_MONTHS,
            [25, 55, 40],
            {"bar_axis": {"min": 10, "max": 70}, "display_ticks": [10, 25, 40, 55, 70]},
            {"verdict": "pass", "expected_finding_types": []},
            render_options={
                "layout_overrides": {
                    "width": 720,
                    "height": 500,
                    "margin_left": 136,
                    "margin_top": 92,
                    "axis_label_box": [200, 30, 650, 60],
                },
                "tick_font_size": 15,
                "x_label_font_size": 13,
            },
        ),
        _case(
            "golden-06",
            "Signed axis basic",
            "golden",
            "signed",
            [-20, 15, 50],
            BASE_MONTHS,
            [-20, 15, 50],
            {"bar_axis": {"min": -40, "max": 60}, "display_ticks": [-40, -20, 0, 20, 40, 60]},
            {"verdict": "pass", "expected_finding_types": []},
        ),
        _case(
            "golden-07",
            "Signed axis layout variation",
            "golden",
            "signed",
            [-30, 0, 45],
            BASE_MONTHS,
            [-30, 0, 45],
            {"bar_axis": {"min": -60, "max": 60}, "display_ticks": [-60, -30, 0, 30, 60]},
            {"verdict": "pass", "expected_finding_types": []},
            render_options={
                "layout_overrides": {
                    "width": 760,
                    "height": 520,
                    "margin_left": 146,
                    "margin_bottom": 118,
                    "axis_label_box": [214, 28, 710, 62],
                }
            },
        ),
        _case(
            "golden-08",
            "Signed axis color variation",
            "golden",
            "signed",
            [-25, 10, 35],
            BASE_MONTHS,
            [-25, 10, 35],
            {"bar_axis": {"min": -50, "max": 50}, "display_ticks": [-50, -25, 0, 25, 50]},
            {"verdict": "pass", "expected_finding_types": []},
            render_options={"bar_fill": [59, 132, 230], "axis_fill": [44, 44, 44]},
        ),
        _case(
            "mutated-01",
            "Wrong bar height zero baseline",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 40, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="wrong_bar_height",
        ),
        _case(
            "mutated-02",
            "Wrong axis unit",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "fail", "expected_finding_types": ["label_missing_or_wrong", "unit_mismatch"]},
            defect_type="wrong_axis_unit",
            display_y_label="Rainfall (cm)",
        ),
        _case(
            "mutated-03",
            "Missing one tick label",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="missing_tick_label",
            render_options={"tick_text_overrides": {"40": ""}},
        ),
        _case(
            "mutated-04",
            "Wrong tick order",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="wrong_tick_order",
            render_options={"tick_text_overrides": {"20": "40", "40": "20"}},
        ),
        _case(
            "mutated-05",
            "Wrong tick step",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="wrong_tick_step",
            render_options={"tick_text_overrides": {"40": "45"}},
        ),
        _case(
            "mutated-06",
            "Unreadable tick labels",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="unreadable_ticks",
            render_options={
                "tick_fill_overrides": {
                    "0": [228, 228, 228],
                    "20": [228, 228, 228],
                    "40": [228, 228, 228],
                    "60": [228, 228, 228],
                    "80": [228, 228, 228]
                }
            },
        ),
        _case(
            "mutated-07",
            "Shifted scale with correct bars",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 25, 50, 75, 100]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="shifted_scale",
        ),
        _case(
            "mutated-08",
            "Ambiguous zero line",
            "mutated",
            "signed",
            [-20, 15, 50],
            BASE_MONTHS,
            [-20, 15, 50],
            {"bar_axis": {"min": -40, "max": 60}, "display_ticks": [-40, -20, 0, 20, 40, 60]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="ambiguous_zero_line",
            render_options={"tick_text_overrides": {"0": ""}},
        ),
        _case(
            "mutated-09",
            "Wrong bar height non-zero minimum",
            "mutated",
            "non_zero_min",
            [35, 65, 50],
            BASE_MONTHS,
            [35, 45, 50],
            {"bar_axis": {"min": 20, "max": 80}, "display_ticks": [20, 35, 50, 65, 80]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="wrong_bar_height_non_zero",
        ),
        _case(
            "mutated-10",
            "Wrong positive signed bar",
            "mutated",
            "signed",
            [-20, 15, 50],
            BASE_MONTHS,
            [-20, 30, 50],
            {"bar_axis": {"min": -40, "max": 60}, "display_ticks": [-40, -20, 0, 20, 40, 60]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="wrong_positive_signed_bar",
        ),
        _case(
            "mutated-11",
            "Wrong negative signed bar",
            "mutated",
            "signed",
            [-20, 15, 50],
            BASE_MONTHS,
            [-35, 15, 50],
            {"bar_axis": {"min": -40, "max": 60}, "display_ticks": [-40, -20, 0, 20, 40, 60]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="wrong_negative_signed_bar",
        ),
        _case(
            "mutated-12",
            "Extra bar rendered",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            ["Jan", "Feb", "Mar", "Mar"],
            [20, 55, 75, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "fail", "expected_finding_types": ["bar_count_mismatch"]},
            defect_type="extra_bar",
        ),
        _case(
            "mutated-13",
            "Missing bar rendered",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            ["Jan", "Feb"],
            [20, 55],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "fail", "expected_finding_types": ["bar_count_mismatch"]},
            defect_type="missing_bar",
        ),
        _case(
            "mutated-14",
            "Signed non-monotonic ticks",
            "mutated",
            "signed",
            [-20, 15, 50],
            BASE_MONTHS,
            [-20, 15, 50],
            {"bar_axis": {"min": -40, "max": 60}, "display_ticks": [-40, -20, 0, 20, 40, 60]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="non_monotonic_signed_ticks",
            render_options={"tick_text_overrides": {"-20": "20", "20": "-20"}},
        ),
        _case(
            "mutated-15",
            "Non-zero minimum wrong displayed scale",
            "mutated",
            "non_zero_min",
            [35, 65, 50],
            BASE_MONTHS,
            [35, 65, 50],
            {"bar_axis": {"min": 20, "max": 80}, "display_ticks": [20, 35, 50, 65, 80]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="wrong_non_zero_scale_labels",
            render_options={"tick_text_overrides": {"20": "0", "35": "20", "50": "40", "65": "60", "80": "80"}},
        ),
        _case(
            "mutated-16",
            "OCR stretch optional backend",
            "mutated",
            "zero_baseline",
            [30, 90, 60],
            BASE_MONTHS,
            [30, 90, 60],
            {"bar_axis": {"min": 0, "max": 120}, "display_ticks": [0, 30, 60, 90, 120]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="ocr_stretch_optional_backend",
            render_options={
                "layout_overrides": {
                    "width": 780,
                    "height": 560,
                    "margin_left": 152,
                    "axis_label_box": [220, 30, 720, 64],
                },
                "tick_font_size": 22,
                "x_label_font_size": 16,
            },
            backend="optional_ocr",
        ),
    ]


def build_dataset(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    for case in dataset_cases():
        case_dir = output_root / case["kind"] / case["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)

        axis_min = float(case["axis_config"]["bar_axis"]["min"])
        axis_max = float(case["axis_config"]["bar_axis"]["max"])
        spec = _base_spec(
            case_id=case["case_id"],
            source_reference=deepcopy(case["source_data"]),
            axis_mode=case["axis_mode"],
            expected_y_label=case["spec_y_label"],
            axis_min=axis_min,
            axis_max=axis_max,
        )

        metadata = {
            "case_id": case["case_id"],
            "title": case["title"],
            "kind": case["kind"],
            "axis_mode": case["axis_mode"],
            "defect_type": case["defect_type"],
            "image_id": case["case_id"],
            "backend": case["backend"],
            "chart_version": "v2",
            "render_options": case["render_options"],
        }

        write_json(case_dir / "visual_spec.json", spec)
        write_json(case_dir / "metadata.json", metadata)
        write_json(case_dir / "expected_report.json", case["expected_report"])
        render_chart_image(
            image_path=case_dir / "image.png",
            data=case["render_data"],
            axis_config=case["axis_config"],
            metadata=case["render_options"],
        )

from __future__ import annotations

import shutil
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .chart_generator import render_chart_image, render_matplotlib_chart_image, write_json

BASE_MONTHS = ["Jan", "Feb", "Mar"]


def _source_data(values: list[float], labels: list[str] | None = None, generic: bool = False) -> list[dict[str, Any]]:
    labels = labels or BASE_MONTHS
    if generic:
        return [
            {"category": label, "value": value}
            for label, value in zip(labels, values, strict=True)
        ]
    return [
        {"month": month, "rainfall_mm": value}
        for month, value in zip(labels, values, strict=True)
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
    learning_objective: str = "Compare rainfall across months using a numerically correct bar chart.",
) -> dict[str, Any]:
    categories = [str(item.get("category", item.get("month"))) for item in source_reference]
    labels = [{"text": category, "target": "bars"} for category in categories]
    labels.append({"text": expected_y_label, "target": "y_axis"})
    return {
        "id": f"chart-{case_id}",
        "domain": "chart",
        "risk_level": "medium",
        "learning_objective": learning_objective,
        "source_reference": {
            "data": source_reference,
            "axis": {
                "expected_scale_mode": axis_mode,
                "expected_min_value": axis_min,
                "expected_max_value": axis_max,
            },
        },
        "required_elements": [
            {"id": "x_axis", "kind": "axis", "name": "category axis", "count": 1},
            {"id": "y_axis", "kind": "axis", "name": "value axis", "count": 1},
            {"id": "bars", "kind": "bar", "name": "value bars", "count": len(source_reference)},
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
    dataset_track: str = "controlled",
    source_labels: list[str] | None = None,
    learning_objective: str | None = None,
    renderer: str = "pillow",
    transform_family: str = "clean",
    provenance: dict[str, Any] | None = None,
    expected_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected_report = deepcopy(expected_report)
    if expected_evidence is not None:
        expected_report["expected_evidence"] = expected_evidence
    return {
        "case_id": case_id,
        "title": title,
        "kind": kind,
        "dataset_track": dataset_track,
        "axis_mode": axis_mode,
        "defect_type": defect_type,
        "source_data": _source_data(
            source_values,
            labels=source_labels,
            generic=source_labels is not None,
        ),
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
        "learning_objective": learning_objective or "Compare rainfall across months using a numerically correct bar chart.",
        "renderer": renderer,
        "transform_family": transform_family,
        "provenance": provenance or {},
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


def noisy_dataset_cases() -> list[dict[str, Any]]:
    return [
        _case(
            "noisy-golden-01",
            "Noisy zero baseline compressed",
            "golden",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "pass", "expected_finding_types": []},
            dataset_track="noisy",
            render_options={
                "layout_overrides": {"width": 744, "height": 516, "margin_left": 142, "axis_label_box": [196, 26, 660, 60]},
                "tick_font_size": 17,
                "x_label_font_size": 15,
                "postprocess": {"downscale_factor": 0.82, "jpeg_quality": 82},
            },
        ),
        _case(
            "noisy-golden-02",
            "Noisy signed blurred",
            "golden",
            "signed",
            [-25, 10, 35],
            BASE_MONTHS,
            [-25, 10, 35],
            {"bar_axis": {"min": -50, "max": 50}, "display_ticks": [-50, -25, 0, 25, 50]},
            {"verdict": "pass", "expected_finding_types": []},
            dataset_track="noisy",
            render_options={
                "bar_fill": [62, 128, 226],
                "grid_fill": [226, 230, 238],
                "postprocess": {"blur_radius": 0.35, "downscale_factor": 0.9},
            },
        ),
        _case(
            "noisy-mutated-01",
            "Noisy wrong bar height",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 38, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="wrong_bar_height",
            dataset_track="noisy",
            render_options={
                "postprocess": {"downscale_factor": 0.85, "jpeg_quality": 80},
                "tick_jitter": {"20": 1, "40": -1, "60": 1},
            },
        ),
        _case(
            "noisy-mutated-02",
            "Noisy unreadable ticks",
            "mutated",
            "zero_baseline",
            [20, 55, 75],
            BASE_MONTHS,
            [20, 55, 75],
            {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="unreadable_ticks",
            dataset_track="noisy",
            render_options={
                "tick_fill_overrides": {"0": [236, 236, 236], "20": [236, 236, 236], "40": [236, 236, 236], "60": [236, 236, 236], "80": [236, 236, 236]},
                "postprocess": {"blur_radius": 0.45, "downscale_factor": 0.84},
            },
        ),
        _case(
            "noisy-mutated-03",
            "Noisy shifted scale",
            "mutated",
            "non_zero_min",
            [35, 65, 50],
            BASE_MONTHS,
            [35, 65, 50],
            {"bar_axis": {"min": 20, "max": 80}, "display_ticks": [20, 35, 50, 65, 80]},
            {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]},
            defect_type="wrong_non_zero_scale_labels",
            dataset_track="noisy",
            render_options={
                "tick_text_overrides": {"20": "0", "35": "20", "50": "40", "65": "60", "80": "80"},
                "postprocess": {"jpeg_quality": 78},
            },
        ),
        _case(
            "noisy-mutated-04",
            "Noisy OCR stretch",
            "mutated",
            "zero_baseline",
            [30, 90, 60],
            BASE_MONTHS,
            [30, 90, 60],
            {"bar_axis": {"min": 0, "max": 120}, "display_ticks": [0, 30, 60, 90, 120]},
            {"verdict": "needs_review", "expected_finding_types": []},
            defect_type="ocr_stretch_optional_backend",
            dataset_track="noisy",
            backend="optional_ocr",
            render_options={
                "layout_overrides": {"width": 792, "height": 562, "margin_left": 156, "axis_label_box": [224, 30, 724, 66]},
                "tick_font_size": 22,
                "x_label_font_size": 16,
                "postprocess": {"downscale_factor": 0.88, "jpeg_quality": 76},
            },
        ),
    ]


WORLD_BANK_POPULATION_2023 = {
    "MYS": 35126298,
    "THA": 71702435,
    "VNM": 100352192,
}


def _world_bank_population_provenance() -> dict[str, Any]:
    snapshot = {
        "indicator": "SP.POP.TOTL",
        "year": 2023,
        "values": WORLD_BANK_POPULATION_2023,
        "normalized_millions": {"MYS": 35.0, "THA": 72.0, "VNM": 100.0},
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "source_type": "public_reference_snapshot",
        "source_url": "https://api.worldbank.org/v2/country/THA;VNM;MYS/indicator/SP.POP.TOTL?date=2023&format=json",
        "license": "CC BY 4.0",
        "license_url": "https://datacatalog.worldbank.org/public-licenses#cc-by",
        "attribution": "The World Bank: World Development Indicators, Population, total (SP.POP.TOTL), 2023.",
        "retrieved_at": "2026-07-10",
        "source_sha256": hashlib.sha256(canonical).hexdigest(),
        "source_snapshot": snapshot,
        "normalization": "Population totals rounded to whole millions for integer tick-reader validation.",
    }


def _pilot_expected_evidence(
    labels: list[str],
    displayed_values: list[float],
    tick_values: list[float] | None,
    axis_mode: str,
    y_label: str,
) -> dict[str, Any]:
    return {
        "bar_count": len(labels),
        "displayed_bar_values": {
            label: float(value) for label, value in zip(labels, displayed_values, strict=True)
        },
        "tick_values": [float(value) for value in tick_values] if tick_values is not None else None,
        "axis_mode": axis_mode,
        "labels": labels,
        "y_label": y_label,
    }


def realworld_pilot_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    renderer_provenance = {
        "source_type": "project_generated",
        "license": "repository test fixture",
        "source_url": None,
        "retrieved_at": "2026-07-10",
    }

    renderer_definitions = [
        ("rw-render-golden-01", "golden", "pillow", [20, 55, 75], [20, 55, 75], "zero_baseline", 0, 80, [0, 20, 40, 60, 80], {}, "pass", [], "jpeg_resize"),
        ("rw-render-golden-02", "golden", "matplotlib", [25, 50, 75], [25, 50, 75], "zero_baseline", 0, 100, [0, 25, 50, 75, 100], {}, "pass", [], "alternate_renderer"),
        ("rw-render-golden-03", "golden", "pillow", [-20, 15, 40], [-20, 15, 40], "signed", -50, 50, [-50, -25, 0, 25, 50], {"postprocess": {"blur_radius": 0.25}}, "pass", [], "signed_blur"),
        ("rw-render-golden-04", "golden", "matplotlib", [35, 50, 65], [35, 50, 65], "non_zero_min", 20, 80, [20, 35, 50, 65, 80], {}, "pass", [], "non_zero_renderer"),
        ("rw-render-mutated-01", "mutated", "pillow", [20, 55, 75], [20, 35, 75], "zero_baseline", 0, 80, [0, 20, 40, 60, 80], {"postprocess": {"jpeg_quality": 84}}, "fail", ["chart_value_mismatch"], "wrong_bar_height"),
        ("rw-render-mutated-02", "mutated", "matplotlib", [25, 50, 75], [25, 70, 75], "zero_baseline", 0, 100, [0, 25, 50, 75, 100], {}, "fail", ["chart_value_mismatch"], "wrong_bar_height"),
        ("rw-render-mutated-03", "mutated", "pillow", [20, 55, 75], [20, 55, 75], "zero_baseline", 0, 80, [0, 20, 40, 60, 80], {"tick_text_overrides": {"20": "25", "40": "50", "60": "75", "80": "100"}}, "fail", ["chart_value_mismatch"], "shifted_scale"),
        ("rw-render-mutated-04", "mutated", "matplotlib", [20, 55, 75], [20, 55, 75], "zero_baseline", 0, 80, [0, 20, 40, 60, 80], {}, "fail", ["label_missing_or_wrong", "unit_mismatch"], "wrong_axis_unit"),
        ("rw-render-ambiguous-01", "mutated", "pillow", [20, 55, 75], [20, 55, 75], "zero_baseline", 0, 80, [0, 20, 40, 60, 80], {"tick_fill_overrides": {str(value): [238, 238, 238] for value in [0, 20, 40, 60, 80]}}, "needs_review", [], "unreadable_ticks"),
        ("rw-render-ambiguous-02", "mutated", "matplotlib", [25, 50, 75], [25, 50, 75], "zero_baseline", 0, 100, [0, 25, 50, 75, 100], {"tick_label_fill": [238, 238, 238]}, "needs_review", [], "unreadable_ticks"),
        ("rw-render-ambiguous-03", "mutated", "pillow", [20, 55, 75], [20, 55, 75], "zero_baseline", 0, 80, [0, 20, 40, 60, 80], {"axis_label_fill": [238, 238, 238]}, "needs_review", [], "unreadable_axis_label"),
        ("rw-render-ambiguous-04", "mutated", "matplotlib", [25, 50, 75], [25, 50, 75], "zero_baseline", 0, 100, [0, 25, 50, 75, 100], {"tick_label_fill": [238, 238, 238], "postprocess": {"blur_radius": 0.7, "downscale_factor": 0.72}}, "needs_review", [], "heavy_resample"),
    ]
    for case_id, kind, renderer, source_values, render_values, axis_mode, axis_min, axis_max, ticks, options, verdict, finding_types, family in renderer_definitions:
        display_label = "Rainfall (cm)" if family == "wrong_axis_unit" else "Rainfall (mm)"
        readable_ticks = None if kind == "mutated" and not finding_types else [float(options.get("tick_text_overrides", {}).get(str(value), value)) for value in ticks]
        cases.append(
            _case(
                case_id,
                f"Renderer-diverse pilot: {family}",
                kind,
                axis_mode,
                source_values,
                BASE_MONTHS,
                render_values,
                {"bar_axis": {"min": axis_min, "max": axis_max}, "display_ticks": ticks},
                {"verdict": verdict, "expected_finding_types": finding_types},
                defect_type=None if kind == "golden" else family,
                display_y_label=display_label,
                render_options=options,
                dataset_track="realworld_pilot",
                renderer=renderer,
                transform_family=family,
                provenance=renderer_provenance,
                expected_evidence=_pilot_expected_evidence(BASE_MONTHS, render_values, readable_ticks, axis_mode, display_label),
            )
        )
        if family in {"unreadable_axis_label", "heavy_resample"}:
            cases[-1]["expected_report"]["expected_evidence"]["labels"] = None

    public_labels = ["Malaysia", "Thailand", "Vietnam"]
    public_values = [35, 72, 100]
    public_provenance = _world_bank_population_provenance()
    public_definitions = [
        ("rw-public-golden-01", "golden", "pillow", public_values, {}, "pass", [], "public_clean"),
        ("rw-public-golden-02", "golden", "pillow", public_values, {"postprocess": {"jpeg_quality": 86}}, "pass", [], "public_jpeg"),
        ("rw-public-golden-03", "golden", "pillow", public_values, {"postprocess": {"blur_radius": 0.25}}, "pass", [], "public_blur"),
        ("rw-public-golden-04", "golden", "matplotlib", public_values, {}, "pass", [], "public_renderer"),
        ("rw-public-golden-05", "golden", "matplotlib", public_values, {"postprocess": {"downscale_factor": 0.86}}, "pass", [], "public_renderer_resize"),
        ("rw-public-golden-06", "golden", "pillow", public_values, {"layout_overrides": {"width": 780, "height": 540, "margin_left": 150, "axis_label_box": [190, 26, 730, 60]}}, "pass", [], "public_wide_layout"),
        ("rw-public-mutated-01", "mutated", "pillow", [35, 55, 100], {"postprocess": {"jpeg_quality": 84}}, "fail", ["chart_value_mismatch"], "public_wrong_bar"),
        ("rw-public-mutated-02", "mutated", "matplotlib", public_values, {"tick_text_overrides": {"30": "40", "60": "80", "90": "120", "120": "160"}}, "fail", ["chart_value_mismatch"], "public_shifted_scale"),
        ("rw-public-mutated-03", "mutated", "pillow", public_values, {}, "fail", ["label_missing_or_wrong", "unit_mismatch"], "public_wrong_unit"),
        ("rw-public-ambiguous-01", "mutated", "pillow", public_values, {"tick_fill_overrides": {str(value): [238, 238, 238] for value in [0, 30, 60, 90, 120]}}, "needs_review", [], "public_unreadable_ticks"),
        ("rw-public-ambiguous-02", "mutated", "matplotlib", public_values, {"axis_label_fill": [238, 238, 238]}, "needs_review", [], "public_unreadable_label"),
        ("rw-public-ambiguous-03", "mutated", "pillow", public_values, {"postprocess": {"blur_radius": 0.8, "downscale_factor": 0.70}}, "needs_review", [], "public_heavy_resample"),
    ]
    for case_id, kind, renderer, render_values, options, verdict, finding_types, family in public_definitions:
        display_label = "Population (thousands)" if family == "public_wrong_unit" else "Population (millions)"
        readable_ticks = None if kind == "mutated" and not finding_types else [float(options.get("tick_text_overrides", {}).get(str(value), value)) for value in [0, 30, 60, 90, 120]]
        cases.append(
            _case(
                case_id,
                f"World Bank reference-backed pilot: {family}",
                kind,
                "zero_baseline",
                public_values,
                public_labels,
                render_values,
                {"bar_axis": {"min": 0, "max": 120}, "display_ticks": [0, 30, 60, 90, 120]},
                {"verdict": verdict, "expected_finding_types": finding_types},
                defect_type=None if kind == "golden" else family,
                spec_y_label="Population (millions)",
                display_y_label=display_label,
                render_options=options,
                dataset_track="realworld_pilot",
                source_labels=public_labels,
                learning_objective="Compare 2023 population totals for Malaysia, Thailand, and Vietnam in millions.",
                renderer=renderer,
                transform_family=family,
                provenance=public_provenance,
                expected_evidence=_pilot_expected_evidence(public_labels, render_values, readable_ticks, "zero_baseline", display_label),
            )
        )
        if family in {"public_unreadable_label", "public_heavy_resample"}:
            cases[-1]["expected_report"]["expected_evidence"]["labels"] = None
    return cases


def covering_array_cases() -> list[dict[str, Any]]:
    """chart-v2 formal input model, per wiki/knowledge-synthetic-coverage-deep-research.md.

    Matrix A: every axis at its in-universe level (catalog ticks, Arial font on
    matplotlib) crossed with color style and defect type. Space is small enough
    (2x3 per renderer) to enumerate exhaustively rather than needing a t-way
    covering-array algorithm; that thinness is itself the finding.
    Set B: any single axis flipped to its out-of-universe level (off-catalog
    ticks, or non-Arial font on matplotlib), crossed with a couple of defect
    levels to test that evidence degradation masks defect detection down to
    needs_review rather than a wrong pass/fail.
    """
    source_values = [20, 55, 75]
    catalog_axis = {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80]}
    off_catalog_axis = {"bar_axis": {"min": 0, "max": 100}, "display_ticks": [0, 22, 47, 83, 100]}

    color_levels: dict[str, dict[str, Any]] = {
        "default": {},
        "custom": {"bar_fill": [45, 104, 230], "grid_fill": [230, 232, 238]},
    }
    defect_levels: dict[str, tuple[list[float], dict[str, Any]]] = {
        "none": (source_values, {"verdict": "pass", "expected_finding_types": []}),
        "wrong_bar_height": ([20, 40, 75], {"verdict": "fail", "expected_finding_types": ["chart_value_mismatch"]}),
        "wrong_axis_unit": (source_values, {"verdict": "fail", "expected_finding_types": ["label_missing_or_wrong", "unit_mismatch"]}),
    }

    def provenance(universe: str, axes: dict[str, str]) -> dict[str, Any]:
        return {
            "source_type": "synthetic_generated",
            "license": "n/a_internal",
            "retrieved_at": "2026-07-11",
            "universe": universe,
            "axes": axes,
        }

    cases: list[dict[str, Any]] = []

    for renderer in ("pillow", "matplotlib"):
        for color_name, color_options in color_levels.items():
            for defect_name, (render_values, expected_report) in defect_levels.items():
                display_y_label = "Rainfall (cm)" if defect_name == "wrong_axis_unit" else None
                cases.append(
                    _case(
                        f"covering-a-{renderer}-{color_name}-{defect_name}",
                        f"Matrix A: {renderer}/{color_name}/{defect_name}",
                        "golden" if defect_name == "none" else "mutated",
                        "zero_baseline",
                        source_values,
                        BASE_MONTHS,
                        render_values,
                        catalog_axis,
                        expected_report,
                        defect_type=None if defect_name == "none" else defect_name,
                        display_y_label=display_y_label,
                        render_options=dict(color_options),
                        dataset_track="covering_array",
                        renderer=renderer,
                        transform_family="in_universe",
                        provenance=provenance(
                            "in",
                            {
                                "tick_catalog": "catalog",
                                "font_family": "arial" if renderer == "matplotlib" else "n/a",
                                "color_style": color_name,
                                "defect": defect_name,
                            },
                        ),
                    )
                )

    def set_b_case(renderer: str, out_axis: str, defect_name: str) -> dict[str, Any]:
        render_values, _ = defect_levels[defect_name]
        expected_report = {"verdict": "needs_review", "expected_finding_types": []}
        render_options: dict[str, Any] = {}
        axis_config = catalog_axis
        if out_axis == "off_catalog_ticks":
            axis_config = off_catalog_axis
        elif out_axis == "non_arial_font":
            render_options["font_family"] = "DejaVu Serif"
        return _case(
            f"covering-b-{renderer}-{out_axis}-{defect_name}",
            f"Set B: {renderer}/{out_axis}/{defect_name}",
            "mutated",
            "zero_baseline",
            source_values,
            BASE_MONTHS,
            render_values,
            axis_config,
            expected_report,
            defect_type=f"{out_axis}__{defect_name}",
            render_options=render_options,
            dataset_track="covering_array",
            renderer=renderer,
            transform_family="out_of_universe",
            provenance=provenance("out", {"out_axis": out_axis, "defect": defect_name}),
        )

    for renderer in ("pillow", "matplotlib"):
        for defect_name in ("none", "wrong_bar_height"):
            cases.append(set_b_case(renderer, "off_catalog_ticks", defect_name))
    for defect_name in ("none", "wrong_bar_height"):
        cases.append(set_b_case("matplotlib", "non_arial_font", defect_name))

    return cases


def build_covering_array_dataset(output_root: Path) -> None:
    build_cases_dataset(output_root, covering_array_cases())
    manifest_cases: list[dict[str, Any]] = []
    for metadata_path in sorted(output_root.glob("**/metadata.json")):
        case_dir = metadata_path.parent
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        checksums = {}
        for name in ("image.png", "visual_spec.json", "expected_report.json", "metadata.json"):
            path = case_dir / name
            checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_cases.append(
            {
                "case_id": metadata["case_id"],
                "relative_path": str(case_dir.relative_to(output_root)).replace("\\", "/"),
                "checksums": checksums,
                "provenance": metadata.get("provenance", {}),
            }
        )
    write_json(
        output_root / "manifest.json",
        {
            "dataset": "chart-v2-covering-v1",
            "status": "frozen",
            "frozen_at": "2026-07-11",
            "case_count": len(manifest_cases),
            "cases": manifest_cases,
        },
    )


def build_dataset(output_root: Path) -> None:
    build_cases_dataset(output_root, dataset_cases())


def build_noisy_dataset(output_root: Path) -> None:
    build_cases_dataset(output_root, noisy_dataset_cases())


def build_realworld_pilot_dataset(output_root: Path) -> None:
    build_cases_dataset(output_root, realworld_pilot_cases())
    manifest_cases: list[dict[str, Any]] = []
    for metadata_path in sorted(output_root.glob("**/metadata.json")):
        case_dir = metadata_path.parent
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        checksums = {}
        for name in ("image.png", "visual_spec.json", "expected_report.json", "metadata.json"):
            path = case_dir / name
            checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_cases.append(
            {
                "case_id": metadata["case_id"],
                "relative_path": str(case_dir.relative_to(output_root)).replace("\\", "/"),
                "checksums": checksums,
                "provenance": metadata.get("provenance", {}),
            }
        )
    write_json(
        output_root / "manifest.json",
        {
            "dataset": "chart-v2-realworld-pilot",
            "status": "pilot_only",
            "frozen_at": "2026-07-10",
            "case_count": len(manifest_cases),
            "cases": manifest_cases,
        },
    )


def build_cases_dataset(output_root: Path, cases: list[dict[str, Any]]) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    for case in cases:
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
            learning_objective=case.get("learning_objective", "Compare rainfall across months using a numerically correct bar chart."),
        )

        metadata = {
            "case_id": case["case_id"],
            "title": case["title"],
            "kind": case["kind"],
            "axis_mode": case["axis_mode"],
            "defect_type": case["defect_type"],
            "dataset_track": case.get("dataset_track", "controlled"),
            "image_id": case["case_id"],
            "backend": case["backend"],
            "chart_version": "v2",
            "render_options": case["render_options"],
            "renderer": case.get("renderer", "pillow"),
            "transform_family": case.get("transform_family", "clean"),
            "provenance": case.get("provenance", {}),
        }

        write_json(case_dir / "visual_spec.json", spec)
        write_json(case_dir / "metadata.json", metadata)
        write_json(case_dir / "expected_report.json", case["expected_report"])
        render_function = render_matplotlib_chart_image if case.get("renderer") == "matplotlib" else render_chart_image
        render_function(
            image_path=case_dir / "image.png",
            data=case["render_data"],
            axis_config=case["axis_config"],
            metadata=case["render_options"],
        )

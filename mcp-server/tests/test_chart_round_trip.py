from __future__ import annotations

from pathlib import Path

import pytest

from visual_qa_mcp.chart_generator import render_chart_image
from visual_qa_mcp.chart_round_trip import (
    build_round_trip_inputs,
    compare_bar_geometry,
    measure_bar_geometry,
    run_round_trip_check,
)
from visual_qa_mcp.contracts import AxisMapping, EvidenceGraph, ExtractedAxis, ExtractedBar, ExtractionProvenance, TickLabel
from visual_qa_mcp.generate_dataset import build_dataset
from visual_qa_mcp.service import run_chart_verification
from visual_qa_mcp.validation import discover_cases


def make_evidence(
    bars: list[ExtractedBar],
    mapping: AxisMapping | None,
    tick_values: list[float] | None = None,
) -> EvidenceGraph:
    tick_values = tick_values if tick_values is not None else [0, 20, 40, 60, 80]
    ticks = [
        TickLabel(text=str(int(value)), parsed_value=value, bbox=[24, 80 + idx * 40, 88, 102 + idx * 40], confidence=0.9)
        for idx, value in enumerate(tick_values)
    ]
    return EvidenceGraph(
        image_id="test-image",
        chart_type="bar",
        bars=bars,
        x_axis_labels=[bar.category for bar in bars],
        y_axis=ExtractedAxis(
            label_text="Rainfall (mm)",
            unit_text="mm",
            label_bbox=[150, 24, 500, 52],
            confidence=0.9,
            tick_labels=ticks,
            axis_line_x=130,
            baseline_y=320,
            top_y=80,
            zero_line_y=None,
            mapping=mapping,
            backend="template",
        ),
        extraction_confidence=0.9,
        provenance=ExtractionProvenance(
            extractor_id="chart-v2",
            extractor_version="0.2.0",
            backend="template",
            metadata_source="file",
            dependency_versions={},
            environment={},
        ),
        gaps=[],
        metadata={"axis_mode": "zero_baseline"},
    )


def make_bar(label: str, value: float | None, bbox: list[int] | None = None) -> ExtractedBar:
    return ExtractedBar(
        bar_id=f"bar-{label}",
        category=label,
        value=value,
        bbox=bbox or [100, 100, 140, 320],
        confidence=0.9,
        matched_label=label,
        top_y=100,
        bottom_y=320,
        value_source="axis_mapping",
    )


DEFAULT_MAPPING = AxisMapping(
    min_value=0,
    max_value=80,
    pixels_per_unit=4.0,
    scale_mode="zero_baseline",
    value_direction="positive_up",
    readable=True,
)


def test_build_round_trip_inputs_produces_well_formed_generator_inputs() -> None:
    evidence = make_evidence([make_bar("Jan", 40.0), make_bar("Feb", 60.0)], DEFAULT_MAPPING)
    inputs = build_round_trip_inputs(evidence)
    assert inputs is not None
    data, axis_config, metadata = inputs
    assert data == [{"label": "Jan", "value": 40.0}, {"label": "Feb", "value": 60.0}]
    assert axis_config["bar_axis"] == {"min": 0, "max": 80}
    assert axis_config["display_ticks"] == [0, 20, 40, 60, 80]
    assert axis_config["y_label"] == "Rainfall (mm)"
    assert isinstance(metadata, dict)


def test_build_round_trip_inputs_returns_none_without_axis_mapping() -> None:
    evidence = make_evidence([make_bar("Jan", 40.0)], mapping=None)
    assert build_round_trip_inputs(evidence) is None


def test_build_round_trip_inputs_returns_none_with_unresolved_value() -> None:
    evidence = make_evidence([make_bar("Jan", None)], DEFAULT_MAPPING)
    assert build_round_trip_inputs(evidence) is None


def test_measure_bar_geometry_on_known_rendered_image(tmp_path: Path) -> None:
    image_path = tmp_path / "known.png"
    data = [{"label": "Jan", "value": 40.0}, {"label": "Feb", "value": 60.0}, {"label": "Mar", "value": 10.0}]
    axis_config = {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 20, 40, 60, 80], "y_label": "Rainfall (mm)"}
    render_chart_image(image_path, data, axis_config, metadata={})

    regions = measure_bar_geometry(image_path)
    assert len(regions) == 3
    # left-to-right order should match input data order
    lefts = [region[0] for region in regions]
    assert lefts == sorted(lefts)


def test_compare_bar_geometry_reports_bar_count_mismatch() -> None:
    bars = [make_bar("Jan", 40.0), make_bar("Feb", 60.0)]
    comparison = compare_bar_geometry(bars, [[10, 10, 20, 20]])
    assert comparison.status == "bar_count_mismatch"
    assert comparison.bar_deltas == []


def test_run_round_trip_check_end_to_end_on_golden_case(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    result = run_chart_verification(case.image_path, case.spec_path, case.metadata_path, backend=case.backend)

    assert result.round_trip is not None
    comparison = result.round_trip
    assert comparison.status == "ok"
    assert comparison.max_top_y_delta_px is not None
    # Smoke-test ceiling, not a product tolerance: axis-mapping self-consistency
    # on a golden case should be well within a handful of pixels.
    assert comparison.max_top_y_delta_px < 10
    assert comparison.max_height_delta_px < 10


def test_run_round_trip_check_skips_without_axis_mapping(tmp_path: Path) -> None:
    evidence = make_evidence([make_bar("Jan", 40.0)], mapping=None)
    image_path = tmp_path / "unused.png"
    render_chart_image(
        image_path,
        [{"label": "Jan", "value": 40.0}],
        {"bar_axis": {"min": 0, "max": 80}, "display_ticks": [0, 40, 80], "y_label": "Rainfall (mm)"},
        metadata={},
    )
    comparison = run_round_trip_check(evidence, image_path)
    assert comparison.status == "skipped_no_axis_mapping"


def test_round_trip_never_raises_when_rendering_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import visual_qa_mcp.chart_round_trip as chart_round_trip_module

    def _broken_render(*_args, **_kwargs) -> None:
        raise RuntimeError("simulated render failure")

    monkeypatch.setattr(chart_round_trip_module, "render_chart_image", _broken_render)
    evidence = make_evidence([make_bar("Jan", 40.0)], DEFAULT_MAPPING)
    comparison = run_round_trip_check(evidence, tmp_path / "does-not-exist.png")
    assert comparison.status == "error"
    assert comparison.notes


def test_verdict_unaffected_by_round_trip_inclusion(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    with_round_trip = run_chart_verification(
        case.image_path, case.spec_path, case.metadata_path, backend=case.backend, include_round_trip=True
    )
    without_round_trip = run_chart_verification(
        case.image_path, case.spec_path, case.metadata_path, backend=case.backend, include_round_trip=False
    )

    assert without_round_trip.round_trip is None
    assert with_round_trip.round_trip is not None
    assert with_round_trip.report.to_dict() == without_round_trip.report.to_dict()

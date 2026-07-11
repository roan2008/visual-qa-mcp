from __future__ import annotations

import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

from .chart_extractor import _find_bar_regions, _load_image, detect_plot_area
from .chart_generator import render_chart_image
from .contracts import BarGeometryDelta, EvidenceGraph, ExtractedBar, RoundTripComparison

# Round-trip renders use generator defaults for colors/fonts because EvidenceGraph does not
# capture the original image's palette. Geometry-affecting keys (layout_overrides, font sizes)
# are carried through from the original case's render_options when available, so the check
# compares like-for-like plot-area geometry instead of confounding layout differences with
# real extraction bugs. See wiki/impl-chart-v2-round-trip-check.md.
_GEOMETRY_METADATA_KEYS = ("layout_overrides", "tick_font_size", "x_label_font_size")


def geometry_render_metadata(render_options: dict[str, Any] | None) -> dict[str, Any]:
    """Whitelist the render_options keys that affect plot-area geometry (not noise/style)."""
    if not render_options:
        return {}
    return {key: render_options[key] for key in _GEOMETRY_METADATA_KEYS if key in render_options}


def measure_bar_geometry(image_path: Path) -> list[list[int]]:
    """Spec-independent low-level bar bbox measurement, reusable on any chart-v2-style image."""
    image = _load_image(image_path)
    rgb = np.array(image)
    plot_info = detect_plot_area(rgb)
    return _find_bar_regions(rgb, plot_info)


def build_round_trip_inputs(
    evidence: EvidenceGraph,
    render_metadata: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]] | None:
    """Adapter: EvidenceGraph -> (data, axis_config, metadata) for render_chart_image.

    Returns None if the evidence does not carry enough information to render
    (missing axis mapping or unresolved bar values) rather than guessing.
    """
    mapping = evidence.y_axis.mapping
    if mapping is None:
        return None
    if not evidence.bars:
        return None
    if any(bar.value is None for bar in evidence.bars):
        return None

    data = [
        {"label": bar.category or f"bar-{index}", "value": float(bar.value)}
        for index, bar in enumerate(evidence.bars)
    ]

    tick_values = sorted(
        {
            tick.parsed_value
            for tick in evidence.y_axis.tick_labels
            if tick.parsed_value is not None
        }
    )
    if len(tick_values) < 2:
        tick_values = [mapping.min_value, mapping.max_value]

    axis_config = {
        "bar_axis": {"min": mapping.min_value, "max": mapping.max_value},
        "display_ticks": tick_values,
        "y_label": evidence.y_axis.label_text or "",
    }
    metadata = geometry_render_metadata(render_metadata)
    return data, axis_config, metadata


def render_round_trip_image(
    evidence: EvidenceGraph,
    output_path: Path,
    render_metadata: dict[str, Any] | None = None,
) -> bool:
    """Render a fresh chart image from extracted evidence. Returns False if evidence is insufficient."""
    inputs = build_round_trip_inputs(evidence, render_metadata)
    if inputs is None:
        return False
    data, axis_config, metadata = inputs
    render_chart_image(output_path, data, axis_config, metadata)
    return True


def compare_bar_geometry(
    original_bars: list[ExtractedBar],
    round_trip_regions: list[list[int]],
) -> RoundTripComparison:
    if len(original_bars) != len(round_trip_regions):
        return RoundTripComparison(
            status="bar_count_mismatch",
            notes=[
                f"original bar count {len(original_bars)} != round-trip bar count {len(round_trip_regions)}"
            ],
        )

    deltas: list[BarGeometryDelta] = []
    for bar, round_trip_bbox in zip(original_bars, round_trip_regions):
        original_bbox = bar.bbox
        top_y_delta = float(abs(original_bbox[1] - round_trip_bbox[1]))
        bottom_y_delta = float(abs(original_bbox[3] - round_trip_bbox[3]))
        height_delta = float(
            abs((original_bbox[3] - original_bbox[1]) - (round_trip_bbox[3] - round_trip_bbox[1]))
        )
        width_delta = float(
            abs((original_bbox[2] - original_bbox[0]) - (round_trip_bbox[2] - round_trip_bbox[0]))
        )
        deltas.append(
            BarGeometryDelta(
                bar_id=bar.bar_id,
                original_bbox=list(original_bbox),
                round_trip_bbox=list(round_trip_bbox),
                top_y_delta_px=top_y_delta,
                bottom_y_delta_px=bottom_y_delta,
                height_delta_px=height_delta,
                width_delta_px=width_delta,
            )
        )

    top_y_values = [delta.top_y_delta_px for delta in deltas if delta.top_y_delta_px is not None]
    height_values = [delta.height_delta_px for delta in deltas if delta.height_delta_px is not None]
    return RoundTripComparison(
        status="ok",
        bar_deltas=deltas,
        max_top_y_delta_px=max(top_y_values) if top_y_values else None,
        mean_top_y_delta_px=mean(top_y_values) if top_y_values else None,
        max_height_delta_px=max(height_values) if height_values else None,
        mean_height_delta_px=mean(height_values) if height_values else None,
    )


def run_round_trip_check(
    evidence: EvidenceGraph,
    original_image_path: Path,
    render_metadata: dict[str, Any] | None = None,
) -> RoundTripComparison:
    """Never raises: diagnostic-only, must not break the main verification path."""
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            round_trip_path = Path(tmp_dir) / "round_trip.png"
            rendered = render_round_trip_image(evidence, round_trip_path, render_metadata)
            if not rendered:
                if evidence.y_axis.mapping is None:
                    return RoundTripComparison(status="skipped_no_axis_mapping")
                return RoundTripComparison(status="skipped_unresolved_values")
            round_trip_regions = measure_bar_geometry(round_trip_path)
            return compare_bar_geometry(evidence.bars, round_trip_regions)
    except Exception as exc:  # noqa: BLE001 - diagnostic step must never raise
        return RoundTripComparison(status="error", notes=[str(exc)])

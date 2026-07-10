from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

import visual_qa_mcp.tick_reader as tick_reader_module
from visual_qa_mcp.chart_extractor import (
    _blue_bar_mask,
    _find_bar_regions,
    detect_plot_area,
    infer_axis_mapping,
)
from visual_qa_mcp.contracts import TickLabel
from visual_qa_mcp.generate_dataset import build_noisy_dataset
from visual_qa_mcp.tick_reader import (
    NumericTemplateCandidate,
    _decode_tick_sequence,
    _decode_tick_sequence_result,
    read_tick_texts,
)


def test_blue_bar_mask_widens_uint8_before_channel_delta() -> None:
    rgb = np.array(
        [[[245, 245, 245], [226, 230, 238], [62, 128, 226]]],
        dtype=np.uint8,
    )
    assert _blue_bar_mask(rgb).tolist() == [[False, False, True]]


def test_noisy_plot_detection_rejects_bar_top_as_gridline(tmp_path: Path) -> None:
    dataset_root = tmp_path / "noisy"
    build_noisy_dataset(dataset_root)
    image = np.array(Image.open(dataset_root / "golden" / "noisy-golden-02" / "image.png").convert("RGB"))
    plot = detect_plot_area(image)
    assert plot["tick_rows"] == [84, 160, 238, 314, 390]
    assert 129 not in plot["tick_rows"]


def test_noisy_bar_segmentation_preserves_three_components(tmp_path: Path) -> None:
    dataset_root = tmp_path / "noisy"
    build_noisy_dataset(dataset_root)
    for image_path in dataset_root.glob("**/image.png"):
        rgb = np.array(Image.open(image_path).convert("RGB"))
        assert len(_find_bar_regions(rgb, detect_plot_area(rgb))) == 3


def test_tick_sequence_uses_visual_consistency_for_ambiguous_labels() -> None:
    ranked_rows = [
        [NumericTemplateCandidate("50", 50, 0.271), NumericTemplateCandidate("60", 60, 0.275)],
        [NumericTemplateCandidate("25", 25, 0.300), NumericTemplateCandidate("20", 20, 0.314)],
        [NumericTemplateCandidate("0", 0, 0.233)],
        [NumericTemplateCandidate("-25", -25, 0.231), NumericTemplateCandidate("-35", -35, 0.268)],
        [
            NumericTemplateCandidate("-80", -80, 0.233),
            NumericTemplateCandidate("-60", -60, 0.237),
            NumericTemplateCandidate("-50", -50, 0.239),
        ],
    ]
    decoded = _decode_tick_sequence(ranked_rows, [84.0, 160.0, 238.0, 314.0, 390.0])
    assert decoded is not None
    assert [candidate.value if candidate is not None else None for candidate in decoded] == [50, 25, 0, -25, -50]


def test_tick_sequence_supports_missing_tick_geometry() -> None:
    ranked_rows = [
        [NumericTemplateCandidate("80", 80, 0.28)],
        [NumericTemplateCandidate("60", 60, 0.26)],
        [NumericTemplateCandidate("40", 40, 0.20)],
        [NumericTemplateCandidate("0", 0, 0.23)],
    ]
    decoded = _decode_tick_sequence(ranked_rows, [84.0, 161.0, 236.0, 392.0])
    assert decoded is not None
    assert [candidate.value if candidate is not None else None for candidate in decoded] == [80, 60, 40, 0]


def test_ambiguous_tick_sequence_does_not_fallback_to_individual_digits(monkeypatch) -> None:
    ranked_rows = [
        [NumericTemplateCandidate("50", 50, 0.20), NumericTemplateCandidate("60", 60, 0.20)],
        [NumericTemplateCandidate("25", 25, 0.20), NumericTemplateCandidate("30", 30, 0.20)],
        [NumericTemplateCandidate("0", 0, 0.20)],
        [NumericTemplateCandidate("-25", -25, 0.20), NumericTemplateCandidate("-30", -30, 0.20)],
        [NumericTemplateCandidate("-50", -50, 0.20), NumericTemplateCandidate("-60", -60, 0.20)],
    ]
    decode_result = _decode_tick_sequence_result(ranked_rows, [10, 30, 50, 70, 90])
    assert decode_result.ambiguous is True
    assert decode_result.selected is None

    ranked_iterator = iter(ranked_rows)
    monkeypatch.setattr(
        tick_reader_module,
        "rank_numeric_text_templates",
        lambda crop: next(ranked_iterator),
    )
    inputs = [(Image.new("RGB", (84, 26), "white"), [0, y, 84, y + 20]) for y in (0, 20, 40, 60, 80)]
    detections, available = read_tick_texts(inputs, backend="template")
    assert available is True
    assert all(tick.parsed_value is None for tick in detections)


def test_axis_mapping_accepts_a_visually_linear_missing_tick() -> None:
    ticks = [
        TickLabel(str(value), float(value), [0, center - 5, 20, center + 5], 0.8)
        for value, center in ((80, 10), (60, 30), (40, 50), (0, 90))
    ]
    mapping, baseline_y, _, gaps = infer_axis_mapping(
        ticks,
        {"axis_line_x": 30, "plot_top": 10, "plot_bottom": 90, "plot_right": 200, "tick_rows": [10, 30, 50, 90]},
        "zero_baseline",
    )
    assert gaps == []
    assert mapping is not None
    assert mapping.min_value == 0
    assert mapping.max_value == 80
    assert mapping.pixels_per_unit == 1.0
    assert baseline_y == 90


def test_axis_mapping_rejects_irregular_pixel_spacing() -> None:
    ticks = [
        TickLabel(str(value), float(value), [0, center - 5, 20, center + 5], 0.8)
        for value, center in ((80, 10), (60, 30), (40, 58), (20, 90))
    ]
    mapping, _, _, gaps = infer_axis_mapping(
        ticks,
        {"axis_line_x": 30, "plot_top": 10, "plot_bottom": 90, "plot_right": 200, "tick_rows": [10, 30, 58, 90]},
        "zero_baseline",
    )
    assert mapping is None
    assert [gap.code for gap in gaps] == ["inconsistent_tick_step"]

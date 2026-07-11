"""Throwaway experiment: strip the crutches from the Matplotlib renderer path one at a
time and observe where chart-v2 extraction actually breaks.

Per wiki/knowledge-accuracy-and-synthetic-data-roadmap.md, the existing
`chart-v2-realworld-pilot` Matplotlib cases are all rendered with layout matched to
`ChartLayout`, the validated Arial font family, and tick values drawn from the
template reader's fixed multiples-of-5 catalog. That proves rasterizer-independence
(Pillow vs. Matplotlib), not content/style-independence. This script removes each
crutch independently against an otherwise-identical golden 3-bar chart and records
what the extractor does: still passes, or degrades to needs_review (the safe,
expected outcome), or -- the finding we're specifically checking for -- silently
produces a wrong pass.

Not part of the test suite or a dataset. Output is read directly by the person
running it.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-server" / "src"))

from visual_qa_mcp.chart_generator import render_matplotlib_chart_image, write_json, _apply_postprocess
from visual_qa_mcp.chart_rules import run_chart_claims
from visual_qa_mcp.claim_graph import build_chart_claim_graph
from visual_qa_mcp.service import extract_chart_evidence_from_inputs


def render_matplotlib_unmatched_layout(image_path, data, axis_config, metadata):
    """Same content as render_matplotlib_chart_image, but lets Matplotlib place its
    own axes (tight_layout) instead of positioning them at the extractor's assumed
    ChartLayout pixel box. This is the genuine 'renderer doesn't know about our
    extractor's geometry assumptions' case."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image

    fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=100, facecolor="white")
    axis_min = float(axis_config["bar_axis"]["min"])
    axis_max = float(axis_config["bar_axis"]["max"])
    ticks = [float(value) for value in axis_config["display_ticks"]]
    labels = [str(item["label"]) for item in data]
    values = [float(item["value"]) for item in data]
    ax.bar(range(len(values)), values, color=(0.2, 0.4, 0.8), width=0.62, zorder=3)
    ax.set_xlim(-0.5, len(values) - 0.5)
    ax.set_ylim(axis_min, axis_max)
    ax.set_xticks(range(len(labels)), labels, fontsize=14)
    ax.set_yticks(ticks, [str(int(v)) for v in ticks], fontsize=15)
    ax.grid(axis="y", color=(0.85, 0.85, 0.85), linewidth=1, zorder=0)
    ax.set_ylabel(axis_config["y_label"])
    fig.tight_layout()
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    image = Image.fromarray(rgba[:, :, :3].copy(), mode="RGB")
    plt.close(fig)
    image = _apply_postprocess(image, image_path, metadata)
    image.save(image_path)

OUT = Path(__file__).resolve().parent / "_renderer_strip_scratch"

BASE_SPEC = {
    "id": "chart-strip-test",
    "domain": "chart",
    "risk_level": "medium",
    "learning_objective": "Renderer-strip experiment.",
    "source_reference": {
        "data": [
            {"category": "Jan", "value": None},
            {"category": "Feb", "value": None},
            {"category": "Mar", "value": None},
        ],
        "axis": {"expected_scale_mode": "zero_baseline", "expected_min_value": 0, "expected_max_value": 100},
    },
    "required_elements": [
        {"id": "x_axis", "kind": "axis", "name": "category axis", "count": 1},
        {"id": "y_axis", "kind": "axis", "name": "value axis", "count": 1},
        {"id": "bars", "kind": "bar", "name": "value bars", "count": 3},
    ],
    "labels": [
        {"text": "Jan", "target": "bars"},
        {"text": "Feb", "target": "bars"},
        {"text": "Mar", "target": "bars"},
        {"text": "Rainfall (mm)", "target": "y_axis"},
    ],
    "relations": [],
    "checks": [
        {"id": "bar-values-match-data", "type": "chart_value_consistency", "severity": "critical",
         "description": "Bar heights should match the source data within tolerance.",
         "params": {"relative_tolerance": 0.05}},
        {"id": "axis-label-present", "type": "label_present", "severity": "high",
         "description": "The y-axis label must be visible."},
        {"id": "axis-unit-present", "type": "axis_unit_present", "severity": "high",
         "description": "The y-axis unit must match the expected unit."},
        {"id": "bar-count-matches", "type": "bar_count_matches", "severity": "high",
         "description": "The number of bars should match the source data."},
        {"id": "axis-scale-readable", "type": "axis_scale_readable", "severity": "high",
         "description": "The chart must expose enough readable tick evidence to derive a stable numeric scale."},
        {"id": "axis-scale-monotonic", "type": "axis_scale_monotonic", "severity": "high",
         "description": "Tick values must be monotonic and internally consistent."},
    ],
}

LAYOUT_OVERRIDES = {
    # mirrors ChartLayout() defaults used by generate_dataset.py's realworld_pilot_cases
}


def run_case(name: str, values: list[float], ticks: list[int], axis_max: int,
             layout_overrides: dict | None, font_family: str,
             renderer=render_matplotlib_chart_image) -> None:
    case_dir = OUT / name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    spec = json.loads(json.dumps(BASE_SPEC))
    for item, value in zip(spec["source_reference"]["data"], values, strict=True):
        item["value"] = value
    write_json(case_dir / "visual_spec.json", spec)

    render_options: dict = {"font_family": font_family}
    if layout_overrides is not None:
        render_options["layout_overrides"] = layout_overrides
    metadata = {"backend": "template", "render_options": render_options}
    write_json(case_dir / "metadata.json", metadata)

    axis_config = {
        "bar_axis": {"min": 0, "max": axis_max},
        "display_ticks": ticks,
        "y_label": "Rainfall (mm)",
    }
    render_data = [
        {"label": label, "value": value}
        for label, value in zip(["Jan", "Feb", "Mar"], values, strict=True)
    ]
    renderer(
        image_path=case_dir / "image.png",
        data=render_data,
        axis_config=axis_config,
        metadata=render_options,
    )

    try:
        evidence = extract_chart_evidence_from_inputs(
            image_path=case_dir / "image.png",
            spec_path=case_dir / "visual_spec.json",
            metadata_path=case_dir / "metadata.json",
        )
    except Exception as exc:  # noqa: BLE001 - this is exactly the failure mode under test
        print(f"\n=== {name} ===")
        print(f"  ticks drawn:      {ticks}")
        print(f"  RAISED (did not degrade to needs_review): {type(exc).__name__}: {exc}")
        return
    claim_graph = build_chart_claim_graph(case_dir / "visual_spec.json")
    report = run_chart_claims(claim_graph, evidence)

    tick_read = [(t.text, t.parsed_value, round(t.confidence, 2)) for t in evidence.y_axis.tick_labels]
    bar_values = [b.value for b in evidence.bars]
    gap_codes = [g.code for g in evidence.gaps]

    print(f"\n=== {name} ===")
    print(f"  ticks drawn:      {ticks}")
    print(f"  ticks read:       {tick_read}")
    print(f"  mapping resolved: {evidence.y_axis.mapping is not None}")
    print(f"  bar values read:  {bar_values} (expected {values})")
    print(f"  evidence gaps:    {gap_codes}")
    print(f"  verdict:          {report.verdict}")
    print(f"  findings:         {[f.finding_type for f in report.findings]}")
    print(f"  checks_skipped:   {report.checks_skipped}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Baseline: matched layout, Arial, catalog tick values (mirrors existing pilot cases).
    run_case(
        "1_baseline_matched",
        values=[25, 50, 75],
        ticks=[0, 25, 50, 75, 100],
        axis_max=100,
        layout_overrides=LAYOUT_OVERRIDES,
        font_family="Arial",
    )

    # 2. Off-catalog tick values: not multiples of 5, still matched layout + Arial.
    run_case(
        "2_off_catalog_ticks",
        values=[22, 47, 83],
        ticks=[0, 22, 47, 83, 100],
        axis_max=100,
        layout_overrides=LAYOUT_OVERRIDES,
        font_family="Arial",
    )

    # 3. Unmatched layout: let Matplotlib place its own axes via tight_layout
    #    (extractor still assumes the default ChartLayout pixel box), catalog ticks, Arial.
    run_case(
        "3_unmatched_layout",
        values=[25, 50, 75],
        ticks=[0, 25, 50, 75, 100],
        axis_max=100,
        layout_overrides=None,
        font_family="Arial",
        renderer=render_matplotlib_unmatched_layout,
    )

    # 4. Non-Arial font: matched layout, catalog ticks, DejaVu Serif instead.
    run_case(
        "4_non_arial_font",
        values=[25, 50, 75],
        ticks=[0, 25, 50, 75, 100],
        axis_max=100,
        layout_overrides=LAYOUT_OVERRIDES,
        font_family="DejaVu Serif",
    )

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from .chart_generator import write_json
from .geometry_generator import render_geometry_diagram

# Renderer-only nominal-to-pixel scale. The spec never declares pixel sizes;
# the verifier checks diameter *ratios* against declared nominal diameters, so
# this constant is dataset-generation knowledge, not verification knowledge.
PX_PER_UNIT = 4.0

GEOMETRY_CHECKS: list[dict[str, Any]] = [
    {
        "id": "hole-count-correct",
        "type": "hole_count_correct",
        "severity": "high",
        "description": "The number of detected circular holes should match the declared holes.",
    },
    {
        "id": "hole-diameter-ratio-correct",
        "type": "hole_diameter_ratio_correct",
        "severity": "critical",
        "description": (
            "Measured hole diameter ratios must match the declared nominal diameter "
            "ratios (no pixel-to-unit calibration in v1)."
        ),
        "params": {"diameter_ratio_tolerance": 0.12},
    },
    {
        "id": "dimension-text-correct",
        "type": "dimension_text_correct",
        "severity": "critical",
        "description": "Each hole's dimension callout text must match the declared dimension.",
    },
]

ALIGNMENT_CHECK: dict[str, Any] = {
    "id": "hole-alignment-correct",
    "type": "hole_alignment_correct",
    "severity": "high",
    "description": (
        "For a declared linear layout, hole centers must be collinear and evenly spaced."
    ),
    "params": {"alignment_tolerance_px": 6.0, "spacing_ratio_tolerance": 0.15},
}


def _spec_holes(holes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": hole["id"],
            "diameter": hole["diameter"],
            "dimension_text": hole["dimension_text"],
        }
        for hole in holes
    ]


def _render_holes(
    holes: list[dict[str, Any]],
    render_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    overrides = render_overrides or {}
    rendered = []
    for hole in holes:
        item = {
            "center": list(hole["center"]),
            "diameter_px": float(hole["diameter"]) * PX_PER_UNIT,
            "label_text": hole["dimension_text"],
        }
        item.update(overrides.get(hole["id"], {}))
        rendered.append(item)
    return rendered


def _base_spec(
    case_id: str,
    holes: list[dict[str, Any]],
    layout: str | None = None,
) -> dict[str, Any]:
    source_reference: dict[str, Any] = {
        "plate": {"kind": "rectangle"},
        "holes": _spec_holes(holes),
    }
    checks = deepcopy(GEOMETRY_CHECKS)
    if layout is not None:
        source_reference["layout"] = layout
        checks.append(deepcopy(ALIGNMENT_CHECK))
    return {
        "id": f"geometry-{case_id}",
        "domain": "mechanical",
        "risk_level": "medium",
        "learning_objective": (
            "Read a mechanical part illustration where each drilled hole has the "
            "correct count, relative diameter, position, and dimension callout."
        ),
        "source_reference": source_reference,
        "required_elements": [
            {"id": "plate", "kind": "rectangle", "name": "plate under illustration", "count": 1},
            {"id": "holes", "kind": "circle", "name": "drilled holes", "count": len(holes)},
        ],
        "labels": [],
        "relations": [],
        "checks": checks,
    }


def _case(
    case_id: str,
    title: str,
    kind: str,
    holes: list[dict[str, Any]],
    expected_report: dict[str, Any],
    defect_type: str | None = None,
    layout: str | None = None,
    render_holes: list[dict[str, Any]] | None = None,
    render_overrides: dict[str, dict[str, Any]] | None = None,
    extra_render_holes: list[dict[str, Any]] | None = None,
    drop_render_hole_ids: list[str] | None = None,
    render_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    render_source = render_holes if render_holes is not None else holes
    if drop_render_hole_ids:
        render_source = [
            hole for hole in render_source if hole["id"] not in drop_render_hole_ids
        ]
    rendered = _render_holes(render_source, render_overrides)
    if extra_render_holes:
        rendered.extend(deepcopy(extra_render_holes))
    expected_report = deepcopy(expected_report)
    expected_report.setdefault("expected_evidence", {"hole_count": None})
    return {
        "case_id": case_id,
        "title": title,
        "kind": kind,
        "defect_type": defect_type,
        "spec_holes": holes,
        "layout": layout,
        "render_holes": rendered,
        "render_options": render_options or {},
        "expected_report": expected_report,
    }


def _linear_holes(diameter: int = 10, text: str = "D10") -> list[dict[str, Any]]:
    return [
        {"id": "hole-a", "diameter": diameter, "dimension_text": text, "center": [180, 225]},
        {"id": "hole-b", "diameter": diameter, "dimension_text": text, "center": [300, 225]},
        {"id": "hole-c", "diameter": diameter, "dimension_text": text, "center": [420, 225]},
    ]


def _mixed_holes() -> list[dict[str, Any]]:
    return [
        {"id": "hole-a", "diameter": 8, "dimension_text": "D8", "center": [170, 200]},
        {"id": "hole-b", "diameter": 8, "dimension_text": "D8", "center": [260, 200]},
        {"id": "hole-c", "diameter": 12, "dimension_text": "D12", "center": [350, 200]},
        {"id": "hole-d", "diameter": 8, "dimension_text": "D8", "center": [440, 200]},
    ]


def dataset_cases() -> list[dict[str, Any]]:
    def golden(hole_count: int) -> dict[str, Any]:
        return {
            "verdict": "pass",
            "expected_finding_types": [],
            "expected_evidence": {"hole_count": hole_count},
        }

    return [
        _case(
            "golden-01",
            "Three equal holes on a linear layout",
            "golden",
            _linear_holes(),
            golden(3),
            layout="linear",
        ),
        _case(
            "golden-02",
            "Four mixed-diameter holes on a linear layout",
            "golden",
            _mixed_holes(),
            golden(4),
            layout="linear",
        ),
        _case(
            "golden-03",
            "Two holes without a declared layout",
            "golden",
            [
                {"id": "hole-a", "diameter": 10, "dimension_text": "D10", "center": [220, 200]},
                {"id": "hole-b", "diameter": 16, "dimension_text": "D16", "center": [390, 250]},
            ],
            golden(2),
        ),
        _case(
            "golden-04",
            "Three holes on a diagonal linear layout",
            "golden",
            [
                {"id": "hole-a", "diameter": 10, "dimension_text": "D10", "center": [180, 160]},
                {"id": "hole-b", "diameter": 10, "dimension_text": "D10", "center": [300, 225]},
                {"id": "hole-c", "diameter": 10, "dimension_text": "D10", "center": [420, 290]},
            ],
            golden(3),
            layout="linear",
        ),
        _case(
            "golden-05",
            "Single hole plate",
            "golden",
            [
                {"id": "hole-a", "diameter": 12, "dimension_text": "D12", "center": [300, 225]},
            ],
            golden(1),
        ),
        _case(
            "mutated-01",
            "Extra undeclared hole",
            "mutated",
            _linear_holes(),
            {
                "verdict": "needs_review",
                "expected_finding_types": ["hole_count_mismatch"],
                "expected_evidence": {"hole_count": 4},
            },
            defect_type="extra_hole",
            layout="linear",
            extra_render_holes=[
                {"center": [240, 300], "diameter_px": 40.0, "label_text": "D10"}
            ],
        ),
        _case(
            "mutated-02",
            "Missing declared hole",
            "mutated",
            _linear_holes(),
            {
                "verdict": "needs_review",
                "expected_finding_types": ["hole_count_mismatch"],
                "expected_evidence": {"hole_count": 2},
            },
            defect_type="missing_hole",
            layout="linear",
            drop_render_hole_ids=["hole-b"],
        ),
        _case(
            "mutated-03",
            "Middle hole oversized against declared ratio",
            "mutated",
            _linear_holes(),
            {
                "verdict": "fail",
                "expected_finding_types": ["hole_diameter_ratio_violation"],
                "expected_evidence": {"hole_count": 3},
            },
            defect_type="oversized_hole",
            layout="linear",
            render_overrides={"hole-b": {"diameter_px": 60.0}},
        ),
        _case(
            "mutated-04",
            "Middle hole undersized against declared ratio",
            "mutated",
            _linear_holes(),
            {
                "verdict": "fail",
                "expected_finding_types": ["hole_diameter_ratio_violation"],
                "expected_evidence": {"hole_count": 3},
            },
            defect_type="undersized_hole",
            layout="linear",
            render_overrides={"hole-b": {"diameter_px": 26.0}},
        ),
        _case(
            "mutated-05",
            "Middle hole shifted off the declared linear layout",
            "mutated",
            _linear_holes(),
            {
                "verdict": "fail",
                "expected_finding_types": ["hole_alignment_violation"],
                "expected_evidence": {"hole_count": 3},
            },
            defect_type="misaligned_hole",
            layout="linear",
            render_overrides={"hole-b": {"center": [300, 195]}},
        ),
        _case(
            "mutated-06",
            "Wrong dimension callout on the middle hole",
            "mutated",
            _linear_holes(),
            {
                "verdict": "fail",
                "expected_finding_types": ["dimension_text_mismatch"],
                "expected_evidence": {"hole_count": 3},
            },
            defect_type="wrong_dimension_text",
            layout="linear",
            render_overrides={"hole-b": {"label_text": "D12"}},
        ),
        _case(
            "mutated-07",
            "Swapped dimension callouts on a mixed-diameter plate",
            "mutated",
            _mixed_holes(),
            {
                "verdict": "fail",
                "expected_finding_types": ["dimension_text_mismatch"],
                "expected_evidence": {"hole_count": 4},
            },
            defect_type="swapped_dimension_text",
            layout="linear",
            render_overrides={
                "hole-b": {"label_text": "D12"},
                "hole-c": {"label_text": "D8"},
            },
        ),
        _case(
            "mutated-08",
            "Two holes drawn overlapping into one blob",
            "mutated",
            _linear_holes(),
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"hole_count": None},
            },
            defect_type="overlapping_holes",
            layout="linear",
            render_overrides={"hole-b": {"center": [390, 225]}},
        ),
        _case(
            "mutated-09",
            "Corrupted dimension text outside the catalog",
            "mutated",
            _linear_holes(),
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"hole_count": 3},
            },
            defect_type="unreadable_dimension_text",
            layout="linear",
            render_overrides={"hole-b": {"label_text": "XX"}},
        ),
    ]


def noisy_dataset_cases() -> list[dict[str, Any]]:
    """Predeclared geometry-v1 robustness cases, grouped by primary transform family."""

    def golden(hole_count: int) -> dict[str, Any]:
        return {
            "verdict": "pass",
            "expected_finding_types": [],
            "expected_evidence": {"hole_count": hole_count},
        }

    def typed(finding_type: str, hole_count: int, verdict: str = "fail") -> dict[str, Any]:
        return {
            "verdict": verdict,
            "expected_finding_types": [finding_type],
            "expected_evidence": {"hole_count": hole_count},
        }

    def ambiguous(hole_count: int | None = None) -> dict[str, Any]:
        return {
            "verdict": "needs_review",
            "expected_finding_types": [],
            "expected_evidence": {"hole_count": hole_count},
        }

    cases: list[dict[str, Any]] = []

    def add(case: dict[str, Any], family: str) -> None:
        case["transform_family"] = family
        cases.append(case)

    # Blur family: two mild goldens, one typed diameter defect, one evidence-loss guard.
    add(_case("noisy-blur-golden-01", "Mild blur on equal holes", "golden", _linear_holes(), golden(3), layout="linear", render_options={"postprocess": {"blur_radius": 0.15}}), "blur")
    add(_case("noisy-blur-golden-02", "Mild blur on mixed holes", "golden", _mixed_holes(), golden(4), layout="linear", render_options={"postprocess": {"blur_radius": 0.35}}), "blur")
    add(_case("noisy-blur-mutated-01", "Blurred oversized middle hole", "mutated", _linear_holes(), typed("hole_diameter_ratio_violation", 3, verdict="needs_review"), defect_type="oversized_hole", layout="linear", render_overrides={"hole-b": {"diameter_px": 60.0}}, render_options={"postprocess": {"blur_radius": 0.35}}), "blur")
    add(_case("noisy-blur-ambiguous-01", "Heavy blur makes labels unreadable", "mutated", _linear_holes(), ambiguous(3), defect_type="unreadable_dimension_text", layout="linear", render_options={"postprocess": {"blur_radius": 1.25}}), "blur")

    # Downscale family.
    add(_case("noisy-downscale-golden-01", "Resampled single D12 hole", "golden", [{"id": "hole-a", "diameter": 12, "dimension_text": "D12", "center": [300, 225]}], golden(1), render_options={"postprocess": {"downscale_factor": 0.86}}), "downscale")
    add(_case("noisy-downscale-golden-02", "Mild resampling on mixed holes", "golden", _mixed_holes(), golden(4), layout="linear", render_options={"postprocess": {"downscale_factor": 0.96}}), "downscale")
    add(_case("noisy-downscale-mutated-01", "Resampled misaligned middle hole", "mutated", _linear_holes(), typed("hole_alignment_violation", 3, verdict="needs_review"), defect_type="misaligned_hole", layout="linear", render_overrides={"hole-b": {"center": [300, 195]}}, render_options={"postprocess": {"downscale_factor": 0.86}}), "downscale")
    add(_case("noisy-downscale-ambiguous-01", "Heavy resampling loses label evidence", "mutated", _linear_holes(), ambiguous(3), defect_type="unreadable_dimension_text", layout="linear", render_options={"postprocess": {"downscale_factor": 0.55}}), "downscale")

    # JPEG family.
    add(_case("noisy-jpeg-golden-01", "JPEG equal holes", "golden", _linear_holes(), golden(3), layout="linear", render_options={"postprocess": {"jpeg_quality": 92}}), "jpeg")
    add(_case("noisy-jpeg-golden-02", "JPEG mixed holes", "golden", _mixed_holes(), golden(4), layout="linear", render_options={"postprocess": {"jpeg_quality": 80}}), "jpeg")
    add(_case("noisy-jpeg-mutated-01", "JPEG wrong dimension label", "mutated", _linear_holes(), typed("dimension_text_mismatch", 3), defect_type="wrong_dimension_text", layout="linear", render_overrides={"hole-b": {"label_text": "D12"}}, render_options={"postprocess": {"jpeg_quality": 92}}), "jpeg")
    add(_case("noisy-jpeg-ambiguous-01", "Low-quality JPEG loses label evidence", "mutated", _linear_holes(), ambiguous(3), defect_type="unreadable_dimension_text", layout="linear", render_options={"postprocess": {"jpeg_quality": 28}}), "jpeg")

    # Global low-contrast family.
    add(_case("noisy-contrast-golden-01", "Low-contrast equal holes", "golden", _linear_holes(), golden(3), layout="linear", render_options={"postprocess": {"contrast_factor": 0.8}}), "low_contrast")
    add(_case("noisy-contrast-golden-02", "Low-contrast mixed holes", "golden", _mixed_holes(), golden(4), layout="linear", render_options={"postprocess": {"contrast_factor": 0.72}}), "low_contrast")
    add(_case("noisy-contrast-mutated-01", "Low-contrast extra hole", "mutated", _linear_holes(), typed("hole_count_mismatch", 4, verdict="needs_review"), defect_type="extra_hole", layout="linear", extra_render_holes=[{"center": [240, 300], "diameter_px": 40.0, "label_text": "D10"}], render_options={"postprocess": {"contrast_factor": 0.75}}), "low_contrast")
    add(_case("noisy-contrast-ambiguous-01", "Very low contrast hides plate evidence", "mutated", _linear_holes(), ambiguous(None), defect_type="plate_not_found", layout="linear", render_options={"postprocess": {"contrast_factor": 0.28}}), "low_contrast")

    # Targeted dimension-label degradation family.
    mild_labels = {hole["id"]: {"label_fill": [55, 55, 55]} for hole in _linear_holes()}
    medium_labels = {hole["id"]: {"label_fill": [80, 80, 80]} for hole in _mixed_holes()}
    add(_case("noisy-label-golden-01", "Mildly faded dimension labels", "golden", _linear_holes(), golden(3), layout="linear", render_overrides=mild_labels), "label_degradation")
    add(_case("noisy-label-golden-02", "Faded mixed dimension labels", "golden", _mixed_holes(), golden(4), layout="linear", render_overrides=medium_labels), "label_degradation")
    add(_case("noisy-label-mutated-01", "Faded wrong dimension label", "mutated", _linear_holes(), typed("dimension_text_mismatch", 3), defect_type="wrong_dimension_text", layout="linear", render_overrides={"hole-a": {"label_fill": [65, 65, 65]}, "hole-b": {"label_text": "D12", "label_fill": [65, 65, 65]}, "hole-c": {"label_fill": [65, 65, 65]}}), "label_degradation")
    add(_case("noisy-label-ambiguous-01", "Labels faded beyond catalog evidence", "mutated", _linear_holes(), ambiguous(3), defect_type="unreadable_dimension_text", layout="linear", render_overrides={hole["id"]: {"label_fill": [190, 190, 190]} for hole in _linear_holes()}), "label_degradation")
    return cases


def build_geometry_dataset(output_root: Path) -> None:
    build_geometry_cases_dataset(output_root, dataset_cases(), dataset_track="controlled")


def build_noisy_geometry_dataset(output_root: Path) -> None:
    build_geometry_cases_dataset(output_root, noisy_dataset_cases(), dataset_track="noisy")
    _write_geometry_manifest(output_root, dataset_name="geometry-v1-noisy", dataset_version="1.0")


def build_geometry_cases_dataset(
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

        spec = _base_spec(case["case_id"], case["spec_holes"], layout=case.get("layout"))
        metadata = {
            "case_id": case["case_id"],
            "title": case["title"],
            "kind": case["kind"],
            "defect_type": case["defect_type"],
            "scenario": "mechanical_plate",
            "dataset_track": dataset_track,
            "image_id": case["case_id"],
            "diagram_version": "geometry-v1",
            "render_options": case["render_options"],
            "renderer": "pillow",
            "transform_family": case.get("transform_family", "controlled"),
        }

        write_json(case_dir / "visual_spec.json", spec)
        write_json(case_dir / "metadata.json", metadata)
        write_json(case_dir / "expected_report.json", case["expected_report"])
        render_geometry_diagram(
            image_path=case_dir / "image.png",
            holes=case["render_holes"],
            render_options=case["render_options"],
        )


def _write_geometry_manifest(
    output_root: Path,
    dataset_name: str,
    dataset_version: str,
) -> None:
    manifest_cases: list[dict[str, Any]] = []
    for metadata_path in sorted(output_root.glob("**/metadata.json")):
        case_dir = metadata_path.parent
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        checksums = {
            name: hashlib.sha256((case_dir / name).read_bytes()).hexdigest()
            for name in ("image.png", "visual_spec.json", "metadata.json", "expected_report.json")
        }
        expected = json.loads((case_dir / "expected_report.json").read_text(encoding="utf-8"))
        manifest_cases.append(
            {
                "case_id": metadata["case_id"],
                "relative_path": str(case_dir.relative_to(output_root)).replace("\\", "/"),
                "kind": metadata["kind"],
                "defect_type": metadata.get("defect_type"),
                "transform_family": metadata["transform_family"],
                "expected_verdict": expected["verdict"],
                "checksums": checksums,
                "provenance": {
                    "source_type": "project_generated",
                    "license": "project_internal",
                    "retrieved_at": "2026-07-10",
                },
            }
        )
    write_json(
        output_root / "manifest.json",
        {
            "dataset": dataset_name,
            "version": dataset_version,
            "case_count": len(manifest_cases),
            "cases": manifest_cases,
        },
    )

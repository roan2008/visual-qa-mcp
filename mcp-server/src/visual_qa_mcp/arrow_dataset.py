from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from .arrow_generator import render_arrow_diagram
from .chart_generator import write_json

WEIGHT_RGB = [214, 48, 49]
NORMAL_RGB = [9, 132, 227]
APPLIED_RGB = [0, 148, 50]
FRICTION_RGB = [230, 126, 34]
EXTRA_RGB = [142, 68, 173]

BASE_FORCES: dict[str, dict[str, Any]] = {
    "weight": {
        "name": "Weight (W)",
        "rgb": WEIGHT_RGB,
        "direction_degrees": 270,
        "anchor": "bottom_center",
        "label_text": "W",
    },
    "normal": {
        "name": "Normal force (N)",
        "rgb": NORMAL_RGB,
        "direction_degrees": 90,
        "anchor": "top_center",
        "label_text": "N",
    },
    "applied": {
        "name": "Applied force (F)",
        "rgb": APPLIED_RGB,
        "direction_degrees": 0,
        "anchor": "right_center",
        "label_text": "F",
    },
    "friction": {
        "name": "Friction (f)",
        "rgb": FRICTION_RGB,
        "direction_degrees": 180,
        "anchor": "left_center",
        "label_text": "f",
    },
}

FORCE_BALANCE_CHECK: dict[str, Any] = {
    "id": "force-balance-correct",
    "type": "force_balance_correct",
    "severity": "critical",
    "description": (
        "For a declared equilibrium scenario, the drawn force arrows must sum to "
        "approximately zero as pixel vectors (translational balance only)."
    ),
    "params": {"resultant_ratio_tolerance": 0.15, "color_match_distance": 60.0},
}

ARROW_CHECKS: list[dict[str, Any]] = [
    {
        "id": "arrow-count-matches",
        "type": "arrow_count_matches",
        "severity": "high",
        "description": "The number of detected force arrows should match the source forces.",
    },
    {
        "id": "required-arrows-present",
        "type": "required_arrows_present",
        "severity": "critical",
        "description": "Every required force arrow must be present with its declared color identity.",
        "params": {"color_match_distance": 60.0},
    },
    {
        "id": "arrow-directions-correct",
        "type": "arrow_directions_correct",
        "severity": "critical",
        "description": "Each force arrow must point in its physically correct direction.",
        "params": {"angle_tolerance_degrees": 15.0, "color_match_distance": 60.0},
    },
    {
        "id": "arrow-anchors-object",
        "type": "arrow_anchors_object",
        "severity": "high",
        "description": "Each force arrow must be attached to the object it acts on.",
        "params": {"anchor_tolerance_px": 14.0, "color_match_distance": 60.0},
    },
]


def _spec_arrows(force_ids: list[str], forces: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": force_id,
            "name": forces[force_id]["name"],
            "rgb": forces[force_id]["rgb"],
            "direction_degrees": forces[force_id]["direction_degrees"],
            "label_text": forces[force_id].get("label_text"),
            "target": "object",
        }
        for force_id in force_ids
    ]


def _render_arrows(
    force_ids: list[str],
    forces: dict[str, dict[str, Any]],
    render_overrides: dict[str, dict[str, Any]] | None = None,
    length_px: float = 90.0,
    include_labels: bool = False,
) -> list[dict[str, Any]]:
    overrides = render_overrides or {}
    arrows = []
    for force_id in force_ids:
        force = forces[force_id]
        arrow = {
            "rgb": force["rgb"],
            "anchor": force["anchor"],
            "angle_degrees": force["direction_degrees"],
            "length_px": length_px,
        }
        if include_labels:
            arrow["label_text"] = force.get("label_text")
        arrow.update(overrides.get(force_id, {}))
        arrows.append(arrow)
    return arrows


def _base_spec(
    case_id: str,
    force_ids: list[str],
    forces: dict[str, dict[str, Any]],
    scenario_type: str | None = None,
) -> dict[str, Any]:
    source_reference: dict[str, Any] = {
        "arrows": _spec_arrows(force_ids, forces),
        "object": {"kind": "box"},
    }
    checks = deepcopy(ARROW_CHECKS)
    if scenario_type is not None:
        source_reference["scenario_type"] = scenario_type
        checks.append(deepcopy(FORCE_BALANCE_CHECK))
    return {
        "id": f"arrow-{case_id}",
        "domain": "physics",
        "risk_level": "medium",
        "learning_objective": (
            "Read a free-body diagram where each force arrow has the correct identity, "
            "direction, and attachment to the object."
        ),
        "source_reference": source_reference,
        "required_elements": [
            {"id": "object", "kind": "box", "name": "object under analysis", "count": 1},
            {"id": "arrows", "kind": "arrow", "name": "force arrows", "count": len(force_ids)},
        ],
        "labels": [],
        "relations": [],
        "checks": checks,
    }


def _case(
    case_id: str,
    title: str,
    kind: str,
    expected_report: dict[str, Any],
    defect_type: str | None = None,
    spec_force_ids: list[str] | None = None,
    render_force_ids: list[str] | None = None,
    render_forces: dict[str, dict[str, Any]] | None = None,
    render_overrides: dict[str, dict[str, Any]] | None = None,
    extra_render_arrows: list[dict[str, Any]] | None = None,
    render_options: dict[str, Any] | None = None,
    length_px: float = 90.0,
    include_labels: bool = False,
    scenario_type: str | None = None,
) -> dict[str, Any]:
    spec_force_ids = spec_force_ids or list(BASE_FORCES)
    render_force_ids = render_force_ids if render_force_ids is not None else list(spec_force_ids)
    forces = render_forces or BASE_FORCES
    render_arrows = _render_arrows(
        render_force_ids, forces, render_overrides, length_px=length_px, include_labels=include_labels
    )
    if extra_render_arrows:
        render_arrows.extend(deepcopy(extra_render_arrows))
    expected_report = deepcopy(expected_report)
    expected_report.setdefault("expected_evidence", {"arrow_count": None})
    return {
        "case_id": case_id,
        "title": title,
        "kind": kind,
        "defect_type": defect_type,
        "spec_force_ids": spec_force_ids,
        "scenario_type": scenario_type,
        "render_arrows": render_arrows,
        "render_options": render_options or {},
        "expected_report": expected_report,
    }


def dataset_cases() -> list[dict[str, Any]]:
    golden_expected = {
        "verdict": "pass",
        "expected_finding_types": [],
        "expected_evidence": {"arrow_count": 4},
    }
    shade_forces = deepcopy(BASE_FORCES)
    shade_forces["weight"]["rgb"] = [200, 60, 60]
    shade_forces["normal"]["rgb"] = [30, 120, 210]
    shade_forces["applied"]["rgb"] = [20, 140, 70]
    shade_forces["friction"]["rgb"] = [220, 130, 50]

    duplicate_forces = deepcopy(BASE_FORCES)
    duplicate_forces["friction"]["rgb"] = list(APPLIED_RGB)

    swapped_forces = deepcopy(BASE_FORCES)
    swapped_forces["weight"]["rgb"] = list(NORMAL_RGB)
    swapped_forces["normal"]["rgb"] = list(WEIGHT_RGB)

    return [
        _case(
            "golden-01",
            "Four-force free-body diagram",
            "golden",
            golden_expected,
        ),
        _case(
            "golden-02",
            "Layout variation with longer arrows",
            "golden",
            golden_expected,
            render_options={
                "width": 720,
                "height": 520,
                "object_box": [300, 240, 440, 340],
            },
            length_px=110.0,
        ),
        _case(
            "golden-03",
            "Three-force variant without applied force",
            "golden",
            {
                "verdict": "pass",
                "expected_finding_types": [],
                "expected_evidence": {"arrow_count": 3},
            },
            spec_force_ids=["weight", "normal", "friction"],
        ),
        _case(
            "golden-04",
            "Alternate color shades",
            "golden",
            golden_expected,
            render_forces=shade_forces,
        ),
        _case(
            "mutated-01",
            "Friction arrow reversed",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_direction_wrong"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="wrong_direction_reversed",
            render_overrides={"friction": {"angle_degrees": 0}},
        ),
        _case(
            "mutated-02",
            "Applied force drawn diagonally",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_direction_wrong"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="wrong_direction_diagonal",
            render_overrides={"applied": {"angle_degrees": 40}},
        ),
        _case(
            "mutated-03",
            "Missing normal force arrow",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_count_mismatch", "arrow_missing"],
                "expected_evidence": {"arrow_count": 3},
            },
            defect_type="missing_arrow",
            render_force_ids=["weight", "applied", "friction"],
        ),
        _case(
            "mutated-04",
            "Extra undeclared arrow",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_count_mismatch", "unexpected_arrow"],
                "expected_evidence": {"arrow_count": 5},
            },
            defect_type="extra_arrow",
            extra_render_arrows=[
                {
                    "rgb": EXTRA_RGB,
                    "anchor": "center",
                    "angle_degrees": 45,
                    "length_px": 100.0,
                    "tail_offset": [60, -45],
                }
            ],
        ),
        _case(
            "mutated-05",
            "Weight arrow detached from object",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_anchor_detached"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="detached_anchor",
            render_overrides={"weight": {"tail_offset": [90, 40]}},
        ),
        _case(
            "mutated-06",
            "Weight and normal colors swapped",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_direction_wrong"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="swapped_arrow_colors",
            render_forces=swapped_forces,
        ),
        _case(
            "mutated-07",
            "Two arrows share one color",
            "mutated",
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="ambiguous_arrow_colors",
            render_forces=duplicate_forces,
        ),
        _case(
            "mutated-08",
            "Degenerate tiny normal arrow",
            "mutated",
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"arrow_count": None},
            },
            defect_type="degenerate_arrow",
            render_overrides={"normal": {"length_px": 14.0, "head_length": 6.0, "head_half_width": 4.0}},
        ),
        _case(
            "golden-05",
            "Labeled diagram, forces correct",
            "golden",
            golden_expected,
            include_labels=True,
        ),
        _case(
            "mutated-09",
            "Color collision resolved via label, friction reversed",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_direction_wrong"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="label_resolved_color_collision",
            render_forces=duplicate_forces,
            render_overrides={"friction": {"angle_degrees": 220}},
            include_labels=True,
        ),
        _case(
            "golden-06",
            "Declared equilibrium, forces balanced",
            "golden",
            golden_expected,
            include_labels=True,
            scenario_type="equilibrium",
        ),
        _case(
            "mutated-10",
            "Declared equilibrium, weight arrow too short",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["force_balance_violation"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="force_balance_magnitude",
            render_overrides={"weight": {"length_px": 50.0}},
            include_labels=True,
            scenario_type="equilibrium",
        ),
        _case(
            "mutated-11",
            "Declared equilibrium, unlabeled color collision blocks balance check",
            "mutated",
            {
                "verdict": "needs_review",
                "expected_finding_types": [],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="ambiguous_arrow_colors_equilibrium",
            render_forces=duplicate_forces,
            scenario_type="equilibrium",
        ),
    ]


def noisy_dataset_cases() -> list[dict[str, Any]]:
    return [
        _case(
            "noisy-golden-01",
            "Noisy diagram, forces correct",
            "golden",
            {
                "verdict": "pass",
                "expected_finding_types": [],
                "expected_evidence": {"arrow_count": 4},
            },
            include_labels=True,
            render_options={"postprocess": {"downscale_factor": 0.88, "jpeg_quality": 82}},
        ),
        _case(
            "noisy-golden-02",
            "Noisy blurred diagram, forces correct",
            "golden",
            {
                "verdict": "pass",
                "expected_finding_types": [],
                "expected_evidence": {"arrow_count": 4},
            },
            include_labels=True,
            render_options={"postprocess": {"blur_radius": 0.4, "downscale_factor": 0.92}},
        ),
        _case(
            "noisy-mutated-01",
            "Noisy friction arrow reversed",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_direction_wrong"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="wrong_direction_reversed",
            render_overrides={"friction": {"angle_degrees": 0}},
            include_labels=True,
            render_options={"postprocess": {"downscale_factor": 0.88, "jpeg_quality": 80}},
        ),
        _case(
            "noisy-mutated-02",
            "Noisy missing normal force arrow",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_count_mismatch", "arrow_missing"],
                "expected_evidence": {"arrow_count": 3},
            },
            defect_type="missing_arrow",
            render_force_ids=["weight", "applied", "friction"],
            include_labels=True,
            render_options={"postprocess": {"blur_radius": 0.35, "downscale_factor": 0.9}},
        ),
        _case(
            "noisy-mutated-03",
            "Noisy weight arrow detached from object",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_anchor_detached"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="detached_anchor",
            render_overrides={"weight": {"tail_offset": [90, 40]}},
            include_labels=True,
            render_options={"postprocess": {"downscale_factor": 0.85, "jpeg_quality": 78}},
        ),
        _case(
            "noisy-mutated-04",
            "Noisy labeled diagram, color collision resolved, friction reversed",
            "mutated",
            {
                "verdict": "fail",
                "expected_finding_types": ["arrow_direction_wrong"],
                "expected_evidence": {"arrow_count": 4},
            },
            defect_type="label_resolved_color_collision",
            render_forces=duplicate_forces_for_noisy(),
            render_overrides={"friction": {"angle_degrees": 220}},
            include_labels=True,
            render_options={"postprocess": {"blur_radius": 0.3, "downscale_factor": 0.9}},
        ),
    ]


def duplicate_forces_for_noisy() -> dict[str, dict[str, Any]]:
    forces = deepcopy(BASE_FORCES)
    forces["friction"]["rgb"] = list(APPLIED_RGB)
    return forces


def build_arrow_dataset(output_root: Path) -> None:
    build_arrow_cases_dataset(output_root, dataset_cases(), dataset_track="controlled")


def build_noisy_arrow_dataset(output_root: Path) -> None:
    build_arrow_cases_dataset(output_root, noisy_dataset_cases(), dataset_track="noisy")


def build_arrow_cases_dataset(
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
            case["spec_force_ids"],
            BASE_FORCES,
            scenario_type=case.get("scenario_type"),
        )
        metadata = {
            "case_id": case["case_id"],
            "title": case["title"],
            "kind": case["kind"],
            "defect_type": case["defect_type"],
            "scenario": "free_body",
            "dataset_track": dataset_track,
            "image_id": case["case_id"],
            "diagram_version": "arrow-v1",
            "render_options": case["render_options"],
        }

        write_json(case_dir / "visual_spec.json", spec)
        write_json(case_dir / "metadata.json", metadata)
        write_json(case_dir / "expected_report.json", case["expected_report"])
        render_arrow_diagram(
            image_path=case_dir / "image.png",
            arrows=case["render_arrows"],
            render_options=case["render_options"],
        )

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import ClaimCheck, ClaimGap, ClaimGraph


def _source_category(item: dict[str, Any]) -> str:
    value = item.get("category", item.get("month"))
    if value is None:
        raise ValueError("Chart source data item is missing 'category' (or legacy 'month').")
    return str(value)


def _source_value(item: dict[str, Any]) -> float:
    value = item.get("value", item.get("rainfall_mm"))
    if value is None:
        raise ValueError("Chart source data item is missing 'value' (or legacy 'rainfall_mm').")
    return float(value)


def _expected_unit_from_label(label_text: str | None) -> str | None:
    if not label_text or "(" not in label_text or ")" not in label_text:
        return None
    return label_text.split("(", 1)[1].split(")", 1)[0].strip() or None


def _chart_claim(
    *,
    check: dict[str, Any],
    target: str,
    expected: dict[str, Any],
    evidence_requirements: list[str],
    tolerance: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ClaimCheck:
    return ClaimCheck(
        claim_id=f"claim-{check['id']}",
        rule_id=_rule_id(check["id"]),
        check_id=check["id"],
        check_type=check["type"],
        severity=check["severity"],
        target=target,
        expected=expected,
        tolerance=tolerance or {},
        evidence_requirements=evidence_requirements,
        metadata=metadata or {},
    )


def _rule_id(check_id: str) -> str:
    return f"chart-v2.{check_id}"


def _arrow_rule_id(check_id: str) -> str:
    return f"arrow-v1.{check_id}"


def build_arrow_claim_graph(spec_path: Path) -> ClaimGraph:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source_reference = spec.get("source_reference", {})
    expected_arrows = source_reference.get("arrows", [])
    scenario_type = source_reference.get("scenario_type")

    claims: list[ClaimCheck] = []
    gaps: list[ClaimGap] = []
    for check in spec.get("checks", []):
        check_id = check["id"]
        params = check.get("params", {})
        common_metadata = {
            "description": check.get("description"),
            "learning_objective": spec.get("learning_objective"),
        }

        def _arrow_claim(target: str, expected: dict[str, Any], evidence_requirements: list[str], tolerance: dict[str, Any] | None = None) -> ClaimCheck:
            return ClaimCheck(
                claim_id=f"claim-{check_id}",
                rule_id=_arrow_rule_id(check_id),
                check_id=check_id,
                check_type=check["type"],
                severity=check["severity"],
                target=target,
                expected=expected,
                tolerance=tolerance or {},
                evidence_requirements=evidence_requirements,
                metadata=common_metadata,
            )

        if check_id == "arrow-count-matches":
            claims.append(
                _arrow_claim(
                    target="arrows",
                    expected={"count": len(expected_arrows)},
                    evidence_requirements=["arrow_geometry"],
                )
            )
        elif check_id == "required-arrows-present":
            claims.append(
                _arrow_claim(
                    target="arrows",
                    expected={
                        "arrows_by_id": {
                            arrow["id"]: {
                                "rgb": arrow["rgb"],
                                "name": arrow.get("name"),
                                "label_text": arrow.get("label_text"),
                            }
                            for arrow in expected_arrows
                        }
                    },
                    evidence_requirements=["arrow_geometry", "arrow_color"],
                    tolerance={
                        "color_match_distance": params.get("color_match_distance", 60.0)
                    },
                )
            )
        elif check_id == "arrow-directions-correct":
            claims.append(
                _arrow_claim(
                    target="arrows",
                    expected={
                        "directions_by_id": {
                            arrow["id"]: {
                                "rgb": arrow["rgb"],
                                "direction_degrees": arrow["direction_degrees"],
                                "label_text": arrow.get("label_text"),
                            }
                            for arrow in expected_arrows
                        }
                    },
                    evidence_requirements=["arrow_geometry", "arrow_color"],
                    tolerance={
                        "angle_tolerance_degrees": params.get("angle_tolerance_degrees", 15.0),
                        "color_match_distance": params.get("color_match_distance", 60.0),
                    },
                )
            )
        elif check_id == "arrow-anchors-object":
            claims.append(
                _arrow_claim(
                    target="arrows",
                    expected={
                        "anchored_arrow_ids": [
                            arrow["id"]
                            for arrow in expected_arrows
                            if arrow.get("target", "object") == "object"
                        ],
                        "arrows_by_id": {
                            arrow["id"]: {
                                "rgb": arrow["rgb"],
                                "label_text": arrow.get("label_text"),
                            }
                            for arrow in expected_arrows
                        },
                    },
                    evidence_requirements=["arrow_geometry", "object_region"],
                    tolerance={
                        "anchor_tolerance_px": params.get("anchor_tolerance_px", 14.0),
                        "color_match_distance": params.get("color_match_distance", 60.0),
                    },
                )
            )
        elif check_id == "force-balance-correct":
            if scenario_type != "equilibrium":
                gaps.append(
                    ClaimGap(
                        check_id=check_id,
                        code="scenario_type_not_declared",
                        message=(
                            "Check 'force-balance-correct' requires "
                            "source_reference.scenario_type = 'equilibrium'; found "
                            f"{scenario_type!r}. The check is opt-in and cannot run "
                            "without a declared equilibrium scenario."
                        ),
                        metadata={
                            "check_type": check.get("type"),
                            "severity": check.get("severity"),
                            "scenario_type": scenario_type,
                        },
                    )
                )
            else:
                claims.append(
                    _arrow_claim(
                        target="arrows",
                        expected={
                            "scenario_type": scenario_type,
                            "arrows_by_id": {
                                arrow["id"]: {
                                    "rgb": arrow["rgb"],
                                    "name": arrow.get("name"),
                                    "label_text": arrow.get("label_text"),
                                }
                                for arrow in expected_arrows
                            },
                        },
                        evidence_requirements=["arrow_geometry", "arrow_color"],
                        tolerance={
                            "resultant_ratio_tolerance": params.get(
                                "resultant_ratio_tolerance", 0.15
                            ),
                            "color_match_distance": params.get("color_match_distance", 60.0),
                        },
                    )
                )
        else:
            gaps.append(
                ClaimGap(
                    check_id=check_id,
                    code="unsupported_claim_check",
                    message=(
                        f"Check '{check_id}' of type '{check.get('type')}' is not mapped "
                        "to an arrow-v1 ClaimGraph contract."
                    ),
                    metadata={
                        "check_type": check.get("type"),
                        "severity": check.get("severity"),
                    },
                )
            )

    if scenario_type == "equilibrium" and not any(
        claim.check_id == "force-balance-correct" for claim in claims
    ) and not any(gap.check_id == "force-balance-correct" for gap in gaps):
        gaps.append(
            ClaimGap(
                check_id="force-balance-correct",
                code="scenario_without_balance_check",
                message=(
                    "source_reference.scenario_type = 'equilibrium' is declared but no "
                    "'force-balance-correct' check was requested, so the equilibrium "
                    "claim cannot be verified."
                ),
                metadata={"scenario_type": scenario_type},
            )
        )

    return ClaimGraph(
        spec_id=spec["id"],
        domain=spec["domain"],
        risk_level=spec.get("risk_level", "medium"),
        claims=claims,
        gaps=gaps,
        source_reference=source_reference,
        metadata={
            "generator": "arrow-v1",
            "spec_path": str(spec_path),
            "required_elements": spec.get("required_elements", []),
        },
    )


def _geometry_rule_id(check_id: str) -> str:
    return f"geometry-v1.{check_id}"


def build_geometry_claim_graph(spec_path: Path) -> ClaimGraph:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source_reference = spec.get("source_reference", {})
    expected_holes = source_reference.get("holes", [])
    layout = source_reference.get("layout")

    claims: list[ClaimCheck] = []
    gaps: list[ClaimGap] = []
    for check in spec.get("checks", []):
        check_id = check["id"]
        params = check.get("params", {})
        common_metadata = {
            "description": check.get("description"),
            "learning_objective": spec.get("learning_objective"),
        }

        def _geometry_claim(
            target: str,
            expected: dict[str, Any],
            evidence_requirements: list[str],
            tolerance: dict[str, Any] | None = None,
        ) -> ClaimCheck:
            return ClaimCheck(
                claim_id=f"claim-{check_id}",
                rule_id=_geometry_rule_id(check_id),
                check_id=check_id,
                check_type=check["type"],
                severity=check["severity"],
                target=target,
                expected=expected,
                tolerance=tolerance or {},
                evidence_requirements=evidence_requirements,
                metadata=common_metadata,
            )

        if check_id == "hole-count-correct":
            claims.append(
                _geometry_claim(
                    target="holes",
                    expected={"count": len(expected_holes)},
                    evidence_requirements=["hole_geometry"],
                )
            )
        elif check_id == "hole-diameter-ratio-correct":
            claims.append(
                _geometry_claim(
                    target="holes",
                    expected={
                        "ordered_holes": [
                            {"id": hole["id"], "diameter": hole["diameter"]}
                            for hole in expected_holes
                        ]
                    },
                    evidence_requirements=["hole_geometry"],
                    tolerance={
                        "diameter_ratio_tolerance": params.get("diameter_ratio_tolerance", 0.12)
                    },
                )
            )
        elif check_id == "hole-alignment-correct":
            if layout != "linear":
                gaps.append(
                    ClaimGap(
                        check_id=check_id,
                        code="layout_not_declared",
                        message=(
                            "Check 'hole-alignment-correct' requires "
                            "source_reference.layout = 'linear'; found "
                            f"{layout!r}. The check is opt-in and cannot run without "
                            "a declared hole layout."
                        ),
                        metadata={
                            "check_type": check.get("type"),
                            "severity": check.get("severity"),
                            "layout": layout,
                        },
                    )
                )
            else:
                claims.append(
                    _geometry_claim(
                        target="holes",
                        expected={
                            "layout": layout,
                            "ordered_hole_ids": [hole["id"] for hole in expected_holes],
                        },
                        evidence_requirements=["hole_geometry"],
                        tolerance={
                            "alignment_tolerance_px": params.get("alignment_tolerance_px", 6.0),
                            "spacing_ratio_tolerance": params.get("spacing_ratio_tolerance", 0.15),
                        },
                    )
                )
        elif check_id == "dimension-text-correct":
            claims.append(
                _geometry_claim(
                    target="holes",
                    expected={
                        "ordered_holes": [
                            {"id": hole["id"], "dimension_text": hole.get("dimension_text")}
                            for hole in expected_holes
                        ]
                    },
                    evidence_requirements=["hole_geometry", "dimension_text"],
                )
            )
        else:
            gaps.append(
                ClaimGap(
                    check_id=check_id,
                    code="unsupported_claim_check",
                    message=(
                        f"Check '{check_id}' of type '{check.get('type')}' is not mapped "
                        "to a geometry-v1 ClaimGraph contract."
                    ),
                    metadata={
                        "check_type": check.get("type"),
                        "severity": check.get("severity"),
                    },
                )
            )

    if layout == "linear" and not any(
        claim.check_id == "hole-alignment-correct" for claim in claims
    ) and not any(gap.check_id == "hole-alignment-correct" for gap in gaps):
        gaps.append(
            ClaimGap(
                check_id="hole-alignment-correct",
                code="layout_without_alignment_check",
                message=(
                    "source_reference.layout = 'linear' is declared but no "
                    "'hole-alignment-correct' check was requested, so the layout "
                    "claim cannot be verified."
                ),
                metadata={"layout": layout},
            )
        )

    return ClaimGraph(
        spec_id=spec["id"],
        domain=spec["domain"],
        risk_level=spec.get("risk_level", "medium"),
        claims=claims,
        gaps=gaps,
        source_reference=source_reference,
        metadata={
            "generator": "geometry-v1",
            "spec_path": str(spec_path),
            "required_elements": spec.get("required_elements", []),
        },
    )


def _coordinate_rule_id(check_id: str) -> str:
    return f"coordinate-graph-v1.{check_id}"


def build_coordinate_claim_graph(spec_path: Path) -> ClaimGraph:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source_reference = spec.get("source_reference", {})
    expected_points = source_reference.get("points", [])
    polyline = source_reference.get("polyline")
    x_axis_reference = source_reference.get("x_axis", {})
    y_axis_reference = source_reference.get("y_axis", {})

    default_tolerance_x = 0.03 * (
        float(x_axis_reference.get("max", 1.0)) - float(x_axis_reference.get("min", 0.0))
    )
    default_tolerance_y = 0.03 * (
        float(y_axis_reference.get("max", 1.0)) - float(y_axis_reference.get("min", 0.0))
    )

    claims: list[ClaimCheck] = []
    gaps: list[ClaimGap] = []
    for check in spec.get("checks", []):
        check_id = check["id"]
        params = check.get("params", {})
        common_metadata = {
            "description": check.get("description"),
            "learning_objective": spec.get("learning_objective"),
        }

        def _coordinate_claim(
            target: str,
            expected: dict[str, Any],
            evidence_requirements: list[str],
            tolerance: dict[str, Any] | None = None,
        ) -> ClaimCheck:
            return ClaimCheck(
                claim_id=f"claim-{check_id}",
                rule_id=_coordinate_rule_id(check_id),
                check_id=check_id,
                check_type=check["type"],
                severity=check["severity"],
                target=target,
                expected=expected,
                tolerance=tolerance or {},
                evidence_requirements=evidence_requirements,
                metadata=common_metadata,
            )

        if check_id == "point-count-matches":
            claims.append(
                _coordinate_claim(
                    target="points",
                    expected={"count": len(expected_points)},
                    evidence_requirements=["point_geometry"],
                )
            )
        elif check_id == "required-points-present":
            claims.append(
                _coordinate_claim(
                    target="points",
                    expected={
                        "points_by_id": {
                            point["id"]: {"rgb": point["rgb"], "name": point.get("name")}
                            for point in expected_points
                        }
                    },
                    evidence_requirements=["point_geometry", "point_color"],
                    tolerance={"color_match_distance": params.get("color_match_distance", 60.0)},
                )
            )
        elif check_id == "point-positions-correct":
            claims.append(
                _coordinate_claim(
                    target="points",
                    expected={
                        "points_by_id": {
                            point["id"]: {"rgb": point["rgb"], "x": point["x"], "y": point["y"]}
                            for point in expected_points
                        }
                    },
                    evidence_requirements=["point_geometry", "point_color", "axis_mapping"],
                    tolerance={
                        "color_match_distance": params.get("color_match_distance", 60.0),
                        "position_tolerance_x": params.get(
                            "position_tolerance_x", default_tolerance_x
                        ),
                        "position_tolerance_y": params.get(
                            "position_tolerance_y", default_tolerance_y
                        ),
                    },
                )
            )
        elif check_id == "polyline-connections-correct":
            if not polyline or not polyline.get("ordered_point_ids"):
                gaps.append(
                    ClaimGap(
                        check_id=check_id,
                        code="polyline_not_declared",
                        message=(
                            "Check 'polyline-connections-correct' requires "
                            "source_reference.polyline.ordered_point_ids; none was declared. "
                            "The check is opt-in and cannot run without a declared polyline."
                        ),
                        metadata={
                            "check_type": check.get("type"),
                            "severity": check.get("severity"),
                        },
                    )
                )
            else:
                claims.append(
                    _coordinate_claim(
                        target="polyline",
                        expected={
                            "ordered_point_ids": polyline["ordered_point_ids"],
                            "points_by_id": {
                                point["id"]: {"rgb": point["rgb"]} for point in expected_points
                            },
                        },
                        evidence_requirements=["point_geometry", "point_color", "polyline_edges"],
                        tolerance={
                            "color_match_distance": params.get("color_match_distance", 60.0)
                        },
                    )
                )
        elif check_id == "axis-scale-correct":
            claims.append(
                _coordinate_claim(
                    target="axes",
                    expected={
                        "x_axis": {
                            "expected_min": x_axis_reference.get("min"),
                            "expected_max": x_axis_reference.get("max"),
                        },
                        "y_axis": {
                            "expected_min": y_axis_reference.get("min"),
                            "expected_max": y_axis_reference.get("max"),
                        },
                    },
                    evidence_requirements=["axis_mapping"],
                    tolerance={"axis_value_tolerance": params.get("axis_value_tolerance", 0.5)},
                )
            )
        else:
            gaps.append(
                ClaimGap(
                    check_id=check_id,
                    code="unsupported_claim_check",
                    message=(
                        f"Check '{check_id}' of type '{check.get('type')}' is not mapped "
                        "to a coordinate-graph-v1 ClaimGraph contract."
                    ),
                    metadata={
                        "check_type": check.get("type"),
                        "severity": check.get("severity"),
                    },
                )
            )

    if polyline and polyline.get("ordered_point_ids") and not any(
        claim.check_id == "polyline-connections-correct" for claim in claims
    ) and not any(gap.check_id == "polyline-connections-correct" for gap in gaps):
        gaps.append(
            ClaimGap(
                check_id="polyline-connections-correct",
                code="polyline_without_connections_check",
                message=(
                    "source_reference.polyline is declared but no "
                    "'polyline-connections-correct' check was requested, so the polyline "
                    "claim cannot be verified."
                ),
                metadata={"polyline": polyline},
            )
        )

    return ClaimGraph(
        spec_id=spec["id"],
        domain=spec["domain"],
        risk_level=spec.get("risk_level", "medium"),
        claims=claims,
        gaps=gaps,
        source_reference=source_reference,
        metadata={
            "generator": "coordinate-graph-v1",
            "spec_path": str(spec_path),
            "required_elements": spec.get("required_elements", []),
        },
    )


def build_chart_claim_graph(spec_path: Path) -> ClaimGraph:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source_reference = spec.get("source_reference", {})
    source_data = source_reference.get("data", [])
    axis_expectations = source_reference.get("axis", {})
    expected_y_label = next(
        (label["text"] for label in spec.get("labels", []) if label.get("target") == "y_axis"),
        None,
    )
    expected_unit = _expected_unit_from_label(expected_y_label)

    claims: list[ClaimCheck] = []
    gaps: list[ClaimGap] = []
    for check in spec.get("checks", []):
        check_id = check["id"]
        common_metadata = {
            "description": check.get("description"),
            "learning_objective": spec.get("learning_objective"),
        }
        if check_id == "bar-values-match-data":
            claims.append(
                _chart_claim(
                    check=check,
                    target="bars",
                    expected={
                        "values_by_category": {
                            _source_category(item): _source_value(item) for item in source_data
                        },
                        "expected_scale_mode": axis_expectations.get("expected_scale_mode"),
                        "expected_min_value": axis_expectations.get("expected_min_value"),
                        "expected_max_value": axis_expectations.get("expected_max_value"),
                    },
                    tolerance={
                        "relative_tolerance": check.get("params", {}).get("relative_tolerance", 0.05)
                    },
                    evidence_requirements=["bar_categories", "bar_values", "axis_mapping"],
                    metadata=common_metadata,
                )
            )
        elif check_id == "axis-label-present":
            claims.append(
                _chart_claim(
                    check=check,
                    target="y_axis_label",
                    expected={"label_text": expected_y_label},
                    evidence_requirements=["axis_label_text"],
                    metadata=common_metadata,
                )
            )
        elif check_id == "axis-unit-present":
            claims.append(
                _chart_claim(
                    check=check,
                    target="y_axis_unit",
                    expected={"unit_text": expected_unit},
                    evidence_requirements=["axis_label_text", "axis_unit_text"],
                    metadata=common_metadata,
                )
            )
        elif check_id == "bar-count-matches":
            claims.append(
                _chart_claim(
                    check=check,
                    target="bars",
                    expected={"count": len(source_data)},
                    evidence_requirements=["bar_geometry"],
                    metadata=common_metadata,
                )
            )
        elif check_id == "axis-scale-readable":
            claims.append(
                _chart_claim(
                    check=check,
                    target="y_axis_scale",
                    expected={"readable": True},
                    evidence_requirements=["tick_labels", "axis_mapping"],
                    metadata=common_metadata,
                )
            )
        elif check_id == "axis-scale-monotonic":
            claims.append(
                _chart_claim(
                    check=check,
                    target="y_axis_scale",
                    expected={"monotonic": True},
                    evidence_requirements=["tick_labels"],
                    metadata=common_metadata,
                )
            )
        elif check_id == "axis-zero-line-resolved":
            claims.append(
                _chart_claim(
                    check=check,
                    target="y_axis_scale",
                    expected={
                        "zero_line_resolved": True,
                        "required_for_scale_mode": axis_expectations.get("expected_scale_mode"),
                    },
                    evidence_requirements=["axis_mapping", "zero_line_geometry"],
                    metadata=common_metadata,
                )
            )
        else:
            gaps.append(
                ClaimGap(
                    check_id=check_id,
                    code="unsupported_claim_check",
                    message=(
                        f"Check '{check_id}' of type '{check.get('type')}' is not mapped "
                        "to a chart-v2 ClaimGraph contract."
                    ),
                    metadata={
                        "check_type": check.get("type"),
                        "severity": check.get("severity"),
                    },
                )
            )

    return ClaimGraph(
        spec_id=spec["id"],
        domain=spec["domain"],
        risk_level=spec.get("risk_level", "medium"),
        claims=claims,
        gaps=gaps,
        source_reference=source_reference,
        metadata={
            "generator": "chart-v2",
            "spec_path": str(spec_path),
            "required_elements": spec.get("required_elements", []),
        },
    )

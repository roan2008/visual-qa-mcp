from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import EvidenceGraph, Finding, OverlayAnnotation, VisualQaReport


def _severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}[severity]


def _make_finding(
    finding_id: str,
    finding_type: str,
    severity: str,
    message: str,
    evidence: dict[str, Any],
    recommendation: str,
) -> Finding:
    return Finding(
        id=finding_id,
        type=finding_type,
        severity=severity,
        message=message,
        evidence=evidence,
        recommendation=recommendation,
    )


def _overall_verdict(findings: list[Finding], skipped: list[dict[str, str]]) -> str:
    if skipped:
        return "needs_review"
    if any(finding.severity == "critical" for finding in findings):
        return "fail"
    if any(finding.severity == "high" for finding in findings):
        return "fail"
    if findings:
        return "warning"
    return "pass"


def run_chart_rules(spec_path: Path, evidence: EvidenceGraph) -> VisualQaReport:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source_data = spec.get("source_reference", {}).get("data", [])
    checks = {check["id"]: check for check in spec.get("checks", [])}
    expected_y_label = next(
        (label["text"] for label in spec.get("labels", []) if label.get("target") == "y_axis"),
        None,
    )
    expected_unit = None
    if expected_y_label and "(" in expected_y_label and ")" in expected_y_label:
        expected_unit = expected_y_label.split("(")[1].split(")")[0]

    findings: list[Finding] = []
    checks_run: list[str] = []
    checks_skipped: list[dict[str, str]] = []
    overlay_annotations: list[OverlayAnnotation] = []

    gaps_by_code = {gap.code: gap for gap in evidence.gaps}
    skipped_by_check: dict[str, list[str]] = {}
    for gap in evidence.gaps:
        for check_id in gap.check_ids:
            skipped_by_check.setdefault(check_id, []).append(gap.message)

    bar_count_check_id = "bar-count-matches"
    if bar_count_check_id in checks:
        checks_run.append(bar_count_check_id)
        expected_count = len(source_data)
        detected_count = len(evidence.bars)
        if detected_count != expected_count:
            finding = _make_finding(
                "finding-bar-count",
                "bar_count_mismatch",
                "high",
                f"Detected {detected_count} bars but expected {expected_count}.",
                {"expected_count": expected_count, "detected_count": detected_count},
                "Regenerate the chart with the required number of bars.",
            )
            findings.append(finding)

    scale_readable_check = "axis-scale-readable"
    if scale_readable_check in checks:
        readable_codes = {"axis_scale_unreadable", "insufficient_tick_evidence", "optional_ocr_unavailable", "invalid_tick_geometry"}
        reasons = [gaps_by_code[code].message for code in readable_codes if code in gaps_by_code]
        if reasons:
            checks_skipped.append({"check_id": scale_readable_check, "reason": reasons[0]})
        else:
            checks_run.append(scale_readable_check)

    monotonic_check = "axis-scale-monotonic"
    if monotonic_check in checks:
        monotonic_codes = {"non_monotonic_tick_values", "inconsistent_tick_step"}
        reasons = [gaps_by_code[code].message for code in monotonic_codes if code in gaps_by_code]
        if reasons:
            checks_skipped.append({"check_id": monotonic_check, "reason": reasons[0]})
        else:
            checks_run.append(monotonic_check)

    zero_line_check = "axis-zero-line-resolved"
    if zero_line_check in checks:
        if "axis_zero_line_unresolved" in gaps_by_code:
            checks_skipped.append({"check_id": zero_line_check, "reason": gaps_by_code["axis_zero_line_unresolved"].message})
        else:
            checks_run.append(zero_line_check)

    chart_check_id = "bar-values-match-data"
    if chart_check_id in checks and chart_check_id in skipped_by_check:
        checks_skipped.append({"check_id": chart_check_id, "reason": skipped_by_check[chart_check_id][0]})
    elif chart_check_id in checks:
        checks_run.append(chart_check_id)
        tolerance = checks.get(chart_check_id, {}).get("params", {}).get("relative_tolerance", 0.05)
        expected_by_label = {item["month"]: float(item["rainfall_mm"]) for item in source_data}
        for bar in evidence.bars:
            if bar.category is None or bar.value is None:
                continue
            expected_value = expected_by_label.get(bar.category)
            if expected_value is None:
                finding_id = f"finding-unexpected-category-{bar.bar_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        "unexpected_category",
                        "high",
                        f"Detected bar category '{bar.category}' is not part of the source data.",
                        {"bar_id": bar.bar_id, "category": bar.category},
                        "Correct the x-axis label so each bar maps to a known source-data category.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id,
                        kind="bbox",
                        bbox=bar.bbox,
                        label="Unexpected category",
                    )
                )
                continue
            delta = abs(bar.value - expected_value)
            relative = delta / max(abs(expected_value), 1.0)
            if relative > tolerance:
                finding_id = f"finding-bar-value-{bar.bar_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        "chart_value_mismatch",
                        "critical",
                        f"Bar '{bar.category}' value {bar.value:.2f} does not match expected {expected_value:.2f}.",
                        {
                            "bar_id": bar.bar_id,
                            "category": bar.category,
                            "expected_value": expected_value,
                            "detected_value": bar.value,
                            "relative_tolerance": tolerance,
                            "value_source": bar.value_source,
                        },
                        "Update the bar height so it matches the source data within tolerance.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id,
                        kind="bbox",
                        bbox=bar.bbox,
                        label=f"{bar.category}: value mismatch",
                    )
                )

    label_check_id = "axis-label-present"
    if label_check_id in checks and label_check_id in skipped_by_check:
        checks_skipped.append({"check_id": label_check_id, "reason": skipped_by_check[label_check_id][0]})
    elif label_check_id in checks:
        checks_run.append(label_check_id)
        if evidence.y_axis.label_text != expected_y_label:
            findings.append(
                _make_finding(
                    "finding-axis-label",
                    "label_missing_or_wrong",
                    "high",
                    "The y-axis label is missing or does not match the expected text.",
                    {
                        "expected_label": expected_y_label,
                        "detected_label": evidence.y_axis.label_text,
                    },
                    "Restore the required y-axis label text.",
                )
            )
            overlay_annotations.append(
                OverlayAnnotation(
                    finding_id="finding-axis-label",
                    kind="bbox",
                    bbox=evidence.y_axis.label_bbox,
                    label="Axis label issue",
                )
            )

    unit_check_id = "axis-unit-present"
    if unit_check_id in checks and unit_check_id in skipped_by_check:
        checks_skipped.append({"check_id": unit_check_id, "reason": skipped_by_check[unit_check_id][0]})
    elif unit_check_id in checks:
        checks_run.append(unit_check_id)
        if evidence.y_axis.unit_text != expected_unit:
            findings.append(
                _make_finding(
                    "finding-axis-unit",
                    "unit_mismatch",
                    "high",
                    "The y-axis unit is missing or incorrect.",
                    {"expected_unit": expected_unit, "detected_unit": evidence.y_axis.unit_text},
                    "Restore the expected y-axis unit in the label.",
                )
            )
            overlay_annotations.append(
                OverlayAnnotation(
                    finding_id="finding-axis-unit",
                    kind="bbox",
                    bbox=evidence.y_axis.label_bbox,
                    label="Axis unit issue",
                )
            )

    findings = sorted(findings, key=lambda item: _severity_rank(item.severity), reverse=True)
    verdict = _overall_verdict(findings, checks_skipped)
    return VisualQaReport(
        image_id=evidence.image_id,
        spec_id=spec["id"],
        verdict=verdict,
        findings=findings,
        checks_run=checks_run,
        checks_skipped=checks_skipped,
        confidence=evidence.extraction_confidence,
        overlay_annotations=overlay_annotations,
    )

from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_qa_mcp.claim_graph import build_chart_claim_graph
from visual_qa_mcp.chart_rules import run_chart_rules
from visual_qa_mcp.contracts import AxisMapping, EvidenceGap, EvidenceGraph, ExtractedAxis, ExtractedBar, ExtractionProvenance, TickLabel


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "specs" / "examples" / "chart-bar.visual-spec.json"


def make_evidence(
    bars: list[ExtractedBar],
    axis_label: str | None = "Rainfall (mm)",
    unit: str | None = "mm",
    gaps: list[EvidenceGap] | None = None,
    mapping: AxisMapping | None = None,
    tick_values: list[float] | None = None,
) -> EvidenceGraph:
    tick_values = tick_values or [80, 60, 40, 20, 0]
    ticks = [
        TickLabel(text=str(int(value)), parsed_value=value, bbox=[24, 80 + idx * 40, 88, 102 + idx * 40], confidence=0.92)
        for idx, value in enumerate(tick_values)
    ]
    return EvidenceGraph(
        image_id="test-image",
        chart_type="bar",
        bars=bars,
        x_axis_labels=[bar.category for bar in bars],
        y_axis=ExtractedAxis(
            label_text=axis_label,
            unit_text=unit,
            label_bbox=[150, 24, 500, 52],
            confidence=0.9,
            tick_labels=ticks,
            axis_line_x=130,
            baseline_y=320,
            top_y=80,
            zero_line_y=None,
            mapping=mapping or AxisMapping(
                min_value=0,
                max_value=80,
                pixels_per_unit=4.0,
                scale_mode="zero_baseline",
                value_direction="positive_up",
                readable=True,
            ),
            backend="template",
        ),
        extraction_confidence=0.9,
        provenance=ExtractionProvenance(
            extractor_id="chart-v2",
            extractor_version="0.2.0",
            backend="template",
            metadata_source="file",
            dependency_versions={"numpy": "test", "pillow": "test", "jsonschema": "test", "mcp": "test"},
            environment={},
        ),
        gaps=gaps or [],
        metadata={"axis_mode": "zero_baseline"},
    )


def make_bar(label: str | None, value: float, bbox: list[int] | None = None) -> ExtractedBar:
    return ExtractedBar(
        bar_id=f"bar-{label or 'unknown'}",
        category=label,
        value=value,
        bbox=bbox or [100, 100, 140, 320],
        confidence=0.9,
        matched_label=label,
        top_y=100,
        bottom_y=320,
        value_source="axis_mapping",
    )


def test_pass_when_all_required_checks_succeed() -> None:
    evidence = make_evidence([make_bar("Jan", 40), make_bar("Feb", 70), make_bar("Mar", 55)])
    report = run_chart_rules(SPEC_PATH, evidence)
    assert report.verdict == "pass"
    assert report.findings == []


def test_value_outside_tolerance_fails() -> None:
    evidence = make_evidence([make_bar("Jan", 40), make_bar("Feb", 50), make_bar("Mar", 55)])
    report = run_chart_rules(SPEC_PATH, evidence)
    assert report.verdict == "fail"
    assert any(finding.type == "chart_value_mismatch" for finding in report.findings)


def test_wrong_axis_label_fails() -> None:
    evidence = make_evidence(
        [make_bar("Jan", 40), make_bar("Feb", 70), make_bar("Mar", 55)],
        axis_label="Rainfall (cm)",
        unit="cm",
    )
    report = run_chart_rules(SPEC_PATH, evidence)
    assert report.verdict == "fail"
    assert {finding.type for finding in report.findings} >= {"label_missing_or_wrong", "unit_mismatch"}


def test_missing_scale_evidence_promotes_needs_review() -> None:
    evidence = make_evidence(
        [make_bar("Jan", 40), make_bar("Feb", 70), make_bar("Mar", 55)],
        gaps=[EvidenceGap(code="axis_scale_unreadable", message="scale unreadable", check_ids=["axis-scale-readable", "bar-values-match-data"])],
        mapping=None,
        tick_values=[80, 60],
    )
    report = run_chart_rules(SPEC_PATH, evidence)
    assert report.verdict == "needs_review"
    assert {item["check_id"] for item in report.checks_skipped} >= {"axis-scale-readable", "bar-values-match-data"}


def test_bar_count_mismatch_fails() -> None:
    evidence = make_evidence([make_bar("Jan", 40), make_bar("Feb", 70)])
    report = run_chart_rules(SPEC_PATH, evidence)
    assert report.verdict == "fail"
    assert any(finding.type == "bar_count_mismatch" for finding in report.findings)


@pytest.mark.parametrize(
    ("jan", "expected_verdict"),
    [
        (38, "pass"),
        (35, "fail"),
    ],
)
def test_tolerance_boundary(jan: float, expected_verdict: str) -> None:
    evidence = make_evidence([make_bar("Jan", jan), make_bar("Feb", 70), make_bar("Mar", 55)])
    report = run_chart_rules(SPEC_PATH, evidence)
    assert report.verdict == expected_verdict


def test_chart_claim_graph_captures_expected_scale_mode_and_values() -> None:
    claim_graph = build_chart_claim_graph(SPEC_PATH)
    claims_by_check = {claim.check_id: claim for claim in claim_graph.claims}
    assert claims_by_check["bar-values-match-data"].rule_id == "chart-v2.bar-values-match-data"
    assert claims_by_check["bar-values-match-data"].expected["expected_scale_mode"] == "zero_baseline"
    assert claims_by_check["bar-values-match-data"].expected["values_by_category"]["Feb"] == 70.0
    assert claims_by_check["axis-unit-present"].expected["unit_text"] == "mm"
    assert claim_graph.gaps == []


def test_unknown_check_becomes_claim_gap_and_needs_review(tmp_path: Path) -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    spec["checks"].append(
        {
            "id": "legend-present",
            "type": "legend_present",
            "severity": "high",
            "description": "Legend must be visible.",
        }
    )
    spec_path = tmp_path / "unknown-check.visual-spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    claim_graph = build_chart_claim_graph(spec_path)
    assert [gap.check_id for gap in claim_graph.gaps] == ["legend-present"]

    evidence = make_evidence([make_bar("Jan", 40), make_bar("Feb", 70), make_bar("Mar", 55)])
    report = run_chart_rules(spec_path, evidence)
    assert report.verdict == "needs_review"
    assert {item["check_id"] for item in report.checks_skipped} >= {"legend-present"}


def test_mistyped_known_check_becomes_claim_gap_and_needs_review(tmp_path: Path) -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    spec["checks"][0]["id"] = "bar-values-match-dtaa"
    spec_path = tmp_path / "mistyped-check.visual-spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    claim_graph = build_chart_claim_graph(spec_path)
    assert [gap.check_id for gap in claim_graph.gaps] == ["bar-values-match-dtaa"]

    evidence = make_evidence([make_bar("Jan", 40), make_bar("Feb", 70), make_bar("Mar", 55)])
    report = run_chart_rules(spec_path, evidence)
    assert report.verdict == "needs_review"
    assert {item["check_id"] for item in report.checks_skipped} >= {"bar-values-match-dtaa"}

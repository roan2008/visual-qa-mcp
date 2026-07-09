from __future__ import annotations

from pathlib import Path

from visual_qa_mcp.generate_dataset import build_dataset
from visual_qa_mcp.validation import discover_cases, load_json, load_schema, run_case, summarize_validation_results, validate_json


ROOT = Path(__file__).resolve().parents[2]


def test_dataset_has_expected_case_counts(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    cases = discover_cases(dataset_root)
    assert len(cases) == 24
    assert sum(1 for case in cases if case.kind == "golden") == 8
    assert sum(1 for case in cases if case.kind == "mutated") == 16


def test_end_to_end_cases_produce_schema_valid_reports(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    findings_schema = load_schema(ROOT / "specs" / "findings.schema.json")
    for case in discover_cases(dataset_root):
        evidence, report = run_case(case, evidence_schema)
        assert validate_json(evidence_schema, evidence.to_dict()) == []
        assert validate_json(findings_schema, report.to_dict()) == []
        assert (case.image_path.parent / "overlay.png").exists()
        assert (case.image_path.parent / "report.json").exists()


def test_expected_defects_are_flagged(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    for case in discover_cases(dataset_root):
        _, report = run_case(case, evidence_schema)
        expected = load_json(case.expected_report_path)
        actual_types = {finding.type for finding in report.findings}
        assert expected["verdict"] == report.verdict
        assert set(expected.get("expected_finding_types", [])).issubset(actual_types)


def test_optional_ocr_backend_case_degrades_to_needs_review(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "mutated-16")
    evidence, report = run_case(case, evidence_schema)
    assert evidence.y_axis.backend == "optional_ocr"
    assert report.verdict == "needs_review"


def test_validation_summary_hits_v2_targets(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    summary = summarize_validation_results(dataset_root)
    assert summary["total_cases"] == 24
    assert summary["critical_error_recall"] >= 0.85
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_failures"] == 0
    assert "signed" in summary["subset_metrics"]
    assert "zero_baseline" in summary["subset_metrics"]

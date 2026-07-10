from __future__ import annotations
import io
import json
from pathlib import Path
from contextlib import redirect_stdout

import pytest

import visual_qa_mcp.cli as cli_module
import visual_qa_mcp.validation as validation_module
from visual_qa_mcp.contracts import ClaimGraph, VerificationResult
from visual_qa_mcp.generate_dataset import build_dataset, build_noisy_dataset, build_realworld_pilot_dataset
from visual_qa_mcp.service import run_chart_verification, write_verification_artifacts
from visual_qa_mcp.validation import (
    discover_cases,
    load_json,
    load_schema,
    run_case,
    summarize_ocr_validation,
    summarize_phase2_validation,
    summarize_validation_results,
    verify_dataset_manifest,
    validate_json,
)


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
    claim_schema = load_schema(ROOT / "specs" / "claim-graph.schema.json")
    for case in discover_cases(dataset_root):
        evidence, report = run_case(case, evidence_schema)
        assert validate_json(evidence_schema, evidence.to_dict()) == []
        assert validate_json(findings_schema, report.to_dict()) == []
        assert (case.image_path.parent / "overlay.png").exists()
        claim_payload = load_json(case.image_path.parent / "claim_graph.json")
        assert validate_json(claim_schema, claim_payload) == []
        assert report.claim_graph_path == str(case.image_path.parent / "claim_graph.json")
        assert (case.image_path.parent / "report.json").exists()
        report_payload = load_json(case.image_path.parent / "report.json")
        assert report_payload["claim_graph_path"] == str(case.image_path.parent / "claim_graph.json")


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


def test_run_case_rejects_invalid_claim_graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    case = discover_cases(dataset_root)[0]
    valid_result = run_chart_verification(case.image_path, case.spec_path, case.metadata_path, backend=case.backend)

    def invalid_result(*args: object, **kwargs: object) -> VerificationResult:
        return VerificationResult(
            image_path=valid_result.image_path,
            spec_path=valid_result.spec_path,
            metadata_path=valid_result.metadata_path,
            backend=valid_result.backend,
            claim_graph=ClaimGraph(
                spec_id="bad-claim",
                domain="chart",
                risk_level="invalid",
                claims=[],
                gaps=[],
                source_reference={},
                metadata={},
            ),
            evidence_graph=valid_result.evidence_graph,
            report=valid_result.report,
        )

    monkeypatch.setattr(validation_module, "run_chart_verification", invalid_result)

    with pytest.raises(ValueError, match="Claim schema validation failed"):
        run_case(case, evidence_schema)


def test_service_verification_is_pure_and_schema_valid(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    findings_schema = load_schema(ROOT / "specs" / "findings.schema.json")
    claim_schema = load_schema(ROOT / "specs" / "claim-graph.schema.json")

    result = run_chart_verification(case.image_path, case.spec_path, case.metadata_path, backend=case.backend)

    assert validate_json(claim_schema, result.claim_graph.to_dict()) == []
    assert validate_json(evidence_schema, result.evidence_graph.to_dict()) == []
    assert validate_json(findings_schema, result.report.to_dict()) == []
    assert result.evidence_graph.provenance.extractor_id == "chart-v2"
    assert result.report.extraction_confidence == result.evidence_graph.extraction_confidence
    assert not (case.image_path.parent / "report.json").exists()
    assert not (case.image_path.parent / "claim_graph.json").exists()
    assert not (case.image_path.parent / "evidence_graph.json").exists()
    assert not (case.image_path.parent / "overlay.png").exists()


def test_artifact_writer_emits_expected_files_and_paths(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    result = run_chart_verification(case.image_path, case.spec_path, case.metadata_path, backend=case.backend)
    paths = write_verification_artifacts(result, case.image_path.parent)

    assert paths.claim_graph_path.exists()
    assert paths.evidence_graph_path.exists()
    assert paths.report_path.exists()
    assert paths.overlay_path.exists()
    assert result.report.claim_graph_path == str(paths.claim_graph_path)
    assert result.report.evidence_graph_path == str(paths.evidence_graph_path)
    report_payload = load_json(paths.report_path)
    assert report_payload["claim_graph_path"] == str(paths.claim_graph_path)
    assert report_payload["evidence_graph_path"] == str(paths.evidence_graph_path)


def test_run_case_delegates_to_service_layer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = discover_cases(dataset_root)[0]
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    calls: list[str] = []
    real_run = validation_module.run_chart_verification
    real_write = validation_module.write_verification_artifacts

    def tracked_run(*args: object, **kwargs: object):
        calls.append("run")
        return real_run(*args, **kwargs)

    def tracked_write(*args: object, **kwargs: object):
        calls.append("write")
        return real_write(*args, **kwargs)

    monkeypatch.setattr(validation_module, "run_chart_verification", tracked_run)
    monkeypatch.setattr(validation_module, "write_verification_artifacts", tracked_write)

    run_case(case, evidence_schema)
    assert calls == ["run", "write"]


def test_template_backend_can_run_without_metadata_when_defaults_are_safe(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    result = run_chart_verification(case.image_path, case.spec_path, metadata_path=None, backend="template")

    assert result.report.verdict == "pass"
    assert result.evidence_graph.y_axis.backend == "template"
    assert result.evidence_graph.image_id == "image"


def test_optional_ocr_without_metadata_still_degrades_safely(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    result = run_chart_verification(case.image_path, case.spec_path, metadata_path=None, backend="optional_ocr")

    assert result.report.verdict == "needs_review"
    assert any(gap.code == "optional_ocr_unavailable" for gap in result.evidence_graph.gaps)


def test_cli_commands_emit_valid_json(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    findings_schema = load_schema(ROOT / "specs" / "findings.schema.json")
    claim_schema = load_schema(ROOT / "specs" / "claim-graph.schema.json")

    def run_cli(argv: list[str]) -> dict[str, object]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli_module.main(argv)
        assert exit_code == 0
        return json.loads(buffer.getvalue())

    claim_payload = run_cli(["build-claim-graph", str(case.spec_path)])
    assert validate_json(claim_schema, claim_payload) == []

    evidence_payload = run_cli(
        [
            "extract-chart-evidence",
            str(case.image_path),
            str(case.spec_path),
            "--metadata",
            str(case.metadata_path),
        ]
    )
    assert validate_json(evidence_schema, evidence_payload) == []

    output_dir = tmp_path / "cli-output"
    verify_payload = run_cli(
        [
            "verify-chart",
            str(case.image_path),
            str(case.spec_path),
            "--metadata",
            str(case.metadata_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    assert validate_json(claim_schema, verify_payload["claim_graph"]) == []
    assert validate_json(evidence_schema, verify_payload["evidence_graph"]) == []
    assert validate_json(findings_schema, verify_payload["report"]) == []
    assert Path(verify_payload["artifact_paths"]["report_path"]).exists()


def test_phase2_validation_reports_controlled_and_noisy_tracks(tmp_path: Path) -> None:
    controlled_root = tmp_path / "chart-v2"
    noisy_root = tmp_path / "chart-v2-noisy"
    build_dataset(controlled_root)
    build_noisy_dataset(noisy_root)
    summary = summarize_phase2_validation(controlled_root, noisy_root)
    assert summary["controlled"]["total_cases"] == 24
    assert summary["controlled"]["false_unsupported_passes"] == 0
    assert summary["noisy"]["total_cases"] == 6
    assert summary["noisy"]["golden_cases"] == 2
    assert summary["noisy"]["mutated_cases"] == 4
    assert summary["noisy"]["golden_non_passes"] == 0
    assert summary["noisy"]["typed_mutated_cases"] == 2
    assert summary["noisy"]["typed_mutated_hits"] == 2
    assert summary["noisy"]["ambiguous_cases"] == 2
    assert summary["noisy"]["ambiguous_guard_rate"] == 1.0
    assert summary["noisy"]["verdict_mismatches"] == 0
    assert summary["noisy"]["false_unsupported_passes"] == 0


def test_ocr_validation_reports_environment_and_separate_metrics(tmp_path: Path) -> None:
    controlled_root = tmp_path / "chart-v2"
    noisy_root = tmp_path / "chart-v2-noisy"
    build_dataset(controlled_root)
    build_noisy_dataset(noisy_root)
    summary = summarize_ocr_validation(controlled_root, noisy_root)
    assert "environment" in summary
    assert "tesseract_available" in summary["environment"]
    assert summary["controlled"]["false_unsupported_passes"] == 0
    assert summary["noisy"]["false_unsupported_passes"] == 0


def test_realworld_pilot_meets_bounded_evidence_gate(tmp_path: Path) -> None:
    pilot_root = tmp_path / "chart-v2-realworld-pilot"
    build_realworld_pilot_dataset(pilot_root)
    summary = summarize_validation_results(pilot_root)
    manifest = verify_dataset_manifest(pilot_root)

    assert summary["total_cases"] == 24
    assert summary["golden_cases"] == 10
    assert summary["typed_mutated_cases"] == 7
    assert summary["critical_error_recall"] >= 0.85
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_failures"] == 0
    assert 1 - summary["golden_non_passes"] / summary["golden_cases"] >= 0.80
    assert summary["evidence_metrics"]["bar_count_accuracy"] >= 0.95
    assert summary["evidence_metrics"]["tick_sequence_accuracy"] >= 0.90
    assert summary["evidence_metrics"]["label_accuracy"] >= 0.90
    assert manifest == {"valid": True, "case_count": 24, "mismatches": []}


def test_realworld_manifest_rejects_incomplete_case_list(tmp_path: Path) -> None:
    pilot_root = tmp_path / "chart-v2-realworld-pilot"
    build_realworld_pilot_dataset(pilot_root)
    manifest_path = pilot_root / "manifest.json"
    manifest = load_json(manifest_path)
    manifest["cases"] = manifest["cases"][:-1]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    result = verify_dataset_manifest(pilot_root)
    assert result["valid"] is False
    assert "manifest:case_count_does_not_match_list" in result["mismatches"]
    assert any(item.startswith("manifest:unlisted_case:") for item in result["mismatches"])


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

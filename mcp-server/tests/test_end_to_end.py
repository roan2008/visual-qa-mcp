from __future__ import annotations
import io
import json
import shutil
from pathlib import Path
from contextlib import redirect_stdout

import pytest

import visual_qa_mcp.cli as cli_module
import visual_qa_mcp.validation as validation_module
from visual_qa_mcp.contracts import ClaimGraph, VerificationResult
from visual_qa_mcp.generate_dataset import (
    build_covering_array_dataset,
    build_dataset,
    build_noisy_dataset,
    build_realworld_pilot_dataset,
)
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


@pytest.fixture(scope="module")
def chart_datasets(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("chart-datasets")
    paths = {
        "controlled": root / "chart-v2",
        "noisy": root / "chart-v2-noisy",
        "pilot": root / "chart-v2-realworld-pilot",
    }
    build_dataset(paths["controlled"])
    build_noisy_dataset(paths["noisy"])
    build_realworld_pilot_dataset(paths["pilot"])
    return paths


@pytest.fixture(scope="module")
def phase2_summary(chart_datasets: dict[str, Path]) -> dict:
    return summarize_phase2_validation(chart_datasets["controlled"], chart_datasets["noisy"])


def test_dataset_has_expected_case_counts(chart_datasets: dict[str, Path]) -> None:
    dataset_root = chart_datasets["controlled"]
    cases = discover_cases(dataset_root)
    assert len(cases) == 24
    assert sum(1 for case in cases if case.kind == "golden") == 8
    assert sum(1 for case in cases if case.kind == "mutated") == 16


def test_end_to_end_cases_produce_schema_valid_reports(phase2_summary: dict) -> None:
    # The summary path validates every claim, evidence, and report schema without
    # writing per-case artifacts; artifact persistence is covered separately.
    assert phase2_summary["controlled"]["total_cases"] == 24
    assert len(phase2_summary["controlled"]["results"]) == 24


def test_expected_defects_are_flagged(phase2_summary: dict) -> None:
    assert phase2_summary["controlled"]["verdict_mismatches"] == 0
    assert phase2_summary["controlled"]["typed_mutated_hits"] == 9


def test_optional_ocr_backend_case_degrades_to_needs_review(chart_datasets: dict[str, Path]) -> None:
    dataset_root = chart_datasets["controlled"]
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "mutated-16")
    evidence, report = run_case(case, evidence_schema, write_artifacts=False)
    assert evidence.y_axis.backend == "optional_ocr"
    assert report.verdict == "needs_review"


def test_run_case_rejects_invalid_claim_graph(chart_datasets: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_root = chart_datasets["controlled"]
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


def test_service_verification_is_pure_and_schema_valid(chart_datasets: dict[str, Path]) -> None:
    dataset_root = chart_datasets["controlled"]
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


def test_artifact_writer_emits_expected_files_and_paths(chart_datasets: dict[str, Path], tmp_path: Path) -> None:
    dataset_root = chart_datasets["controlled"]
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    result = run_chart_verification(case.image_path, case.spec_path, case.metadata_path, backend=case.backend)
    paths = write_verification_artifacts(result, tmp_path / "artifacts")

    assert paths.claim_graph_path.exists()
    assert paths.evidence_graph_path.exists()
    assert paths.report_path.exists()
    assert paths.overlay_path.exists()
    assert result.report.claim_graph_path == str(paths.claim_graph_path)
    assert result.report.evidence_graph_path == str(paths.evidence_graph_path)
    report_payload = load_json(paths.report_path)
    assert report_payload["claim_graph_path"] == str(paths.claim_graph_path)
    assert report_payload["evidence_graph_path"] == str(paths.evidence_graph_path)


def test_run_case_delegates_to_service_layer(chart_datasets: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_root = tmp_path / "chart-v2"
    shutil.copytree(chart_datasets["controlled"], dataset_root)
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


def test_template_backend_can_run_without_metadata_when_defaults_are_safe(chart_datasets: dict[str, Path]) -> None:
    dataset_root = chart_datasets["controlled"]
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    result = run_chart_verification(case.image_path, case.spec_path, metadata_path=None, backend="template")

    assert result.report.verdict == "pass"
    assert result.evidence_graph.y_axis.backend == "template"
    assert result.evidence_graph.image_id == "image"


def test_optional_ocr_without_metadata_still_degrades_safely(chart_datasets: dict[str, Path]) -> None:
    dataset_root = chart_datasets["controlled"]
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "golden-01")

    result = run_chart_verification(case.image_path, case.spec_path, metadata_path=None, backend="optional_ocr")

    assert result.report.verdict == "needs_review"
    assert any(gap.code == "optional_ocr_unavailable" for gap in result.evidence_graph.gaps)


def test_cli_commands_emit_valid_json(chart_datasets: dict[str, Path], tmp_path: Path) -> None:
    dataset_root = chart_datasets["controlled"]
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


def test_phase2_validation_reports_controlled_and_noisy_tracks(phase2_summary: dict) -> None:
    summary = phase2_summary
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


def test_ocr_validation_reports_environment_and_separate_metrics(chart_datasets: dict[str, Path]) -> None:
    summary = summarize_ocr_validation(chart_datasets["controlled"], chart_datasets["noisy"])
    assert "environment" in summary
    assert "tesseract_available" in summary["environment"]
    assert summary["controlled"]["false_unsupported_passes"] == 0
    assert summary["noisy"]["false_unsupported_passes"] == 0


def test_realworld_pilot_meets_bounded_evidence_gate(chart_datasets: dict[str, Path]) -> None:
    pilot_root = chart_datasets["pilot"]
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


def test_realworld_manifest_rejects_incomplete_case_list(chart_datasets: dict[str, Path], tmp_path: Path) -> None:
    pilot_root = tmp_path / "chart-v2-realworld-pilot"
    shutil.copytree(chart_datasets["pilot"], pilot_root)
    manifest_path = pilot_root / "manifest.json"
    manifest = load_json(manifest_path)
    manifest["cases"] = manifest["cases"][:-1]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    result = verify_dataset_manifest(pilot_root)
    assert result["valid"] is False
    assert "manifest:case_count_does_not_match_list" in result["mismatches"]
    assert any(item.startswith("manifest:unlisted_case:") for item in result["mismatches"])


def test_covering_array_matrix_a_and_set_b_oracle_holds(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2-covering-v1"
    build_covering_array_dataset(dataset_root)
    summary = summarize_validation_results(dataset_root)
    manifest = verify_dataset_manifest(dataset_root)

    assert summary["total_cases"] == 18
    assert summary["golden_cases"] == 4
    assert summary["typed_mutated_cases"] == 8
    assert summary["typed_mutated_hits"] == 8
    assert summary["ambiguous_cases"] == 6
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["verdict_mismatches"] == 0
    assert manifest == {"valid": True, "case_count": 18, "mismatches": []}

    results_by_id = {result["case_id"]: result for result in summary["results"]}
    for case_id, result in results_by_id.items():
        if case_id.startswith("covering-b-"):
            assert result["actual_verdict"] == "needs_review", case_id


def test_validation_summary_hits_v2_targets(phase2_summary: dict) -> None:
    summary = phase2_summary["controlled"]
    assert summary["total_cases"] == 24
    assert summary["critical_error_recall"] >= 0.85
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_failures"] == 0
    assert "signed" in summary["subset_metrics"]
    assert "zero_baseline" in summary["subset_metrics"]

from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_qa_mcp.claim_graph import build_geometry_claim_graph
from visual_qa_mcp.geometry_dataset import build_geometry_dataset
from visual_qa_mcp.geometry_extractor import extract_geometry_evidence
from visual_qa_mcp.service import run_geometry_verification, write_verification_artifacts
from visual_qa_mcp.validation import (
    discover_geometry_cases,
    load_schema,
    summarize_geometry_validation_results,
    validate_json,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def geometry_cases(tmp_path_factory: pytest.TempPathFactory):
    dataset_root = tmp_path_factory.mktemp("geometry") / "geometry-v1"
    build_geometry_dataset(dataset_root)
    return dataset_root, discover_geometry_cases(dataset_root)


def test_geometry_dataset_has_expected_structure(geometry_cases) -> None:
    dataset_root, cases = geometry_cases
    assert len(cases) == 14
    assert sum(case.kind == "golden" for case in cases) == 5
    assert sum(case.kind == "mutated" for case in cases) == 9
    assert all((case.image_path.parent / "image.png").exists() for case in cases)
    assert dataset_root.is_dir()


def test_geometry_evidence_and_claims_match_schemas(geometry_cases) -> None:
    _, cases = geometry_cases
    case = next(item for item in cases if item.case_id == "golden-02")
    evidence = extract_geometry_evidence(case.image_path)
    claims = build_geometry_claim_graph(case.spec_path)
    assert validate_json(
        load_schema(ROOT / "specs" / "geometry-evidence-graph.schema.json"),
        evidence.to_dict(),
    ) == []
    assert validate_json(
        load_schema(ROOT / "specs" / "claim-graph.schema.json"),
        claims.to_dict(),
    ) == []


def test_geometry_golden_passes_and_typed_defect_fails(geometry_cases) -> None:
    _, cases = geometry_cases
    golden = next(item for item in cases if item.case_id == "golden-01")
    mutated = next(item for item in cases if item.case_id == "mutated-03")
    assert run_geometry_verification(golden.image_path, golden.spec_path).report.verdict == "pass"
    result = run_geometry_verification(mutated.image_path, mutated.spec_path)
    assert result.report.verdict == "fail"
    assert "hole_diameter_ratio_violation" in {item.type for item in result.report.findings}


def test_geometry_ambiguity_never_passes(geometry_cases) -> None:
    _, cases = geometry_cases
    case = next(item for item in cases if item.case_id == "mutated-08")
    result = run_geometry_verification(case.image_path, case.spec_path)
    assert result.report.verdict == "needs_review"
    assert result.report.checks_skipped


def test_geometry_artifact_writer(geometry_cases, tmp_path: Path) -> None:
    _, cases = geometry_cases
    case = next(item for item in cases if item.case_id == "mutated-06")
    result = run_geometry_verification(case.image_path, case.spec_path)
    paths = write_verification_artifacts(result, tmp_path / "artifacts")
    assert paths.overlay_path.exists()
    assert json.loads(paths.report_path.read_text(encoding="utf-8"))["verdict"] == "fail"


def test_geometry_validation_summary(geometry_cases) -> None:
    dataset_root, _ = geometry_cases
    summary = summarize_geometry_validation_results(dataset_root)
    assert summary["total_cases"] == 14
    assert summary["typed_mutated_cases"] == 7
    assert summary["typed_mutated_hits"] == 7
    assert summary["ambiguous_cases"] == 2
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_non_passes"] == 0

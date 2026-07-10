from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from visual_qa_mcp.claim_graph import build_geometry_claim_graph
from visual_qa_mcp.geometry_dataset import build_geometry_dataset, build_noisy_geometry_dataset
from visual_qa_mcp.geometry_extractor import extract_geometry_evidence
from visual_qa_mcp.service import run_geometry_verification, write_verification_artifacts
from visual_qa_mcp.validation import (
    discover_geometry_cases,
    load_schema,
    summarize_geometry_validation_results,
    validate_json,
    verify_dataset_manifest,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def geometry_cases(tmp_path_factory: pytest.TempPathFactory):
    dataset_root = tmp_path_factory.mktemp("geometry") / "geometry-v1"
    build_geometry_dataset(dataset_root)
    return dataset_root, discover_geometry_cases(dataset_root)


@pytest.fixture(scope="module")
def noisy_geometry_cases(tmp_path_factory: pytest.TempPathFactory):
    dataset_root = tmp_path_factory.mktemp("geometry-noisy") / "geometry-v1-noisy"
    build_noisy_geometry_dataset(dataset_root)
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


def test_noisy_geometry_gate_and_transform_denominators(noisy_geometry_cases) -> None:
    dataset_root, cases = noisy_geometry_cases
    summary = summarize_geometry_validation_results(dataset_root)
    assert len(cases) == 20
    assert summary["golden_cases"] == 10
    assert summary["golden_non_passes"] == 0
    assert summary["typed_mutated_cases"] == 5
    assert summary["typed_mutated_hits"] == 5
    assert summary["ambiguous_cases"] == 5
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["verdict_mismatches"] == 0
    assert set(summary["transform_metrics"]) == {
        "blur",
        "downscale",
        "jpeg",
        "low_contrast",
        "label_degradation",
    }
    assert all(metrics["total"] == 4 for metrics in summary["transform_metrics"].values())


def test_noisy_geometry_manifest_is_valid_and_deterministic(
    noisy_geometry_cases, tmp_path: Path
) -> None:
    dataset_root, _ = noisy_geometry_cases
    assert verify_dataset_manifest(dataset_root) == {
        "valid": True,
        "case_count": 20,
        "mismatches": [],
    }
    second_root = tmp_path / "geometry-v1-noisy"
    build_noisy_geometry_dataset(second_root)
    assert (dataset_root / "manifest.json").read_bytes() == (
        second_root / "manifest.json"
    ).read_bytes()


def test_noisy_geometry_manifest_rejects_artifact_drift(
    noisy_geometry_cases, tmp_path: Path
) -> None:
    dataset_root, _ = noisy_geometry_cases
    copied_root = tmp_path / "geometry-v1-noisy"
    shutil.copytree(dataset_root, copied_root)
    image_path = next(copied_root.glob("**/image.png"))
    image_path.write_bytes(image_path.read_bytes() + b"drift")
    result = verify_dataset_manifest(copied_root)
    assert result["valid"] is False
    assert any(item.endswith("image.png:checksum_mismatch") for item in result["mismatches"])


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("unsafe_path", "relative_path:unsafe"),
        ("metadata_mismatch", "metadata:kind_mismatch"),
        ("verdict_mismatch", "expected_verdict_mismatch"),
    ],
)
def test_noisy_geometry_manifest_rejects_unsafe_or_inconsistent_declarations(
    noisy_geometry_cases,
    tmp_path: Path,
    mutation: str,
    expected_error: str,
) -> None:
    dataset_root, _ = noisy_geometry_cases
    copied_root = tmp_path / mutation / "geometry-v1-noisy"
    shutil.copytree(dataset_root, copied_root)
    manifest_path = copied_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "unsafe_path":
        manifest["cases"][0]["relative_path"] = "../escape"
    elif mutation == "metadata_mismatch":
        manifest["cases"][0]["kind"] = "mutated"
    else:
        manifest["cases"][0]["expected_verdict"] = "fail"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    result = verify_dataset_manifest(copied_root)
    assert result["valid"] is False
    assert any(expected_error in item for item in result["mismatches"])

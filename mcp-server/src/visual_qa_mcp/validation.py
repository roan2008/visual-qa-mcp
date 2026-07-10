from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .contracts import (
    ArrowDatasetCase,
    ArrowEvidenceGraph,
    ChartDatasetCase,
    EvidenceGraph,
    GeometryDatasetCase,
    GeometryEvidenceGraph,
    VisualQaReport,
)
from .environment import capture_ocr_environment
from .service import (
    run_arrow_verification,
    run_chart_verification,
    run_geometry_verification,
    write_verification_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(schema_path: Path) -> Draft202012Validator:
    schema = load_json(schema_path)
    return Draft202012Validator(schema)


def validate_json(validator: Draft202012Validator, payload: dict[str, Any]) -> list[str]:
    return [error.message for error in validator.iter_errors(payload)]


def discover_cases(dataset_root: Path) -> list[ChartDatasetCase]:
    cases: list[ChartDatasetCase] = []
    for metadata_path in sorted(dataset_root.glob("**/metadata.json")):
        metadata = load_json(metadata_path)
        case_dir = metadata_path.parent
        cases.append(
            ChartDatasetCase(
                case_id=metadata["case_id"],
                title=metadata["title"],
                kind=metadata["kind"],
                defect_type=metadata.get("defect_type"),
                axis_mode=metadata["axis_mode"],
                backend=metadata.get("backend", "template"),
                image_path=case_dir / "image.png",
                spec_path=case_dir / "visual_spec.json",
                metadata_path=metadata_path,
                expected_report_path=case_dir / "expected_report.json",
                dataset_track=metadata.get("dataset_track", "controlled"),
            )
        )
    return cases


def run_case(
    case: ChartDatasetCase,
    evidence_schema: Draft202012Validator | None = None,
    backend_override: str | None = None,
) -> tuple[EvidenceGraph, VisualQaReport]:
    backend = backend_override or case.backend
    result = run_chart_verification(
        image_path=case.image_path,
        spec_path=case.spec_path,
        metadata_path=case.metadata_path,
        backend=backend,
    )
    claim_schema = load_schema(REPO_ROOT / "specs" / "claim-graph.schema.json")
    claim_errors = validate_json(claim_schema, result.claim_graph.to_dict())
    if claim_errors:
        raise ValueError(f"Claim schema validation failed for {case.case_id}: {claim_errors}")
    if evidence_schema is not None:
        errors = validate_json(evidence_schema, result.evidence_graph.to_dict())
        if errors:
            raise ValueError(f"Evidence schema validation failed for {case.case_id}: {errors}")
    write_verification_artifacts(result, case.image_path.parent)
    return result.evidence_graph, result.report


def summarize_validation_results(dataset_root: Path, backend_override: str | None = None) -> dict[str, Any]:
    return summarize_validation_results_for_cases(discover_cases(dataset_root), backend_override=backend_override)


def summarize_validation_results_for_cases(
    cases: list[ChartDatasetCase],
    backend_override: str | None = None,
) -> dict[str, Any]:
    findings_schema = load_schema(REPO_ROOT / "specs" / "findings.schema.json")
    evidence_schema = load_schema(REPO_ROOT / "specs" / "evidence-graph.schema.json")
    results: list[dict[str, Any]] = []
    typed_mutated = 0
    typed_mutated_hits = 0
    unsupported_passes = 0
    golden_failures = 0
    golden_non_passes = 0
    ambiguous_cases = 0
    ambiguous_guarded = 0
    verdict_mismatches = 0
    mode_stats: dict[str, dict[str, int]] = {}
    evidence_stats = {
        "bar_count_cases": 0,
        "bar_count_hits": 0,
        "tick_sequence_cases": 0,
        "tick_sequence_hits": 0,
        "label_cases": 0,
        "label_hits": 0,
    }

    for case in cases:
        evidence, report = run_case(case, evidence_schema, backend_override=backend_override)
        report_errors = validate_json(findings_schema, report.to_dict())
        if report_errors:
            raise ValueError(f"Report schema validation failed for {case.case_id}: {report_errors}")
        expected = load_json(case.expected_report_path)
        expected_evidence = expected.get("expected_evidence")
        if expected_evidence:
            if expected_evidence.get("bar_count") is not None:
                evidence_stats["bar_count_cases"] += 1
                if len(evidence.bars) == int(expected_evidence["bar_count"]):
                    evidence_stats["bar_count_hits"] += 1
            if expected_evidence.get("tick_values") is not None:
                evidence_stats["tick_sequence_cases"] += 1
                detected_ticks = [
                    float(tick.parsed_value)
                    for tick in evidence.y_axis.tick_labels
                    if tick.parsed_value is not None
                ]
                if detected_ticks == [float(value) for value in expected_evidence["tick_values"]][::-1]:
                    evidence_stats["tick_sequence_hits"] += 1
            if expected_evidence.get("labels") is not None:
                evidence_stats["label_cases"] += 1
                if [bar.category for bar in evidence.bars] == list(expected_evidence["labels"]):
                    evidence_stats["label_hits"] += 1
        matched_types = {finding["type"] for finding in report.to_dict()["findings"]}
        expected_types = set(expected.get("expected_finding_types", []))
        result = {
            "case_id": case.case_id,
            "kind": case.kind,
            "axis_mode": case.axis_mode,
            "backend": backend_override or case.backend,
            "expected_verdict": expected["verdict"],
            "actual_verdict": report.verdict,
            "expected_types": sorted(expected_types),
            "actual_types": sorted(matched_types),
        }
        results.append(result)
        if case.kind == "golden" and report.verdict == "fail":
            golden_failures += 1
        if case.kind == "golden" and report.verdict != "pass":
            golden_non_passes += 1
        if case.kind == "mutated":
            mode_stats.setdefault(case.axis_mode, {"typed_cases": 0, "typed_hits": 0, "guarded_cases": 0, "total_cases": 0})
            mode_stats[case.axis_mode]["total_cases"] += 1
            if report.verdict != "pass":
                mode_stats[case.axis_mode]["guarded_cases"] += 1
            if expected_types:
                typed_mutated += 1
                mode_stats[case.axis_mode]["typed_cases"] += 1
                if expected_types.issubset(matched_types):
                    typed_mutated_hits += 1
                    mode_stats[case.axis_mode]["typed_hits"] += 1
            else:
                ambiguous_cases += 1
                if report.verdict != "pass":
                    ambiguous_guarded += 1
        if expected["verdict"] != "pass" and report.verdict == "pass":
            unsupported_passes += 1
        if expected["verdict"] != report.verdict:
            verdict_mismatches += 1

    guarded_mutated_cases = sum(
        1
        for result in results
        if result["kind"] == "mutated" and result["actual_verdict"] != "pass"
    )

    subset_metrics = {}
    for axis_mode, stats in mode_stats.items():
        subset_metrics[axis_mode] = {
            "typed_cases": stats["typed_cases"],
            "typed_hits": stats["typed_hits"],
            "typed_recall": round(stats["typed_hits"] / max(stats["typed_cases"], 1), 2),
            "guard_rate": round(stats["guarded_cases"] / max(stats["total_cases"], 1), 2),
        }

    evidence_metrics = {
        **evidence_stats,
        "bar_count_accuracy": round(
            evidence_stats["bar_count_hits"] / max(evidence_stats["bar_count_cases"], 1), 2
        ),
        "tick_sequence_accuracy": round(
            evidence_stats["tick_sequence_hits"] / max(evidence_stats["tick_sequence_cases"], 1), 2
        ),
        "label_accuracy": round(
            evidence_stats["label_hits"] / max(evidence_stats["label_cases"], 1), 2
        ),
    }
    return {
        "total_cases": len(cases),
        "golden_cases": sum(1 for case in cases if case.kind == "golden"),
        "mutated_cases": sum(1 for case in cases if case.kind == "mutated"),
        "critical_error_recall": round(typed_mutated_hits / max(typed_mutated, 1), 2),
        "typed_mutated_cases": typed_mutated,
        "typed_mutated_hits": typed_mutated_hits,
        "ambiguous_cases": ambiguous_cases,
        "ambiguous_guard_rate": round(ambiguous_guarded / max(ambiguous_cases, 1), 2),
        "mutated_case_guard_rate": round(guarded_mutated_cases / max(sum(1 for case in cases if case.kind == "mutated"), 1), 2),
        "false_unsupported_passes": unsupported_passes,
        "golden_failures": golden_failures,
        "golden_non_passes": golden_non_passes,
        "verdict_mismatches": verdict_mismatches,
        "verdict_accuracy": round((len(cases) - verdict_mismatches) / max(len(cases), 1), 2),
        "subset_metrics": subset_metrics,
        "evidence_metrics": evidence_metrics,
        "results": results,
    }


def discover_arrow_cases(dataset_root: Path) -> list[ArrowDatasetCase]:
    cases: list[ArrowDatasetCase] = []
    for metadata_path in sorted(dataset_root.glob("**/metadata.json")):
        metadata = load_json(metadata_path)
        case_dir = metadata_path.parent
        cases.append(
            ArrowDatasetCase(
                case_id=metadata["case_id"],
                title=metadata["title"],
                kind=metadata["kind"],
                defect_type=metadata.get("defect_type"),
                scenario=metadata.get("scenario", "free_body"),
                image_path=case_dir / "image.png",
                spec_path=case_dir / "visual_spec.json",
                metadata_path=metadata_path,
                expected_report_path=case_dir / "expected_report.json",
                dataset_track=metadata.get("dataset_track", "controlled"),
            )
        )
    return cases


def run_arrow_case(
    case: ArrowDatasetCase,
    evidence_schema: Draft202012Validator | None = None,
) -> tuple[ArrowEvidenceGraph, VisualQaReport]:
    result = run_arrow_verification(
        image_path=case.image_path,
        spec_path=case.spec_path,
        metadata_path=case.metadata_path,
    )
    claim_schema = load_schema(REPO_ROOT / "specs" / "claim-graph.schema.json")
    claim_errors = validate_json(claim_schema, result.claim_graph.to_dict())
    if claim_errors:
        raise ValueError(f"Claim schema validation failed for {case.case_id}: {claim_errors}")
    if evidence_schema is not None:
        errors = validate_json(evidence_schema, result.evidence_graph.to_dict())
        if errors:
            raise ValueError(f"Evidence schema validation failed for {case.case_id}: {errors}")
    write_verification_artifacts(result, case.image_path.parent)
    return result.evidence_graph, result.report


def summarize_arrow_validation_results(dataset_root: Path) -> dict[str, Any]:
    findings_schema = load_schema(REPO_ROOT / "specs" / "findings.schema.json")
    evidence_schema = load_schema(REPO_ROOT / "specs" / "arrow-evidence-graph.schema.json")
    cases = discover_arrow_cases(dataset_root)
    results: list[dict[str, Any]] = []
    typed_mutated = 0
    typed_mutated_hits = 0
    unsupported_passes = 0
    golden_failures = 0
    golden_non_passes = 0
    ambiguous_cases = 0
    ambiguous_guarded = 0
    verdict_mismatches = 0
    arrow_count_cases = 0
    arrow_count_hits = 0
    force_balance_cases = 0
    force_balance_hits = 0

    for case in cases:
        evidence, report = run_arrow_case(case, evidence_schema)
        report_errors = validate_json(findings_schema, report.to_dict())
        if report_errors:
            raise ValueError(f"Report schema validation failed for {case.case_id}: {report_errors}")
        expected = load_json(case.expected_report_path)
        expected_evidence = expected.get("expected_evidence", {})
        if expected_evidence.get("arrow_count") is not None:
            arrow_count_cases += 1
            if len(evidence.arrows) == int(expected_evidence["arrow_count"]):
                arrow_count_hits += 1
        matched_types = {finding["type"] for finding in report.to_dict()["findings"]}
        expected_types = set(expected.get("expected_finding_types", []))
        results.append(
            {
                "case_id": case.case_id,
                "kind": case.kind,
                "defect_type": case.defect_type,
                "expected_verdict": expected["verdict"],
                "actual_verdict": report.verdict,
                "expected_types": sorted(expected_types),
                "actual_types": sorted(matched_types),
            }
        )
        if case.kind == "golden" and report.verdict == "fail":
            golden_failures += 1
        if case.kind == "golden" and report.verdict != "pass":
            golden_non_passes += 1
        if case.kind == "mutated":
            if expected_types:
                typed_mutated += 1
                if expected_types.issubset(matched_types):
                    typed_mutated_hits += 1
            else:
                ambiguous_cases += 1
                if report.verdict != "pass":
                    ambiguous_guarded += 1
        if "force_balance_violation" in expected_types:
            force_balance_cases += 1
            if "force_balance_violation" in matched_types:
                force_balance_hits += 1
        if expected["verdict"] != "pass" and report.verdict == "pass":
            unsupported_passes += 1
        if expected["verdict"] != report.verdict:
            verdict_mismatches += 1

    return {
        "total_cases": len(cases),
        "golden_cases": sum(1 for case in cases if case.kind == "golden"),
        "mutated_cases": sum(1 for case in cases if case.kind == "mutated"),
        "critical_error_recall": round(typed_mutated_hits / max(typed_mutated, 1), 2),
        "typed_mutated_cases": typed_mutated,
        "typed_mutated_hits": typed_mutated_hits,
        "ambiguous_cases": ambiguous_cases,
        "ambiguous_guard_rate": round(ambiguous_guarded / max(ambiguous_cases, 1), 2),
        "false_unsupported_passes": unsupported_passes,
        "golden_failures": golden_failures,
        "golden_non_passes": golden_non_passes,
        "verdict_mismatches": verdict_mismatches,
        "verdict_accuracy": round((len(cases) - verdict_mismatches) / max(len(cases), 1), 2),
        "evidence_metrics": {
            "arrow_count_cases": arrow_count_cases,
            "arrow_count_hits": arrow_count_hits,
            "arrow_count_accuracy": round(arrow_count_hits / max(arrow_count_cases, 1), 2),
        },
        "force_balance_metrics": {
            "typed_cases": force_balance_cases,
            "typed_hits": force_balance_hits,
            "typed_hit_rate": round(force_balance_hits / max(force_balance_cases, 1), 2),
        },
        "results": results,
    }


def discover_geometry_cases(dataset_root: Path) -> list[GeometryDatasetCase]:
    cases: list[GeometryDatasetCase] = []
    for metadata_path in sorted(dataset_root.glob("**/metadata.json")):
        metadata = load_json(metadata_path)
        case_dir = metadata_path.parent
        cases.append(
            GeometryDatasetCase(
                case_id=metadata["case_id"],
                title=metadata["title"],
                kind=metadata["kind"],
                defect_type=metadata.get("defect_type"),
                scenario=metadata.get("scenario", "mechanical_plate"),
                image_path=case_dir / "image.png",
                spec_path=case_dir / "visual_spec.json",
                metadata_path=metadata_path,
                expected_report_path=case_dir / "expected_report.json",
                dataset_track=metadata.get("dataset_track", "controlled"),
            )
        )
    return cases


def run_geometry_case(
    case: GeometryDatasetCase,
    evidence_schema: Draft202012Validator | None = None,
) -> tuple[GeometryEvidenceGraph, VisualQaReport]:
    result = run_geometry_verification(
        image_path=case.image_path,
        spec_path=case.spec_path,
        metadata_path=case.metadata_path,
    )
    claim_schema = load_schema(REPO_ROOT / "specs" / "claim-graph.schema.json")
    claim_errors = validate_json(claim_schema, result.claim_graph.to_dict())
    if claim_errors:
        raise ValueError(f"Claim schema validation failed for {case.case_id}: {claim_errors}")
    if evidence_schema is not None:
        errors = validate_json(evidence_schema, result.evidence_graph.to_dict())
        if errors:
            raise ValueError(f"Evidence schema validation failed for {case.case_id}: {errors}")
    write_verification_artifacts(result, case.image_path.parent)
    return result.evidence_graph, result.report


def summarize_geometry_validation_results(dataset_root: Path) -> dict[str, Any]:
    findings_schema = load_schema(REPO_ROOT / "specs" / "findings.schema.json")
    evidence_schema = load_schema(REPO_ROOT / "specs" / "geometry-evidence-graph.schema.json")
    cases = discover_geometry_cases(dataset_root)
    results: list[dict[str, Any]] = []
    typed_mutated = 0
    typed_mutated_hits = 0
    ambiguous_cases = 0
    ambiguous_guarded = 0
    unsupported_passes = 0
    golden_failures = 0
    golden_non_passes = 0
    verdict_mismatches = 0
    hole_count_cases = 0
    hole_count_hits = 0

    for case in cases:
        evidence, report = run_geometry_case(case, evidence_schema)
        report_errors = validate_json(findings_schema, report.to_dict())
        if report_errors:
            raise ValueError(f"Report schema validation failed for {case.case_id}: {report_errors}")
        expected = load_json(case.expected_report_path)
        expected_types = set(expected.get("expected_finding_types", []))
        matched_types = {finding.type for finding in report.findings}
        expected_count = expected.get("expected_evidence", {}).get("hole_count")
        if expected_count is not None:
            hole_count_cases += 1
            if len(evidence.holes) == int(expected_count):
                hole_count_hits += 1
        results.append(
            {
                "case_id": case.case_id,
                "kind": case.kind,
                "defect_type": case.defect_type,
                "expected_verdict": expected["verdict"],
                "actual_verdict": report.verdict,
                "expected_types": sorted(expected_types),
                "actual_types": sorted(matched_types),
            }
        )
        if case.kind == "golden" and report.verdict == "fail":
            golden_failures += 1
        if case.kind == "golden" and report.verdict != "pass":
            golden_non_passes += 1
        if case.kind == "mutated":
            if expected_types:
                typed_mutated += 1
                if expected_types.issubset(matched_types):
                    typed_mutated_hits += 1
            else:
                ambiguous_cases += 1
                if report.verdict != "pass":
                    ambiguous_guarded += 1
        if expected["verdict"] != "pass" and report.verdict == "pass":
            unsupported_passes += 1
        if expected["verdict"] != report.verdict:
            verdict_mismatches += 1

    return {
        "total_cases": len(cases),
        "golden_cases": sum(1 for case in cases if case.kind == "golden"),
        "mutated_cases": sum(1 for case in cases if case.kind == "mutated"),
        "critical_error_recall": round(typed_mutated_hits / max(typed_mutated, 1), 2),
        "typed_mutated_cases": typed_mutated,
        "typed_mutated_hits": typed_mutated_hits,
        "ambiguous_cases": ambiguous_cases,
        "ambiguous_guard_rate": round(ambiguous_guarded / max(ambiguous_cases, 1), 2),
        "false_unsupported_passes": unsupported_passes,
        "golden_failures": golden_failures,
        "golden_non_passes": golden_non_passes,
        "verdict_mismatches": verdict_mismatches,
        "verdict_accuracy": round((len(cases) - verdict_mismatches) / max(len(cases), 1), 2),
        "evidence_metrics": {
            "hole_count_cases": hole_count_cases,
            "hole_count_hits": hole_count_hits,
            "hole_count_accuracy": round(hole_count_hits / max(hole_count_cases, 1), 2),
        },
        "results": results,
    }


def summarize_phase2_validation(
    controlled_root: Path,
    noisy_root: Path,
    backend_override: str | None = None,
) -> dict[str, Any]:
    controlled_cases = discover_cases(controlled_root)
    noisy_cases = discover_cases(noisy_root)
    return {
        "controlled": summarize_validation_results_for_cases(controlled_cases, backend_override=backend_override),
        "noisy": summarize_validation_results_for_cases(noisy_cases, backend_override=backend_override),
    }


def summarize_ocr_validation(
    controlled_root: Path,
    noisy_root: Path,
) -> dict[str, Any]:
    environment = capture_ocr_environment()
    return {
        "environment": environment,
        "controlled": summarize_validation_results(controlled_root, backend_override="optional_ocr"),
        "noisy": summarize_validation_results(noisy_root, backend_override="optional_ocr"),
    }


def verify_dataset_manifest(dataset_root: Path) -> dict[str, Any]:
    manifest_path = dataset_root / "manifest.json"
    if not manifest_path.exists():
        return {"valid": False, "case_count": 0, "mismatches": ["manifest.json is missing"]}
    manifest = load_json(manifest_path)
    mismatches: list[str] = []
    manifest_cases = manifest.get("cases", [])
    declared_count = int(manifest.get("case_count", 0))
    if declared_count != len(manifest_cases):
        mismatches.append("manifest:case_count_does_not_match_list")
    if manifest.get("dataset") == "chart-v2-realworld-pilot" and declared_count != 24:
        mismatches.append("manifest:pilot_case_count_must_be_24")

    case_ids = [str(case.get("case_id")) for case in manifest_cases]
    relative_paths = [str(case.get("relative_path")) for case in manifest_cases]
    if len(case_ids) != len(set(case_ids)):
        mismatches.append("manifest:duplicate_case_id")
    if len(relative_paths) != len(set(relative_paths)):
        mismatches.append("manifest:duplicate_relative_path")

    discovered_paths = {
        str(path.parent.relative_to(dataset_root)).replace("\\", "/")
        for path in dataset_root.glob("**/metadata.json")
    }
    listed_paths = set(relative_paths)
    for missing in sorted(discovered_paths - listed_paths):
        mismatches.append(f"manifest:unlisted_case:{missing}")
    for extra in sorted(listed_paths - discovered_paths):
        mismatches.append(f"manifest:missing_case_directory:{extra}")

    required_checksums = {"image.png", "visual_spec.json", "expected_report.json", "metadata.json"}
    for case in manifest_cases:
        case_root = dataset_root / case["relative_path"]
        checksums = case.get("checksums", {})
        missing_checksum_keys = required_checksums - set(checksums)
        for name in sorted(missing_checksum_keys):
            mismatches.append(f"{case['case_id']}:{name}:checksum_missing")
        provenance = case.get("provenance", {})
        for field in ("source_type", "license", "retrieved_at"):
            if not provenance.get(field):
                mismatches.append(f"{case['case_id']}:provenance:{field}_missing")
        metadata_path = case_root / "metadata.json"
        if metadata_path.exists():
            metadata = load_json(metadata_path)
            for field in ("renderer", "transform_family"):
                if not metadata.get(field):
                    mismatches.append(f"{case['case_id']}:metadata:{field}_missing")
        for name, expected_sha in checksums.items():
            path = case_root / name
            if not path.exists():
                mismatches.append(f"{case['case_id']}:{name}:missing")
                continue
            actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_sha != expected_sha:
                mismatches.append(f"{case['case_id']}:{name}:checksum_mismatch")
    return {
        "valid": not mismatches,
        "case_count": declared_count,
        "mismatches": mismatches,
    }


def summarize_chart_validation_suite(
    controlled_root: Path,
    noisy_root: Path,
    pilot_root: Path,
) -> dict[str, Any]:
    return {
        "controlled": summarize_validation_results(controlled_root),
        "noisy": summarize_validation_results(noisy_root),
        "realworld_pilot": summarize_validation_results(pilot_root),
        "pilot_manifest": verify_dataset_manifest(pilot_root),
    }

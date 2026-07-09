from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .chart_extractor import extract_chart_evidence
from .chart_rules import run_chart_rules
from .contracts import ChartDatasetCase, EvidenceGraph, VisualQaReport
from .overlay import make_overlay

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
            )
        )
    return cases


def run_case(
    case: ChartDatasetCase,
    evidence_schema: Draft202012Validator | None = None,
    backend_override: str | None = None,
) -> tuple[EvidenceGraph, VisualQaReport]:
    backend = backend_override or case.backend
    evidence = extract_chart_evidence(case.image_path, case.spec_path, case.metadata_path, backend=backend)
    if evidence_schema is not None:
        errors = validate_json(evidence_schema, evidence.to_dict())
        if errors:
            raise ValueError(f"Evidence schema validation failed for {case.case_id}: {errors}")
    report = run_chart_rules(case.spec_path, evidence)
    overlay_path = case.image_path.parent / "overlay.png"
    make_overlay(case.image_path, report, overlay_path)
    report.evidence_graph_path = str(case.image_path.parent / "evidence_graph.json")
    Path(report.evidence_graph_path).write_text(
        json.dumps(evidence.to_dict(), indent=2),
        encoding="utf-8",
    )
    (case.image_path.parent / "report.json").write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )
    return evidence, report


def summarize_validation_results(dataset_root: Path, backend_override: str | None = None) -> dict[str, Any]:
    findings_schema = load_schema(REPO_ROOT / "specs" / "findings.schema.json")
    evidence_schema = load_schema(REPO_ROOT / "specs" / "evidence-graph.schema.json")
    results: list[dict[str, Any]] = []
    cases = discover_cases(dataset_root)
    typed_mutated = 0
    typed_mutated_hits = 0
    unsupported_passes = 0
    golden_failures = 0
    ambiguous_cases = 0
    ambiguous_guarded = 0
    mode_stats: dict[str, dict[str, int]] = {}

    for case in cases:
        evidence, report = run_case(case, evidence_schema, backend_override=backend_override)
        report_errors = validate_json(findings_schema, report.to_dict())
        if report_errors:
            raise ValueError(f"Report schema validation failed for {case.case_id}: {report_errors}")
        expected = load_json(case.expected_report_path)
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
        "subset_metrics": subset_metrics,
        "results": results,
    }

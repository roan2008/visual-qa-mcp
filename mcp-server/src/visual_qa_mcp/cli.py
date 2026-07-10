from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .arrow_dataset import build_arrow_dataset, build_noisy_arrow_dataset
from .generate_dataset import build_dataset, build_noisy_dataset, build_realworld_pilot_dataset
from .geometry_dataset import build_geometry_dataset, build_noisy_geometry_dataset
from .server import main as server_main
from .service import (
    build_claim_graph_from_spec,
    extract_chart_evidence_from_inputs,
    extract_primitive_evidence_from_inputs,
    run_arrow_verification,
    run_chart_rules_from_graphs,
    run_chart_verification,
    run_geometry_verification,
    write_verification_artifacts,
)
from .validation import (
    discover_cases,
    load_schema,
    run_case,
    summarize_arrow_validation_results,
    summarize_ocr_validation,
    summarize_chart_validation_suite,
    summarize_geometry_validation_results,
    summarize_geometry_validation_suite,
    summarize_phase2_validation,
    summarize_validation_results,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-first Visual QA MCP verifier CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate-dataset")
    generate_parser.add_argument("--output", type=Path, default=Path("datasets") / "charts" / "chart-v2")

    noisy_generate_parser = subparsers.add_parser("generate-noisy-dataset")
    noisy_generate_parser.add_argument("--output", type=Path, default=Path("datasets") / "charts" / "chart-v2-noisy")

    pilot_generate_parser = subparsers.add_parser("generate-realworld-pilot")
    pilot_generate_parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets") / "charts" / "chart-v2-realworld-pilot",
    )

    claim_parser = subparsers.add_parser("build-claim-graph")
    claim_parser.add_argument("spec_path", type=Path)

    extract_parser = subparsers.add_parser("extract-chart-evidence")
    extract_parser.add_argument("image_path", type=Path)
    extract_parser.add_argument("spec_path", type=Path)
    extract_parser.add_argument("--metadata", type=Path, default=None)
    extract_parser.add_argument("--backend", choices=["template", "optional_ocr"], default=None)

    rules_parser = subparsers.add_parser("run-rules")
    rules_parser.add_argument("--claim-graph", type=Path, default=None)
    rules_parser.add_argument("--evidence-graph", type=Path, default=None)

    verify_parser = subparsers.add_parser("verify-chart")
    verify_parser.add_argument("image_path", type=Path)
    verify_parser.add_argument("spec_path", type=Path)
    verify_parser.add_argument("--metadata", type=Path, default=None)
    verify_parser.add_argument("--backend", choices=["template", "optional_ocr"], default=None)
    verify_parser.add_argument("--output-dir", type=Path, default=None)

    run_case_parser = subparsers.add_parser("run-case")
    run_case_parser.add_argument("case_dir", type=Path)
    run_case_parser.add_argument("--backend", choices=["template", "optional_ocr"], default=None)

    validate_parser = subparsers.add_parser("run-validation")
    validate_parser.add_argument("--dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2")
    validate_parser.add_argument("--backend", choices=["template", "optional_ocr"], default=None)

    phase2_validate_parser = subparsers.add_parser("run-phase2-validation")
    phase2_validate_parser.add_argument("--controlled-dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2")
    phase2_validate_parser.add_argument("--noisy-dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2-noisy")
    phase2_validate_parser.add_argument("--backend", choices=["template", "optional_ocr"], default=None)

    ocr_validate_parser = subparsers.add_parser("run-ocr-validation")
    ocr_validate_parser.add_argument("--controlled-dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2")
    ocr_validate_parser.add_argument("--noisy-dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2-noisy")

    suite_validate_parser = subparsers.add_parser("run-chart-suite-validation")
    suite_validate_parser.add_argument("--controlled-dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2")
    suite_validate_parser.add_argument("--noisy-dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2-noisy")
    suite_validate_parser.add_argument(
        "--pilot-dataset",
        type=Path,
        default=Path("datasets") / "charts" / "chart-v2-realworld-pilot",
    )

    arrow_generate_parser = subparsers.add_parser("generate-arrow-dataset")
    arrow_generate_parser.add_argument("--output", type=Path, default=Path("datasets") / "physics" / "arrow-v1")

    arrow_noisy_generate_parser = subparsers.add_parser("generate-noisy-arrow-dataset")
    arrow_noisy_generate_parser.add_argument("--output", type=Path, default=Path("datasets") / "physics" / "arrow-v1-noisy")

    arrow_verify_parser = subparsers.add_parser("verify-arrow")
    arrow_verify_parser.add_argument("image_path", type=Path)
    arrow_verify_parser.add_argument("spec_path", type=Path)
    arrow_verify_parser.add_argument("--output-dir", type=Path, default=None)

    arrow_validate_parser = subparsers.add_parser("run-arrow-validation")
    arrow_validate_parser.add_argument("--dataset", type=Path, default=Path("datasets") / "physics" / "arrow-v1")

    geometry_generate_parser = subparsers.add_parser("generate-geometry-dataset")
    geometry_generate_parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets") / "mechanical" / "geometry-v1",
    )

    geometry_noisy_generate_parser = subparsers.add_parser("generate-noisy-geometry-dataset")
    geometry_noisy_generate_parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets") / "mechanical" / "geometry-v1-noisy",
    )

    geometry_verify_parser = subparsers.add_parser("verify-geometry")
    geometry_verify_parser.add_argument("image_path", type=Path)
    geometry_verify_parser.add_argument("spec_path", type=Path)
    geometry_verify_parser.add_argument("--output-dir", type=Path, default=None)

    primitive_parser = subparsers.add_parser("extract-primitives")
    primitive_parser.add_argument("image_path", type=Path)
    primitive_parser.add_argument(
        "--profile",
        required=True,
        choices=["chart-v2", "arrow-v1", "geometry-v1"],
    )

    geometry_validate_parser = subparsers.add_parser("run-geometry-validation")
    geometry_validate_parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets") / "mechanical" / "geometry-v1",
    )

    geometry_suite_parser = subparsers.add_parser("run-geometry-suite-validation")
    geometry_suite_parser.add_argument(
        "--controlled-dataset",
        type=Path,
        default=Path("datasets") / "mechanical" / "geometry-v1",
    )
    geometry_suite_parser.add_argument(
        "--noisy-dataset",
        type=Path,
        default=Path("datasets") / "mechanical" / "geometry-v1-noisy",
    )

    serve_parser = subparsers.add_parser("serve-mcp")

    args = parser.parse_args(argv)

    if args.command == "generate-dataset":
        build_dataset(args.output)
        print(f"Dataset generated at {args.output}")
        return 0

    if args.command == "generate-noisy-dataset":
        build_noisy_dataset(args.output)
        print(f"Noisy dataset generated at {args.output}")
        return 0

    if args.command == "generate-realworld-pilot":
        build_realworld_pilot_dataset(args.output)
        print(f"Real-world pilot dataset generated at {args.output}")
        return 0

    if args.command == "build-claim-graph":
        claim_graph = build_claim_graph_from_spec(args.spec_path)
        print(json.dumps(claim_graph.to_dict(), indent=2))
        return 0

    if args.command == "extract-chart-evidence":
        evidence = extract_chart_evidence_from_inputs(
            image_path=args.image_path,
            spec_path=args.spec_path,
            metadata_path=args.metadata,
            backend=args.backend,
        )
        print(json.dumps(evidence.to_dict(), indent=2))
        return 0

    if args.command == "run-rules":
        if args.claim_graph is None or args.evidence_graph is None:
            raise SystemExit("run-rules requires --claim-graph and --evidence-graph.")
        report = run_chart_rules_from_graphs(args.claim_graph, args.evidence_graph)
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    if args.command == "verify-chart":
        result = run_chart_verification(
            image_path=args.image_path,
            spec_path=args.spec_path,
            metadata_path=args.metadata,
            backend=args.backend,
        )
        payload = result.to_dict()
        if args.output_dir is not None:
            artifact_paths = write_verification_artifacts(result, args.output_dir)
            payload["artifact_paths"] = artifact_paths.to_dict()
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "run-case":
        case_dir: Path = args.case_dir
        evidence_schema = load_schema(Path("specs") / "evidence-graph.schema.json")
        if not case_dir.is_dir():
            raise SystemExit("run-case expects a case directory path.")
        dataset_root = case_dir.parent.parent
        matching = [item for item in discover_cases(dataset_root) if item.image_path.parent == case_dir]
        if not matching:
            raise SystemExit(f"Could not find case at {case_dir}")
        case = matching[0]
        _, report = run_case(case, evidence_schema, backend_override=args.backend)
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    if args.command == "run-validation":
        summary = summarize_validation_results(args.dataset, backend_override=args.backend)
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "run-phase2-validation":
        summary = summarize_phase2_validation(
            controlled_root=args.controlled_dataset,
            noisy_root=args.noisy_dataset,
            backend_override=args.backend,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "run-ocr-validation":
        summary = summarize_ocr_validation(
            controlled_root=args.controlled_dataset,
            noisy_root=args.noisy_dataset,
        )
        print(json.dumps(summary, indent=2))
        return 0


    if args.command == "run-chart-suite-validation":
        summary = summarize_chart_validation_suite(
            controlled_root=args.controlled_dataset,
            noisy_root=args.noisy_dataset,
            pilot_root=args.pilot_dataset,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "generate-arrow-dataset":
        build_arrow_dataset(args.output)
        print(f"Arrow dataset generated at {args.output}")
        return 0

    if args.command == "generate-noisy-arrow-dataset":
        build_noisy_arrow_dataset(args.output)
        print(f"Noisy arrow dataset generated at {args.output}")
        return 0

    if args.command == "verify-arrow":
        result = run_arrow_verification(
            image_path=args.image_path,
            spec_path=args.spec_path,
        )
        payload = result.to_dict()
        if args.output_dir is not None:
            artifact_paths = write_verification_artifacts(result, args.output_dir)
            payload["artifact_paths"] = artifact_paths.to_dict()
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "run-arrow-validation":
        summary = summarize_arrow_validation_results(args.dataset)
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "generate-geometry-dataset":
        build_geometry_dataset(args.output)
        print(f"Geometry dataset generated at {args.output}")
        return 0

    if args.command == "generate-noisy-geometry-dataset":
        build_noisy_geometry_dataset(args.output)
        print(f"Noisy geometry dataset generated at {args.output}")
        return 0

    if args.command == "verify-geometry":
        result = run_geometry_verification(
            image_path=args.image_path,
            spec_path=args.spec_path,
        )
        payload = result.to_dict()
        if args.output_dir is not None:
            artifact_paths = write_verification_artifacts(result, args.output_dir)
            payload["artifact_paths"] = artifact_paths.to_dict()
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "extract-primitives":
        graph = extract_primitive_evidence_from_inputs(args.image_path, args.profile)
        print(json.dumps(graph.to_dict(), indent=2))
        return 0

    if args.command == "run-geometry-validation":
        summary = summarize_geometry_validation_results(args.dataset)
        print(json.dumps(summary, indent=2))
        return 0


    if args.command == "run-geometry-suite-validation":
        summary = summarize_geometry_validation_suite(
            controlled_root=args.controlled_dataset,
            noisy_root=args.noisy_dataset,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "serve-mcp":
        server_main()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

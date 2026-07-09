from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .generate_dataset import build_dataset
from .validation import discover_cases, load_schema, run_case, summarize_validation_results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Visual QA MCP chart verifier CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate-dataset")
    generate_parser.add_argument("--output", type=Path, default=Path("datasets") / "charts" / "chart-v2")

    run_case_parser = subparsers.add_parser("run-case")
    run_case_parser.add_argument("case_dir", type=Path)
    run_case_parser.add_argument("--backend", choices=["template", "optional_ocr"], default=None)

    validate_parser = subparsers.add_parser("run-validation")
    validate_parser.add_argument("--dataset", type=Path, default=Path("datasets") / "charts" / "chart-v2")
    validate_parser.add_argument("--backend", choices=["template", "optional_ocr"], default=None)

    args = parser.parse_args(argv)

    if args.command == "generate-dataset":
        build_dataset(args.output)
        print(f"Dataset generated at {args.output}")
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

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_gate1_evidence() -> dict[str, Any]:
    return {
        "gate": "gate-1-scale-contract-review",
        "scope": "chart-only bar chart verifier v2",
        "checks": [
            "chart_value_consistency",
            "bar_count_matches",
            "axis_label_present",
            "axis_unit_present",
            "axis_scale_readable",
            "axis_scale_monotonic",
            "axis_zero_line_resolved_for_signed",
        ],
        "contract_changes": [
            "Tick label detections are first-class evidence.",
            "Axis mapping is explicit in EvidenceGraph.",
            "Bars derive values from axis mapping rather than metadata max_value.",
        ],
        "release_rule": "missing or contradictory scale evidence must not produce pass",
        "non_goals": ["physics", "mechanical", "medical", "broad real-world chart QA claim"],
    }


def build_gate2_evidence() -> dict[str, Any]:
    return {
        "gate": "gate-2-implementation-review",
        "interfaces": [
            "VisualSpec",
            "EvidenceGraph",
            "VisualQaReport",
            "tick_reader backend interface",
        ],
        "decisions": [
            "Use a dual tick-reader path: template by default, optional OCR when configured.",
            "Use image-derived tick values for bar value mapping in chart-v2 mode.",
            "Use layout-aware but evidence-first extraction for synthetic and semi-realistic fixtures.",
            "Treat unreadable, contradictory, or unresolved scale evidence as checks_skipped leading to needs_review.",
        ],
    }


def build_gate3_evidence(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate": "gate-3-readiness-review",
        "metrics": {
            "critical_error_recall": summary["critical_error_recall"],
            "typed_mutated_cases": summary.get("typed_mutated_cases"),
            "typed_mutated_hits": summary.get("typed_mutated_hits"),
            "ambiguous_guard_rate": summary.get("ambiguous_guard_rate"),
            "mutated_case_guard_rate": summary.get("mutated_case_guard_rate"),
            "false_unsupported_passes": summary["false_unsupported_passes"],
            "golden_failures": summary["golden_failures"],
            "total_cases": summary["total_cases"],
            "subset_metrics": summary.get("subset_metrics", {}),
        },
        "unknowns": [
            "Template backend is still tuned to the synthetic-to-semi-realistic dataset family.",
            "Optional OCR backend is scaffolded but not validated in this environment.",
            "Readiness claims remain limited to the configured backend used in validation.",
        ],
    }


def write_evidence_pack(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

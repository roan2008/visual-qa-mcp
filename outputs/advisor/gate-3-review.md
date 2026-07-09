# Advisor Gate 3 Review

Recommendation: Approve chart-v2 as a bounded, template-backed controlled-to-semi-realistic bar-chart verifier. [Confidence: Medium; Action: recoverable]

Why:

- The chart-v2 evidence contract is sufficient to reconstruct linear bar-chart values in the current bounded scope.
- Missing, contradictory, or unreadable scale evidence is guarded through `checks_skipped` and `needs_review` rather than being silently passed.
- Validation is strong on the configured local dataset family, but the readiness claim must stay bounded to the template-backed path.

Basis:

Facts:

- The local chart-v2 dataset contains 24 cases: 8 golden and 16 mutated.
- Current validation summary:
  - `critical_error_recall = 1.0`
  - `typed_mutated_cases = 9`
  - `typed_mutated_hits = 9`
  - `ambiguous_guard_rate = 1.0`
  - `mutated_case_guard_rate = 1.0`
  - `false_unsupported_passes = 0`
  - `golden_failures = 0`
- Subset metrics are reported separately for `zero_baseline`, `non_zero_min`, and `signed`.
- Local verification passed with `18` tests.

Assumptions:

- "Controlled-to-semi-realistic" means generated/local chart families with bounded layouts, colors, fonts, units, and tick ranges.
- The validated default backend is the template backend, not optional OCR.

Unknowns:

- OCR accuracy is not validated in this environment.
- Real-world chart variability is not yet proven.
- The implementation is still tuned to the current dataset family, including color and category assumptions.

Advisor Pass:

- `Agreed`: chart-v2 is ready as a controlled verifier for the configured template backend and local dataset family.
- `Agreed`: the dual backend boundary is honest when optional OCR is described as scaffolded and unvalidated.
- `Nuanced`: the scale-evidence contract is strong for bounded linear bar charts, but not yet for broader chart types or arbitrary visual styles.
- `Nuanced`: readiness claims are proportionate only when the denominators are stated explicitly: typed recall is over 9 typed mutated cases, while ambiguity handling is measured separately over 7 ambiguity-oriented cases.
- `Unverified`: general real-world chart QA claims, OCR-backed readiness, or robustness beyond the current synthetic-to-semi-realistic dataset family.

Validation:

- Reviewed chart-v2 workflow, evidence packs, validation summary, schema, extractor, tick-reader, rule layer, and end-to-end tests.
- Reconciled the advisor caution by keeping the milestone language bounded to the validated template-backed dataset family.
- No blocking issue remains for calling this chart-v2 milestone a controlled local verifier.

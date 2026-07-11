---
name: impl-circuit-v1
description: Circuit-v1 controlled structural verifier feasibility and implementation record
metadata:
  type: implementation
  status: complete
  last_updated: 2026-07-11
---

# Circuit v1: Controlled Structural Schematic Verifier

## Completion status (2026-07-11)

Both separately gated milestones are complete within the frozen controlled scope.

### circuit-v1a

- 11 cases: 2 golden and 9 mutated.
- Typed defects 4/4: extra component, wrong symbol type, complete swapped terminal netlist, and
  complete non-series topology.
- Ambiguity guards 5/5: broken wire, near-terminal miss, no wires, extra fragment, and unrecognized
  geometry all return `needs_review`.
- Component counts 10/10, net counts 8/8, semantic terminal netlists 6/6.
- Zero unsupported passes, golden non-passes, and verdict mismatches.
- CLI and all three MCP circuit handlers execute end to end; all 11 cases retain audit artifacts.

GPT-5.6 Sol medium independently re-ran validation and the full suite and returned GO for the
bounded v1a completion claim. Its documentation-closeout condition was completed in this session.

### circuit-v1b

V1b extends the same undirected component-terminal-to-net graph. `CircuitEvidenceGraph` records
explicit junction-dot evidence, and nets may attach more than two terminals. Junction dots are
evidence that wire segments merge into one electrical net, not ordinary components. Topology is
derived from the canonical extracted graph.

- 14 cases: 4 golden and 10 mutated.
- Two distinct component/routing layouts for simple-parallel and two for the bounded
  series-parallel family.
- Typed defects 7/7: missing junction, extra junction, complete merged/shorted nets, wrong declared
  topology, a wired extra branch, complete missing/split branch, and swapped branch attachments.
- Ambiguity guards 3/3: disconnected/dangling branch, false near-junction, and unrecognized symbol.
- Component counts 13/13, semantic terminal netlists 11/11, junction counts 11/11.
- Simple-parallel: golden 2/2 and typed 4/4. Bounded series-parallel: golden 2/2 and typed 3/3.
- Zero unsupported passes, golden non-passes, and verdict mismatches; all 14 cases retain artifacts.
- Unified regression: 157/157 tests pass.

The final GPT-5.6 Sol medium advisor pass first paused completion on missing/split/extra/swapped
branch coverage, inspected the live expansion, reran the 14-case gate and unified suite, and then
returned GO with no technical or documentation blockers inside the frozen scope.

This is controlled-family validation only. No noisy/checksum-frozen or independently authored
holdout track exists yet.

## Delivery plan (advisor-reconciled 2026-07-11)

The next implementation scope is deliberately split rather than broadened behind one
readiness claim.

- **circuit-v1a: graph foundation.** Controlled Pillow-rendered one-loop series diagrams using a
  battery, resistor, and lamp; orthogonal, non-crossing wires; component presence/type and an
  exact declared terminal-to-net graph. Layout may vary within this family, but every component
  has two typed terminals and every validated net has exactly two terminal attachments.
- **circuit-v1b: bounded branches.** A later, separately gated extension for explicit junction
  dots, simple parallel circuits, and one bounded mixed series-parallel family. Junction evidence
  must be extracted before branch connectivity can be claimed.

Both milestones share a bipartite `TerminalNetGraph`: typed component terminals attach to electrical
nets; detector IDs are never treated as semantic identity. Rules compare a canonicalized declared
netlist against the extracted graph and derive topology from that graph. Incomplete or ambiguous
evidence yields `needs_review`; complete contradiction yields a typed finding. A "short" may only
be reported when the evidence proves an unexpected net merge.

The advisor recommendation is **agreed**: this expands beyond a single hard-coded drawing while
preserving the project’s evidence-first boundary. It explicitly prohibits arbitrary schematics,
crossing-versus-junction inference, electrical quantities/laws/functionality, OCR, rotation, and
engineering-certification claims in v1a.

## Implementation progress: evidence contract

The formerly private feasibility extractor now exposes a typed `CircuitEvidenceGraph` with
`ExtractedCircuitComponent` (typed terminals, color, geometry) and `ExtractedCircuitNet`
(attachment references, pixel support), provenance, confidence, and machine-readable evidence
gaps. `specs/circuit-evidence-graph.schema.json` validates the golden probe artifact. The old
`extract_circuit_probe` dictionary response remains only as a compatibility adapter until the probe
cases are promoted into the v1a dataset/test suite. This is evidence-layer progress, **not** a
validation/readiness result.

## Implementation progress: claims and structural rules

`build_circuit_claim_graph` now maps the controlled spec's declared component colors/types,
terminal pairs, and `topology: "series_loop"` into five explicit checks: component count, presence,
type, exact terminal netlist, and derived series-loop topology. `run_circuit_claims` matches
components by controlled color identity, remaps detector-local terminal IDs to declared IDs, and
compares canonical undirected net pairs. It only produces missing/extra net or topology findings
when evidence is complete; any extractor gap skips the affected checks and returns `needs_review`.

Initial automated evidence: a correct three-component loop passes all five checks, while a diagram
with no wire evidence has no guessed findings and returns `needs_review` with all five checks
skipped. This is an early unit-test result, not the dataset validation gate.

## Feasibility gate (GO for bounded implementation)

Circuit-v1 starts as a controlled, structural verifier for one-loop DC diagrams, not a general
electrical-schematic reader. Before the full evidence/claims/rules pipeline was started, a
spec-blind image probe rendered and extracted a battery, resistor, lamp, and three orthogonal wire
nets. The golden case produced three symbol detections and three complete two-terminal wire nets
with no gaps. [source: experiments/circuit_v1_probe.py]

Mutation probes established the required separation of failure modes:

- A wrong resistor symbol (rendered as a lamp) keeps canonical wire routes fixed, then correctly
  makes connectivity incomplete because terminals are type-derived.
- A broken return wire produces two one-terminal wire fragments and
  `unresolved_wire_attachment`.
- A near-terminal wire miss also produces explicit attachment uncertainty.

An initial terminal offset outside the rendered glyph boundary was corrected. Independent GPT-5.6
Sol review then found two additional invalid probe claims: the wrong-symbol mutation recalculates
ports and wire paths rather than holding topology fixed, and the near-miss route crosses the
nominal terminal despite its offset. The probe was repaired and re-reviewed; the advisor now grants
a **GO for bounded implementation**. [source: advisor task 019f4f82-1457-73d1-a227-01b8e4672ce2]

Before claiming validation readiness, promote probe cases into exact automated tests (symbol types,
net counts, attachment sets, and complete gap sets). The spurious bridge is safely rejected as an
unattached extra net; duplicate attachment has its own separate case. All later circuit rules must
treat unresolved symbol or terminal evidence as `needs_review`, never as a guessed broken-net defect.

## Scope freeze

- Controlled Pillow renders only; battery, resistor, lamp; orthogonal single loops.
- Component identity may use controlled unique colors, but type is separately classified from
  geometry.
- Evidence uses undirected terminal-to-net relationships, not directed flowchart-style edges.
- No switches, crossings, junctions, branches, OCR, arbitrary rotation, values/polarity, or
  electrical law checks in v1.

## Planned checks

- `component-count-matches`
- `required-components-present`
- `component-type-correct`
- `netlist-connectivity-correct`

Symbol evidence gaps and wire/terminal gaps must be scoped independently. Connectivity necessarily
depends on terminal localization, so it is separately reported but not assumed independent from
symbol extraction.

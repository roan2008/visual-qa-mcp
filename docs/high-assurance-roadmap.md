# High-Assurance Domain Roadmap

## Purpose

The long-term goal is not only to make educational visuals usable for teaching. The project should move toward high-confidence, theory-aligned verification for scientific, medical, engineering, and technical visuals where plausible-looking errors can mislead learners or reviewers.

The early MVP stays narrow because the system must first prove that it can extract evidence, run deterministic checks, report uncertainty, and avoid unsupported passes. The high-assurance domains below are target tracks, not permanent exclusions.

## Target Tracks

### Medical And Anatomy Visuals

Goal: verify anatomy teaching images, medical education diagrams, clinical workflow illustrations, and labeled body-system visuals against trusted references.

Required before claiming readiness:

- Curated reference sources with version and provenance.
- Laterality checks for left/right anatomy.
- Required structure and relationship checks.
- Label-to-structure alignment checks.
- Explicit risk tier and expert review requirement.
- No automated clinical, diagnostic, or regulatory certification claims.

### Open-Ended Anatomy

Goal: support anatomy diagrams where the expected structures are not limited to a small fixed spec.

Required before claiming readiness:

- Controlled anatomical ontology or terminology source.
- Region-specific structure inventory.
- Relationship rules for adjacency, containment, branching, and symmetry.
- Handling of acceptable variation.
- Human expert review for ambiguous or high-risk findings.

### Complex Chemistry And Biology

Goal: verify molecular diagrams, reactions, biological pathways, cell diagrams, and process flows against domain rules and reference data.

Required before claiming readiness:

- Chemistry checks for valence, charge, stoichiometry, reaction direction, and units.
- Biology checks for structure presence, process order, pathway direction, and required labels.
- Source-backed expected entities and relations.
- Separation between detected visual evidence and inferred domain conclusions.
- Escalation when the visual claim is outside encoded rules.

### Full CAD Reconstruction

Goal: compare technical illustrations or generated part visuals against CAD, drawing, or manufacturing references.

Required before claiming readiness:

- Reference CAD, STEP, drawing, or dimensioned source artifact.
- Geometry extraction with tolerance handling.
- Dimension, alignment, hole, feature, and assembly relation checks.
- Projection and perspective handling.
- Clear distinction between visual illustration QA and engineering release approval.

## Maturity Levels

### Level 0: Visual Plausibility

The system can describe visible content, but it cannot verify correctness. This level is not enough for this project.

### Level 1: Evidence Extraction

The system can extract text, arrows, geometry, chart marks, objects, or regions with confidence scores.

### Level 2: Spec Matching

The system can compare extracted evidence to a structured visual spec and produce findings with coordinates or measurements.

### Level 3: Theory-Aligned Rules

The system can run domain rules grounded in equations, reference data, ontologies, or engineering constraints.

### Level 4: Reference-Grounded Review

The system can cite source references, record check provenance, and explain which claims were verified, skipped, or escalated.

### Level 5: Expert-Audited Workflow

The system supports expert review, sign-off records, validation datasets, and measured recall against injected high-severity errors.

## Design Requirements

- Every high-assurance verdict must separate visual evidence from domain inference.
- `pass` is allowed only when required checks ran and required evidence is present.
- Missing evidence should produce `needs_review`, not `pass`.
- Reports should include check provenance: rule name, source reference, tolerance, evidence, and skipped-check reason.
- High-risk domains must include a human expert review path.
- The project should never claim clinical, regulatory, safety, or professional engineering certification without explicit external validation and qualified review.

## Roadmap Strategy

1. Prove the loop on charts, arrows, geometry, and simple physics.
2. Add theory-aware rule modules for physics and mechanical diagrams.
3. Add stronger schema support for source references, rule provenance, tolerances, and confidence separation.
4. Build small golden and mutated-error datasets for each target track.
5. Expand into medical, anatomy, chemistry, biology, and CAD only when reference data and validation rules are available.

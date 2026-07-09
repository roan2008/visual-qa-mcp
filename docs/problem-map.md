# Problem Map

AI-generated educational visuals often fail in ways that are visually plausible but instructionally wrong. The project tracks these failures as a taxonomy so tools can detect them systematically.

## Cross-Domain Failure Types

### Text And Label Errors

- Misspelled terms.
- Incorrect labels.
- Duplicate labels.
- Labels pointing to the wrong object.
- Missing units.
- Wrong unit conversions.
- Legend items that do not match the visual encoding.

### Spatial Relation Errors

- Left/right reversal.
- Above/below or inside/outside mismatch.
- Objects touching when they should be separated.
- Objects separated when they should be connected.
- Components misaligned with callouts or dimensions.

### Counting And Presence Errors

- Missing required objects.
- Extra hallucinated objects.
- Wrong number of repeated parts, atoms, teeth, cells, wires, or supports.
- Required safety elements omitted.

### Arrow And Flow Errors

- Arrow tip misses the target.
- Arrow direction is reversed.
- Flow path is broken.
- Causal order is wrong.
- Decision branches or process outputs are missing.

### Geometry And Measurement Errors

- Incorrect angles.
- Incorrect distances.
- Non-parallel edges where parallelism is required.
- Non-concentric holes.
- Shape deformation that changes the concept being taught.
- Perspective that makes the measurement misleading.

### Chart And Data Errors

- Bar height does not match numeric value.
- Pie slices do not sum to 100%.
- Axis scale is inconsistent.
- Trend does not match source data.
- Data labels contradict the marks.
- Visual encoding makes comparisons misleading.

### Domain Logic Errors

- Physics diagrams violate force, torque, energy, optics, or circuit rules.
- Engineering illustrations show impossible assemblies or missing constraints.
- Chemistry diagrams violate valence, bonding, stoichiometry, or reaction direction.
- Biology diagrams invent structures or place them in the wrong relation.
- Medical diagrams show incorrect anatomy, laterality, or unsafe simplification.

## Risk Levels

### Low Risk

Decorative or conceptual visuals where exact structure is not essential.

### Medium Risk

Educational visuals where mistakes can teach the wrong concept but are unlikely to cause immediate harm.

### High Risk

Medical, safety, engineering, laboratory, or clinical visuals where errors can affect decisions, procedures, or safety behavior.

## Product Hypothesis

The biggest value is not detecting whether an image is AI-generated. The value is detecting whether a visual claim is correct enough for its teaching purpose and faithful enough to the relevant theory, reference data, or engineering constraints.

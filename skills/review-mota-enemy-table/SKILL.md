---
name: review-mota-enemy-table
description: Review a generated classic Mota enemy stat table together with projected per-floor hero growth and candidate pools. Use inside the tower pipeline after enemy-data generation and before floor-map generation to check tier coverage, global role diversity, special legality, and cross-floor raw-strength progression. Do not require every candidate to be immediately killable, review final map placement, or claim whole-tower solvability.
---

# Review Mota Enemy Table

## Scope

Review the supplied enemy table, projected hero bands, local numeric analysis, and per-floor candidate assignments. Treat the table as a reusable catalog; later monster generation chooses the concrete subset placed on each map.

Do not review concrete monster coordinates, route geometry, or final tower solvability. Those belong to later floor and integration reviewers.

## Cross-Floor Progression

- Require a clear weak-to-strong raw-stat tier ladder across the table without demanding monotonic growth in every attribute.
- Reject red-sea raw-strength regression or a table that lacks a meaningful later tier.
- For each enemy id's first assigned red-sea floor, require enemy ATK+DEF to be at least the target projected hero ATK+DEF. Do not reapply this threshold when the id is reused later.
- Allow temporarily unbeatable candidates and defense thresholds; projected killability is not a table-level requirement.
- Use projected hero bands as scale evidence, not as exact playthrough states.

## Role Diversity

Require the complete table to offer multiple roles, without requiring every floor pool to contain each role:

- `tank`: higher HP.
- `high attack`: higher attack.
- `balanced`: moderate HP, attack, and defense.
- `defense threshold`: defense near the projected hero's attack threshold.
- allowed special-pressure roles such as magic attack, zone, first strike, and repulse.

Require at least three role families in a normal candidate pool. At least half of actively assigned enemy types must have no special ability unless the confirmed brief explicitly changes that rule.

## Review Evidence

For every failure, identify concrete `floor_indices` and `enemy_ids`. Cite tier coverage, raw-strength progression, role-family coverage, or special ratios from the supplied analysis.

Do not fail merely because the table differs from a few-shot example. Few-shot enemy tables calibrate relative roles and progression only; the confirmed tower resources and projected hero bands define this tower's numeric scale.

## Output

Return only JSON matching the orchestrator schema. Set `status="fail"` when any issue with `severity="fail"` is present. Every issue must contain:

- `severity`: always `fail`; do not emit warnings.
- `floor_indices`: affected zero-based floors.
- `enemy_ids`: affected enemy ids.
- `reason`: measurable problem.
- `required_change`: targeted stat or assignment adjustment.

Keep changes local: adjust named enemies or floor assignments and preserve unrelated records.

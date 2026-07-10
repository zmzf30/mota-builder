---
name: review-mota-enemy-table
description: Review a generated classic Mota enemy stat table together with projected per-floor hero growth and concrete floor enemy pools. Use inside the tower pipeline after enemy-data generation and before floor-map generation to check target-hero-relative difficulty continuity, same-floor attribute tradeoffs, role diversity, low-tax limits, special usage, and floor assignment quality. Do not review map placement or claim whole-tower solvability.
---

# Review Mota Enemy Table

## Scope

Review the supplied enemy table, projected hero bands, local numeric analysis, and per-floor enemy assignments. Treat local calculations as evidence and inspect whether the proposed table can support coherent floor combat pools.

Do not review concrete monster coordinates, route geometry, or final tower solvability. Those belong to later floor and integration reviewers.

## Cross-Floor Progression

- Require role-appropriate progression, not monotonic growth in all three raw stats.
- Compare enemies against the target projected hero for their assigned floor, not against one global static score.
- Keep adjacent floors' core relative difficulty reasonably close. Allow a gradual increase and explicit spike or relief floors from `floor_progression_plan`, but reject unexplained discontinuities.
- Allow a strong enemy from one floor to become an easier carryover enemy on the next floor.
- Reject pools dominated by zero-loss enemies or enemies the target projected hero cannot damage.
- Use conservative and completion hero bands as sensitivity checks. Do not treat the projections as exact playthrough states.

## Same-Floor Balance

- Keep most ordinary enemies in a reasonably close target-hero-relative difficulty band.
- Fail when one ordinary core enemy has HP, ATK, and DEF all at least another ordinary core enemy. Ordinary core enemies must trade attributes.
- Reject an unmarked ordinary enemy whose expected loss is several times the floor median.
- Define a plain enemy below 35% of the floor median relative difficulty as low-tax. Allow at most one per traditional floor and none on red-sea floors. Cross-floor id reuse is allowed in red-sea only when the enemy remains in the ordinary difficulty band rather than acting as a carryover role.
- Allow a mini-boss outlier only when the progression plan identifies it and the pool does not use it as routine filler.

## Role Diversity

Require distinct roles without requiring identical damage:

- `tank`: higher HP with restrained attack/defense and at least the floor-median combat rounds.
- `high attack`: higher attack with low HP/defense and at most the floor-median combat rounds.
- `balanced`: moderate HP, attack, and defense.
- `defense threshold`: defense near the projected hero's attack threshold.
- `magic attack specialist`: raw strength at or below the floor median; magic attack creates its pressure.
- `zone elite`: HP, ATK, and DEF each at least the floor median; this is the explicit all-round-strong exception.
- `first strike` and `repulse` specialists: use a clear stat tradeoff instead of stacking the strongest raw stats.

Fail a normal floor pool that lacks tank, high attack, or balanced/defense-threshold roles. When magic attack or zone is allowed, require its corresponding specialist. At least half of actively assigned enemy types must have no special ability unless the confirmed brief explicitly changes that rule.

## Review Evidence

For every failure, identify concrete `floor_indices` and `enemy_ids`. Cite projected hero stats, relative difficulty, attribute medians, strict-dominance pairs, low-tax ids, role coverage, or special ratio from the supplied analysis.

Do not fail merely because the table differs from a few-shot example. Few-shot enemy tables calibrate relative roles and progression only; the confirmed tower resources and projected hero bands define this tower's numeric scale.

## Output

Return only JSON matching the orchestrator schema. Set `status="fail"` when any issue with `severity="fail"` is present. Every issue must contain:

- `severity`: `fail` or `warn`.
- `floor_indices`: affected zero-based floors.
- `enemy_ids`: affected enemy ids.
- `reason`: measurable problem.
- `required_change`: targeted stat or assignment adjustment.

Keep changes local: adjust named enemies or floor assignments and preserve unrelated records.

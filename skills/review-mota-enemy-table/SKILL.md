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

## Role Contracts

When `monster_policy.role_slots` is present, review every floor candidate pool against the explicit role catalog. The default pool is 10-12 types: `high_attack=1`, `balanced=2-3`, `magic=1`, `zone=1`, `repulse=1`, `high_hp=1`, `gem_gate=1`, and `strong=2-3`.

Use the floor's target hero bands for `A/D`, and completion bands for `Ac/Dc`:

- `high_attack`: ATK 5-7A, DEF at most 0.1ATK, HP 0.6-1.2ATK.
- `balanced`: ATK about 1.8max(A,D), DEF 0.3-0.4ATK, HP 2.5-3.5ATK.
- `magic`: ATK 0.7-0.9A, DEF 0.5-0.7D, HP 3-6A, magic special.
- `zone`: ATK about 3max(A,D), DEF 0.3-0.4ATK, HP 5-8A, zone special.
- `repulse`: zone ATK/DEF/HP scaled to 0.85-0.95, with repulse special.
- `high_hp`: ATK about 1.5max(A,D), DEF 0.45-0.55ATK, HP 9-12A.
- `gem_gate`: DEF about Ac-3, ATK at least 1.5DEF, HP 0.8-1.2A.
- `strong`: ATK 3-4Ac, DEF 0.6-0.8Dc, HP 4-7A; verify completion-state battle loss is about 2.5-3.5 blue potions.

Except for `magic`, reject ATK below the floor target hero DEF. Ordinary roles (`balanced`, `high_hp`, `gem_gate`, `strong`) should have no specials; only `zone` and `repulse` receive geometry-specific map duties. `numeric_score = HP*0.08 + ATK*2 + DEF*2.5` is ordering metadata only, never the core difficulty metric.

Enforce carry constraints on every reused enemy: no id may appear on three consecutive floors, a previous-floor id cannot occupy the current `strong` slot, and a carried id must satisfy `ATK >= current floor completion.DEF * 1.3`. The preferred carry roles are `high_attack`, `magic`, `zone`, `repulse`, and `strong`.

When no explicit role slots are configured, retain the legacy checks: require multiple role families and at least half of actively assigned enemy types without specials unless the confirmed brief changes that rule.

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

---
name: review-mota-floor
description: Review one traditional topology stage, economy stage, or final encounter composition. Local scripts own deterministic legality; this reviewer judges the remaining design quality and never edits maps.
---

# Review Mota Floor

## Role

Review exactly one supplied stage. The orchestrator owns generation, deterministic validation, retries, persistence, and project writing. Do not generate or edit floor content.

## Evidence

- Judge the actual map, tile catalog, enemy records, deterministic metrics, floor contract, and upstream stage maps.
- Treat annotations as design intent, not proof.
- Use reviewer few-shot holdouts for route and compensation calibration, never as numeric quotas.
- Do not recalculate schema, counts, connectivity, adjacency, coordinate preservation, special geometry, or exact budgets after the local review has passed; use the supplied deterministic result.

## Stage Scope

### Topology

- Only judge whether graph-valid branches, junctions, pockets, shortcuts, and route families create meaningful structure.
- Reject fake branches, uncontrolled open grids, decorative wall patterns, repeated adjacent-floor grammar, and insufficient downstream design capacity.
- Return structural issues to `topology`.

### Economy

- Economy must contain keys, resources, tools, and pressure intent, but no doors or enemies.
- It preserves every wall and stair from topology.
- Judge resource dispersion, access stages, route rewards, tool purpose, entrance exposure, and whether pressure intent clearly identifies what later needs protection.
- Pressure intent must not prescribe a door color or concrete enemy.
- Return resource, key, tool, or pressure-intent issues to `economy`; structural insufficiency returns to `topology`.

### Final Integration

- Encounter may only replace economy-stage empty ground with doors or allowed enemies. Every non-ground economy tile remains exact.
- Judge doors, monsters, and specials as one route-pressure system.
- Every door must buy reward access, a shortcut, route change, or safer combat profile; stronger doors require stronger compensation.
- Every monster must tax a route, guard value, enforce a threshold, control a shortcut, or create supported special pressure.
- Reject filler, naked rewards, all-cost routes, cosmetic alternatives, and a route that is both cheaper and richer than all others.
- Judge combat thresholds against the projected hero supplied in `current_floor_policy`.
- Door/enemy/special placement issues return to `encounter`; economy placement issues return to `economy`; structural issues return to `topology`.

## Traditional Quality

- Target 2-4 real route families and roughly 6-20 meaningful decisions.
- Target 70%-90% protected important rewards and a 0%-10% resource safety margin.
- Blue/red doors should protect stronger rewards or strategic access than yellow-door baselines.
- Traditional special pressure should be perceivable and compensated; do not demand unsupported abilities merely to meet a count.
- Do not infer numeric monster strength from tower style.

## Zone And Repulse

- Zone and repulse must affect a real route, reward entrance, shortcut, or junction.
- Reject unavoidable uncompensated early pressure and decorative specials.
- Use the script-supplied geometry result as authoritative; judge only route meaning and compensation.

## Output

Return only schema-valid JSON. Every failure includes `owner_stage`, `severity`, `repair_stage`, coordinates when available, reason, and required change. `repair_stage` is exactly one of `topology`, `economy`, or `encounter` and names the earliest stage that can fix the issue.

Use `fail` only for required repair. Do not emit replacement floor content.

---
name: economy-mota-floor
description: Fill doors, keys, resources, tools, and combat role annotations into a topology-only classic mota-js floor. Use as stage 2 of the staged floor pipeline after topology-mota-floor and before monster-special-mota-floor.
---

# Economy Mota Floor

## Role

Act as stage 2 of a staged per-floor Magic Tower generator.

Start from the topology stage output. Add the floor's economy: doors, keys, resources, tools, and route-tax intent. Do not choose final concrete monsters. Instead, annotate where combat and special pressure should go.

## Real Few-Shot Input

When `few_shot_reference_floors` is present, it is the economy generator's construction set: one generator/reviewer shared anchor plus generator-only examples. Decode its actual `map_codes` through the project-local `tile_legend`, then use the candidate routes, route-graph edge contents, and `resource_reachability_order` as positive examples. Reproduce relationships such as staged access, competing key uses, stronger compensation behind stronger gates, and optional deep rewards. Do not copy source tile codes, totals, scripts, or unsupported mechanics. Reviewer holdouts are intentionally absent; do not guess or optimize for them.

## Hard Rules

- Return only JSON matching the orchestrator schema.
- Preserve `floor_id`, `floor.floorId`, dimensions, stairs, and the general topology from `topology_output`.
- Use only legal tile codes from the supplied catalog.
- Keep `0` as the only ground and `1` as the only wall.
- Do not place enemy tiles.
- Do not add scripts, hidden events, story mechanics, new assets, or plugin mechanics.
- Keep required empty fields present.
- Treat `remaining_whole_tower_budget` as a hard ceiling.
- When `floor_contract.resource_limits` is present, treat it as exact tracked-resource quotas for this floor.

## Economy Quality

- Follow `tower_brief.tower_style` without changing the user's resource totals.
- For `traditional`, use clear regions with multiple branch types, target 70%-90% protected important resources and 0%-10% key/resource safety margin, and place 0.5-2 tools per floor on average when the confirmed whole-tower budget permits.
- For `red_sea`, distribute rewards across narrow local branches and protect nearly every valuable reward with a door, monster role, route commitment, supported special pressure, or existing tool relationship.
- Add meaningful door/key pressure. Doors should buy shortcuts, reward access, route changes, or safer combat profiles.
- Do not spend budget just because it is available.
- Keep the entrance free region controlled: no naked tool or unprotected important-resource cluster.
- Avoid large low-cost connected resource blobs.
- Disperse by real access cost: ≥1/4 of floor gems (min 2) in one region or ≥1/3 (min 3) across a one-door/one-wall link fails; a decorative guard is not dispersion.
- Distribute keys and tools across route stages instead of bunching them near the entrance.
- Blue doors and tool routes need better compensation than yellow-door baseline routes.
- Tools such as pickaxe, bomb, and centerFly must be protected or must unlock a clear route/reward purpose.
- Higher-cost or riskier route choices need stronger rewards or shorter access.
- Balance every candidate route as a cost/reward tradeoff. Compare door/key cost, tool commitment, expected combat or special pressure, detour length, and reachable rewards; no route should be all cost, and no route should be simultaneously cheaper and richer than every alternative.
- Respect resource progression from `current_floor_policy.resource_progression`.
- You may add, remove, or move up to 3 wall tiles when needed to make a door, tool, reward pocket, or shortcut actually meaningful.
- Do not treat broken walls as decoration. A pocket or gap should change access cost, protect value, create tool value, or create a later combat/special placement.
- Do not place high-value resources in a simple dead-end pocket unless the pocket entrance is costed by a door, combat annotation, special annotation, tool requirement, or route commitment.

## Combat Role Annotations

Do not place monsters. Add `annotations` entries that tell the monster-special stage what role a coordinate should play.

Use these `kind` values when relevant:

- `combat_chokepoint`
- `reward_guard`
- `route_tax`
- `special_candidate`
- `mini_boss_candidate`

Each annotation should cite concrete coordinates and describe the intended pressure, compensation, and route relationship.

## Repair

When `repair_feedback` is present:

- Repair only economy-owned issues.
- Preserve topology unless a small wall adjustment is needed to make the economy valid or to make a pocket/tool/shortcut actually costed.
- Do not place final enemies to fix an economy review.
- Use only the stage input, current output, structured issue, and downstream hard constraint summary supplied by the orchestrator.

## Output

Return a full floor wrapper with updated `floor.map` and `annotations`. The final stage will choose concrete enemies.

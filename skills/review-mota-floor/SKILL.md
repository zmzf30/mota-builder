---
name: review-mota-floor
description: Review one classic mota-js floor object or staged floor output against a confirmed whole-tower brief, current budget ledger, and traditional Magic Tower constraints. Use inside the code-orchestrated staged build pipeline after topology, economy, or monster-special generation. The skill returns pass/fail, issues, required changes, and budget validation. Do not use for generating floors, confirming the whole-tower brief, or editing files.
---

# Review Mota Floor

## Role

Act as the reusable per-floor review agent for a traditional Magic Tower pipeline.

Review exactly one staged or final mota-js floor output. The code orchestrator owns sequencing, retries, local validation, persistence, project writing, and final completion.

## Review Philosophy

The staged generators output maps plus annotations. Your job is to validate the actual `floor.map`, `maps.js` tile meanings, `enemys.js` monster data, and any stage annotations supplied by the orchestrator.

Treat annotations as hints, not proof. Infer route structure, route cost, resource protection, and special pressure from the map itself.

When `upstream_stage_maps` is present, it contains the complete map matrix and annotations from every available earlier generator stage, with unrelated empty floor boilerplate omitted. Compare the candidate map coordinate-by-coordinate against these baselines. Economy review must use the topology baseline; monster and integration review must use both topology and economy baselines. Do not infer stage preservation from summaries, annotation counts, or tile totals alone.

When `few_shot_reference_floors` is present, it contains one anchor shared with the generator plus reviewer-only holdout floors, with actual maps, route graphs, resource-access order, and used enemy records. Use the shared anchor as a common calibration point and the holdouts to test whether the candidate generalized the design relationships beyond its construction examples. Judge relationships and design density, not literal tile-code or wall-mask similarity. Apply `contrastive_rejection_cases` as explicit anti-pattern checks; they supplement rather than override the stage scope and tower brief.

Few-shot examples calibrate only the design dimension owned by the current reviewer. They never define an exact wall ratio, resource total, or enemy count. Those values come only from the confirmed tower brief, floor contract, and current policies.

## Critical Budget Rule

Any quantity limits in the tower brief are whole-tower totals, not per-floor allowances.

Check the floor object against the used-so-far ledger and remaining whole-tower budget. A floor fails if its actual map-derived budget exceeds remaining budget for any tracked resource.

When `floor_contract` is present, the pipeline is running parallel floor generation. In that mode, `floor_contract.resource_limits` is this floor's hard tracked-resource slice from the whole-tower budget; fail the floor if its map-derived budget exceeds that slice.

## Required Checks

- The floor follows the confirmed whole-tower brief and requested `floor_size`.
- Economy output preserves the supplied topology baseline except for its explicitly allowed small wall adjustments; monster output preserves the topology and the economy's doors, keys, resources, tools, and route structure except for explicitly justified small local coordinate adjustments.
- Do not require an outer wall border.
- The map uses valid tile codes and consistent dimensions.
- Tile code `0` is the only allowed passable/default ground code and tile code `1` is the only allowed wall code. Fail any use of alternate ground, grass, thin-wall, white-wall, blue-wall, or other wall terrain codes in `floor.map`, `bgmap`, or `fgmap`.
- The floor has a `downFloor` entrance and an `upFloor` exit.
- Entrance to exit should be reachable; if not directly reachable, it may still pass only when removing one wall/obstacle would connect them and the floor provides plausible tool pressure.
- Apply `tower_brief.tower_style`. Traditional floors target 2-4 plausible route families and around 6-20 effective decisions; red-sea floors target at least 3 route families and around 10-40 meaningful local opportunities.
- Do not count opportunities from annotations alone. Confirm their coordinates correspond to actual junctions, articulation points, branch ends, pockets, or shortcuts, and verify that topology capacity leaves enough non-adjacent enemy cells, door sites, and resource cells for downstream stages.
- Fail repeated wall templates or adjacent floors with nearly identical wall masks. Clean legible wall runs and regions are valid for traditional style; red-sea fragmentation must be purposeful.
- Broken walls only count as precise when they change access cost, reward protection, tool value, special pressure, or route choice.
- Fail decorative broken walls: fragmented pockets or gaps with no route, reward, tool, combat, or special-pressure purpose.
- Fail uncontrolled open-grid topology: large non-wall regions with many equivalent loops do not count as meaningful candidate routes.
- Do not assume keys must be before doors. Check whether a viable key-door ordering can exist; fail only if all orderings are deadlocked.
- Every floor must contain both battle pressure and key/resource pressure. Fail pure resource, pure transition, pure shop, pure puzzle, or pure combat floors.
- High-value resources are not exposed in naked piles. Traditional style targets 70%-90% protected important resources and 0%-10% key/resource safety margin; red-sea style should protect nearly every valuable reward.
- The entrance/free region reachable without doors, monsters, walls, or special damage should not expose tools or an unprotected important-resource cluster.
- Monster special abilities are within the whitelist.
- Each monster has at most the allowed number of special abilities.
- Monster type count does not exceed `monster_types_per_floor`; default 9.
- Enemy count must be within `monster_policy.enemy_count_min_per_floor` and `monster_policy.enemy_count_max_per_floor`; default 18-28 for traditional and 22-33 for red-sea when absent.
- Traditional style targets 2-6 meaningful special-pressure positions and 0.5-2 tools per floor on average when the whitelist, map capacity, and confirmed budget permit.
- If `current_floor_policy` is present, all placed enemies must be in its allowed enemy ids/codes.
- No two enemy tiles may be orthogonally adjacent; diagonal contact is allowed.
- Zone and repulse damage must be within `current_floor_policy.special_damage_red_potion_range` when that policy is present.
- Same-floor monster stats should be balanced but distinct: high HP/low attack, high attack/low HP, high defense/threshold, and balanced profiles should not collapse into one identical profile.
- The floor does not rely on random, hidden, script-heavy, plugin, UI, new-asset, or story mechanics. Red-sea style does not authorize clamp, drain, self-destruct, lamps, arrows, one-way tiles, or any other unsupported mechanism.
- Do not infer numeric difficulty or require stronger monster HP/ATK/DEF from the tower style.

## Candidate Route Review

Infer the style-specific number of candidate route families from entrance to exit. For each route family, estimate:

- Door/key cost.
- Monster combat cost and stat profile.
- Blood-net or terrain tax.
- Zone monster pressure.
- Repulse monster pressure.
- Route length and detour cost.
- Rewards reachable along or just behind the route.

Fail or request changes when:

- One route strictly dominates another by having lower cost and higher reward.
- A candidate route has only cost and no compensation.
- A candidate route has mostly naked rewards and little cost.
- Routes differ only cosmetically and do not create a meaningful tradeoff.

For integration review, estimate every supplied candidate route's door/key cost, expected battle loss, special damage, length, and reachable rewards. Use the deterministic route analysis when present, then reject likely strict dominance or resource-region connections whose cost is abnormally low for their combined value.

## Zone And Repulse Review

For `special: 15` zone monsters:

- Pass when the zone taxes a route, guards a reward, controls a junction, or makes a shorter/richer route more expensive.
- Fail when a zone covers all routes with no compensation.
- Fail when a zone sits near the entrance as unavoidable early damage without compensation.
- Fail when the zone does not affect any meaningful route or reward.
- Require a range-1 cross on a wall-constrained route node with exactly 2-3 effective passable affected cells.
- Require annotations to name affected cells, the affected route or reward entrance, and compensation.

For `special: 18` repulse monsters:

- Pass when repulse affects a corridor, reward entrance, route junction, or a route-vs-route cost tradeoff.
- Fail when repulse is decorative and affects no plausible movement.
- Fail when several repulse monsters stack on the same route without stronger compensation.
- Require a linear corridor and at least one approach direction with an empty retreat cell that continues into another path.
- Require annotations to name the approach/retreat cells, affected route, and compensation.

## Resource Review

- Keys behind doors are allowed when a viable ordering exists.
- Door-heavy routes need meaningful rewards or shortcuts.
- Blue/red doors should guard stronger rewards or strategic access.
- Yellow doors/keys are the low-cost baseline. Blue doors and wall-breaking/tool access should provide stronger compensation than a yellow-door route.
- Tools such as pickaxe, bomb, and centerFly must either be protected or clearly support route logic.
- Large resource clusters must require enough combat, door, wall/tool, special-damage, or route-length pressure before access.
- Disperse by real access cost: ≥1/4 of floor gems (min 2) in one region or ≥1/3 (min 3) across a one-door/one-wall link fails; a decorative guard is not dispersion.
- Gem and potion totals should follow `current_floor_policy.resource_progression` when that policy is present.
- Blood nets should be route tax tied to compensation, not random punishment.

## Positive Calibration Anchors

- Traditional style: use only `寒云谷2103`, `溯`, and `CCW` references selected for the current floor.
- Red-sea style: use only `红蓝的记忆2.10`, `星月神话 2.10.3`, `dist`, `剑阁2.9`, and `出塞V2.10.0` references selected for the current floor.
- Never compare a candidate against the other style as a fallback.
- Format only, not a balance target: `HTML5魔塔样板V2.7.3.1 / MT2` and `MT3`.

## Output Contract

Return only JSON when used by the build script.

Use the JSON schema supplied by the orchestrator. In the staged pipeline, issues are structured objects with `owner_stage`, `severity`, `coordinates`, `reason`, and `required_change`. For a basic non-structured schema, use this shape:

```json
{
  "status": "pass",
  "issues": [],
  "required_changes": [],
  "budget_delta": {
    "yellow_doors": 0,
    "blue_doors": 0,
    "red_doors": 0,
    "yellow_keys": 0,
    "blue_keys": 0,
    "red_keys": 0,
    "pickaxes": 0,
    "bombs": 0,
    "centerFly": 0,
    "jumpShoes": 0,
    "redGems": 0,
    "blueGems": 0,
    "greenGems": 0,
    "redPotions": 0,
    "bluePotions": 0,
    "yellowPotions": 0,
    "greenPotions": 0
  },
  "summary": "short review summary"
}
```

Set `status` to `fail` if any required check fails. Put concrete map-level fixes in `required_changes`, preferably referencing coordinates when possible.

Every structured issue must also include `repair_stage`, set to the earliest generator stage that can make the requested change: `topology`, `economy`, or `monster`. An integration finding still needs a concrete editable repair stage.

## Boundary

- Review one floor only.
- Do not generate replacement floor content.
- Do not change files.
- Do not approve a floor that violates whole-tower budget limits.

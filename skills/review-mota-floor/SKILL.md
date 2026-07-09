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

## Critical Budget Rule

Any quantity limits in the tower brief are whole-tower totals, not per-floor allowances.

Check the floor object against the used-so-far ledger and remaining whole-tower budget. A floor fails if its actual map-derived budget exceeds remaining budget for any tracked resource.

When `floor_contract` is present, the pipeline is running parallel floor generation. In that mode, `floor_contract.resource_limits` is this floor's hard tracked-resource slice from the whole-tower budget; fail the floor if its map-derived budget exceeds that slice.

## Required Checks

- The floor follows the confirmed whole-tower brief and requested `floor_size`.
- Do not require an outer wall border.
- The map uses valid tile codes and consistent dimensions.
- Tile code `0` is the only allowed passable/default ground code and tile code `1` is the only allowed wall code. Fail any use of alternate ground, grass, thin-wall, white-wall, blue-wall, or other wall terrain codes in `floor.map`, `bgmap`, or `fgmap`.
- The floor has a `downFloor` entrance and an `upFloor` exit.
- Entrance to exit should be reachable; if not directly reachable, it may still pass only when removing one wall/obstacle would connect them and the floor provides plausible tool pressure.
- The floor offers at least 3 plausible entrance-to-exit candidate route families and around 8-12 meaningful branch, pocket, shortcut, or gated-access opportunities.
- Fail clean repeated wall templates, symmetric straight-bar mazes, or adjacent floors with nearly identical wall masks.
- Broken walls only count as precise when they change access cost, reward protection, tool value, special pressure, or route choice.
- Fail decorative broken walls: fragmented pockets or gaps with no route, reward, tool, combat, or special-pressure purpose.
- Fail uncontrolled open-grid topology: large non-wall regions with many equivalent loops do not count as meaningful candidate routes.
- Do not assume keys must be before doors. Check whether a viable key-door ordering can exist; fail only if all orderings are deadlocked.
- Every floor must contain both battle pressure and key/resource pressure. Fail pure resource, pure transition, pure shop, pure puzzle, or pure combat floors.
- High-value resources are not exposed in naked piles.
- The entrance/free region reachable without doors, monsters, walls, or special damage should not expose more than a tiny starter reward and should not expose tools.
- Monster special abilities are within the whitelist.
- Each monster has at most the allowed number of special abilities.
- Monster type count does not exceed `monster_types_per_floor`; default 9.
- Enemy count must be within `monster_policy.enemy_count_min_per_floor` and `monster_policy.enemy_count_max_per_floor`; default 22-33 when absent.
- If `current_floor_policy` is present, all placed enemies must be in its allowed enemy ids/codes.
- No two enemy tiles may be orthogonally adjacent; diagonal contact is allowed.
- Zone and repulse damage must be within `current_floor_policy.special_damage_red_potion_range` when that policy is present.
- Same-floor monster stats should be balanced but distinct: high HP/low attack, high attack/low HP, high defense/threshold, and balanced profiles should not collapse into one identical profile.
- The floor does not rely on random, hidden, script-heavy, plugin, UI, new-asset, or story mechanics.

## Candidate Route Review

Infer at least 3 candidate route families from entrance to exit. For each route family, estimate:

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

## Zone And Repulse Review

For `special: 15` zone monsters:

- Pass when the zone taxes a route, guards a reward, controls a junction, or makes a shorter/richer route more expensive.
- Fail when a zone covers all routes with no compensation.
- Fail when a zone sits near the entrance as unavoidable early damage without compensation.
- Fail when the zone does not affect any meaningful route or reward.

For `special: 18` repulse monsters:

- Pass when repulse affects a corridor, reward entrance, route junction, or a route-vs-route cost tradeoff.
- Fail when repulse is decorative and affects no plausible movement.
- Fail when several repulse monsters stack on the same route without stronger compensation.

## Resource Review

- Keys behind doors are allowed when a viable ordering exists.
- Door-heavy routes need meaningful rewards or shortcuts.
- Blue/red doors should guard stronger rewards or strategic access.
- Yellow doors/keys are the low-cost baseline. Blue doors and wall-breaking/tool access should provide stronger compensation than a yellow-door route.
- Tools such as pickaxe, bomb, and centerFly must either be protected or clearly support route logic.
- Large resource clusters must require enough combat, door, wall/tool, special-damage, or route-length pressure before access.
- Gem and potion totals should follow `current_floor_policy.resource_progression` when that policy is present.
- Blood nets should be route tax tied to compensation, not random punishment.

## Positive Calibration Anchors

- Overall compact pressure: `红蓝的记忆2.10 / MT6` and `一层小塔 2.10 / MT0`.
- Branching and protected rewards: `剑阁2.9 / MT3` and `MT6`.
- Connectivity density: `剑阁2.9 / MT3`, `剑阁2.9 / MT6`, `红蓝的记忆2.10 / MT6`, and `dist / MT1-MT2`.
- Resource balance: `红蓝的记忆2.10 / MT6`, `一层小塔 2.10 / MT0`, `剑阁2.9 / MT3`, `出塞 / MT0-MT2`, and `星月神话 / MT7-MT8`.
- Zone pressure: `红蓝的记忆2.10 / MT1` and `MT4`.
- Repulse and mechanism pressure: `dist / MT1-MT2` and `Oblivion 2.10 / MT1`.
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

## Boundary

- Review one floor only.
- Do not generate replacement floor content.
- Do not change files.
- Do not approve a floor that violates whole-tower budget limits.

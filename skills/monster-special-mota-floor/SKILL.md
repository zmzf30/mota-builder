---
name: monster-special-mota-floor
description: Replace economy-stage combat annotations with concrete allowed monsters and special pressure for one classic mota-js floor. Use as stage 3 of the staged floor pipeline after topology and economy stages.
---

# Monster Special Mota Floor

## Role

Act as stage 3 of a staged per-floor Magic Tower generator.

Start from the economy stage output. Choose concrete enemy tile codes and place special pressure so the final floor has real combat pacing, perceivable zone/repulse effects, and distinct monster roles.

## Real Few-Shot Input

When `few_shot_reference_floors` is present, it is the monster generator's construction set: one generator/reviewer shared anchor plus generator-only examples. Inspect the real enemy coordinates, route gates, and `used_enemy_stats_from_enemys_js` together. Learn relative roles, threshold pressure, optional-versus-mandatory guards, and special coverage. Scale all values and placements to the current tower's hero state, whitelist, and allowed enemy ids; do not copy unsupported source specials or raw source values blindly. Reviewer holdouts are intentionally absent; do not guess or optimize for them.

## Hard Rules

- Tower style controls placement grammar only. Do not infer numeric difficulty or stronger HP/ATK/DEF from it.
- Do not add clamp, drain, self-destruct, lamps, arrows, one-way tiles, scripts, or other unsupported mechanics for red-sea style.
- Return only JSON matching the orchestrator schema.
- Preserve floor id, dimensions, stairs, topology, and economy unless a small local coordinate adjustment is necessary.
- Use only enemy ids and tile codes from `current_floor_policy.allowed_enemy_ids` and `current_floor_policy.allowed_enemy_codes`.
- Do not invent enemies, specials, stats, scripts, events, assets, or plugins.
- Respect the tower special whitelist.
- Each monster must obey `max_specials_per_monster`.
- Place between `monster_policy.enemy_count_min_per_floor` and `monster_policy.enemy_count_max_per_floor` enemies on the final floor; default to 18-28 for traditional and 22-33 for red-sea when absent.
- Traditional style targets 2-6 meaningful special-pressure positions when the user's whitelist and map capacity permit. Do not add unsupported mechanism types merely to meet the target.
- No two enemy tiles may be orthogonally adjacent.
- Keep `0` as the only ground and `1` as the only wall.
- Do not rebuild the economy to solve monster placement unless a tiny local adjustment is required.

## Monster Quality

- Convert combat annotations into real enemies where possible.
- If combat annotations are fewer than the required enemy minimum, add extra non-adjacent enemies as route tax, reward guards, branch blockers, or visible pressure on valid ground cells while preserving resource and door quotas.
- Same-floor monsters should not collapse into one repeated role. Use the allowed pool to create distinct pressure:
  - high HP or endurance,
  - high attack pressure,
  - defense threshold,
  - balanced combat,
  - optional zone or repulse pressure.
- Every enemy should contribute to a route cost, reward guard, chokepoint, shortcut decision, or route-vs-route tradeoff.
- Use `estimated_hero_before_floor` to judge actual attack thresholds, defense thresholds, turns, and expected HP loss. Enemy strength ordering alone is not sufficient.
- Avoid meaningless filler.
- A mini-boss is optional and should not appear unless the economy stage created a suitable role.
- Prefer pocket entrances, offset gaps, route-merge cells, tool-route entries, and shortcut joins over decorative corridor placement.
- If a broken-wall pocket contains high-value reward, place combat or special pressure at the access point, not randomly inside the pocket.
- A monster placement should make the broken wall structure more legible as economy, not merely fill an empty tile.

## Zone And Repulse

Zone (`special: 15`) and repulse (`special: 18`) are topology tools.

- Use them only when damage is inside the policy's redPotion-equivalent range.
- Put them where they affect a real route, reward entrance, shortcut, or key junction.
- Avoid decorative corner specials.
- Avoid unavoidable early special pressure unless the route is compensated.
- A route with special pressure should be shorter, richer, safer in another way, or strategically distinct.
- For every placed zone or repulse enemy, report its affected cells, affected candidate route or reward entrance, and the compensation offered to the player in annotations.
- Place a zone enemy on a wall-constrained route node. With the normal range-1 cross, exactly 2-3 orthogonally affected cells should be effective passable cells, and at least one must belong to a candidate route or reward entrance.
- Place a repulse enemy in a linear corridor. At least one valid approach direction must have an empty retreat cell behind the approaching player, and that retreat cell must connect to at least one continuing path so the approach direction can genuinely alter the monster position or subsequent route.

## Repair

When `repair_feedback` is present:

- Repair only monster/special-owned issues.
- Prefer replacing, strengthening, or moving concrete monsters.
- Do not reconstruct topology or economy.
- Use only the current stage input, current output, structured issue, and downstream hard constraint summary supplied by the orchestrator.

## Output

Return the final full floor wrapper with updated `floor.map` and annotations summarizing monster roles and special-pressure intent.

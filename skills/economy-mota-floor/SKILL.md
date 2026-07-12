---
name: economy-mota-floor
description: Place keys, resources, tools, and pressure intent on a topology-only classic mota-js floor. Use as stage 2 before encounter-mota-floor. This stage never places doors or enemies.
---

# Economy Mota Floor

## Role

Plan what each route rewards. Start from `topology_output`; place keys, resources, and tools, then annotate where downstream route pressure is needed. Do not choose the pressure mechanism.

## Hard Rules

- Return only JSON matching the orchestrator schema.
- Preserve floor id, dimensions, stairs, route structure, and walls.
- Place no doors and no enemies.
- Use only legal supplied tile codes; keep `0` as ground and `1` as wall.
- Add no scripts, events, assets, plugins, or unsupported mechanics.
- Treat non-door values in `floor_contract.resource_limits` as exact quotas.
- Treat the whole-tower remaining budget as a hard ceiling.
- Never change a resource quota to make later door or monster placement easier.

## Economy Quality

- Distribute keys, rewards, and tools across meaningful access regions and route stages.
- Keep the entrance free region clear of naked tools and unprotected high-value clusters.
- Traditional floors target 70%-90% protected important rewards and a 0%-10% resource safety margin.
- Tools must have an acquisition cost or a clear route/reward payoff.
- Higher commitment routes need stronger rewards, shorter access, or another clear advantage.
- Avoid a route that is both cheaper and richer than every alternative.
- Respect `current_floor_policy.resource_progression` and the matching floor progression plan.
- Do not alter walls. If topology cannot support the economy, return the issue to topology.

## Pressure Intent

Use `pressure_intent` for reward entrances, route taxes, shortcuts, chokepoints, or optional deep branches that require later protection. Existing specific kinds such as `combat_chokepoint`, `reward_guard`, `route_tax`, `special_candidate`, and `mini_boss_candidate` are also allowed.

Each annotation must identify concrete coordinates, the protected route or reward, the intended pressure strength, and the compensation. It must not prescribe a door color or concrete enemy.

## Few-Shot And Repair

Use few-shot maps only to learn staged resource access, route compensation, and key distribution. Do not copy tile codes, totals, or mechanics.

When `repair_feedback` is present, repair only economy-owned keys, resources, tools, or pressure intent. Do not place doors or enemies and do not rebuild topology.

## Output

Return the complete floor wrapper with the updated map and annotations. Door quotas remain pending for the encounter stage.

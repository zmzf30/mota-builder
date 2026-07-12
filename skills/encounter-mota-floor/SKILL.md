---
name: encounter-mota-floor
description: Finalize one classic mota-js floor by jointly placing doors, allowed monsters, and special pressure on an economy-stage map. Use as stage 3 after economy-mota-floor.
---

# Encounter Mota Floor

## Role

Turn the economy map's pressure intent into a coherent set of doors, monsters, and supported special abilities. Decide which pressure mechanism best prices each route or reward.

## Hard Rules

- Return only JSON matching the orchestrator schema.
- Preserve floor id, dimensions, stairs, walls, keys, resources, tools, and all other non-ground economy tiles exactly.
- Only replace empty ground with a legal door or an allowed enemy. Never move economy content.
- Place the exact door quotas from `floor_contract.resource_limits`.
- Use only enemy ids/codes from `current_floor_policy` and obey the special whitelist.
- Place the required enemy count, use no more than the allowed enemy types, and never place orthogonally adjacent enemies.
- Keep `0` as ground and `1` as wall. Add no scripts, events, assets, plugins, or unsupported mechanics.
- If the economy layout makes legal doors impossible, return `repair_stage=economy`. If structural positions are insufficient, return `repair_stage=topology`.

## Encounter Quality

- Treat doors, ordinary monsters, threshold monsters, and special monsters as alternative route costs.
- A door must buy reward access, a shortcut, a route change, or a safer combat profile.
- Blue and red doors need stronger compensation than yellow-door baseline routes.
- Every enemy must tax a route, guard value, enforce a threshold, control a shortcut, or create supported special pressure.
- Use the projected hero state to distinguish endurance, attack, defense, balanced, and optional-pressure roles.
- Avoid filler and avoid one route that is both cheaper and richer than all alternatives.
- Realize pressure intent where possible; if an intent is intentionally replaced, preserve its route purpose and compensation.

## Zone And Repulse

- Use zone and repulse only within the configured damage range and on a real route or reward entrance.
- A range-1 zone placement must affect exactly 2-3 effective passable cells on a constrained route node.
- A repulse placement must have a valid retreat cell that continues into another path.
- Annotate affected cells, route effect, and compensation for every special placement.

## Few-Shot And Repair

Use few-shot floors to learn combined door, monster, route-gate, and threshold roles. Do not copy raw stats, codes, or unsupported mechanics.

When repairing, change only doors, enemies, and special-pressure annotations. Never move economy content or reconstruct topology.

## Output

Return the final complete floor wrapper with encounter annotations.

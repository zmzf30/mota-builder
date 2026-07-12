---
name: encounter-red-sea-mota-floor
description: Finalize one red-sea mota-js floor by jointly placing doors, allowed monsters, and special pressure while balancing purposeful regional pressure.
---

# Encounter Red Sea Mota Floor

## Role

Turn the red-sea economy map's pressure intent into doors, monsters, and supported special abilities. Jointly price routes while preserving the dispersed economy.

## Hard Rules

- Require `tower_style=red_sea` and return only schema-valid JSON.
- Preserve floor id, dimensions, stairs, walls, keys, resources, tools, and every non-ground economy tile exactly.
- Only replace empty ground with a legal door or an allowed enemy.
- Place exact door quotas from `floor_contract.resource_limits`.
- Reuse shared enemy stats; style never implies stronger numeric stats.
- Obey enemy pool, count, type, adjacency, special whitelist, and special geometry rules.
- Add no scripts, events, assets, plugins, or unsupported mechanics.
- Route impossible door placement to economy or topology instead of moving existing content.

## Red-Sea Encounter Quality

- Treat doors and monsters as one pressure system: choose the mechanism that best prices each reward, shortcut, threshold, or route commitment.
- Target the configured occupied-non-wall ratio and keep 3x3 macro-zone visual density range within the configured maximum.
- Distribute purposeful pressure across sparse regions before adding more to dense regions.
- Preserve regional variety: different regions may emphasize doors, combat thresholds, specials, tools, or protected rewards.
- Every door and enemy must affect route cost, reward access, a threshold, a shortcut, or supported special pressure.
- Never create density with meaningless filler and never move dispersed resources to balance density.

## Zone And Repulse

- Use supported specials only on real route or reward geometry and within the configured damage range.
- Range-1 zone affects exactly 2-3 effective passable cells on a constrained node.
- Repulse requires a continuing retreat path.
- Annotate affected cells, route effect, and compensation.

## Few-Shot And Repair

Use few-shot floors to learn combined gate, monster, regional pressure, and threshold roles. Do not copy raw stats, tile codes, or unsupported mechanics.

When repairing, change only doors, enemies, and special-pressure annotations. Never move economy content or reconstruct topology.

## Output

Return the final complete floor wrapper with encounter annotations.

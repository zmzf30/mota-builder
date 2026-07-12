---
name: economy-red-sea-mota-floor
description: Place keys, spatially dispersed resources, tools, and pressure intent on a red-sea topology floor. Use as stage 2 before encounter-red-sea-mota-floor. This stage never places doors or enemies.
---

# Economy Red Sea Mota Floor

## Role

Plan the red-sea floor's route rewards. Start from `topology_output`; place keys, resources, and tools, then annotate where downstream pressure is required. Do not choose doors or monsters.

## Hard Rules

- Require `tower_style=red_sea` and return only schema-valid JSON.
- Preserve floor id, dimensions, stairs, topology, and every wall.
- Place no doors and no enemies.
- Use only legal supplied tiles; add no scripts, events, assets, or unsupported mechanics.
- Treat non-door values in `floor_contract.resource_limits` as exact quotas.
- Never move or change resource quotas to solve downstream density.

## Red-Sea Economy

- Distribute each major resource type across distinct access regions when quota permits.
- Keep any one region below 35% of a major resource type unless its cost and floor role clearly justify it.
- Put at most two copies of the same major resource in one small pocket.
- Separate spatial dispersion from access-stage dispersion: use starter, middle, and deep reward bands.
- Protect nearly every valuable reward and every tool through a declared route commitment or pressure intent.
- Keep macro-region reward density reasonably balanced, but give regions different economic roles.
- Keep the entrance free region clear of naked tools and high-value clusters.
- Do not alter walls. Return structural insufficiency to topology.

## Pressure Intent

Use `pressure_intent` or the existing specific pressure annotation kinds. Each annotation must identify concrete coordinates, the protected route or reward, intended pressure strength, and compensation. It must not choose a door color or concrete enemy.

Reserve enough meaningful pressure positions across sparse regions for the encounter stage, without adding decorative annotations.

## Few-Shot And Repair

Use few-shot maps only to learn staged access, resource dispersion, and route compensation. Do not copy codes, totals, or mechanics.

When repairing, change only keys, resources, tools, or pressure intent. Do not place doors or enemies and do not rebuild topology.

## Output

Return the complete floor wrapper with updated map and annotations. Door quotas remain pending for the encounter stage.

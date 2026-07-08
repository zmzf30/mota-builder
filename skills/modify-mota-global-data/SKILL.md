---
name: modify-mota-global-data
description: Implement predesigned tower-wide structure in mota-js project/data.js. Use when Codex needs to apply an already-specified floor count/order, main mechanism, growth curve, floor pacing, key-door-shop-resource structure, boss milestones, initial hero data, shops, level-up rules, values, flags, or project-wide settings. Do not use for designing the tower, route simulation, story/events, custom items/equipment, scripts/plugins, assets/tiles, UI, playtesting, or publishing.
---

# Modify Mota Global Data

## Scope

Use this skill only to implement tower-wide decisions that are already specified by the user or a separate design document.

This skill owns:

- Total floor count and `main.floorIds` order.
- Global main mechanism switches represented by `values`, `flags`, `shops`, `levelUp`, initial status, or other `project/data.js` fields.
- Growth curve implementation: initial hero stats, gem/potion values, level-up rewards, shop costs/rewards, and other global numeric progression.
- Floor pacing metadata: floor ordering, start floor, floor naming conventions when represented globally.
- Key/door/shop/resource structure at the global-rule level, especially starting inventory, shop definitions, and resource value tables.
- Boss milestone metadata when represented in global config or floor ordering.

This skill does not design any of the above. If the user asks for design decisions, ask for concrete values or use the provided design exactly.

Out of scope:

- Single-floor tile placement or coordinate edits; use `modify-mota-map`.
- Enemy stats, rewards, or special abilities; use `modify-mota-enemy-data`.
- Branch routes, loops, side quests, story, dialogue, public events, custom events, scripts, plugins, custom items/equipment, new assets, tile registration, UI customization, route simulation, gameplay validation, playtesting, or publishing.

## Locate Data

Work from the repository root. Prefer `mota-js/project` in this workspace; if a codebase uses `projects/<projectName>`, use the project directory the user requested.

The main file is `project/data.js`, assigned as `var data_<uuid> = { ... }`.

Important top-level areas:

- `main`: floor ids and existing global metadata. Do not register new assets unless explicitly instructed outside this Agent scope.
- `firstData`: title, project name/version, start floor, initial hero status/location/items, shops, level-up rules.
- `values`: numeric rules such as gem/potion values, lava damage, poison damage, movement speed, and floor-change timing.
- `flags`: engine and UI toggles such as status bar items, fly behavior, shop behavior, route folding, and enemy point display.

## Workflow

1. Confirm the request is an implementation request with concrete values. Do not invent a tower plan, balance curve, route, or resource distribution.
2. Identify the exact keys with `rg` before editing. Many concepts appear in more than one area.
3. For total floor count/order, update `main.floorIds`. If the corresponding floor files do not exist, create only minimal default floor files when the request explicitly requires creating floors; otherwise leave point layout to `modify-mota-map`.
4. For starting setup, update `firstData.floorId`, `firstData.hero.loc`, and the relevant `firstData.hero` status fields or inventory fields together.
5. For growth curve implementation, update only global numeric levers such as `firstData.hero`, `values`, `firstData.shops`, and `firstData.levelUp`.
6. For shop/resource structure, preserve the mota-js event action schema. Shop actions are JSON-like objects with `type` fields and often string expressions.
7. For `values` and `flags`, keep existing value types stable unless the requested change explicitly changes behavior. Booleans stay booleans; numbers stay numbers; arrays stay arrays.
8. Do not edit `project/events.js`, `project/items.js`, `project/functions.js`, `project/plugins.js`, `project/icons.js`, `project/maps.js`, asset folders, UI files, or `libs/` for this Agent scope.

## Common Edits

- Rename the game: edit `firstData.title`, `firstData.name`, and optionally `firstData.version`.
- Change initial hero stats: edit `firstData.hero.hp`, `atk`, `def`, `money`, `exp`, keys/items, and `loc`.
- Change gem/potion effects: edit `values.redGem`, `values.blueGem`, `values.greenGem`, and potion values.
- Implement simple shop curves: edit `firstData.shops` choices, `need`, and `action` values.
- Implement level-up curves: edit `firstData.levelUp`.
- Set linear floor progression: edit `main.floorIds`; avoid branch-route metadata unless explicitly provided.

## Handoff Notes

When work requires single-floor tile placement, hand the coordinate list and tile codes to `modify-mota-map`. When work requires monster stat or ability changes, hand the enemy ids and desired fields to `modify-mota-enemy-data`.

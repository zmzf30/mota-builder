---
name: modify-mota-enemy-data
description: Modify monster ability and stat data in mota-js projects. Use when Codex needs to set existing enemies' project/enemys.js hp, atk, def, money, exp, point, special abilities, and related ability fields. Do not use for route balancing, map placement, global data, new assets/tile registration, story/events, scripts/plugins, UI, playtesting, or publishing.
---

# Modify Mota Enemy Data

## Locate Data

Work from the repository root. Prefer `mota-js/project` in this workspace; if a codebase uses `projects/<projectName>`, use the project directory the user requested.

Core files:

- `project/enemys.js`: enemy records keyed by enemy id, for example `"greenSlime": {"name":"绿头怪", ...}`.
- `project/maps.js`: read only to resolve numeric map code to enemy id.
- `project/icons.js`: read only to resolve an existing sprite class if needed.
- `project/floors/*.js`: read only if the user identifies an enemy by map placement.

## Workflow

1. Resolve the enemy id. Search both ids and Chinese display names with `rg` in `project/enemys.js`, `project/maps.js`, `project/icons.js`, and `project/floors`.
2. For stat edits, update only the target object in `project/enemys.js`. Common fields are `name`, `hp`, `atk`, `def`, `money`, `exp`, `point`, and `special`.
3. Preserve unknown or special-dependent fields such as `value`, `damage`, `range`, `repulse`, `zoneSquare`, `atkValue`, `defValue`, `notBomb`, `bigImage`, and `faceIds`.
4. Keep the existing `special` shape unless the requested behavior requires a change. `0` means no special in many sample entries; arrays are used for multiple specials.
5. Do not add new enemy graphics, new map codes, or new icon registrations in this Agent scope. Use existing enemies and existing registered ids.
6. Do not place enemies on maps; point placement belongs to `modify-mota-map`.
7. Do not edit engine files under `libs/`, project scripts, plugins, events, items, assets, or UI.

## Boundary

Use this skill only for explicit monster ability and attribute settings. If the user asks where monsters should be placed, use `modify-mota-map`. If the user asks for growth curve, floor pacing, shop/resource structure, or boss milestone implementation, use `modify-mota-global-data`. Do not perform route simulation or balancing unless the user provides exact target values.

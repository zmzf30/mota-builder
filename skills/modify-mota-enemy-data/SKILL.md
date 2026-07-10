---
name: modify-mota-enemy-data
description: Modify monster ability and stat data in mota-js projects. Use when Codex needs to set existing enemies' project/enemys.js hp, atk, def, money, exp, point, special abilities, and related ability fields, including the code-orchestrated tower pipeline when projected hero bands and enemy-table review feedback are supplied. Do not use for map placement, global data, new assets/tile registration, story/events, scripts/plugins, UI, playtesting, or publishing.
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

## Tower Pipeline Rules

- Use projected hero bands to keep each floor pool in a coherent relative-difficulty band.
- Progress role lanes, not one HP/ATK/DEF staircase. Ordinary core enemies on the same floor must trade attributes; do not make one core enemy at least as high as another in all three stats.
- Every normal floor pool needs a high-HP tank with restrained ATK/DEF and above-median combat rounds, a high-ATK enemy with low HP/DEF and at-most-median combat rounds, and a balanced or defense-threshold enemy.
- When allowed, include a magic attacker below the floor raw-stat median and a zone elite whose HP, ATK, and DEF each reach the floor median. The zone elite is the all-round-strong exception.
- A plain enemy below 35% of its floor median relative difficulty is low-tax. Allow at most one per traditional floor and none on red-sea floors. Red-sea may reuse an id across floors only when it remains in the ordinary difficulty band, not as a carryover role.
- Give first-strike and repulse enemies a clear stat tradeoff; do not stack the strongest HP, ATK, and DEF on them.

## Boundary

Use this skill only for monster ability and attribute settings. In the tower pipeline, use supplied projected hero bands, per-floor numeric analysis, and reviewer feedback to shape a reusable enemy table; do not claim this proves final map balance. If the user asks where monsters should be placed, use `modify-mota-map`. If the user asks for shop/resource structure or map pacing, use `modify-mota-global-data`. Do not perform route simulation.

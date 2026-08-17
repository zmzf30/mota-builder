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

- Build a clear weak-to-strong tier ladder across the complete table so later floor selection has stronger raw-stat options.
- Use the explicit role catalog `high_attack`, `balanced`, `magic`, `zone`, `repulse`, `high_hp`, `gem_gate`, and `strong`.
- Default per-floor candidate slots are high_attack=1, balanced=2-3, magic=1, zone=1, repulse=1,
  high_hp=1, gem_gate=1, and strong=2-3. The concrete map may place a smaller subset.
- Use the user's aggressive contracts: high_attack ATK=5-7A/DEF<=0.1ATK/HP=0.6-1.2ATK;
  balanced ATK=1.8*max(A,D)/DEF=0.3-0.4ATK/HP=2.5-3.5ATK; magic ATK=0.7-0.9A,
  DEF=0.5-0.7D, HP=3-6A; zone ATK=3*max(A,D), DEF=0.3-0.4ATK, HP=5-8A;
  repulse is 0.85-0.95 of its paired zone; high_hp ATK=1.5*max(A,D), DEF=0.45-0.55ATK,
  HP=9-12A; gem_gate DEF=Ac-3, ATK>=1.5*DEF, HP=0.8-1.2A; strong ATK=3-4Ac,
  DEF=0.6-0.8Dc, HP=4-7A and is calibrated by battle simulation.
- Except for magic, never allow monster ATK below the projected hero DEF for that floor.
- `high_attack` may be ordinary or first-strike; `balanced`, `high_hp`, `gem_gate`, and `strong` are
  ordinary by default; `magic`, `zone`, and `repulse` must use their named specials.
- `numeric_score = HP*0.08 + ATK*2 + DEF*2.5` is ordering metadata only, never the core difficulty metric.
- Cross-floor roles are normally high_attack, magic, zone, repulse, and strong. No enemy may appear on
  three consecutive floors; every carried enemy must satisfy `ATK >= current next-floor completion DEF * 1.3`;
  an enemy from the immediately previous floor must not fill the current strong slot.
- A candidate may be temporarily unbeatable for the projected hero on a floor. Do not lower or remove a tier merely to make every candidate killable.
- For red-sea towers, size later stat tiers against the full confirmed prior-floor gem and potion budget. As projected hero ATK/DEF rises, later floor pools must also rise in raw combat strength; do not keep a mostly unchanged weak pool across several floors.
- When an enemy id first enters a red-sea floor candidate pool, require `enemy ATK + DEF >= target projected hero ATK + DEF` for that floor. Later reuse of the same id is exempt from this debut threshold.

## Boundary

Use this skill only for monster ability and attribute settings. In the tower pipeline, use supplied projected hero bands, per-floor numeric analysis, and reviewer feedback to shape a reusable enemy table; do not claim this proves final map balance. If the user asks where monsters should be placed, use `modify-mota-map`. If the user asks for shop/resource structure or map pacing, use `modify-mota-global-data`. Do not perform route simulation.

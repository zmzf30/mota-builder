---
name: modify-mota-map
description: Modify single-floor point data in mota-js projects. Use when Codex needs to edit one point or multiple points in project/floors/*.js, including map array tile ids, stairs/changeFloor at coordinates, and existing coordinate-bound floor data. Do not use for tower-wide design, global data, enemy stats, story/events, scripts/plugins, assets, UI, playtesting, or publishing.
---

# Modify Mota Map

## Locate Data

Work from the repository root. Prefer `mota-js/project` in this workspace; if a codebase uses `projects/<projectName>`, use the project directory the user requested.

Core files:

- `project/floors/<floorId>.js`: one floor per file, assigned as `main.floors.<floorId>= { ... }`.
- `project/data.js`: read only for floor id lookup. Tower-wide floor count/order belongs to `modify-mota-global-data`.
- `project/maps.js`: numeric map code to logical block id, for example `"87": {"cls":"terrains","id":"upFloor"}`.
- `project/icons.js`: read only when tile identity is unclear. Do not register new graphics.

Use `rg --files | rg '/(project|projects)/.*(data|maps|icons|floors)'` if the project root is unclear.

## Workflow

1. Resolve the target floor id from `project/data.js` `main.floorIds`, `project/floors/*.js`, and user wording.
2. Read the target floor file and relevant `project/maps.js` entries before editing. Floor coordinates are zero-based `x,y`; the matrix is indexed as `map[y][x]`.
3. For terrain/item/enemy placement, edit the numeric values in the floor `map` array. Do not guess uncommon tile codes; look them up in `project/maps.js`.
4. For stairs and coordinate-bound system behavior, edit keyed objects such as `changeFloor`, `afterBattle`, `afterGetItem`, `afterOpenDoor`, `cannotMove`, `beforeBattle`, and `cannotMoveIn`. Keep keys exactly as `"x,y"`.
5. Keep `width` and `height` consistent with the `map` dimensions. Each row length must match `width`, and row count must match `height`.
6. Do not create, delete, rename, or reorder floors unless explicitly asked as a map-file operation. Tower-wide floor count/order belongs to `modify-mota-global-data`.
7. Do not add story, dialogue, public events, custom scripts, plugins, assets, or UI. This Agent scope has no event/story layer.

## Common Tile Checks

Typical codes in the bundled sample include:

- `0`: empty/default ground.
- `1`: wall; this is the only allowed wall code for this project's generated tower rules.
- Do not use alternate passable ground codes such as `300`, `311`, `313`, `305`, or `308`, and do not use alternate wall or thin-wall codes such as `2`, `3`, or `301`-`318`.
- `21`, `22`, `23`: yellow, blue, red keys.
- `27`, `28`, `29`: red, blue, green gems.
- `81`, `82`, `83`: yellow, blue, red doors.
- `87`, `88`: up/down stairs.
- `201+`: enemies, mapped through `project/maps.js`.

Always prefer `project/maps.js` over memory when exact ids matter.

## Boundary

Use this skill for "change this tile", "place these enemies/items/doors", "connect this stair", and other explicit point or multi-point edits on one or more floor files. If the request is about overall floor count, growth curve, shops, or global resource structure, use `modify-mota-global-data`. If the request is about enemy hp/atk/def/reward/special ability, use `modify-mota-enemy-data`.

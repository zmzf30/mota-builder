---
name: topology-red-sea-mota-floor
description: Generate only the fragmented, regionally balanced structural topology for one red-sea-style mota-js floor. Use as stage 1 when tower_style is red_sea, before economy and encounter placement. Output no doors, keys, resources, tools, monsters, nets, scripts, or events.
---

# Topology Red Sea Mota Floor

## Role

Act as stage 1 of the red-sea per-floor generator.

Generate the structural shell for exactly one mota-js floor. The output must already be a legal floor object with the requested id, size, stairs, empty required fields, and a map matrix. It is not the final playable floor; later stages will add economy and monsters.

## Real Few-Shot Input

When `few_shot_reference_floors` is present, it is the topology generator's construction set: one generator/reviewer shared anchor plus generator-only examples. Inspect the actual source `map_codes`, project-local `tile_legend`, `topology_map`, compressed `route_graph`, and `candidate_routes` before generating. Transfer route grammar, junction placement, room/corridor scale, and alternative-route relationships. Numeric codes are local to the source project: never copy them into the output. Do not clone a source wall mask cell-for-cell. Reviewer holdouts are intentionally absent; do not guess or optimize for them.

## Hard Rules

- Return only JSON matching the orchestrator schema.
- Use the requested `floor_id`, `floor_index`, and `floor_size`.
- `floor.floorId` must equal `floor_id`.
- `floor.width`, `floor.height`, and every map row must match `floor_size`.
- Use only these map tiles:
  - `0`: the only empty/default passable ground.
  - `1`: the only wall.
  - `downFloor`: exactly one entrance.
  - `upFloor`: exactly one exit.
- Do not place doors, keys, resources, tools, blood nets, enemies, NPCs, overlays, scripts, shops, or story events.
- Keep `events`, `changeFloor`, `afterBattle`, `afterGetItem`, `afterOpenDoor`, `cannotMove`, `autoEvent`, `beforeBattle`, and `cannotMoveIn` empty.
- Keep `bgmap` and `fgmap` empty.
- Do not use alternate ground, grass, thin-wall, white-wall, blue-wall, or other wall terrain codes.

## Topology Quality

- Require `tower_brief.tower_style=red_sea` and follow the supplied red-sea layout contract.
- Create 4-5 meaningful route families and around 16-40 graph-real local opportunities.
- Avoid a single obvious corridor.
- Avoid uncontrolled open grids with too many equivalent loops.
- Avoid thick filler walls, solid padding, pure decoration, and branches that cannot support later cost/reward choices.
- Treat wall ratio 0.40-0.52 as a soft target. Local density balance and downstream capacity are stronger requirements.
- For smaller floors, keep the same idea with less absolute wall count: controlled branches and junctions matter more than decorative density.
- Leave enough empty cells for the economy stage to add doors, keys, rewards, tools, and combat slots.
- Put route junctions and candidate reward rooms where a later door, enemy, or special pressure could matter.
- Prefer broken-but-purposeful short wall groups over clean orthogonal maze bars, thick blocks, or reused floor masks.
- Use offset gaps, small pockets, T/corner wall joins, and short local loops only when they can support later economy.
- A broken wall is valid only if it can change access cost, reward protection, tool value, or route choice.
- Do not satisfy the style-specific opportunity target by annotation count alone. Every annotated junction, pocket, shortcut, reward room, door site, or special-pressure site must correspond to a real structural feature in the map graph.
- Preserve downstream capacity. After stairs and walls, leave enough usable cells for the required non-orthogonally-adjacent enemies, several meaningful door sites, and staged resource placements. Do not create a visually dense topology that later stages can fill only with corridor clutter.

## Regional Density

- Treat the floor as nine spatial macro-zones as well as logical access regions.
- Keep structural density present across the whole floor; do not put nearly all wall boundaries and branches on one side.
- Keep the macro-zone topology density range at or below 0.40 before economy placement, with 0.32 as the final-floor target after objects are placed.
- Do not leave two adjacent macro-zones simultaneously sparse.
- Vary later region roles rather than prescribing the same resource recipe everywhere.

## Fragmentation Contract

Satisfy at least three of the supplied four fragmentation checks:

- At least 18 wall components on a 13x13 floor.
- At least 55% of wall cells belong to wall components of no more than five cells.
- Wall/non-wall adjacency transition ratio is at least 0.43.
- The longest uninterrupted interior wall run is no more than five cells.

Exclude a deliberate outer border from the straight-run intuition, but do not use a border as filler. Build short route segments that turn, branch, and rejoin. Keep non-wall junction share near or above 0.42 without opening an uncontrolled grid.

Every wall fragment must bound a route, create a door or guard site, protect a future reward, create tool value, shape special pressure, or form a meaningful short loop. Random wall confetti fails.

## Annotations

Output an `annotations` array. Each annotation object must include all schema fields.

Use these `kind` values when relevant:

- `candidate_route`
- `junction`
- `region`
- `pocket_candidate`
- `shortcut_candidate`
- `reward_room_candidate`
- `door_candidate`
- `special_pressure_candidate`

Coordinates must be concrete `[x,y]` map coordinates. For route annotations, include the route path coordinates in `coordinates` and put a short description in `description`.

## Repair

When `repair_feedback` is present:

- Repair only topology-owned issues.
- Do not solve economy or monster issues in this stage.
- Keep the returned object complete and schema-valid.
- Use only the current contract, current stage output context, structured issue, and downstream hard constraint summary supplied by the orchestrator.

## Output

Return a complete floor wrapper:

```json
{
  "floor_id": "MT0",
  "floor_index": 0,
  "floor_size": 13,
  "summary": "structural topology only",
  "floor": {
    "floorId": "MT0",
    "title": "主塔 0 层",
    "name": "0",
    "canFlyTo": true,
    "canFlyFrom": true,
    "canUseQuickShop": true,
    "cannotViewMap": false,
    "defaultGround": "ground",
    "images": [],
    "ratio": 1,
    "map": [[0]],
    "firstArrive": [],
    "eachArrive": [],
    "parallelDo": "",
    "events": {},
    "changeFloor": {},
    "afterBattle": {},
    "afterGetItem": {},
    "afterOpenDoor": {},
    "cannotMove": {},
    "bgmap": [],
    "fgmap": [],
    "width": 13,
    "height": 13,
    "autoEvent": {},
    "beforeBattle": {},
    "cannotMoveIn": {}
  },
  "annotations": []
}
```

The example map is a placeholder only.

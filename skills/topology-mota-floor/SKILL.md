---
name: topology-mota-floor
description: Generate only the structural topology for one classic mota-js floor inside the staged floor pipeline. Use after a tower brief and floor contract exist, before economy and monster-special stages. Outputs a complete floor object plus structural annotations, but no doors, keys, resources, tools, monsters, nets, scripts, or events.
---

# Topology Mota Floor

## Role

Act as stage 1 of a staged per-floor Magic Tower generator.

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

- Follow `tower_brief.tower_style` and the supplied layout constraint.
- For `traditional`, create 2-4 meaningful route families and around 6-20 effective decision opportunities. Favor clear regions, legible wall runs, and multiple kinds of branches.
- For `red_sea`, create at least 3 meaningful route families and around 10-40 opportunities. Favor purposeful fragments, narrow routes, and frequent local commitments.
- Avoid a single obvious corridor.
- Avoid uncontrolled open grids with too many equivalent loops.
- Avoid thick filler walls, solid padding, pure decoration, and branches that cannot support later cost/reward choices.
- Use the supplied style-specific wall-ratio target: normally 0.35-0.45 for traditional and 0.45-0.55 for red-sea, unless the user explicitly overrides it.
- For smaller floors, keep the same idea with less absolute wall count: controlled branches and junctions matter more than decorative density.
- Leave enough empty cells for the economy stage to add doors, keys, rewards, tools, and combat slots.
- Put route junctions and candidate reward rooms where a later door, enemy, or special pressure could matter.
- In traditional style, clean wall runs and clear regions are valid. In red-sea style, prefer broken-but-purposeful wall fragments over clean orthogonal maze bars or reused floor masks.
- Use offset gaps, small pockets, T/corner wall joins, and short local loops only when they can support later economy.
- A broken wall is valid only if it can change access cost, reward protection, tool value, or route choice.
- Do not satisfy the style-specific opportunity target by annotation count alone. Every annotated junction, pocket, shortcut, reward room, door site, or special-pressure site must correspond to a real structural feature in the map graph.
- Preserve downstream capacity. After stairs and walls, leave enough usable cells for the required non-orthogonally-adjacent enemies, several meaningful door sites, and staged resource placements. Do not create a visually dense topology that later stages can fill only with corridor clutter.

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

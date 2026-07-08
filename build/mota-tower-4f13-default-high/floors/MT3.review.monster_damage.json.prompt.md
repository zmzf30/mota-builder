Read and follow this skill file first:
        /Users/kanyun/workspace/learn/mota/skills/review-mota-floor/SKILL.md

        You are a specialist reviewer inside a split-review pipeline. Return only JSON matching
        the provided schema. Set status to fail for material issues in your specialist scope.
        Do not approve by relying on another reviewer to catch your scope.
        Do not fail the final floor for a missing win/final-completion event in floor_output.events:
        the orchestrator adds the final win event automatically in write_generated_project() after
        floor review passes, because the floor-generation schema keeps events empty.

        Specialist scope:

Focus only on monster stats, combat pacing, and zone/repulse damage.

Use the current enemy catalog and the tower brief's redPotion value. Judge monster cost qualitatively:
some monsters can be threshold checks, but a route must not rely on impossible early fights or
on enemies that are trivially avoidable filler.

For zone/repulse:
- Damage should normally matter relative to a redPotion, roughly a fraction of one redPotion.
- Very small special damage is decorative; unavoidable high special damage needs strong compensation.
- A special enemy must affect a real route or protected reward, not just sit near a corner.

Positive calibration anchors:
- 红蓝的记忆2.10 / MT1 and MT4: zone enemies tax route/reward decisions instead of sitting decoratively.
- dist / MT1-MT2 and Oblivion 2.10 / MT1: repulse enemies affect movement near corridors, rewards, or mechanism gates.
- 剑阁2.9 / MT3 and MT6: combat profiles vary across branches and protect different reward types.

Fail when:
- Important route monsters are impossible or absurdly expensive for likely hero state.
- Many placed monsters are zero/near-zero damage filler after naked resource collection.
- Zone/repulse damage is decorative, all avoidable, or not compensated by route/reward tradeoff.
- Monster profiles collapse into one repeated role or lack meaningful pacing across the floor.

Feedback detail requirement:
- Cite exact monster coordinates from enemy_tiles or min_route_to_exit.cost_tiles.
- For weak monsters, say whether to strengthen stats, replace with a higher-tier enemy, or move the
  monster onto a real chokepoint.
- For special monsters, cite the monster coordinate and the affected/avoided route segment.

Return budget_delta as all zeros; the orchestrator will replace it.


        Allowed tile codes:
0: empty/default passable ground (the only allowed ground code)
1: animates.yellowWall (the only allowed wall code)
11: animates.lavaNet
12: animates.poisonNet
13: animates.weakNet
14: animates.curseNet
21: items.yellowKey
22: items.blueKey
23: items.redKey
27: items.redGem
28: items.blueGem
29: items.greenGem
30: items.yellowGem
31: items.redPotion
32: items.bluePotion
33: items.greenPotion
34: items.yellowPotion
47: items.pickaxe
49: items.bomb
50: items.centerFly
56: items.superPotion
81: animates.yellowDoor
82: animates.blueDoor
83: animates.redDoor
84: animates.greenDoor
85: animates.specialDoor
86: animates.steelDoor
87: terrains.upFloor
88: terrains.downFloor
319: npc48.tallYellowDoor
320: npc48.tallBlueDoor
321: npc48.tallRedDoor
322: npc48.tallGreenDoor
323: npc48.tallSpecialDoor
324: npc48.tallSteelDoor

Allowed enemy tile codes with current stats:
204: slimelord 怪王 hp=85 atk=30 def=6 money=5 special=0
206: bigBat 大蝙蝠 hp=70 atk=36 def=6 money=6 special=[1]
211: skeletonCaptain 骷髅队长 hp=78 atk=38 def=7 money=6 special=[1]
214: zombieKnight 兽人武士 hp=150 atk=34 def=18 money=8 special=[3]
218: redPriest 高级法师 hp=70 atk=28 def=5 money=5 special=[2]

        Input JSON:
        {
  "tower_brief": {
    "status": "ready",
    "summary": "Build a 4-floor 13x13 traditional mota-js tower using floor IDs MT0-MT3. Use only existing mota-js/project defaults, assets, item/enemy definitions, and runtime. No floor maps are generated in this stage. The tower is classic, high-pressure, combat-heavy, key-door/resource-choice driven, with no NPCs, mechanisms, story, dark walls, shops, bombs, plugins, new assets, or runtime changes. Only stair floor changes and the final win event are allowed.",
    "floor_count": 4,
    "floor_size": 13,
    "fixed_rules": [
      "13x13 floors",
      "floor IDs must be MT0, MT1, MT2, MT3",
      "do not generate floor maps in stage 0",
      "use current mota-js/project default JS global data and existing assets only",
      "do not add assets, plugins, runtime code, or custom systems",
      "terrain may use only tile code 0 for ground and tile code 1 for walls",
      "no NPCs, mechanisms, story events, scripted events, dark walls, or shops",
      "only stair-based floor transitions and one final completion event are allowed",
      "no green gems, yellow gems, yellow potions, green potions, or bombs may be placed",
      "exact whole-tower placed resources: redGem=22, blueGem=22, greenGem=0, yellowGem=0, redPotion=25, bluePotion=8, pickaxe=3, centerFly=2, bomb=0",
      "per-floor exact resource quotas: MT0 redGem=4 blueGem=4 redPotion=6 bluePotion=2 pickaxe=1 centerFly=0",
      "per-floor exact resource quotas: MT1 redGem=5 blueGem=5 redPotion=6 bluePotion=2 pickaxe=1 centerFly=1",
      "per-floor exact resource quotas: MT2 redGem=6 blueGem=6 redPotion=6 bluePotion=2 pickaxe=1 centerFly=0",
      "per-floor exact resource quotas: MT3 redGem=7 blueGem=7 redPotion=7 bluePotion=2 pickaxe=0 centerFly=1",
      "traditional clear structure with distinct branches, high monster pressure, key-door pressure, and meaningful resource choices",
      "passability is not required to be guaranteed by the brief"
    ],
    "global_limits": {
      "yellow_doors": "high pressure density; exact count allocated by floor stage using existing yellowDoor only",
      "blue_doors": "moderate-to-high pressure density; exact count allocated by floor stage using existing blueDoor only",
      "red_doors": "low but meaningful pressure density; exact count allocated by floor stage using existing redDoor only",
      "yellow_keys": "scarce relative to yellow doors; exact count allocated by floor stage",
      "blue_keys": "scarce relative to blue doors; exact count allocated by floor stage",
      "red_keys": "very scarce relative to red doors; exact count allocated by floor stage",
      "pickaxes": 3,
      "bombs": 0,
      "centerFly": 2
    },
    "global_settings": {
      "initial_hero": {
        "hp": 300,
        "atk": 10,
        "def": 10,
        "money": 0,
        "keys": {
          "yellow": 1,
          "blue": 0,
          "red": 0
        }
      },
      "gems": {
        "redGem": 1,
        "blueGem": 1,
        "greenGem": 5
      },
      "potions": {
        "redPotion": 80,
        "bluePotion": 200,
        "yellowPotion": 500,
        "greenPotion": 800
      },
      "shop": {
        "enabled": false,
        "rule": "No shop placement or shop events; existing default shop data remains unused.",
        "atk_gain": null,
        "def_gain": null
      }
    },
    "monster_policy": {
      "allowed_specials": [
        1,
        2,
        3,
        15,
        18
      ],
      "max_specials_per_monster": 1,
      "min_no_special_ratio": 0.5,
      "monster_types_per_floor": 9,
      "floor_overlap_ratio": 0.7,
      "special_damage_red_potion_min": 0.5,
      "special_damage_red_potion_max": 1,
      "no_adjacent_enemies": true
    },
    "resource_policy": {
      "gem_floor_delta_min": 2,
      "gem_floor_delta_max": 2,
      "potion_floor_delta_min": 0,
      "potion_floor_delta_max": 1,
      "potion_compare_mode": "red_potion_equiv; exact placed resources: redGem/blueGem MT0=4/4, MT1=5/5, MT2=6/6, MT3=7/7; redPotion counts 6/6/6/7; bluePotion counts 2 per floor; pickaxe on MT0/MT1/MT2 only; centerFly on MT1/MT3 only"
    },
    "layout_policy": [
      "13x13 square floors with traditional mota structure and distinct branches",
      "avoid large empty areas and repeated wall padding",
      "avoid exposed high-value resource piles without monster, door, or path cost",
      "place stairs to create clear vertical progression MT0 to MT3",
      "use pickaxes to create optional wall-breaking route choices, not mandatory script mechanics",
      "place centerFly only where center symmetry creates meaningful optional routing",
      "maintain high monster density but do not orthogonally adjacent enemy tiles",
      "resource access should usually require combat, door spending, or route commitment",
      "final floor MT3 contains the only final completion event"
    ],
    "questions": [],
    "confirmation_prompt": "Confirm this whole-tower brief before floor generation."
  },
  "floor_output": {
    "floor_id": "MT3",
    "floor_index": 3,
    "floor_size": 13,
    "summary": "MT3 is a compact final floor with a repaired central finish and two pressured side routes: slimelords satisfy no-special density but are paired with blue/yellow doors or stronger chokepoints, while zombieKnight and skeletonCaptain guards break the former easy gem-region links. Exact MT3 gem, potion, key, and centerFly quotas are preserved with the final win event on the up stair.",
    "floor": {
      "floorId": "MT3",
      "title": "主塔 3 层",
      "name": "3",
      "canFlyTo": true,
      "canFlyFrom": true,
      "canUseQuickShop": false,
      "cannotViewMap": false,
      "defaultGround": "ground",
      "images": [],
      "ratio": 1,
      "width": 13,
      "height": 13,
      "map": [
        [
          1,
          1,
          1,
          1,
          1,
          1,
          1,
          1,
          1,
          1,
          1,
          1,
          1
        ],
        [
          1,
          1,
          1,
          1,
          1,
          1,
          87,
          1,
          1,
          1,
          1,
          1,
          1
        ],
        [
          1,
          31,
          1,
          1,
          1,
          1,
          83,
          1,
          1,
          1,
          1,
          1,
          1
        ],
        [
          1,
          27,
          1,
          1,
          1,
          1,
          214,
          1,
          1,
          1,
          1,
          1,
          1
        ],
        [
          1,
          211,
          1,
          1,
          27,
          204,
          23,
          211,
          27,
          214,
          28,
          32,
          1
        ],
        [
          1,
          28,
          1,
          1,
          204,
          1,
          204,
          1,
          0,
          1,
          1,
          1,
          1
        ],
        [
          1,
          0,
          21,
          27,
          81,
          204,
          50,
          204,
          28,
          214,
          31,
          81,
          1
        ],
        [
          1,
          204,
          1,
          1,
          31,
          1,
          218,
          1,
          1,
          1,
          21,
          204,
          1
        ],
        [
          1,
          82,
          32,
          22,
          1,
          27,
          82,
          28,
          1,
          28,
          214,
          27,
          1
        ],
        [
          1,
          1,
          1,
          204,
          1,
          1,
          211,
          1,
          1,
          204,
          1,
          1,
          1
        ],
        [
          1,
          27,
          81,
          31,
          81,
          21,
          0,
          204,
          22,
          82,
          214,
          28,
          1
        ],
        [
          1,
          31,
          1,
          1,
          1,
          1,
          211,
          1,
          31,
          1,
          28,
          31,
          1
        ],
        [
          1,
          1,
          1,
          1,
          1,
          1,
          88,
          1,
          1,
          1,
          1,
          1,
          1
        ]
      ],
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
      "autoEvent": {},
      "beforeBattle": {},
      "cannotMoveIn": {}
    }
  },
  "floor_size": 13,
  "current_floor_policy": {
    "allowed_enemy_ids": [
      "slimelord",
      "redPriest",
      "bigBat",
      "skeletonCaptain",
      "zombieKnight"
    ],
    "allowed_enemy_codes": [
      204,
      218,
      206,
      211,
      214
    ],
    "enemy_role_hints": {
      "slimelord": "balanced combat",
      "redPriest": "balanced combat",
      "bigBat": "balanced combat",
      "skeletonCaptain": "balanced combat",
      "zombieKnight": "defense threshold"
    },
    "fallback_no_special_enemy_ids": [],
    "no_adjacent_enemies": true,
    "enemy_adjacency": "orthogonal",
    "special_damage_red_potion_range": [
      0.5,
      1.0
    ],
    "resource_progression": {
      "gem_floor_delta_min": 2.0,
      "gem_floor_delta_max": 2.0,
      "potion_floor_delta_min": 0.0,
      "potion_floor_delta_max": 1.0,
      "potion_compare_mode": "red_potion_equiv; exact placed resources: redGem/blueGem MT0=4/4, MT1=5/5, MT2=6/6, MT3=7/7; redPotion counts 6/6/6/7; bluePotion counts 2 per floor; pickaxe on MT0/MT1/MT2 only; centerFly on MT1/MT3 only",
      "previous_floor": {
        "gem_count": 12.0,
        "potion_red_equiv": 11.0
      },
      "allowed_current": {
        "gem_count": [
          14.0,
          14.0
        ],
        "potion_red_equiv": [
          11.0,
          12.0
        ]
      }
    }
  },
  "used_budget_so_far": {
    "yellow_doors": 25,
    "blue_doors": 6,
    "red_doors": 0,
    "yellow_keys": 10,
    "blue_keys": 5,
    "red_keys": 0,
    "pickaxes": 3,
    "bombs": 0,
    "centerFly": 1
  },
  "remaining_whole_tower_budget": {
    "yellow_doors": null,
    "blue_doors": null,
    "red_doors": null,
    "yellow_keys": null,
    "blue_keys": null,
    "red_keys": null,
    "pickaxes": 0,
    "bombs": 0,
    "centerFly": 1
  },
  "previous_accepted_floor_summaries": [
    {
      "floor_id": "MT0",
      "floor_size": 13,
      "summary": "MT0 uses three gated routes from the entrance to the exit: a direct central combat route, a left yellow-door combat/reward route, and a stronger right blue-door route with the pickaxe pocket. Early key refunds and lower-center reward exposure are split into deeper guarded branches while preserving exact MT0 resource quotas.",
      "budget_delta": {
        "yellow_doors": 6,
        "blue_doors": 1,
        "red_doors": 0,
        "yellow_keys": 3,
        "blue_keys": 1,
        "red_keys": 0,
        "pickaxes": 1,
        "bombs": 0,
        "centerFly": 0
      },
      "resumed": true
    },
    {
      "floor_id": "MT1",
      "floor_size": 13,
      "summary": "MT1 uses three compact gated routes from the lower entrance: a central combat route, a left blue-door reward pocket, and a stronger upper-right blue-door package with centerFly and pickaxe, while splitting the previous low-cost lower resource cluster into guarded pockets.",
      "budget_delta": {
        "yellow_doors": 11,
        "blue_doors": 3,
        "red_doors": 0,
        "yellow_keys": 4,
        "blue_keys": 2,
        "red_keys": 0,
        "pickaxes": 1,
        "bombs": 0,
        "centerFly": 1
      },
      "resumed": true
    },
    {
      "floor_id": "MT2",
      "floor_size": 13,
      "summary": "MT2 is rebuilt as three separated pressured routes: a combat-heavy center line, a yellow-door left route with staged key/resource pockets, and a blue-door right route protecting the pickaxe and stronger rewards. Exact MT2 gem, potion, and tool quotas are preserved with no exposed entrance cluster.",
      "budget_delta": {
        "yellow_doors": 8,
        "blue_doors": 2,
        "red_doors": 0,
        "yellow_keys": 3,
        "blue_keys": 2,
        "red_keys": 0,
        "pickaxes": 1,
        "bombs": 0,
        "centerFly": 0
      },
      "resumed": true
    }
  ],
  "static_metrics": {
    "available": true,
    "width": 13,
    "height": 13,
    "wall_ratio": 0.627,
    "wall_count": 106,
    "non_wall_cells": 63,
    "enemy_count": 20,
    "door_count": 8,
    "monster_density_non_wall": 0.317,
    "components_non_wall": 1,
    "main_component_cells": 63,
    "main_cycle_rank": 7,
    "main_cycle_rank_ratio": 0.111,
    "resource_weight_total": 37.0,
    "tool_count": 1,
    "free_region_cells": 1,
    "free_region_bbox": [
      [
        6,
        12
      ],
      [
        6,
        12
      ]
    ],
    "free_region_reaches_exit": false,
    "free_region_resource_count": 0,
    "free_region_resource_weight": 0.0,
    "free_region_resources": [],
    "free_region_tools": [],
    "free_region_keys": [],
    "approx_resource_weight_by_access_cost": {
      "0": 0.0,
      "1": 1.0,
      "2": 4.0,
      "3": 32.0
    },
    "lowest_cost_resources": [
      {
        "id": "yellowKey",
        "coord": [
          5,
          10
        ],
        "approx_cost": 1.0,
        "weight": 1.0
      },
      {
        "id": "redPotion",
        "coord": [
          3,
          10
        ],
        "approx_cost": 2.0,
        "weight": 1.0
      },
      {
        "id": "blueKey",
        "coord": [
          8,
          10
        ],
        "approx_cost": 2.0,
        "weight": 2.0
      },
      {
        "id": "redPotion",
        "coord": [
          8,
          11
        ],
        "approx_cost": 2.0,
        "weight": 1.0
      },
      {
        "id": "bluePotion",
        "coord": [
          2,
          8
        ],
        "approx_cost": 3.0,
        "weight": 2.5
      },
      {
        "id": "blueKey",
        "coord": [
          3,
          8
        ],
        "approx_cost": 3.0,
        "weight": 2.0
      },
      {
        "id": "redGem",
        "coord": [
          1,
          10
        ],
        "approx_cost": 3.0,
        "weight": 1.0
      },
      {
        "id": "redPotion",
        "coord": [
          1,
          11
        ],
        "approx_cost": 3.0,
        "weight": 1.0
      },
      {
        "id": "redGem",
        "coord": [
          5,
          8
        ],
        "approx_cost": 4.0,
        "weight": 1.0
      },
      {
        "id": "blueGem",
        "coord": [
          7,
          8
        ],
        "approx_cost": 4.0,
        "weight": 1.0
      },
      {
        "id": "centerFly",
        "coord": [
          6,
          6
        ],
        "approx_cost": 5.0,
        "weight": 0.0
      },
      {
        "id": "blueGem",
        "coord": [
          9,
          8
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "blueGem",
        "coord": [
          11,
          10
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "blueGem",
        "coord": [
          10,
          11
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "redPotion",
        "coord": [
          11,
          11
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "redKey",
        "coord": [
          6,
          4
        ],
        "approx_cost": 6.0,
        "weight": 4.0
      },
      {
        "id": "redGem",
        "coord": [
          8,
          4
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "blueGem",
        "coord": [
          1,
          5
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "yellowKey",
        "coord": [
          2,
          6
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "redGem",
        "coord": [
          3,
          6
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      }
    ],
    "low_cost_resource_clusters": [
      {
        "threshold_cost": 1.0,
        "bbox": [
          [
            5,
            10
          ],
          [
            6,
            12
          ]
        ],
        "cells": 4,
        "resource_weight": 1.0,
        "resources": [
          {
            "id": "yellowKey",
            "coord": [
              5,
              10
            ],
            "weight": 1.0
          }
        ],
        "tools": []
      },
      {
        "threshold_cost": 2.0,
        "bbox": [
          [
            3,
            9
          ],
          [
            8,
            12
          ]
        ],
        "cells": 10,
        "resource_weight": 5.0,
        "resources": [
          {
            "id": "redPotion",
            "coord": [
              3,
              10
            ],
            "weight": 1.0
          },
          {
            "id": "yellowKey",
            "coord": [
              5,
              10
            ],
            "weight": 1.0
          },
          {
            "id": "blueKey",
            "coord": [
              8,
              10
            ],
            "weight": 2.0
          },
          {
            "id": "redPotion",
            "coord": [
              8,
              11
            ],
            "weight": 1.0
          }
        ],
        "tools": []
      }
    ],
    "suggested_relocation_cells": [
      {
        "coord": [
          8,
          5
        ],
        "approx_cost": 6.0
      },
      {
        "coord": [
          1,
          6
        ],
        "approx_cost": 6.0
      }
    ],
    "open_junction_wall_candidates": [
      {
        "coord": [
          6,
          10
        ],
        "degree": 4
      },
      {
        "coord": [
          1,
          6
        ],
        "degree": 3
      }
    ],
    "enemy_tiles": [
      {
        "id": "zombieKnight",
        "code": 214,
        "coord": [
          6,
          3
        ],
        "hp": 150,
        "atk": 34,
        "def": 18,
        "special": [
          3
        ]
      },
      {
        "id": "skeletonCaptain",
        "code": 211,
        "coord": [
          1,
          4
        ],
        "hp": 78,
        "atk": 38,
        "def": 7,
        "special": [
          1
        ]
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          5,
          4
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "skeletonCaptain",
        "code": 211,
        "coord": [
          7,
          4
        ],
        "hp": 78,
        "atk": 38,
        "def": 7,
        "special": [
          1
        ]
      },
      {
        "id": "zombieKnight",
        "code": 214,
        "coord": [
          9,
          4
        ],
        "hp": 150,
        "atk": 34,
        "def": 18,
        "special": [
          3
        ]
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          4,
          5
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          6,
          5
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          5,
          6
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          7,
          6
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "zombieKnight",
        "code": 214,
        "coord": [
          9,
          6
        ],
        "hp": 150,
        "atk": 34,
        "def": 18,
        "special": [
          3
        ]
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          1,
          7
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "redPriest",
        "code": 218,
        "coord": [
          6,
          7
        ],
        "hp": 70,
        "atk": 28,
        "def": 5,
        "special": [
          2
        ]
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          11,
          7
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "zombieKnight",
        "code": 214,
        "coord": [
          10,
          8
        ],
        "hp": 150,
        "atk": 34,
        "def": 18,
        "special": [
          3
        ]
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          3,
          9
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "skeletonCaptain",
        "code": 211,
        "coord": [
          6,
          9
        ],
        "hp": 78,
        "atk": 38,
        "def": 7,
        "special": [
          1
        ]
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          9,
          9
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          7,
          10
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "zombieKnight",
        "code": 214,
        "coord": [
          10,
          10
        ],
        "hp": 150,
        "atk": 34,
        "def": 18,
        "special": [
          3
        ]
      },
      {
        "id": "skeletonCaptain",
        "code": 211,
        "coord": [
          6,
          11
        ],
        "hp": 78,
        "atk": 38,
        "def": 7,
        "special": [
          1
        ]
      }
    ],
    "min_route_to_exit": {
      "enemy_count": 5,
      "door_cost": 6.0,
      "special_red_potion_equiv": 0.0,
      "total_cost_proxy": 11.0,
      "steps": 11,
      "cost_tiles": [
        {
          "id": "skeletonCaptain",
          "coord": [
            6,
            11
          ],
          "code": 211
        },
        {
          "id": "skeletonCaptain",
          "coord": [
            6,
            9
          ],
          "code": 211
        },
        {
          "id": "blueDoor",
          "coord": [
            6,
            8
          ],
          "code": 82
        },
        {
          "id": "redPriest",
          "coord": [
            6,
            7
          ],
          "code": 218
        },
        {
          "id": "slimelord",
          "coord": [
            6,
            5
          ],
          "code": 204
        },
        {
          "id": "redKey",
          "coord": [
            6,
            4
          ],
          "code": 23
        },
        {
          "id": "zombieKnight",
          "coord": [
            6,
            3
          ],
          "code": 214
        },
        {
          "id": "redDoor",
          "coord": [
            6,
            2
          ],
          "code": 83
        }
      ]
    },
    "special_sources": [],
    "special_affected_cells": 0,
    "special_can_be_fully_avoided": null,
    "red_potion_value": 80.0
  },
  "reviewer": "monster_damage"
}

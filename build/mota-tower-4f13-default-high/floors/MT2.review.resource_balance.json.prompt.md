Read and follow this skill file first:
        /Users/kanyun/workspace/learn/mota/skills/review-mota-floor/SKILL.md

        You are a specialist reviewer inside a split-review pipeline. Return only JSON matching
        the provided schema. Set status to fail for material issues in your specialist scope.
        Do not approve by relying on another reviewer to catch your scope.

        Specialist scope:

Focus only on resource access, low-cost resource clusters, key-door economics, and tool protection.

Important cost calibration:
- Yellow-key/ yellow-door cost is the low-cost baseline: roughly 1.
- Monster cost is not mechanically 1. Make a simple qualitative estimate from enemy stats,
  floor position, likely hero state, and nearby rewards.
- Blue doors and wall-breaking access are usually more expensive than yellow doors and must connect
  to stronger rewards, better shortcuts, or meaningful strategic access.
- Script access-cost metrics are hints for early/low-cost exposure, not a substitute for design judgment.

Positive calibration anchors:
- 红蓝的记忆2.10 / MT6: staged resources and tools with low free-region exposure.
- 一层小塔 2.10 / MT0: compact single-floor economy with meaningful key/resource pressure.
- 剑阁2.9 / MT3: side rewards are protected by route cost instead of exposed as naked piles.
- 出塞 / MT0-MT2 and 星月神话 / MT7-MT8: tool or blood-net routes should have compensation.

Fail when:
- The entrance/free region exposes too many resources, tools, or strong keys.
- A large resource cluster is connected through too little battle, door, wall, or special pressure.
- A blue door or tool route does not unlock a benefit larger than a yellow-door baseline route.
- Tools are naked, early, or usable mainly to bypass the intended structure.
- Keys/tools are bunched in one region rather than reasonably distributed across route stages.

Feedback detail requirement:
- For every low-cost cluster issue, cite the bbox from low_cost_resource_clusters, for example
  "bbox [6,6]->[9,12]", and list the main resource/tool coordinates.
- Suggest moving specific resources/tools to coordinates from suggested_relocation_cells, or suggest
  adding a specific door/monster/wall before the cluster.
- For blue-door/tool issues, cite the door/tool coordinate and state the stronger reward/shortcut it
  should unlock.

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
205: bat 小蝙蝠 hp=42 atk=24 def=4 money=3 special=0
206: bigBat 大蝙蝠 hp=70 atk=36 def=6 money=6 special=[1]
209: skeleton 骷髅人 hp=65 atk=28 def=5 money=4 special=0
213: zombie 兽人 hp=90 atk=25 def=9 money=4 special=0
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
    "floor_id": "MT2",
    "floor_index": 2,
    "floor_size": 13,
    "summary": "MT2 is rebuilt as three separated pressured routes: a combat-heavy center line, a yellow-door left route with staged key/resource pockets, and a blue-door right route protecting the pickaxe and stronger rewards. Exact MT2 gem, potion, and tool quotas are preserved with no exposed entrance cluster.",
    "floor": {
      "floorId": "MT2",
      "title": "Main Tower 2F",
      "name": "2",
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
          205,
          0,
          1,
          1,
          0,
          1,
          1,
          0,
          209,
          28,
          1
        ],
        [
          1,
          1,
          1,
          21,
          0,
          209,
          0,
          206,
          0,
          31,
          1,
          1,
          1
        ],
        [
          1,
          27,
          205,
          28,
          1,
          27,
          204,
          31,
          1,
          27,
          1,
          32,
          1
        ],
        [
          1,
          1,
          1,
          213,
          1,
          1,
          81,
          1,
          1,
          204,
          81,
          0,
          1
        ],
        [
          1,
          1,
          1,
          22,
          1,
          1,
          206,
          1,
          1,
          22,
          1,
          28,
          1
        ],
        [
          1,
          28,
          81,
          0,
          1,
          1,
          0,
          27,
          1,
          82,
          1,
          1,
          1
        ],
        [
          1,
          31,
          1,
          209,
          1,
          1,
          218,
          1,
          1,
          0,
          1,
          27,
          1
        ],
        [
          1,
          1,
          1,
          81,
          1,
          1,
          0,
          1,
          1,
          205,
          81,
          21,
          1
        ],
        [
          1,
          1,
          1,
          0,
          21,
          1,
          205,
          1,
          1,
          0,
          1,
          1,
          1
        ],
        [
          1,
          32,
          81,
          218,
          0,
          81,
          0,
          82,
          28,
          204,
          81,
          47,
          1
        ],
        [
          1,
          28,
          1,
          31,
          1,
          1,
          209,
          1,
          1,
          27,
          1,
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
      "bat",
      "skeleton",
      "zombie",
      "slimelord",
      "redPriest",
      "bigBat"
    ],
    "allowed_enemy_codes": [
      205,
      209,
      213,
      204,
      218,
      206
    ],
    "enemy_role_hints": {
      "bat": "balanced combat",
      "skeleton": "balanced combat",
      "zombie": "balanced combat",
      "slimelord": "balanced combat",
      "redPriest": "balanced combat",
      "bigBat": "balanced combat"
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
        "gem_count": 10.0,
        "potion_red_equiv": 11.0
      },
      "allowed_current": {
        "gem_count": [
          12.0,
          12.0
        ],
        "potion_red_equiv": [
          11.0,
          12.0
        ]
      }
    }
  },
  "used_budget_so_far": {
    "yellow_doors": 17,
    "blue_doors": 4,
    "red_doors": 0,
    "yellow_keys": 7,
    "blue_keys": 3,
    "red_keys": 0,
    "pickaxes": 2,
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
    "pickaxes": 1,
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
      "playtest": {
        "status": "skipped",
        "summary": "1055/1056 already served another process; skipped to avoid playtesting the wrong project.",
        "issues": [
          "Stop the existing local mota-js server or run without --project-dir to test that server."
        ]
      }
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
      "playtest": {
        "status": "skipped",
        "summary": "1055/1056 already served another process; skipped to avoid playtesting the wrong project.",
        "issues": [
          "Stop the existing local mota-js server or run without --project-dir to test that server."
        ]
      }
    }
  ],
  "static_metrics": {
    "available": true,
    "width": 13,
    "height": 13,
    "wall_ratio": 0.592,
    "wall_count": 100,
    "non_wall_cells": 69,
    "enemy_count": 16,
    "door_count": 10,
    "monster_density_non_wall": 0.232,
    "components_non_wall": 1,
    "main_component_cells": 69,
    "main_cycle_rank": 5,
    "main_cycle_rank_ratio": 0.072,
    "resource_weight_total": 30.0,
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
      "1": 0.0,
      "2": 1.0,
      "3": 29.0
    },
    "lowest_cost_resources": [
      {
        "id": "yellowKey",
        "coord": [
          4,
          9
        ],
        "approx_cost": 2.0,
        "weight": 1.0
      },
      {
        "id": "redGem",
        "coord": [
          7,
          6
        ],
        "approx_cost": 3.0,
        "weight": 1.0
      },
      {
        "id": "blueGem",
        "coord": [
          8,
          10
        ],
        "approx_cost": 3.0,
        "weight": 1.0
      },
      {
        "id": "redPotion",
        "coord": [
          3,
          11
        ],
        "approx_cost": 3.0,
        "weight": 1.0
      },
      {
        "id": "blueKey",
        "coord": [
          3,
          5
        ],
        "approx_cost": 4.0,
        "weight": 2.0
      },
      {
        "id": "bluePotion",
        "coord": [
          1,
          10
        ],
        "approx_cost": 4.0,
        "weight": 2.5
      },
      {
        "id": "blueGem",
        "coord": [
          1,
          11
        ],
        "approx_cost": 4.0,
        "weight": 1.0
      },
      {
        "id": "redGem",
        "coord": [
          9,
          11
        ],
        "approx_cost": 4.0,
        "weight": 1.0
      },
      {
        "id": "yellowKey",
        "coord": [
          3,
          2
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "blueGem",
        "coord": [
          3,
          3
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "blueGem",
        "coord": [
          1,
          6
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "redPotion",
        "coord": [
          1,
          7
        ],
        "approx_cost": 5.0,
        "weight": 1.0
      },
      {
        "id": "pickaxe",
        "coord": [
          11,
          10
        ],
        "approx_cost": 5.0,
        "weight": 0.0
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
        "id": "redPotion",
        "coord": [
          1,
          1
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "redGem",
        "coord": [
          1,
          3
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "redGem",
        "coord": [
          5,
          3
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "redPotion",
        "coord": [
          7,
          3
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "redGem",
        "coord": [
          11,
          7
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      },
      {
        "id": "yellowKey",
        "coord": [
          11,
          8
        ],
        "approx_cost": 6.0,
        "weight": 1.0
      }
    ],
    "low_cost_resource_clusters": [
      {
        "threshold_cost": 2.0,
        "bbox": [
          [
            3,
            8
          ],
          [
            6,
            12
          ]
        ],
        "cells": 9,
        "resource_weight": 1.0,
        "resources": [
          {
            "id": "yellowKey",
            "coord": [
              4,
              9
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
          11,
          4
        ],
        "approx_cost": 9.0
      },
      {
        "coord": [
          9,
          1
        ],
        "approx_cost": 7.0
      },
      {
        "coord": [
          8,
          2
        ],
        "approx_cost": 7.0
      },
      {
        "coord": [
          6,
          1
        ],
        "approx_cost": 6.0
      },
      {
        "coord": [
          6,
          2
        ],
        "approx_cost": 6.0
      },
      {
        "coord": [
          3,
          1
        ],
        "approx_cost": 5.0
      },
      {
        "coord": [
          4,
          2
        ],
        "approx_cost": 5.0
      },
      {
        "coord": [
          9,
          7
        ],
        "approx_cost": 5.0
      },
      {
        "coord": [
          3,
          6
        ],
        "approx_cost": 4.0
      },
      {
        "coord": [
          9,
          9
        ],
        "approx_cost": 4.0
      },
      {
        "coord": [
          6,
          6
        ],
        "approx_cost": 3.0
      }
    ],
    "open_junction_wall_candidates": [
      {
        "coord": [
          6,
          2
        ],
        "degree": 4
      },
      {
        "coord": [
          6,
          10
        ],
        "degree": 4
      },
      {
        "coord": [
          11,
          4
        ],
        "degree": 3
      },
      {
        "coord": [
          3,
          6
        ],
        "degree": 3
      },
      {
        "coord": [
          6,
          6
        ],
        "degree": 3
      },
      {
        "coord": [
          3,
          9
        ],
        "degree": 3
      },
      {
        "coord": [
          4,
          10
        ],
        "degree": 3
      }
    ],
    "enemy_tiles": [
      {
        "id": "bat",
        "code": 205,
        "coord": [
          2,
          1
        ],
        "hp": 42,
        "atk": 24,
        "def": 4,
        "special": []
      },
      {
        "id": "skeleton",
        "code": 209,
        "coord": [
          10,
          1
        ],
        "hp": 65,
        "atk": 28,
        "def": 5,
        "special": []
      },
      {
        "id": "skeleton",
        "code": 209,
        "coord": [
          5,
          2
        ],
        "hp": 65,
        "atk": 28,
        "def": 5,
        "special": []
      },
      {
        "id": "bigBat",
        "code": 206,
        "coord": [
          7,
          2
        ],
        "hp": 70,
        "atk": 36,
        "def": 6,
        "special": [
          1
        ]
      },
      {
        "id": "bat",
        "code": 205,
        "coord": [
          2,
          3
        ],
        "hp": 42,
        "atk": 24,
        "def": 4,
        "special": []
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          6,
          3
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "zombie",
        "code": 213,
        "coord": [
          3,
          4
        ],
        "hp": 90,
        "atk": 25,
        "def": 9,
        "special": []
      },
      {
        "id": "slimelord",
        "code": 204,
        "coord": [
          9,
          4
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "bigBat",
        "code": 206,
        "coord": [
          6,
          5
        ],
        "hp": 70,
        "atk": 36,
        "def": 6,
        "special": [
          1
        ]
      },
      {
        "id": "skeleton",
        "code": 209,
        "coord": [
          3,
          7
        ],
        "hp": 65,
        "atk": 28,
        "def": 5,
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
        "id": "bat",
        "code": 205,
        "coord": [
          9,
          8
        ],
        "hp": 42,
        "atk": 24,
        "def": 4,
        "special": []
      },
      {
        "id": "bat",
        "code": 205,
        "coord": [
          6,
          9
        ],
        "hp": 42,
        "atk": 24,
        "def": 4,
        "special": []
      },
      {
        "id": "redPriest",
        "code": 218,
        "coord": [
          3,
          10
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
          9,
          10
        ],
        "hp": 85,
        "atk": 30,
        "def": 6,
        "special": []
      },
      {
        "id": "skeleton",
        "code": 209,
        "coord": [
          6,
          11
        ],
        "hp": 65,
        "atk": 28,
        "def": 5,
        "special": []
      }
    ],
    "min_route_to_exit": {
      "enemy_count": 4,
      "door_cost": 2.0,
      "special_red_potion_equiv": 0.0,
      "total_cost_proxy": 6.0,
      "steps": 18,
      "cost_tiles": [
        {
          "id": "skeleton",
          "coord": [
            6,
            11
          ],
          "code": 209
        },
        {
          "id": "yellowDoor",
          "coord": [
            5,
            10
          ],
          "code": 81
        },
        {
          "id": "yellowKey",
          "coord": [
            4,
            9
          ],
          "code": 21
        },
        {
          "id": "yellowDoor",
          "coord": [
            3,
            8
          ],
          "code": 81
        },
        {
          "id": "skeleton",
          "coord": [
            3,
            7
          ],
          "code": 209
        },
        {
          "id": "blueKey",
          "coord": [
            3,
            5
          ],
          "code": 22
        },
        {
          "id": "zombie",
          "coord": [
            3,
            4
          ],
          "code": 213
        },
        {
          "id": "blueGem",
          "coord": [
            3,
            3
          ],
          "code": 28
        },
        {
          "id": "yellowKey",
          "coord": [
            3,
            2
          ],
          "code": 21
        },
        {
          "id": "skeleton",
          "coord": [
            5,
            2
          ],
          "code": 209
        }
      ]
    },
    "special_sources": [],
    "special_affected_cells": 0,
    "special_can_be_fully_avoided": null,
    "red_potion_value": 80.0
  },
  "reviewer": "resource_balance"
}

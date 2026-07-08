Read and follow this skill file first:
        /Users/kanyun/workspace/learn/mota/skills/review-mota-floor/SKILL.md

        You are the topology-reviewer in a staged per-floor pipeline. Return only JSON matching
        the provided structured review schema. Every issue must be an object with:
        owner_stage, severity, coordinates, reason, required_change.
        Use severity="fail" only when the issue must trigger repair. Use severity="warn" for non-blocking notes.
        Do not emit string issues.

        Reviewer scope:

Focus only on structural topology.

Required checks:
- floor id, dimensions, schema shape, and stairs are correct.
- Only tile code 0, tile code 1, downFloor, and upFloor appear in floor.map.
- 0 is the only ground and 1 is the only wall.
- The entrance and exit are connected through meaningful space.
- The structure suggests 2 or 3 candidate routes, not one corridor and not an uncontrolled open grid.
- For 13x13, wall ratio should normally be around 0.50-0.60.
- Avoid thick fill walls, purely decorative branches, fake branches, and dead space that cannot support economy.

Return structured issues with owner_stage="topology".


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
201: greenSlime 绿头怪 hp=50 atk=17 def=1 money=1 special=[1]
202: redSlime 红头怪 hp=43 atk=22 def=2 money=2 special=0
203: blackSlime 青头怪 hp=60 atk=18 def=7 money=2 special=0
205: bat 小蝙蝠 hp=42 atk=24 def=4 money=3 special=0

        Input JSON:
        {
  "tower_brief": {
    "status": "ready",
    "summary": "从当前 mota-js 项目和现有素材出发，生成 4 层 13x13 经典数值向魔塔；无新插件、无新素材、无商店。整体强调可计算战斗、钥匙门压力、分支资源选择和稳定可通关路线，不生成楼层地图。",
    "floor_count": 4,
    "floor_size": 13,
    "fixed_rules": [
      "13x13 floors",
      "使用当前 mota-js 项目和现有素材，不新增插件或素材",
      "经典数值向，优先战斗节奏、钥匙门压力、资源选择和可通关性",
      "仅使用 tile code 0 作为默认可通行地面，tile code 1 作为墙",
      "不要求外圈整墙，使用墙、门、怪物、机关和道具组织路线",
      "避免大面积空地、重复墙填充和无代价高价值资源堆",
      "每层需要结构清晰，并有至少一个有意义分支选择",
      "不生成楼层地图"
    ],
    "global_limits": {
      "yellow_doors": 20,
      "blue_doors": 6,
      "red_doors": 1,
      "yellow_keys": 17,
      "blue_keys": 5,
      "red_keys": 1,
      "pickaxes": 1,
      "bombs": 1,
      "centerFly": 0
    },
    "global_settings": {
      "initial_hero": {
        "hp": 1000,
        "atk": 10,
        "def": 10,
        "money": 0,
        "keys": {
          "yellow": 0,
          "blue": 0,
          "red": 0
        }
      },
      "gems": {
        "redGem": 3,
        "blueGem": 3,
        "greenGem": 5
      },
      "potions": {
        "redPotion": 100,
        "bluePotion": 250,
        "yellowPotion": 500,
        "greenPotion": 800
      },
      "shop": {
        "enabled": false,
        "rule": "",
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
      "gem_floor_delta_min": 0,
      "gem_floor_delta_max": 2,
      "potion_floor_delta_min": 0,
      "potion_floor_delta_max": 2,
      "potion_compare_mode": "red_potion_equiv"
    },
    "layout_policy": [
      "每层主线必须可通关，分支奖励允许消耗额外钥匙或血量",
      "黄门承担基础路线压力，蓝门用于中高价值分支或捷径，红门用于终局关键门或大奖励门",
      "钥匙总量略少于同色门总量，允许玩家通过路线选择跳过部分门",
      "镐和炸弹作为稀缺路线调整工具，不能成为唯一通关条件",
      "每层怪物强度随楼层递进，相邻楼层保留约 70% 怪物池重叠并替换较弱怪物",
      "怪物不得正交相邻，避免形成不可读的连续怪墙",
      "高价值宝石、药水和钥匙不得裸露堆放，必须绑定战斗、门耗或路线代价",
      "楼梯路径清晰但不直给，至少经过一次战斗或钥匙门决策"
    ],
    "questions": [],
    "confirmation_prompt": "Confirm this whole-tower brief before floor generation."
  },
  "stage": "topology",
  "stage_output": {
    "floor_id": "MT0",
    "floor_index": 0,
    "floor_size": 13,
    "summary": "Topology-only 13x13 MT0 shell with one downFloor entrance, one upFloor exit, three controlled entrance-to-exit candidate routes, branch pockets, and annotated future pressure points. Map uses only ground 0, wall 1, upFloor 87, and downFloor 88.",
    "floor": {
      "floorId": "MT0",
      "title": "主塔 0 层",
      "name": "0",
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
          0,
          0,
          0,
          1,
          0,
          0,
          0,
          0,
          1,
          0,
          87,
          1
        ],
        [
          1,
          0,
          1,
          0,
          1,
          0,
          1,
          1,
          0,
          1,
          0,
          0,
          1
        ],
        [
          1,
          0,
          1,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          1
        ],
        [
          1,
          0,
          1,
          1,
          1,
          0,
          1,
          0,
          1,
          1,
          1,
          0,
          1
        ],
        [
          1,
          0,
          0,
          0,
          1,
          0,
          0,
          0,
          0,
          0,
          1,
          0,
          1
        ],
        [
          1,
          1,
          1,
          0,
          1,
          0,
          1,
          1,
          1,
          0,
          1,
          0,
          1
        ],
        [
          1,
          0,
          0,
          0,
          1,
          0,
          1,
          0,
          0,
          0,
          1,
          0,
          1
        ],
        [
          1,
          0,
          1,
          1,
          1,
          0,
          1,
          0,
          1,
          0,
          1,
          0,
          1
        ],
        [
          1,
          0,
          0,
          0,
          0,
          0,
          1,
          0,
          1,
          0,
          0,
          0,
          1
        ],
        [
          1,
          0,
          1,
          1,
          1,
          0,
          1,
          0,
          1,
          1,
          1,
          0,
          1
        ],
        [
          1,
          88,
          0,
          0,
          1,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          1
        ],
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
    },
    "annotations": [
      {
        "stage": "topology",
        "kind": "candidate_route",
        "label": "lower_route",
        "coordinates": [
          [
            1,
            11
          ],
          [
            1,
            10
          ],
          [
            1,
            9
          ],
          [
            2,
            9
          ],
          [
            3,
            9
          ],
          [
            4,
            9
          ],
          [
            5,
            9
          ],
          [
            5,
            10
          ],
          [
            5,
            11
          ],
          [
            6,
            11
          ],
          [
            7,
            11
          ],
          [
            8,
            11
          ],
          [
            9,
            11
          ],
          [
            10,
            11
          ],
          [
            11,
            11
          ],
          [
            11,
            10
          ],
          [
            11,
            9
          ],
          [
            11,
            8
          ],
          [
            11,
            7
          ],
          [
            11,
            6
          ],
          [
            11,
            5
          ],
          [
            11,
            4
          ],
          [
            11,
            3
          ],
          [
            11,
            2
          ],
          [
            11,
            1
          ]
        ],
        "description": "Long lower route from entrance through the south corridor and east ascent column; suited for baseline combat and yellow-door pressure later.",
        "tags": [
          "candidate_routes",
          "mainline",
          "long_route"
        ],
        "data": "route_id=lower_route; intended_cost_profile=baseline; stairs_preserved=true"
      },
      {
        "stage": "topology",
        "kind": "candidate_route",
        "label": "central_loop_route",
        "coordinates": [
          [
            1,
            11
          ],
          [
            1,
            10
          ],
          [
            1,
            9
          ],
          [
            2,
            9
          ],
          [
            3,
            9
          ],
          [
            4,
            9
          ],
          [
            5,
            9
          ],
          [
            5,
            8
          ],
          [
            5,
            7
          ],
          [
            5,
            6
          ],
          [
            5,
            5
          ],
          [
            6,
            5
          ],
          [
            7,
            5
          ],
          [
            8,
            5
          ],
          [
            9,
            5
          ],
          [
            9,
            6
          ],
          [
            9,
            7
          ],
          [
            9,
            8
          ],
          [
            9,
            9
          ],
          [
            10,
            9
          ],
          [
            11,
            9
          ],
          [
            11,
            8
          ],
          [
            11,
            7
          ],
          [
            11,
            6
          ],
          [
            11,
            5
          ],
          [
            11,
            4
          ],
          [
            11,
            3
          ],
          [
            11,
            2
          ],
          [
            11,
            1
          ]
        ],
        "description": "Middle route climbs at the central spine, crosses the central hall, and rejoins the east column; useful for a second viable path with different door or monster costs.",
        "tags": [
          "candidate_routes",
          "middle",
          "loop"
        ],
        "data": "route_id=central_loop_route; intended_cost_profile=alternate; route_shares_exit_column=true"
      },
      {
        "stage": "topology",
        "kind": "candidate_route",
        "label": "north_gallery_route",
        "coordinates": [
          [
            1,
            11
          ],
          [
            1,
            10
          ],
          [
            1,
            9
          ],
          [
            2,
            9
          ],
          [
            3,
            9
          ],
          [
            4,
            9
          ],
          [
            5,
            9
          ],
          [
            5,
            8
          ],
          [
            5,
            7
          ],
          [
            5,
            6
          ],
          [
            5,
            5
          ],
          [
            5,
            4
          ],
          [
            5,
            3
          ],
          [
            6,
            3
          ],
          [
            7,
            3
          ],
          [
            8,
            3
          ],
          [
            9,
            3
          ],
          [
            10,
            3
          ],
          [
            11,
            3
          ],
          [
            11,
            2
          ],
          [
            11,
            1
          ]
        ],
        "description": "Upper route reaches the north gallery before the exit column; later stages can make it shorter but more expensive.",
        "tags": [
          "candidate_routes",
          "upper",
          "shortcut_candidate"
        ],
        "data": "route_id=north_gallery_route; intended_cost_profile=short_high_pressure"
      },
      {
        "stage": "topology",
        "kind": "junction",
        "label": "southwest_split",
        "coordinates": [
          [
            1,
            9
          ],
          [
            2,
            9
          ],
          [
            3,
            9
          ],
          [
            4,
            9
          ],
          [
            5,
            9
          ]
        ],
        "description": "First meaningful split after the entrance, where routes can continue low or climb toward the center.",
        "tags": [
          "junctions",
          "route_split",
          "early_floor"
        ],
        "data": "junction_id=southwest_split; connects=lower_route,central_loop_route,north_gallery_route"
      },
      {
        "stage": "topology",
        "kind": "junction",
        "label": "central_spine",
        "coordinates": [
          [
            5,
            5
          ],
          [
            5,
            6
          ],
          [
            5,
            7
          ],
          [
            5,
            8
          ],
          [
            5,
            9
          ]
        ],
        "description": "Vertical central spine that connects lower, middle, and upper options and can hold later gating decisions.",
        "tags": [
          "junctions",
          "central",
          "route_control"
        ],
        "data": "junction_id=central_spine; branch_count=3"
      },
      {
        "stage": "topology",
        "kind": "junction",
        "label": "east_rejoin",
        "coordinates": [
          [
            11,
            9
          ],
          [
            11,
            8
          ],
          [
            11,
            7
          ],
          [
            11,
            6
          ],
          [
            11,
            5
          ]
        ],
        "description": "East-side rejoin where lower and central routes converge before climbing toward the exit.",
        "tags": [
          "junctions",
          "rejoin",
          "exit_pressure"
        ],
        "data": "junction_id=east_rejoin; supports_late_pressure=true"
      },
      {
        "stage": "topology",
        "kind": "junction",
        "label": "north_gallery_rejoin",
        "coordinates": [
          [
            9,
            3
          ],
          [
            10,
            3
          ],
          [
            11,
            3
          ]
        ],
        "description": "Upper gallery merges into the exit ascent, suitable for a shortcut gate or a guarded bypass.",
        "tags": [
          "junctions",
          "upper",
          "shortcut"
        ],
        "data": "junction_id=north_gallery_rejoin; supports_shortcut_gate=true"
      },
      {
        "stage": "topology",
        "kind": "region",
        "label": "entrance_region",
        "coordinates": [
          [
            1,
            11
          ],
          [
            2,
            11
          ],
          [
            3,
            11
          ],
          [
            1,
            10
          ],
          [
            1,
            9
          ],
          [
            2,
            9
          ],
          [
            3,
            9
          ],
          [
            4,
            9
          ],
          [
            5,
            9
          ]
        ],
        "description": "Entrance-side movement region with enough space for first-floor tutorial pressure without placing content now.",
        "tags": [
          "regions",
          "entrance",
          "early_floor"
        ],
        "data": "region_id=entrance_region; role=start_and_first_split"
      },
      {
        "stage": "topology",
        "kind": "region",
        "label": "central_region",
        "coordinates": [
          [
            5,
            5
          ],
          [
            6,
            5
          ],
          [
            7,
            5
          ],
          [
            8,
            5
          ],
          [
            9,
            5
          ],
          [
            5,
            6
          ],
          [
            9,
            6
          ],
          [
            5,
            7
          ],
          [
            7,
            7
          ],
          [
            8,
            7
          ],
          [
            9,
            7
          ],
          [
            5,
            8
          ],
          [
            7,
            8
          ],
          [
            9,
            8
          ],
          [
            5,
            9
          ],
          [
            7,
            9
          ],
          [
            9,
            9
          ]
        ],
        "description": "Controlled central loop with separated corridors for future monsters, keys, or mutually exclusive rewards.",
        "tags": [
          "regions",
          "central",
          "loop"
        ],
        "data": "region_id=central_region; role=route_comparison"
      },
      {
        "stage": "topology",
        "kind": "region",
        "label": "north_region",
        "coordinates": [
          [
            1,
            1
          ],
          [
            2,
            1
          ],
          [
            3,
            1
          ],
          [
            5,
            1
          ],
          [
            6,
            1
          ],
          [
            7,
            1
          ],
          [
            8,
            1
          ],
          [
            10,
            1
          ],
          [
            11,
            1
          ],
          [
            3,
            2
          ],
          [
            5,
            2
          ],
          [
            8,
            2
          ],
          [
            10,
            2
          ],
          [
            11,
            2
          ],
          [
            3,
            3
          ],
          [
            4,
            3
          ],
          [
            5,
            3
          ],
          [
            6,
            3
          ],
          [
            7,
            3
          ],
          [
            8,
            3
          ],
          [
            9,
            3
          ],
          [
            10,
            3
          ],
          [
            11,
            3
          ]
        ],
        "description": "Northern gallery and exit approach with enough horizontal space to support a higher-cost shortcut path.",
        "tags": [
          "regions",
          "north",
          "exit_approach"
        ],
        "data": "region_id=north_region; role=shortcut_and_exit"
      },
      {
        "stage": "topology",
        "kind": "region",
        "label": "east_ascent_region",
        "coordinates": [
          [
            11,
            11
          ],
          [
            11,
            10
          ],
          [
            11,
            9
          ],
          [
            11,
            8
          ],
          [
            11,
            7
          ],
          [
            11,
            6
          ],
          [
            11,
            5
          ],
          [
            11,
            4
          ],
          [
            11,
            3
          ],
          [
            11,
            2
          ],
          [
            11,
            1
          ],
          [
            10,
            9
          ],
          [
            9,
            9
          ],
          [
            9,
            8
          ],
          [
            9,
            7
          ],
          [
            9,
            6
          ],
          [
            9,
            5
          ]
        ],
        "description": "East ascent column forms the shared endgame approach for this floor and supports late route pressure.",
        "tags": [
          "regions",
          "exit",
          "ascent"
        ],
        "data": "region_id=east_ascent_region; role=shared_exit_column"
      },
      {
        "stage": "topology",
        "kind": "reward_room_candidate",
        "label": "west_side_pocket",
        "coordinates": [
          [
            1,
            5
          ],
          [
            2,
            5
          ],
          [
            3,
            5
          ],
          [
            3,
            6
          ],
          [
            3,
            7
          ],
          [
            2,
            7
          ],
          [
            1,
            7
          ],
          [
            1,
            8
          ]
        ],
        "description": "West side pocket can become an optional early reward branch with door, monster, or HP cost.",
        "tags": [
          "reward_room_candidates",
          "optional",
          "early_reward"
        ],
        "data": "candidate_id=west_side_pocket; suggested_gate=yellow_or_monster"
      },
      {
        "stage": "topology",
        "kind": "reward_room_candidate",
        "label": "northwest_pocket",
        "coordinates": [
          [
            1,
            1
          ],
          [
            2,
            1
          ],
          [
            3,
            1
          ],
          [
            3,
            2
          ],
          [
            3,
            3
          ],
          [
            4,
            3
          ]
        ],
        "description": "Northwest pocket is off the upper route and can hold a small reward for taking the north gallery.",
        "tags": [
          "reward_room_candidates",
          "optional",
          "north"
        ],
        "data": "candidate_id=northwest_pocket; suggested_gate=yellow"
      },
      {
        "stage": "topology",
        "kind": "reward_room_candidate",
        "label": "southeast_vault",
        "coordinates": [
          [
            7,
            10
          ],
          [
            7,
            11
          ],
          [
            8,
            11
          ],
          [
            9,
            11
          ],
          [
            10,
            11
          ]
        ],
        "description": "Southeast pocket near the lower route can support a better reward with a blue-door or combat tax later.",
        "tags": [
          "reward_room_candidates",
          "optional",
          "higher_value"
        ],
        "data": "candidate_id=southeast_vault; suggested_gate=blue_or_monster"
      },
      {
        "stage": "topology",
        "kind": "reward_room_candidate",
        "label": "upper_east_alcove",
        "coordinates": [
          [
            10,
            1
          ],
          [
            10,
            2
          ],
          [
            10,
            3
          ],
          [
            9,
            3
          ],
          [
            8,
            3
          ]
        ],
        "description": "Upper east alcove can reward the shortcut route without blocking the required stair path.",
        "tags": [
          "reward_room_candidates",
          "optional",
          "shortcut_reward"
        ],
        "data": "candidate_id=upper_east_alcove; suggested_gate=yellow_or_special_pressure"
      },
      {
        "stage": "topology",
        "kind": "door_candidate",
        "label": "entrance_gate",
        "coordinates": [
          [
            1,
            10
          ]
        ],
        "description": "Single-cell choke immediately after the downFloor, suitable for a light early gate if economy stage needs initial key pressure.",
        "tags": [
          "door_candidates",
          "yellow_candidate",
          "early_gate"
        ],
        "data": "candidate_id=entrance_gate; suggested_color=yellow; blocks_all_routes=true"
      },
      {
        "stage": "topology",
        "kind": "door_candidate",
        "label": "central_spine_gate",
        "coordinates": [
          [
            5,
            8
          ]
        ],
        "description": "Gate on the central spine can separate lower route from middle and upper choices.",
        "tags": [
          "door_candidates",
          "yellow_candidate",
          "route_choice"
        ],
        "data": "candidate_id=central_spine_gate; suggested_color=yellow; blocks=central_loop_route,north_gallery_route"
      },
      {
        "stage": "topology",
        "kind": "door_candidate",
        "label": "north_shortcut_gate",
        "coordinates": [
          [
            5,
            4
          ]
        ],
        "description": "Gate below the north gallery can make the shorter upper route optional or more expensive.",
        "tags": [
          "door_candidates",
          "yellow_candidate",
          "shortcut"
        ],
        "data": "candidate_id=north_shortcut_gate; suggested_color=yellow_or_blue; blocks=north_gallery_route"
      },
      {
        "stage": "topology",
        "kind": "door_candidate",
        "label": "southeast_vault_gate",
        "coordinates": [
          [
            7,
            11
          ]
        ],
        "description": "Optional branch gate for the southeast vault candidate without blocking stair access.",
        "tags": [
          "door_candidates",
          "blue_candidate",
          "reward_gate"
        ],
        "data": "candidate_id=southeast_vault_gate; suggested_color=blue; optional=true"
      },
      {
        "stage": "topology",
        "kind": "door_candidate",
        "label": "exit_column_gate",
        "coordinates": [
          [
            11,
            5
          ]
        ],
        "description": "Late shared choke in the east ascent can create final floor pressure while preserving all candidate routes.",
        "tags": [
          "door_candidates",
          "yellow_candidate",
          "late_gate"
        ],
        "data": "candidate_id=exit_column_gate; suggested_color=yellow; blocks_all_routes=true"
      },
      {
        "stage": "topology",
        "kind": "special_pressure_candidate",
        "label": "early_pressure_cell",
        "coordinates": [
          [
            3,
            9
          ]
        ],
        "description": "Early corridor cell can hold a non-adjacent future enemy or pressure obstacle before the first route split.",
        "tags": [
          "special_pressure_candidates",
          "combat_slot",
          "early"
        ],
        "data": "candidate_id=early_pressure_cell; adjacency_buffer=available"
      },
      {
        "stage": "topology",
        "kind": "special_pressure_candidate",
        "label": "central_cross_pressure",
        "coordinates": [
          [
            7,
            5
          ],
          [
            9,
            7
          ]
        ],
        "description": "Separated central cells can carry future special or balanced monster pressure without creating orthogonal enemy adjacency.",
        "tags": [
          "special_pressure_candidates",
          "combat_slots",
          "central"
        ],
        "data": "candidate_id=central_cross_pressure; min_pair_distance=4"
      },
      {
        "stage": "topology",
        "kind": "special_pressure_candidate",
        "label": "north_gallery_pressure",
        "coordinates": [
          [
            7,
            3
          ],
          [
            10,
            3
          ]
        ],
        "description": "Upper gallery cells can make the shortcut route costly while keeping route readability clear.",
        "tags": [
          "special_pressure_candidates",
          "shortcut_pressure",
          "north"
        ],
        "data": "candidate_id=north_gallery_pressure; no_adjacent_enemy_slots=true"
      },
      {
        "stage": "topology",
        "kind": "special_pressure_candidate",
        "label": "exit_ascent_pressure",
        "coordinates": [
          [
            11,
            7
          ],
          [
            11,
            3
          ]
        ],
        "description": "Shared ascent cells can carry late pressure after routes rejoin, useful for pacing the final approach to the upFloor.",
        "tags": [
          "special_pressure_candidates",
          "late_pressure",
          "exit"
        ],
        "data": "candidate_id=exit_ascent_pressure; shared_by_routes=true"
      }
    ]
  },
  "topology_output": {},
  "economy_output": {},
  "floor_size": 13,
  "current_floor_policy": {
    "allowed_enemy_ids": [
      "greenSlime",
      "redSlime",
      "blackSlime",
      "bat"
    ],
    "allowed_enemy_codes": [
      201,
      202,
      203,
      205
    ],
    "enemy_role_hints": {
      "greenSlime": "balanced combat",
      "redSlime": "balanced combat",
      "blackSlime": "balanced combat",
      "bat": "balanced combat"
    },
    "fallback_no_special_enemy_ids": [
      "bat"
    ],
    "no_adjacent_enemies": true,
    "enemy_adjacency": "orthogonal",
    "special_damage_red_potion_range": [
      0.5,
      1.0
    ],
    "resource_progression": {
      "gem_floor_delta_min": 0.0,
      "gem_floor_delta_max": 2.0,
      "potion_floor_delta_min": 0.0,
      "potion_floor_delta_max": 2.0,
      "potion_compare_mode": "red_potion_equiv"
    }
  },
  "used_budget_so_far": {
    "yellow_doors": 0,
    "blue_doors": 0,
    "red_doors": 0,
    "yellow_keys": 0,
    "blue_keys": 0,
    "red_keys": 0,
    "pickaxes": 0,
    "bombs": 0,
    "centerFly": 0
  },
  "remaining_whole_tower_budget": {
    "yellow_doors": 20,
    "blue_doors": 6,
    "red_doors": 1,
    "yellow_keys": 17,
    "blue_keys": 5,
    "red_keys": 1,
    "pickaxes": 1,
    "bombs": 1,
    "centerFly": 0
  },
  "previous_accepted_floor_summaries": [],
  "static_metrics": {
    "available": true,
    "width": 13,
    "height": 13,
    "wall_ratio": 0.538,
    "wall_count": 91,
    "non_wall_cells": 78,
    "enemy_count": 0,
    "door_count": 0,
    "monster_density_non_wall": 0.0,
    "components_non_wall": 1,
    "main_component_cells": 78,
    "main_cycle_rank": 8,
    "main_cycle_rank_ratio": 0.103,
    "resource_weight_total": 0.0,
    "tool_count": 0,
    "free_region_cells": 78,
    "free_region_bbox": [
      [
        1,
        1
      ],
      [
        11,
        11
      ]
    ],
    "free_region_reaches_exit": true,
    "free_region_resource_count": 0,
    "free_region_resource_weight": 0.0,
    "free_region_resources": [],
    "free_region_tools": [],
    "free_region_keys": [],
    "approx_resource_weight_by_access_cost": {
      "0": 0.0,
      "1": 0.0,
      "2": 0.0,
      "3": 0.0
    },
    "lowest_cost_resources": [],
    "low_cost_resource_clusters": [],
    "suggested_relocation_cells": [
      {
        "coord": [
          1,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          2,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          3,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          5,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          6,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          7,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          8,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          10,
          1
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          1,
          2
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          3,
          2
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          5,
          2
        ],
        "approx_cost": 0.0
      },
      {
        "coord": [
          8,
          2
        ],
        "approx_cost": 0.0
      }
    ],
    "open_junction_wall_candidates": [
      {
        "coord": [
          5,
          3
        ],
        "degree": 4
      },
      {
        "coord": [
          10,
          2
        ],
        "degree": 3
      },
      {
        "coord": [
          11,
          2
        ],
        "degree": 3
      },
      {
        "coord": [
          7,
          3
        ],
        "degree": 3
      },
      {
        "coord": [
          8,
          3
        ],
        "degree": 3
      },
      {
        "coord": [
          10,
          3
        ],
        "degree": 3
      },
      {
        "coord": [
          11,
          3
        ],
        "degree": 3
      },
      {
        "coord": [
          5,
          5
        ],
        "degree": 3
      },
      {
        "coord": [
          7,
          5
        ],
        "degree": 3
      },
      {
        "coord": [
          9,
          7
        ],
        "degree": 3
      },
      {
        "coord": [
          1,
          9
        ],
        "degree": 3
      },
      {
        "coord": [
          5,
          9
        ],
        "degree": 3
      },
      {
        "coord": [
          11,
          9
        ],
        "degree": 3
      },
      {
        "coord": [
          7,
          11
        ],
        "degree": 3
      }
    ],
    "enemy_tiles": [],
    "min_route_to_exit": {
      "enemy_count": 0,
      "door_cost": 0.0,
      "special_red_potion_equiv": 0.0,
      "total_cost_proxy": 0.0,
      "steps": 20,
      "cost_tiles": []
    },
    "special_sources": [],
    "special_affected_cells": 0,
    "special_can_be_fully_avoided": null,
    "red_potion_value": 100.0
  },
  "budget_delta_from_map": {
    "yellow_doors": 0,
    "blue_doors": 0,
    "red_doors": 0,
    "yellow_keys": 0,
    "blue_keys": 0,
    "red_keys": 0,
    "pickaxes": 0,
    "bombs": 0,
    "centerFly": 0
  },
  "floor_contract": {}
}

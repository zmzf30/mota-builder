Read and follow this skill file first:
        /Users/kanyun/workspace/learn/mota/skills/topology-mota-floor/SKILL.md

        You are stage 1 of a staged per-floor pipeline. Return only JSON matching the provided schema.
        Generate a complete floor object plus annotations, but only place:
        - 0 empty/default ground,
        - 1 wall,
        - one downFloor entrance,
        - one upFloor exit.
        Do not place doors, keys, resources, tools, nets, monsters, events, scripts, or decorative overlays.
        Output annotations for candidate_routes, junctions, regions, reward_room_candidates,
        door_candidates, and special_pressure_candidates.
        If repair_feedback is present, repair current_stage_output_to_repair only for the listed topology issue.
        Keep downstream hard constraints in mind but do not solve economy or monster placement in this stage.

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
  "floor_index": 0,
  "floor_id": "MT0",
  "floor_size": 13,
  "floor_count": 4,
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
  "floor_contract": {},
  "repair_feedback": {},
  "current_stage_output_to_repair": {},
  "downstream_hard_constraints_summary": {
    "stage_being_repaired": "topology",
    "resource_budget_remaining": {
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
    "floor_contract_resource_limits": {},
    "enemy_policy": {
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
    "allowed_specials": [
      1,
      2,
      3,
      15,
      18
    ],
    "max_specials_per_monster": 1,
    "no_adjacent_enemies": true,
    "resource_progression": {
      "gem_floor_delta_min": 0.0,
      "gem_floor_delta_max": 2.0,
      "potion_floor_delta_min": 0.0,
      "potion_floor_delta_max": 2.0,
      "potion_compare_mode": "red_potion_equiv"
    },
    "final_floor_requirements": [
      "final output must pass local floor validation",
      "final output must preserve downFloor and upFloor stairs",
      "write_generated_project will wire stairs and final win event after review"
    ]
  }
}

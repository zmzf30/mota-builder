Read and follow this skill file first:
        /Users/kanyun/workspace/learn/mota/skills/generate-mota-floor/SKILL.md

        Generate exactly one complete mota-js floor object. Return only JSON matching the provided schema.
        Critical: quantity limits in tower_brief are whole-tower totals, not this floor's allowance.
        remaining_whole_tower_budget is a ceiling, not a target; do not spend all doors/keys/tools
        unless each one creates meaningful ordering pressure, a shortcut, a protected reward, or a
        balanced route tradeoff. Do not output abstract topology,
        placements, or design_intent; encode the design directly in floor.map and coordinate-bound fields.
        Use only enemy ids/codes listed in current_floor_policy. If current_floor_policy includes
        fallback_no_special_enemy_ids, treat their enemy_role_hints as the intended combat roles for
        placement on this floor. No two enemy tiles may be orthogonally adjacent; diagonal contact is allowed.
        Gem and potion placement must follow current_floor_policy.resource_progression.

        If review_feedback_to_fix is present, make concrete structural repairs:
        - For a low-cost resource cluster bbox, split or move the named resources/tools to the suggested
          relocation coordinates, or add a specific door/monster/wall before that bbox.
        - For open_junction_wall_candidates, convert suitable empty candidate coordinates into walls or
          gated chokepoints to break smooth loops while preserving a viable route.
        - For weak monster feedback, strengthen, replace, or move the named monster coordinate onto a
          real chokepoint or protected reward route.
        Do not keep the same topology while only changing prose, summary, or intent text.


Positive examples to emulate by rule:
- Complete floor.js format: HTML5魔塔样板V2.7.3.1 / MT2 and MT3. They are clean full floor objects with stable map/changeFloor shape.
- Compact default pressure: 红蓝的记忆2.10 / MT6 and 一层小塔 2.10 / MT0 combine battle pressure, door/key pressure, rewards, and allowed specials without needing story scripts. Most examples are 13x13; for 11x11 floors, preserve the pressure relationships while reducing absolute counts.
- Branching door/key/resource pressure: 剑阁2.9 / MT3 and MT6 show multi-branch routes with protected rewards and low free-region exposure.
- Repulse and tool-route topology: dist / MT1-MT2 and Oblivion 2.10 / MT1 place 阻击 enemies, tools, and mechanisms where they influence actual route cost rather than decorative corners.
- Zone topology: 红蓝的记忆2.10 / MT1 and MT4, and 剑阁2.9 / MT3, place 领域 enemies around route/reward pressure points.
- Mechanism gates: Oblivion 2.10 / MT1 is a reference for kill-count auto-door gates and multiple stair connections. Use Oblivion 2.10 / MT2 only for boss/final-gate calibration, not as a default floor template.
- Tool and blood-net pressure: 出塞 / MT0-MT2 and 星月神话 / MT7-MT8 are examples for tools or nets changing route cost; use these as local ideas, not as full style templates.
- Budget is a ceiling, not a target. A door/key/tool should be omitted unless it creates viable ordering pressure, a shortcut, a protected reward, or a route tradeoff.

Split-review quality gates to satisfy:
- Do not expose many resources in the entrance/free region. From downFloor, walking through only empty/resource tiles should reveal at most a very small starter reward and no naked tool.
- Avoid large low-cost connected reward blobs. A rich reward cluster needs enough combat, door, wall/tool, special-damage, or route-length pressure before it.
- Treat yellow doors/keys as the low-cost baseline. Blue doors and wall-breaking/tool access are higher-cost choices and must unlock clearly stronger rewards, shortcuts, or strategic route changes.
- Monster cost is contextual; do not assume every monster equals one unit. Place monsters where their current stats create real pacing for the likely hero state.
- Keep wall density and monster density close to the positive few-shot style, with controlled branches instead of open-grid route networks.
- Zone/repulse monsters must affect an actual route or protected reward. A route with special pressure should be shorter, richer, or strategically different from the route that avoids it.


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
  "floor_index": 2,
  "floor_id": "MT2",
  "floor_size": 13,
  "floor_count": 4,
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
  "review_feedback_to_fix": {
    "status": "fail",
    "issues": [
      "[connectivity density] The non-wall graph is too open for controlled 2-3 route structure: main_cycle_rank_ratio is 0.286 with many degree-4/degree-3 junctions, so the branches merge into a smooth loop network rather than distinct candidate routes.",
      "[connectivity density] The lowest-cost entrance-to-exit route is under-pressured for MT2: min_route_to_exit reaches the exit in 14 steps with only 2 enemies, 2 yellow doors, no special pressure, and total_cost_proxy 4.0. Route cost tiles are yellowDoor (5,12), yellowKey (5,11), blueGem (5,10), yellowDoor (5,8), blueGem (5,5), bat (6,5), skeleton (6,3).",
      "[connectivity density] Wall ratio 0.462 and monster_density_non_wall 0.187 are not the primary problem, but the effective topology remains too permissive because the central and side lanes reconnect repeatedly.",
      "[resource balance] Low-cost entrance cluster bbox [5,9]->[7,12] exposes blueGem [5,10], redPotion [6,10], yellowKey [5,11], and yellowKey [7,11] after only the entrance skeleton at [6,11]. The two adjacent yellow keys immediately overfeed/refund the lower yellow-door economy and are stronger than a yellow-door baseline.",
      "[resource balance] Expanded low-cost central cluster bbox [3,5]->[8,12] adds blueGem [5,5] and redGem [7,5] to the same early package, so six resources/keys are concentrated along the main shaft with only light combat/yellow-door pressure instead of staged branch commitment.",
      "[gem route balance] Entry-to-gem route is too easy for blueGem@[5,10] in region [5,9]->[7,11]: score=0.86, hp_loss=36.0, key_cost=0.0, enemies=1, doors=0, steps=3; path [6,12]->[6,11]->[5,11]->[5,10].",
      "[gem route balance] Large direct resource region [10,7]->[11,11] has resource_weight=9.5, resources=6, gems=2: blueGem@[11,7], bluePotion@[11,8], redPotion@[11,9], yellowKey@[11,10], redGem@[10,11], pickaxe@[11,11].",
      "[gem route balance] Large direct resource region [9,1]->[11,5] has resource_weight=8.5, resources=6, gems=3: redGem@[10,1], blueGem@[11,1], bluePotion@[11,2], redPotion@[11,3], blueGem@[10,5], blueKey@[11,5].",
      "[gem route balance] Large direct resource region [1,7]->[2,11] has resource_weight=6.0, resources=5, gems=2: redGem@[1,7], redPotion@[1,8], blueKey@[1,10], redPotion@[1,11], blueGem@[2,11].",
      "[gem route balance] Gem regions [4,5]->[8,7] and [1,7]->[2,11] are connected by an unusually easy route: score=0.84, hp_loss=36.0, key_cost=0.0, enemies=1, doors=0, steps=2; path [4,7]->[3,7]->[2,7].",
      "[gem route balance] Gem regions [1,1]->[3,5] and [1,7]->[2,11] are connected by an unusually easy route: score=1.19, hp_loss=0.0, key_cost=1.0, enemies=0, doors=1, steps=2; path [2,5]->[2,6]->[2,7].",
      "[gem route balance] Gem regions [9,1]->[11,5] and [10,7]->[11,11] are connected by an unusually easy route: score=1.19, hp_loss=0.0, key_cost=1.0, enemies=0, doors=1, steps=2; path [10,5]->[10,6]->[10,7].",
      "[gem route balance] Gem regions [4,5]->[8,7] and [5,9]->[7,11] are connected by an unusually easy route: score=1.19, hp_loss=0.0, key_cost=1.0, enemies=0, doors=1, steps=2; path [5,7]->[5,8]->[5,9]."
    ],
    "required_changes": [
      "[connectivity density] Add walls at selected open_junction_wall_candidates to break smooth loops, especially around (6,6), (5,7), (7,7), (6,8), and (7,10); also consider (6,1) or (6,2) to reduce the top-center 4-way merge.",
      "[connectivity density] Increase pressure on the cheapest route segment from (5,12) through (5,8) to (6,3): add a meaningful door/enemy choke or wall split around (5,8)-(5,5)-(6,5), so the exit route cannot bypass most branch costs after only two fights.",
      "[connectivity density] Preserve 2 or 3 intentional routes by making the left branch, central shaft, and right branch diverge and rejoin less often; avoid leaving the center cells (5,7), (6,7), (7,7), and (6,8) as an open interchange.",
      "[resource balance] Break bbox [5,9]->[7,12] by moving yellowKey [7,11] to suggested relocation cell [3,2] and redPotion [6,10] to suggested relocation cell [9,2], so the entrance skeleton no longer opens two keys plus potion/gem at once.",
      "[resource balance] Break bbox [3,5]->[8,12] by moving blueGem [5,5] to suggested relocation cell [3,3] and redGem [7,5] to suggested relocation cell [9,3], or add explicit yellow-door/monster pressure before both [5,5] and [7,5].",
      "[gem route balance] Rebuild region [5,9]->[7,11] around blueGem@[5,10]: increase the easiest route difficulty with a real door/enemy/special-damage chokepoint, a longer detour, or by moving this gem deeper into another region.",
      "[gem route balance] Rebuild direct resource region [10,7]->[11,11]: split the resources into staged sub-regions and add pressure on the easiest internal route before the richest rewards.",
      "[gem route balance] Rebuild direct resource region [9,1]->[11,5]: split the resources into staged sub-regions and add pressure on the easiest internal route before the richest rewards.",
      "[gem route balance] Rebuild direct resource region [1,7]->[2,11]: split the resources into staged sub-regions and add pressure on the easiest internal route before the richest rewards.",
      "[gem route balance] Rebuild the connection between gem regions [4,5]->[8,7] and [1,7]->[2,11]: add a stronger route gate or separate the regions so the easiest connection no longer dominates other gem-region choices.",
      "[gem route balance] Rebuild the connection between gem regions [1,1]->[3,5] and [1,7]->[2,11]: add a stronger route gate or separate the regions so the easiest connection no longer dominates other gem-region choices.",
      "[gem route balance] Rebuild the connection between gem regions [9,1]->[11,5] and [10,7]->[11,11]: add a stronger route gate or separate the regions so the easiest connection no longer dominates other gem-region choices.",
      "[gem route balance] Rebuild the connection between gem regions [4,5]->[8,7] and [5,9]->[7,11]: add a stronger route gate or separate the regions so the easiest connection no longer dominates other gem-region choices."
    ],
    "budget_delta": {
      "yellow_doors": 10,
      "blue_doors": 2,
      "red_doors": 0,
      "yellow_keys": 4,
      "blue_keys": 2,
      "red_keys": 0,
      "pickaxes": 1,
      "bombs": 0,
      "centerFly": 0
    },
    "summary": "current: MT2 passes: map shape, tile codes, exact MT2 resources, remaining tower budget, enemy policy, adjacency, and resource progression all validate; entrance-to-exit routing has viable central combat, yellow-door bypass, and gated reward-branch tradeoffs. | connectivity density: Fails connectivity/density review: nominal density is acceptable, but route structure is an over-connected loop network and the cheapest exit route has too little battle/door pressure. | resource balance: Blue-door rewards and the pickaxe at [11,11] are acceptably protected, but the lower central resource/key cluster is too cheap and too concentrated for MT2. | monster damage: Monster pacing is acceptable: the cheap yellow-door exit line still has combat at [6,5] and [6,3], while optional branches use heavier guards such as [6,7], [9,7], [9,9], and [3,4] around richer rewards. No zone or repulse enemies are placed, so there is no decorative or uncompensated zone/repulse damage issue. | gem route balance: Gem route balance reviewer found 8 route/resource imbalance issue(s)."
  }
}

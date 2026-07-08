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
201: greenSlime 绿头怪 hp=32 atk=15 def=1 money=1 special=0
202: redSlime 红头怪 hp=38 atk=22 def=2 money=2 special=0
203: blackSlime 青头怪 hp=60 atk=18 def=7 money=2 special=0
205: bat 小蝙蝠 hp=42 atk=24 def=4 money=3 special=0

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
      "gem_floor_delta_min": 2.0,
      "gem_floor_delta_max": 2.0,
      "potion_floor_delta_min": 0.0,
      "potion_floor_delta_max": 1.0,
      "potion_compare_mode": "red_potion_equiv; exact placed resources: redGem/blueGem MT0=4/4, MT1=5/5, MT2=6/6, MT3=7/7; redPotion counts 6/6/6/7; bluePotion counts 2 per floor; pickaxe on MT0/MT1/MT2 only; centerFly on MT1/MT3 only"
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
    "yellow_doors": null,
    "blue_doors": null,
    "red_doors": null,
    "yellow_keys": null,
    "blue_keys": null,
    "red_keys": null,
    "pickaxes": 3,
    "bombs": 0,
    "centerFly": 2
  },
  "previous_accepted_floor_summaries": [],
  "review_feedback_to_fix": {
    "status": "fail",
    "issues": [
      "[current] Budget delta is within remaining whole-tower budget, and tile codes, dimensions, stairs, enemy policy, enemy adjacency, and MT0 exact resource quotas are valid.",
      "[current] Resource protection fails in the lower-center cluster bbox [[3,6],[9,11]]: after the mandatory greenSlime at [6,10], the yellow doors at [5,9] and [7,9] immediately refund through yellowKeys at [4,9] and [8,9], exposing redPotion [3,7], redGem [3,9], and blueGem [9,9] with no additional combat or lasting key cost.",
      "[current] Route balance fails: the direct central route [6,11]->[6,1] is dominated by taking the lower left/right detours first, because the player returns to the same key state while gaining redGem [3,9], redPotion [3,7], and blueGem [9,9] before continuing.",
      "[resource balance] Low-cost cluster bbox [3,6]->[9,11] is too rich for MT0: redPotion [6,6], redPotion [3,7], redGem [3,9], yellowKey [4,9], yellowKey [8,9], and blueGem [9,9] are all in the first side-stage. After the entrance greenSlime, the yellow doors at [5,9] and [7,9] immediately refund keys while also exposing gems, so the area gives too much resource and key access for a yellow-door baseline.",
      "[resource balance] Keys are bunched in the lower branch: yellowKeys [4,9], [8,9], [1,7] and blueKey [10,7] sit in one early region, collapsing the intended scarce-key pressure instead of staging key recovery across deeper route commitments.",
      "[resource balance] Blue door [9,6] is under-compensated as a blue-door route: it uses nearby blueKey [10,7] to enter an upper-right pocket that is also reachable through yellowDoor [7,5], so it mostly duplicates a yellow-door route rather than unlocking a stronger unique reward or shortcut.",
      "[gem route balance] Entry-to-gem route is too easy for redGem@[3,9] in region [3,7]->[4,9]: score=1.79, hp_loss=15.0, key_cost=1.0, enemies=1, doors=1, steps=5; path [6,11]->[6,10]->[6,9]->[5,9]->[4,9]->[3,9].",
      "[gem route balance] Entry-to-gem route is too easy for blueGem@[9,9] in region [8,7]->[9,9]: score=1.79, hp_loss=15.0, key_cost=1.0, enemies=1, doors=1, steps=5; path [6,11]->[6,10]->[6,9]->[7,9]->[8,9]->[9,9].",
      "[gem route balance] Large direct resource region [1,1]->[8,2] has resource_weight=4.0, resources=4, gems=3: blueGem@[2,1], redGem@[4,1], redPotion@[5,1], blueGem@[7,1]."
    ],
    "required_changes": [
      "[current] Break the refundable-door pattern around [5,9] and [7,9]: move yellowKeys [4,9] and [8,9] behind real branch pressure, such as after existing bat gates near [2,7] and [9,7], or add a non-refunded combat/door commitment before those keys while preserving a viable key-door ordering to [6,2].",
      "[current] Protect or relocate the exposed rewards in bbox [[3,6],[9,11]]. Move redPotion [3,7], redGem [3,9], and/or blueGem [9,9] to higher-cost suggested cells such as [1,1], [3,1], [8,1], [4,3], [8,5], or [9,5], or place blocking combat/door gates on the actual approach after moving the refund keys.",
      "[current] After rebalancing, keep MT0 quotas unchanged: redGem=4, blueGem=4, redPotion=6, bluePotion=2, pickaxe=1, centerFly=0, with no bombs and no orthogonally adjacent enemies.",
      "[resource balance] Break up low-cost cluster bbox [3,6]->[9,11]. Move at least yellowKey [8,9] to [8,3] or [9,2], and move blueGem [9,9] to [9,5] or [8,5]. If the left side remains too rewarding, move redGem [3,9] to [4,3] or [3,1].",
      "[resource balance] Remove the immediate double key refund. Keep at most one early yellowKey near [4,9]/[8,9], or replace one old key cell with a redSlime/blackSlime before the gem pocket and relocate that key to a suggested deeper cell such as [8,3], [9,2], or [4,3].",
      "[resource balance] Make blue door [9,6] unlock a benefit clearly stronger than a yellow-door baseline: either make it the exclusive shortcut into the upper-right reward pocket by blocking/downgrading the alternate [7,5] yellow-door access, or move a stronger unique reward behind [9,6] such as the upper-right gem/potion pair while keeping the yellow-door route separate.",
      "[gem route balance] Rebuild region [3,7]->[4,9] around redGem@[3,9]: increase the easiest route difficulty with a real door/enemy/special-damage chokepoint, a longer detour, or by moving this gem deeper into another region.",
      "[gem route balance] Rebuild region [8,7]->[9,9] around blueGem@[9,9]: increase the easiest route difficulty with a real door/enemy/special-damage chokepoint, a longer detour, or by moving this gem deeper into another region.",
      "[gem route balance] Rebuild direct resource region [1,1]->[8,2]: split the resources into staged sub-regions and add pressure on the easiest internal route before the richest rewards."
    ],
    "budget_delta": {
      "yellow_doors": 6,
      "blue_doors": 2,
      "red_doors": 0,
      "yellow_keys": 3,
      "blue_keys": 1,
      "red_keys": 0,
      "pickaxes": 1,
      "bombs": 0,
      "centerFly": 0
    },
    "summary": "current: MT0 is structurally connected and budget-valid, but fails due to unprotected refundable side-branch rewards that dominate the intended central route. | connectivity density: Connectivity/density pass: wall_ratio 0.615 and main_cycle_rank_ratio 0.062 indicate a controlled dense layout, not an open grid. The floor supports about three candidate entrance-to-exit routes with central/left/right pressure, and min_route_to_exit has 3 enemies plus 2 door cost, which is sufficient for MT0 route pressure. Monster density 0.185 is appropriate and no special monster avoidance issue applies. | resource balance: MT0 fails resource-balance review because early side branches expose too many key refunds and gems for baseline yellow-door costs, and blue door [9,6] does not provide enough unique strategic value over an alternate yellow-door path. | monster damage: Monster pacing is acceptable for MT0: the exit route uses greenSlime [6,10] into blackSlime checks at [2,5] and [3,3], while side rewards are guarded by redSlime/bat/blackSlime at [2,9], [10,9], [2,7], [9,7], and [9,3]. Damage remains meaningful against redPotion=80 without making likely early routes impossible. No zone or repulse monsters are present, so special-damage routing is not applicable. | gem route balance: Gem route balance reviewer found 3 route/resource imbalance issue(s)."
  }
}

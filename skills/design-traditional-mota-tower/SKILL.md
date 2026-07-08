---
name: design-traditional-mota-tower
description: Understand and confirm the overall design brief for a classic mota-js Magic Tower before any per-floor generation. Use as the first stage of a code-orchestrated tower build pipeline when the user provides a traditional tower idea, global rule preferences, resource constraints, monster constraints, or floor-count intent. Do not use for generating individual floors, reviewing floors, or directly editing mota-js files.
---

# Design Traditional Mota Tower

## Role

Act as the stage-0 understanding agent for a traditional Magic Tower build pipeline.

Convert the user's broad idea into a concise, confirmed whole-tower brief. The brief is consumed by code, then reused by per-floor production and review agents. Do not generate individual floors in this stage.

## Fixed Rules

- Treat the current `mota-js` project as the tower to be transformed.
- Design a classic tower that is structurally clear, resource-computable, passable, and choice-driven.
- Prioritize numeric quality, route choices, key-door pressure, and battle pacing.
- Avoid complex story, random systems, script-heavy mechanics, plugin mechanics, new assets, UI work, and decorative map novelty.
- Use square floors. Supported floor sizes are 9x9, 11x11, and 13x13; default to 11x11 unless the user requests another supported size.
- Do not require an outer wall border. Let walls, doors, monsters, nets, and tools define the topology.
- Use tile code `0` as the only passable/default ground code and tile code `1` as the only wall code. Do not use alternate ground, grass, thin-wall, white-wall, blue-wall, or other wall terrain codes.
- Avoid large empty areas and repeated wall padding.
- Avoid exposing many high-value resources without cost.
- Require each floor to have at least three route families and around 8-12 branch, pocket, shortcut, or gated-access opportunities.
- Prefer broken-but-purposeful wall structure: fragments, pockets, and gaps must serve access cost, reward protection, tool value, special pressure, or route choice.
- Adjacent floors should not reuse the same wall mask or structural grammar.

## Monster Ability Policy

- Monsters may have no special ability, represented as `special: 0` or `special: []`.
- Allowed special ability whitelist:
  - `1`: 先攻
  - `2`: 魔攻
  - `3`: 坚固
  - `15`: 领域
  - `18`: 阻击
- Each monster has at most one special ability unless the user explicitly changes this rule.
- At least half of all actively used monster types must have no special ability.
- Each floor may use at most `monster_types_per_floor`. If unspecified, set it to `9`.
- Each floor must place 22-33 enemy tiles by default: `enemy_count_min_per_floor=22` and `enemy_count_max_per_floor=33`.
- Monster tiers should overlap between adjacent floors: a stronger subset of the previous floor's monster pool may appear on the next floor, but weak lower-tier enemies should not keep reappearing on higher floors.
- Zone and repulse damage should be 50%-100% of the red potion value.
- Enemy tiles may not be orthogonally adjacent; diagonal contact is allowed.
- Gem and potion totals should not decrease on higher floors; normal floor-to-floor increases are 0-2.

## Parameters To Confirm

Before returning a buildable brief, identify whether these values are present or need confirmation:

- `floor_count`
- `floor_size`: use 11 if unspecified; otherwise use only 9, 11, or 13.
- Initial hero HP, attack, defense, money, and starting yellow/blue/red keys.
- Red, blue, and green gem values.
- Red, blue, yellow, and green potion values.
- Shop progressive gold-cost rule and attack/defense gain per purchase.
- Whole-tower yellow/blue/red door quantity or density.
- Whole-tower yellow/blue/red key, pickaxe, bomb, and centerFly quantity or density.

## Output Contract

Return only JSON when used by the build script.

Use this shape:

```json
{
  "status": "ready",
  "summary": "brief human-readable whole-tower summary",
  "floor_count": 5,
  "floor_size": 11,
  "fixed_rules": ["default 11x11 floors unless user requests 9x9 or 13x13", "direct floor map generation"],
  "global_limits": {
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
    "allowed_specials": [1, 2, 3, 15, 18],
    "max_specials_per_monster": 1,
    "min_no_special_ratio": 0.5,
    "monster_types_per_floor": 9,
    "enemy_count_min_per_floor": 22,
    "enemy_count_max_per_floor": 33,
    "floor_overlap_ratio": 0.7,
    "special_damage_red_potion_min": 0.5,
    "special_damage_red_potion_max": 1.0,
    "no_adjacent_enemies": true
  },
  "resource_policy": {
    "gem_floor_delta_min": 0,
    "gem_floor_delta_max": 2,
    "potion_floor_delta_min": 0,
    "potion_floor_delta_max": 2,
    "potion_compare_mode": "red_potion_equiv"
  },
  "layout_policy": ["no naked piles of high-value resources"],
  "questions": [],
  "confirmation_prompt": "Confirm this whole-tower brief before floor generation."
}
```

Set `status` to `needs_input` if required information is too vague to proceed. In that case, fill `questions` with concise questions and do not invent hidden defaults except for `floor_size = 11`, `monster_types_per_floor = 9`, `enemy_count_min_per_floor = 22`, and `enemy_count_max_per_floor = 33`.

## Boundary

- Do not generate floor maps.
- Do not review floor maps.
- Do not edit project files.
- Do not hand off to `modify-mota-global-data`, `modify-mota-enemy-data`, or `modify-mota-map`; the code orchestrator decides when implementation begins.

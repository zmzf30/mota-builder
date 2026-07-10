---
name: design-traditional-mota-tower
description: Understand and confirm the overall design brief for a classic mota-js Magic Tower before any per-floor generation. Use as the first stage of a code-orchestrated tower build pipeline when the user provides a traditional tower idea, global rule preferences, resource constraints, monster constraints, or floor-count intent. Do not use for generating individual floors, reviewing floors, or directly editing mota-js files.
---

# Design Traditional Mota Tower

## Role

Act as the stage-0 understanding agent for a classic Magic Tower build pipeline with two layout styles.

Convert the user's broad idea into a concise, confirmed whole-tower brief. The brief is consumed by code, then reused by per-floor production and review agents. Do not generate individual floors in this stage.

## Real Few-Shot Input

When `Real few-shot tower progression input` is present, it was extracted from actual mota-js projects, not from prose-only reference names. Use its per-floor metrics, route costs, resource-access stages, initial hero, and item values to infer uneven floor roles and whole-tower pacing. Do not flatten every floor into the same resource recipe. The user's explicit totals and restrictions remain authoritative.

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
- Set `tower_style` to exactly `traditional` or `red_sea`; default to `traditional`.
- For `traditional`, target wall ratio 0.35-0.45, 2-4 route families, 6-20 meaningful decisions, 18-28 enemies, 2-6 special-pressure positions, 0.5-2 tools per floor on average, 70%-90% protected important resources, and 0%-10% key/resource safety margin. Use clear regions with multiple kinds of branches.
- For `red_sea`, target wall ratio 0.45-0.55, 22-33 enemies, purposeful fragmented walls, narrow routes, at least 3 route families, and around 10-40 meaningful local opportunities. Distribute rewards and protect nearly every valuable reward.
- Never infer numeric difficulty or stronger monster HP/ATK/DEF from `tower_style`.
- Red-sea style does not authorize clamp, drain, self-destruct, lamps, arrows, one-way tiles, scripts, or any other unsupported mechanism.
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
- Traditional floors place 18-28 enemy tiles by default; red-sea floors place 22-33. Explicit user settings remain authoritative.
- Always set the initial monster book to exactly one: `global_settings.initial_hero.tools.book=1`. Do not ask the user to choose it.
- Monster tiers should overlap between adjacent floors: a stronger subset of the previous floor's monster pool may appear on the next floor, but weak lower-tier enemies should not keep reappearing on higher floors.
- Zone and repulse damage should be 50%-100% of the red potion value.
- Enemy tiles may not be orthogonally adjacent; diagonal contact is allowed.
- Gem and potion totals should not decrease on higher floors; normal floor-to-floor increases are 0-2.

## Parameters To Confirm

Before returning a buildable brief, identify whether these values are present or need confirmation:

- `floor_count`
- `floor_size`: use 11 if unspecified; otherwise use only 9, 11, or 13.
- Initial hero HP, attack, defense, money, starting yellow/blue/red keys, starting pickaxe, bomb, centerFly, and jumpShoes. Monster book is fixed to 1.
- Red, blue, and green gem values.
- Red, blue, yellow, and green potion values.
- Shop progressive gold-cost rule and attack/defense gain per purchase.
- Whole-tower yellow/blue/red door quantity or density.
- Whole-tower yellow/blue/red key, pickaxe, bomb, centerFly, jumpShoes, gem, and potion quantity or density.

## Whole-Tower Floor Progression

When the brief is ready, define one `floor_progression_plan` entry per floor. This is the semantic whole-tower route plan consumed by later stages. Each entry must identify the floor's distinct role, route archetypes, key/door arc, staged resource access, combat threshold, tool acquisition or payoff, carry-forward intent, and the concrete reference patterns that informed it. Avoid assigning every floor the same recipe.

## Output Contract

Return only JSON when used by the build script.

Use this shape:

```json
{
  "status": "ready",
  "summary": "brief human-readable whole-tower summary",
  "tower_style": "traditional",
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
    "centerFly": 0,
    "jumpShoes": 0,
    "redGems": 0,
    "blueGems": 0,
    "greenGems": 0,
    "redPotions": 0,
    "bluePotions": 0,
    "yellowPotions": 0,
    "greenPotions": 0
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
      },
      "tools": {
        "pickaxe": 0,
        "bomb": 0,
        "centerFly": 0,
        "jumpShoes": 0,
        "book": 1
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
    "enemy_count_min_per_floor": 18,
    "enemy_count_max_per_floor": 28,
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
  "floor_progression_plan": [
    {
      "floor_index": 0,
      "role": "opening fork and first key commitment",
      "resource_budget": {
        "yellow_doors": 4, "blue_doors": 1, "red_doors": 0,
        "yellow_keys": 2, "blue_keys": 0, "red_keys": 0,
        "pickaxes": 0, "bombs": 0, "centerFly": 0, "jumpShoes": 0,
        "redGems": 6, "blueGems": 6, "greenGems": 0,
        "redPotions": 6, "bluePotions": 1, "yellowPotions": 0, "greenPotions": 0
      },
      "route_archetypes": ["short combat tax", "long resource route", "locked optional pocket"],
      "key_door_arc": "teach one competing yellow-key use and preserve the option to carry one key forward",
      "resource_access_arc": "one free starter item, then two separately gated reward stages",
      "combat_threshold_arc": "a reachable gem changes one optional guard from expensive to efficient",
      "tool_arc": "foreshadow a later wall shortcut; do not award the tool yet",
      "carry_forward_intent": "player may leave with either an extra key or an extra stat reward, not both",
      "reference_patterns": ["reference project/floor and the relationship borrowed from it"]
    }
  ],
  "questions": [],
  "confirmation_prompt": "Confirm this whole-tower brief before floor generation."
}
```

Every `floor_progression_plan` entry must contain all fields of `resource_budget`. For every numeric whole-tower limit, per-floor values must be non-negative integers whose sum exactly matches that limit. Allocate by floor role and intended access pressure instead of evenly dividing by default.

Set `status` to `needs_input` if required information is too vague to proceed. In that case, fill `questions` with concise questions. Defaults are `floor_size = 11`, `tower_style = traditional`, `monster_types_per_floor = 9`, traditional enemy count 18-28, red-sea enemy count 22-33, and initial monster book 1.

## Boundary

- Do not generate floor maps.
- Do not review floor maps.
- Do not edit project files.
- Do not hand off to `modify-mota-global-data`, `modify-mota-enemy-data`, or `modify-mota-map`; the code orchestrator decides when implementation begins.

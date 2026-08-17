import unittest

from scripts.build_mota_tower import (
    DEFAULT_CROSS_FLOOR_ATTACK_MULTIPLIER,
    DEFAULT_CROSS_FLOOR_MAX_SPAN,
    DEFAULT_CROSS_FLOOR_ROLES,
    DEFAULT_ENEMY_ROLE_SLOTS,
    build_role_slot_floor_policies,
    enemy_role_contract_error,
    role_contract_review_issues,
    role_slot_targets,
)


def role_brief(limit: int = 12) -> dict:
    return {
        "tower_style": "traditional",
        "global_settings": {
            "initial_hero": {"hp": 10000, "atk": 100, "def": 90},
            "potions": {"redPotion": 100, "bluePotion": 300},
        },
        "global_limits": {},
        "monster_policy": {
            "candidate_types_per_floor": limit,
            "monster_types_per_floor": limit,
            "role_slots": DEFAULT_ENEMY_ROLE_SLOTS,
            "cross_floor_roles": DEFAULT_CROSS_FLOOR_ROLES,
            "cross_floor_max_span": DEFAULT_CROSS_FLOOR_MAX_SPAN,
            "cross_floor_attack_multiplier": DEFAULT_CROSS_FLOOR_ATTACK_MULTIPLIER,
        },
    }


def role_enemy(role: str, index: int) -> tuple[dict, dict]:
    enemy = {"hp": 100, "atk": 100, "def": 50, "special": 0}
    if role == "high_attack":
        enemy.update({"hp": 500, "atk": 600, "def": 50})
    elif role == "balanced":
        enemy.update({"hp": 486, "atk": 162, "def": 55})
    elif role == "magic":
        enemy.update({"hp": 400, "atk": 80, "def": 54, "special": 2})
    elif role == "zone":
        enemy.update({"hp": 600, "atk": 270, "def": 100, "special": 15, "zone": 75})
    elif role == "repulse":
        enemy.update({"hp": 540, "atk": 243, "def": 90, "special": 18, "repulse": 75})
    elif role == "high_hp":
        enemy.update({"hp": 1000, "atk": 135, "def": 67})
    elif role == "gem_gate":
        enemy.update({"hp": 100, "atk": 180, "def": 117})
    elif role == "strong":
        enemy.update({"hp": 600, "atk": 360, "def": 77})
    enemy_id = f"{role}_{index}"
    candidate = {
        "id": enemy_id,
        "code": 200 + index,
        **enemy,
        "numeric_score": enemy["hp"] * 0.08 + enemy["atk"] * 2 + enemy["def"] * 2.5,
        "special": [enemy["special"]] if enemy["special"] else [],
        "role": role,
        "cross_floor": role in DEFAULT_CROSS_FLOOR_ROLES,
    }
    return candidate, enemy


class EnemyRoleContractTest(unittest.TestCase):
    def test_default_role_slots_expand_to_three_balanced_and_strong(self) -> None:
        targets = role_slot_targets(role_brief(), 12)
        self.assertEqual(targets["balanced"], 3)
        self.assertEqual(targets["strong"], 3)
        self.assertEqual(sum(targets.values()), 12)

    def test_role_selector_limits_carry_to_two_consecutive_floors(self) -> None:
        candidates = []
        enemys = {}
        index = 0
        for role, limits in DEFAULT_ENEMY_ROLE_SLOTS.items():
            for variant in range(6):
                candidate, enemy = role_enemy(role, index)
                candidates.append(candidate)
                enemys[candidate["id"]] = enemy
                index += 1
        hero = [
            {
                "target": {"hp": 10000, "atk": 100, "def": 90},
                "completion": {"hp": 12000, "atk": 120, "def": 110},
            }
            for _ in range(4)
        ]
        policies = build_role_slot_floor_policies(4, candidates, enemys, role_brief(), hero, 12)
        self.assertTrue(all(policy["role_slot_counts"].get("strong") == 3 for policy in policies))
        for floor_index in range(2, len(policies)):
            repeated = set(policies[floor_index - 1]["allowed_enemy_ids"]) & set(
                policies[floor_index - 2]["allowed_enemy_ids"]
            )
            self.assertFalse(repeated & set(policies[floor_index]["allowed_enemy_ids"]))
        for floor_index in range(1, len(policies)):
            previous_strong = {
                enemy_id
                for enemy_id, role in policies[floor_index - 1]["enemy_role_hints"].items()
                if role == "strong"
            }
            current_strong = {
                enemy_id
                for enemy_id, role in policies[floor_index]["enemy_role_hints"].items()
                if role == "strong"
            }
            self.assertFalse(previous_strong & current_strong)

    def test_review_rejects_low_non_magic_attack_and_three_floor_carry(self) -> None:
        brief = role_brief(1)
        brief["monster_policy"]["role_slots"] = {"high_attack": {"min": 1, "max": 1}}
        enemy = {"hp": 500, "atk": 600, "def": 50, "special": 0}
        policies = []
        for floor_index in range(3):
            policies.append(
                {
                    "floor_index": floor_index,
                    "allowed_enemy_ids": ["same"],
                    "enemy_role_hints": {"same": "high_attack"},
                    "enemy_role_families": {"same": "high_attack"},
                    "enemy_combat_metrics": {"same": {"killable": True, "difficulty_score": 1.0}},
                    "enemy_raw_strength": {"same": 100},
                    "estimated_hero_bands": {
                        "target": {"hp": 10000, "atk": 100, "def": 90},
                        "completion": {"hp": 12000, "atk": 120, "def": 110},
                    },
                }
            )
        issues = role_contract_review_issues(policies, {"same": enemy}, brief)
        reasons = [issue["reason"] for issue in issues]
        self.assertTrue(any("three consecutive floors" in reason for reason in reasons))

        policies[0]["enemy_role_hints"]["same"] = "balanced"
        low_attack = {"hp": 300, "atk": 50, "def": 40, "special": 0}
        issues = role_contract_review_issues([policies[0]], {"same": low_attack}, brief)
        self.assertTrue(any("below projected hero DEF" in issue["reason"] for issue in issues))

    def test_carry_threshold_uses_current_floor_completion_defense(self) -> None:
        brief = role_brief(1)
        brief["monster_policy"]["role_slots"] = {"high_attack": {"min": 1, "max": 1}}
        enemy = {"hp": 500, "atk": 600, "def": 50, "special": 0}
        policies = []
        for floor_index, completion_def in enumerate((110, 500)):
            policies.append(
                {
                    "floor_index": floor_index,
                    "allowed_enemy_ids": ["same"],
                    "enemy_role_hints": {"same": "high_attack"},
                    "enemy_role_families": {"same": "high_attack"},
                    "enemy_combat_metrics": {"same": {"killable": True, "difficulty_score": 1.0}},
                    "enemy_raw_strength": {"same": 100},
                    "estimated_hero_bands": {
                        "target": {"hp": 10000, "atk": 100, "def": 90},
                        "completion": {"hp": 12000, "atk": 120, "def": completion_def},
                    },
                }
            )
        issues = role_contract_review_issues(policies, {"same": enemy}, brief)
        self.assertTrue(any("current completion DEF 500" in issue["reason"] for issue in issues))

    def test_repulse_contract_is_0_85_to_0_95_of_zone_attack(self) -> None:
        hero_bands = {
            "target": {"atk": 100, "def": 90},
            "completion": {"atk": 120, "def": 110},
        }
        valid = {"hp": 540, "atk": 270, "def": 100}
        invalid = {"hp": 540, "atk": 220, "def": 90}
        self.assertLessEqual(enemy_role_contract_error(valid, "repulse", hero_bands), 0.01)
        self.assertGreater(enemy_role_contract_error(invalid, "repulse", hero_bands), 0.05)

    def test_carried_enemy_uses_attack_gate_instead_of_new_floor_role_ratio(self) -> None:
        brief = role_brief(1)
        brief["monster_policy"]["role_slots"] = {"balanced": {"min": 1, "max": 1}}
        enemy = {"hp": 540, "atk": 180, "def": 63, "special": 0}
        policies = [
            {
                "floor_index": 0,
                "allowed_enemy_ids": ["same"],
                "enemy_role_hints": {"same": "balanced"},
                "enemy_role_families": {"same": "balanced"},
                "enemy_combat_metrics": {"same": {"killable": True, "difficulty_score": 1.0}},
                "enemy_raw_strength": {"same": 100},
                "estimated_hero_bands": {
                    "target": {"hp": 10000, "atk": 100, "def": 90},
                    "completion": {"hp": 12000, "atk": 120, "def": 110},
                },
            },
            {
                "floor_index": 1,
                "allowed_enemy_ids": ["same"],
                "enemy_role_hints": {"same": "balanced"},
                "enemy_role_families": {"same": "balanced"},
                "enemy_combat_metrics": {"same": {"killable": True, "difficulty_score": 1.0}},
                "enemy_raw_strength": {"same": 100},
                "estimated_hero_bands": {
                    "target": {"hp": 10000, "atk": 300, "def": 130},
                    "completion": {"hp": 12000, "atk": 320, "def": 130},
                },
            },
        ]
        issues = role_contract_review_issues(policies, {"same": enemy}, brief)
        self.assertFalse(any("violates balanced stat contract" in issue["reason"] for issue in issues))


if __name__ == "__main__":
    unittest.main()

import argparse
from pathlib import Path
import tempfile
import unittest

from scripts.build_mota_tower import run_route_balance_review, route_sensitivity_issues_from_report
from scripts.mota_route_balance import (
    _battle_damage,
    _build_special_coverage,
    _deterministic_monster_sample,
    analyze_route_balance,
    analyze_route_sensitivity,
)


MAPS = {
    "1": {"cls": "animates", "id": "yellowWall"},
    "21": {"cls": "terrains", "id": "yellowDoor"},
    "22": {"cls": "terrains", "id": "blueDoor"},
    "27": {"cls": "items", "id": "redGem"},
    "87": {"cls": "terrains", "id": "downFloor"},
    "201": {"cls": "enemys", "id": "routeA"},
    "202": {"cls": "enemys", "id": "routeB"},
    "203": {"cls": "enemys", "id": "routeC"},
    "204": {"cls": "enemys", "id": "decorative"},
}


def balance_floor() -> dict:
    matrix = [[1 for _ in range(9)] for _ in range(9)]
    for y in range(3, 6):
        for x in range(1, 8):
            matrix[y][x] = 0
    # A three-cell pressure cut separates one free entrance region from one
    # free gem region. Each cut cell is one real route family.
    matrix[3][4] = 201
    matrix[4][4] = 202
    matrix[5][4] = 203
    matrix[7][1] = 87
    matrix[6][1] = 0
    matrix[1][7] = 27
    matrix[2][7] = 0
    return {
        "floor_index": 0,
        "floor_id": "MT0",
        "floor": {"floorId": "MT0", "width": 9, "height": 9, "map": matrix},
    }


def request(enemys: dict) -> dict:
    return {
        "floor_output": balance_floor(),
        "maps": MAPS,
        "enemys": enemys,
        "hero": {"atk": 10, "def": 10, "mdef": 0},
        "gem_values": {"redGem": 3, "blueGem": 3, "greenGem": 5},
        "red_potion_hp": 100,
        "config": {
            "required_routes": 3,
            "ratio_threshold": 0.8,
            "max_expansions": 10000,
            "max_seconds": 1,
            "max_routes": 6,
        },
    }


class RouteBalanceSearchTest(unittest.TestCase):
    def test_three_close_route_families_pass(self) -> None:
        enemys = {
            "routeA": {"hp": 15, "atk": 160, "def": 0, "special": 0},
            "routeB": {"hp": 15, "atk": 170, "def": 0, "special": 0},
            "routeC": {"hp": 15, "atk": 180, "def": 0, "special": 0},
        }
        report = analyze_route_balance(request(enemys))
        self.assertEqual(report["status"], "pass")
        selected = report["groups"][0]["selected_signature_group"]
        self.assertGreaterEqual(selected["route_family_count"], 3)
        self.assertGreaterEqual(selected["balance_score"], 0.8)
        self.assertFalse(report["search"]["truncated"])
        self.assertTrue(report["search"]["early_stopped_after_all_targets_passed"])
        self.assertLess(report["graph"]["graph_nodes"], report["graph"]["passable_cells"])
        self.assertGreaterEqual(report["graph"]["safe_area_nodes"], 2)
        self.assertEqual(report["graph"]["auto_collected_safe_gems"], 1)

    def test_expensive_third_route_fails(self) -> None:
        enemys = {
            "routeA": {"hp": 15, "atk": 160, "def": 0, "special": 0},
            "routeB": {"hp": 15, "atk": 170, "def": 0, "special": 0},
            "routeC": {"hp": 15, "atk": 300, "def": 0, "special": 0},
        }
        report = analyze_route_balance(request(enemys))
        self.assertEqual(report["status"], "fail")
        self.assertLess(report["groups"][0]["selected_signature_group"]["balance_score"], 0.8)

    def test_inert_door_is_reported_by_full_ablation(self) -> None:
        floor_output = balance_floor()
        matrix = floor_output["floor"]["map"]
        # Three two-tile routes cost 2.0, 2.2, and 2.5. Removing the yellow
        # door keeps that order; removing the blue door promotes its route.
        matrix[3][4], matrix[3][5] = 21, 201
        matrix[4][4], matrix[4][5] = 22, 203
        matrix[5][4], matrix[5][5] = 202, 201
        enemys = {
            "routeA": {"hp": 15, "atk": 60, "def": 0, "special": 0},
            "routeB": {"hp": 15, "atk": 180, "def": 0, "special": 0},
            "routeC": {"hp": 1, "atk": 0, "def": 0, "special": 0},
        }
        payload = request(enemys)
        payload["floor_output"] = floor_output
        baseline = analyze_route_balance(payload)
        sensitivity = analyze_route_sensitivity(payload, baseline)
        selected = baseline["groups"][0]["selected_signature_group"]
        self.assertEqual(
            [route["cost"] for route in selected["routes"][:3]],
            [2.0, 2.2, 2.5],
        )
        self.assertEqual(sensitivity["status"], "fail")
        self.assertEqual(len(sensitivity["door_tests"]), 2)
        self.assertEqual(
            [(item["id"], item["coord"]) for item in sensitivity["inert_doors"]],
            [("yellowDoor", [4, 3])],
        )
        blue_test = next(item for item in sensitivity["door_tests"] if item["id"] == "blueDoor")
        self.assertTrue(blue_test["changed"])
        with tempfile.TemporaryDirectory() as tmp:
            review = run_route_balance_review(
                argparse.Namespace(), Path(tmp) / "MT0_integration", payload, run_agent=False
            )
        self.assertEqual(review["status"], "fail")
        self.assertEqual(
            review["route_balance_report"]["sensitivity"]["inert_doors"][0]["id"],
            "yellowDoor",
        )

    def test_route_gate_is_changed_when_removal_opens_the_target_region(self) -> None:
        floor_output = balance_floor()
        floor_output["floor"]["map"][3][4] = 21
        enemys = {
            "routeB": {"hp": 15, "atk": 170, "def": 0, "special": 0},
            "routeC": {"hp": 15, "atk": 180, "def": 0, "special": 0},
        }
        payload = request(enemys)
        payload["floor_output"] = floor_output
        baseline = analyze_route_balance(payload)
        sensitivity = analyze_route_sensitivity(payload, baseline)
        self.assertEqual(baseline["status"], "pass")
        self.assertTrue(sensitivity["door_tests"][0]["changed"])
        self.assertEqual(sensitivity["inert_doors"], [])

    def test_inert_optional_monster_is_reported_for_agent_consideration(self) -> None:
        floor_output = balance_floor()
        floor_output["floor"]["map"][4][2] = 204
        floor_output["floor"]["map"][6][1] = 204  # Blocking this entrance monster cuts every route.
        enemys = {
            "routeA": {"hp": 15, "atk": 160, "def": 0, "special": 0},
            "routeB": {"hp": 15, "atk": 170, "def": 0, "special": 0},
            "routeC": {"hp": 15, "atk": 180, "def": 0, "special": 0},
            "decorative": {"hp": 15, "atk": 170, "def": 0, "special": 0},
        }
        payload = request(enemys)
        payload["floor_output"] = floor_output
        baseline = analyze_route_balance(payload)
        sensitivity = analyze_route_sensitivity(payload, baseline)
        self.assertEqual(sensitivity["status"], "pass")
        self.assertEqual(sensitivity["sampled_enemy_count"], 4)
        self.assertIn([2, 4], [item["coord"] for item in sensitivity["inert_monsters"]])
        self.assertNotIn([1, 6], [item["coord"] for item in sensitivity["monster_tests"]])

    def test_optional_monster_sample_is_deterministic_and_capped_at_five(self) -> None:
        candidates = [
            {"coord": [index, 1], "id": f"enemy{index}", "code": 200 + index}
            for index in range(8)
        ]
        first = _deterministic_monster_sample(candidates, "MT3", 5, "fixed")
        second = _deterministic_monster_sample(list(reversed(candidates)), "MT3", 5, "fixed")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)

    def test_reviewer_fails_inert_doors_but_only_warns_for_monsters(self) -> None:
        issues = route_sensitivity_issues_from_report({
            "sensitivity": {
                "inert_doors": [{"coord": [2, 4], "id": "yellowDoor"}],
                "inert_monsters": [{"coord": [3, 4], "id": "decorative"}],
            }
        })
        self.assertEqual([issue["severity"] for issue in issues], ["fail", "warn"])
        self.assertTrue(all(issue["repair_stage"] == "encounter" for issue in issues))

    def test_gem_gain_changes_later_battle_damage(self) -> None:
        enemy = {"hp": 20, "atk": 30, "def": 9, "special": 0}
        before = _battle_damage(enemy, atk=10, defense=10, mdef=0)
        after = _battle_damage(enemy, atk=13, defense=10, mdef=0)
        self.assertLess(after, before)

    def test_solid_and_shield_follow_mota_rules(self) -> None:
        enemy = {"hp": 3, "atk": 30, "def": 0, "special": [1, 3]}
        without_shield = _battle_damage(enemy, atk=20, defense=10, mdef=0)
        with_shield = _battle_damage(enemy, atk=20, defense=10, mdef=15)
        self.assertGreater(without_shield, with_shield)
        self.assertEqual(with_shield, max(0, without_shield - 15))

    def test_special_coverage_is_preindexed_per_micro_node(self) -> None:
        coverage = _build_special_coverage(
            5,
            5,
            [{
                "obstacle_index": 0,
                "coord": (2, 2),
                "enemy": {"zone": 30, "repulse": 20, "range": 1},
                "specials": {15, 18},
            }],
        )
        self.assertEqual(set(coverage), {(1, 2), (3, 2), (2, 1), (2, 3)})
        self.assertEqual(
            {event["kind"] for event in coverage[(1, 2)]},
            {"zone", "repulse"},
        )


if __name__ == "__main__":
    unittest.main()

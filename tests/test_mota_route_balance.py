import unittest

from scripts.mota_route_balance import _battle_damage, _build_special_coverage, analyze_route_balance


MAPS = {
    "1": {"cls": "animates", "id": "yellowWall"},
    "27": {"cls": "items", "id": "redGem"},
    "87": {"cls": "terrains", "id": "downFloor"},
    "201": {"cls": "enemys", "id": "routeA"},
    "202": {"cls": "enemys", "id": "routeB"},
    "203": {"cls": "enemys", "id": "routeC"},
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

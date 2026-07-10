#!/usr/bin/env python3
"""Extract and retrieve real mota-js floor examples for generation prompts.

The source projects are read-only.  Numeric tile codes are project-local, so the
extractor always carries the source map table, a semantic map, route skeletons,
and approximate resource-access order alongside the original map matrix.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import heapq
import json
import re
from pathlib import Path
from typing import Any


CORPUS_VERSION = "mota-few-shot-v2-style"
SELECTION_PLAN_VERSION = "mota-few-shot-selection-v3-style-split"
TRADITIONAL_LAYOUT_SELECTION_PLAN_VERSION = "mota-few-shot-selection-v4-traditional-layout-curation"
DEFAULT_REFERENCE_ROOT = Path.home() / "Documents" / "例子"
DEFAULT_BUNDLED_CORPUS = Path(__file__).resolve().parents[1] / "references" / "few-shot" / "corpus.json"

TOWER_STYLES = {"traditional", "red_sea"}
DEFAULT_TOWER_STYLE = "traditional"
BUNDLED_STYLE_PROJECTS: dict[str, str] = {
    "寒云谷2103": "traditional",
    "溯": "traditional",
    "CCW": "traditional",
    "红蓝的记忆2.10": "red_sea",
    "星月神话 2.10.3": "red_sea",
    "dist": "red_sea",
    "剑阁2.9": "red_sea",
    "出塞V2.10.0": "red_sea",
}

# Traditional layout calibration is intentionally narrower than the full
# traditional corpus.  These are the user-curated floors whose sparse layout
# and strongly controlled resource access should guide per-floor generation
# and review.  Enemy-table few-shot selection remains based on the full style
# corpus and is built independently below.
TRADITIONAL_LAYOUT_REFERENCE_IDS = frozenset({
    "寒云谷2103/MT2",
    "寒云谷2103/MT3",
    "寒云谷2103/MT4",
    "寒云谷2103/MT7",
    "寒云谷2103/MT8",
    "寒云谷2103/MT11",
    "寒云谷2103/MT12",
    "溯/MT2",
    "溯/MT3",
    "溯/MT5",
    "溯/MT6",
    "溯/MT7",
    "溯/MT8",
    "溯/MT9",
})

TRADITIONAL_LAYOUT_RESOURCE_REWRITES: dict[str, dict[str, str]] = {
    "寒云谷2103": {
        # Debuff cures and money pickups are treated as ordinary controlled
        # stat rewards in the layout reference.
        "poisonWine": "redGem",
        "weakWine": "blueGem",
        # The combined cure includes the requested poison/weakness cures.
        "superWine": "redGem",
        "coin": "redGem",
        "pack": "blueGem",
        "I343": "redGem",
    },
    "溯": {
        "greenGem": "redGem",
        "yellowGem": "blueGem",
        "redDoor": "blueDoor",
        "redKey": "blueKey",
    },
}

RESOURCE_IDS = {
    "yellowKey", "blueKey", "redKey", "greenKey", "steelKey", "bigKey",
    "redGem", "blueGem", "greenGem", "yellowGem",
    "redPotion", "bluePotion", "greenPotion", "yellowPotion", "superPotion",
    "pickaxe", "bomb", "centerFly", "jumpShoes", "book", "fly",
    "sword0", "sword1", "sword2", "sword3", "sword4", "sword5",
    "shield0", "shield1", "shield2", "shield3", "shield4", "shield5",
}

FORMAT_ONLY_PREFIXES = ("HTML5魔塔样板",)

# These are the calibration anchors already named by review-mota-floor.  The
# difference is that retrieval now supplies their actual maps and data.
ANCHOR_BONUSES: dict[str, dict[tuple[str, str], float]] = {
    "topology": {
        ("红蓝的记忆2.10", "MT6"): 12,
        ("一层小塔 2.10", "MT0"): 11,
        ("剑阁2.9", "MT3"): 10,
        ("剑阁2.9", "MT6"): 10,
        ("dist", "MT1"): 9,
        ("dist", "MT2"): 9,
    },
    "economy": {
        ("红蓝的记忆2.10", "MT6"): 12,
        ("一层小塔 2.10", "MT0"): 11,
        ("剑阁2.9", "MT3"): 10,
        ("出塞V2.10.0", "MT0"): 9,
        ("出塞V2.10.0", "MT1"): 9,
        ("出塞V2.10.0", "MT2"): 9,
        ("星月神话 2.10.3", "MT7"): 9,
        ("星月神话 2.10.3", "MT8"): 9,
    },
    "monster": {
        ("红蓝的记忆2.10", "MT1"): 12,
        ("红蓝的记忆2.10", "MT4"): 12,
        ("dist", "MT1"): 11,
        ("dist", "MT2"): 11,
        ("Oblivion 2.10", "MT1"): 11,
    },
}
ANCHOR_BONUSES["integration"] = {
    key: max(
        ANCHOR_BONUSES["topology"].get(key, 0),
        ANCHOR_BONUSES["economy"].get(key, 0),
        ANCHOR_BONUSES["monster"].get(key, 0),
    )
    for key in set().union(*(value.keys() for value in ANCHOR_BONUSES.values()))
}

REVIEWER_CONTRASTIVE_REJECTION_CASES: dict[str, list[str]] = {
    "topology": [
        "Reject a different-looking wall mask that repeats the same structural grammar as an adjacent floor.",
        "Reject the style-required annotated candidate routes when they collapse to the same practical entrance-to-exit path.",
        "Reject checkerboard fragments, one-cell corridor filler, or dead pockets that cannot carry later cost/reward meaning.",
    ],
    "economy": [
        "Reject evenly sprinkled per-floor quotas when resources do not have visibly different access stages.",
        "Reject a stronger door, longer detour, or tool commitment that has no stronger compensation than the baseline route.",
        "Reject naked high-value resource clusters or tools reachable in the free entrance region without a meaningful commitment.",
    ],
    "monster": [
        "Reject enemies added only to reach the count when they do not tax a route, guard value, or create a threshold.",
        "Reject zone or repulse enemies whose coverage does not materially affect movement, access, or compensation.",
        "Reject a monster pool whose apparent roles collapse to nearly identical combat thresholds.",
    ],
    "integration": [
        "Reject a floor that passes tile and count checks but does not materially express its floor_progression_plan.",
        "Reject route sets where one route has both lower total cost and greater reachable reward than every alternative.",
        "Reject cross-stage composition that destroys the topology's intended choice or the economy's access order.",
    ],
}

class FewShotError(RuntimeError):
    pass


def load_reference_corpus(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    try:
        corpus = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FewShotError(f"cannot load bundled few-shot corpus {path}: {exc}") from exc
    if not isinstance(corpus, dict) or not isinstance(corpus.get("floors"), list):
        raise FewShotError(f"invalid few-shot corpus: {path}")
    if corpus.get("version") != CORPUS_VERSION:
        raise FewShotError(
            f"unsupported few-shot corpus version {corpus.get('version')!r}; expected {CORPUS_VERSION!r}"
        )
    return corpus


def _strip_js_comments(text: str) -> str:
    """Remove JS comments without touching comment markers inside strings."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if quote is not None:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            output.append(char)
            index += 1
            continue
        if char == "/" and nxt == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and nxt == "*":
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != "*/":
                index += 1
            index += 2
            continue
        output.append(char)
        index += 1
    return "".join(output)


def load_js_assignment(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    match = re.match(r".*?=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not match:
        raise FewShotError(f"cannot parse JS assignment: {path}")
    object_text = match.group(1)
    try:
        value = json.loads(object_text)
    except json.JSONDecodeError:
        relaxed = _strip_js_comments(object_text)
        relaxed = re.sub(r",\s*([}\]])", r"\1", relaxed)
        value = json.loads(relaxed)
    if not isinstance(value, dict):
        raise FewShotError(f"JS assignment is not an object: {path}")
    return value


def _specials(enemy: dict[str, Any]) -> list[int]:
    raw = enemy.get("special")
    if raw in (None, 0):
        return []
    if isinstance(raw, list):
        return [int(value) for value in raw if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return [int(raw)]
    return []


def _is_wall(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    entry_id = str(entry.get("id", ""))
    entry_name = str(entry.get("name", ""))
    if (
        entry.get("canBreak") is True
        or entry.get("cls") == "autotile"
        or "wall" in entry_id.lower()
        or "墙" in entry_name
    ):
        return True
    # Common non-passable background barriers used as outer walls by examples.
    if entry_id in {"star", "lava", "blueLava", "water", "ice", "darkLight"} and entry.get("canPass") is not True:
        return True
    return False


def _is_door(entry: dict[str, Any] | None) -> bool:
    return bool(entry and entry.get("doorInfo") and entry.get("trigger") == "openDoor")


def _is_enemy(entry: dict[str, Any] | None) -> bool:
    return bool(entry and entry.get("cls") in {"enemys", "enemy48"})


def _kind(code: int, entry: dict[str, Any] | None) -> str:
    if code == 0:
        return "ground"
    if _is_wall(entry):
        return "wall"
    if _is_door(entry):
        return "door"
    if _is_enemy(entry):
        return "enemy"
    if not entry:
        return "unknown"
    entry_id = str(entry.get("id", ""))
    if entry_id in {"upFloor", "downFloor"}:
        return "stair"
    if entry.get("cls") == "items" or entry_id in RESOURCE_IDS:
        return "resource"
    if entry.get("canPass") is True or entry.get("trigger") in {"null", "ski"}:
        return "hazard"
    if entry.get("cls") in {"terrains", "animates"}:
        return "terrain"
    return "other"


def _semantic_token(code: int, entry: dict[str, Any] | None) -> str:
    kind = _kind(code, entry)
    entry_id = str((entry or {}).get("id", ""))
    if kind == "ground":
        return "."
    if kind == "wall":
        return "#"
    if entry_id == "downFloor":
        return "DOWN"
    if entry_id == "upFloor":
        return "UP"
    if kind == "enemy":
        return f"E:{entry_id}"
    if kind == "door":
        return f"D:{entry_id}"
    if kind == "resource":
        return f"R:{entry_id}"
    if kind == "hazard":
        return f"H:{entry_id}"
    return f"X:{entry_id or code}"


def _door_weight(entry: dict[str, Any]) -> float:
    keys = entry.get("doorInfo", {}).get("keys", {})
    if "redKey" in keys:
        return 4.0
    if "blueKey" in keys:
        return 2.0
    if "yellowKey" in keys:
        return 1.0
    return 3.0


def _cell_pressure(code: int, entry: dict[str, Any] | None, enemys: dict[str, Any]) -> float:
    if _is_wall(entry):
        return float("inf")
    if _is_door(entry):
        return _door_weight(entry or {})
    if _is_enemy(entry):
        enemy = enemys.get(str((entry or {}).get("id", "")), {})
        return 1.0 + (0.5 if _specials(enemy) else 0.0)
    if _kind(code, entry) == "hazard":
        return 0.5
    return 0.0


def _neighbors(coord: tuple[int, int], width: int, height: int) -> list[tuple[int, int]]:
    x, y = coord
    result = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nxt = (x + dx, y + dy)
        if 0 <= nxt[0] < width and 0 <= nxt[1] < height:
            result.append(nxt)
    return result


def _path_details(
    path: list[tuple[int, int]],
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gates: list[dict[str, Any]] = []
    rewards: list[dict[str, Any]] = []
    for x, y in path:
        code = matrix[y][x]
        entry = maps.get(str(code), {})
        kind = _kind(code, entry)
        entry_id = entry.get("id")
        if kind in {"door", "enemy", "hazard"}:
            item: dict[str, Any] = {"coord": [x, y], "kind": kind, "id": entry_id}
            if kind == "enemy":
                enemy = enemys.get(str(entry_id), {})
                item["specials"] = _specials(enemy)
            gates.append(item)
        elif kind == "resource":
            rewards.append({"coord": [x, y], "id": entry_id})
    return gates, rewards


def _find_path(
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    start: tuple[int, int],
    goal: tuple[int, int],
    mode: str,
    penalized: set[tuple[int, int]] | None = None,
) -> dict[str, Any] | None:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    penalized = penalized or set()
    distances: dict[tuple[int, int], float] = {start: 0.0}
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    while heap:
        distance, coord = heapq.heappop(heap)
        if distance != distances.get(coord):
            continue
        if coord == goal:
            break
        for nxt in _neighbors(coord, width, height):
            x, y = nxt
            entry = maps.get(str(matrix[y][x]), {})
            pressure = _cell_pressure(matrix[y][x], entry, enemys)
            if pressure == float("inf"):
                continue
            step = 1.0 if mode == "shortest" else 0.02 + pressure
            if nxt in penalized and nxt not in {start, goal}:
                step += 2.0
            candidate = distance + step
            if candidate < distances.get(nxt, float("inf")):
                distances[nxt] = candidate
                previous[nxt] = coord
                heapq.heappush(heap, (candidate, nxt))
    if goal not in previous:
        return None
    path: list[tuple[int, int]] = []
    node: tuple[int, int] | None = goal
    while node is not None:
        path.append(node)
        node = previous[node]
    path.reverse()
    gates, rewards = _path_details(path, matrix, maps, enemys)
    barrier_cost = sum(_cell_pressure(matrix[y][x], maps.get(str(matrix[y][x]), {}), enemys) for x, y in path)
    return {
        "mode": mode,
        "steps": max(len(path) - 1, 0),
        "barrier_cost_proxy": round(barrier_cost, 2),
        "path": [[x, y] for x, y in path],
        "gates": gates[:18],
        "rewards_on_path": rewards[:18],
    }


def _candidate_routes(
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    start: tuple[int, int] | None,
    goal: tuple[int, int] | None,
) -> list[dict[str, Any]]:
    if start is None or goal is None:
        return []
    routes: list[dict[str, Any]] = []
    first = _find_path(matrix, maps, enemys, start, goal, "pressure")
    if first:
        routes.append(first)
    shortest = _find_path(matrix, maps, enemys, start, goal, "shortest")
    if shortest and shortest.get("path") != (first or {}).get("path"):
        routes.append(shortest)
    penalized = {tuple(coord) for route in routes for coord in route.get("path", [])[1:-1]}
    alternative = _find_path(matrix, maps, enemys, start, goal, "alternative", penalized)
    if alternative and all(alternative.get("path") != route.get("path") for route in routes):
        routes.append(alternative)
    return routes[:3]


def _route_graph(
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    start: tuple[int, int] | None,
    goal: tuple[int, int] | None,
) -> dict[str, Any]:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    passable = {
        (x, y)
        for y, row in enumerate(matrix)
        for x, code in enumerate(row)
        if not _is_wall(maps.get(str(code), {}))
    }
    adjacency = {
        coord: [nxt for nxt in _neighbors(coord, width, height) if nxt in passable]
        for coord in passable
    }
    node_coords = {coord for coord, links in adjacency.items() if len(links) != 2}
    if start:
        node_coords.add(start)
    if goal:
        node_coords.add(goal)
    ordered_nodes = sorted(node_coords, key=lambda value: (value[1], value[0]))
    node_ids = {coord: f"n{index}" for index, coord in enumerate(ordered_nodes)}
    nodes = []
    for coord in ordered_nodes:
        if coord == start:
            kind = "entrance"
        elif coord == goal:
            kind = "exit"
        elif len(adjacency.get(coord, [])) >= 3:
            kind = "junction"
        else:
            kind = "endpoint"
        nodes.append({"id": node_ids[coord], "coord": list(coord), "kind": kind, "degree": len(adjacency.get(coord, []))})

    visited_steps: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    edges: list[dict[str, Any]] = []
    for source in ordered_nodes:
        for first in adjacency.get(source, []):
            undirected = tuple(sorted((source, first)))
            if undirected in visited_steps:
                continue
            path = [source, first]
            previous, current = source, first
            visited_steps.add(undirected)
            while current not in node_coords:
                candidates = [coord for coord in adjacency.get(current, []) if coord != previous]
                if not candidates:
                    break
                nxt = candidates[0]
                visited_steps.add(tuple(sorted((current, nxt))))
                path.append(nxt)
                previous, current = current, nxt
            if current not in node_ids:
                continue
            gates, rewards = _path_details(path, matrix, maps, enemys)
            edges.append({
                "from": node_ids[source],
                "to": node_ids[current],
                "length": max(len(path) - 1, 0),
                "path": [[x, y] for x, y in path],
                "gates": gates,
                "rewards": rewards,
            })
    main_edges = sum(1 for coord in passable for nxt in adjacency[coord] if coord < nxt)
    cycle_rank = max(main_edges - len(passable) + 1, 0) if passable else 0
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "cycle_rank": cycle_rank,
        "nodes": nodes,
        "edges": edges,
    }


def _resource_reachability(
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    start: tuple[int, int] | None,
) -> list[dict[str, Any]]:
    if start is None:
        return []
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    distances: dict[tuple[int, int], float] = {start: 0.0}
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    while heap:
        distance, coord = heapq.heappop(heap)
        if distance != distances.get(coord):
            continue
        for nxt in _neighbors(coord, width, height):
            x, y = nxt
            entry = maps.get(str(matrix[y][x]), {})
            pressure = _cell_pressure(matrix[y][x], entry, enemys)
            if pressure == float("inf"):
                continue
            candidate = distance + pressure + 0.01
            if candidate < distances.get(nxt, float("inf")):
                distances[nxt] = candidate
                previous[nxt] = coord
                heapq.heappush(heap, (candidate, nxt))

    results: list[dict[str, Any]] = []
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            entry = maps.get(str(code), {})
            if _kind(code, entry) != "resource" or (x, y) not in distances:
                continue
            path = []
            node: tuple[int, int] | None = (x, y)
            while node is not None:
                path.append(node)
                node = previous.get(node)
            path.reverse()
            gates, _ = _path_details(path[:-1], matrix, maps, enemys)
            barrier = sum(_cell_pressure(matrix[py][px], maps.get(str(matrix[py][px]), {}), enemys) for px, py in path)
            if barrier <= 0:
                stage = "free"
            elif barrier <= 1.5:
                stage = "early"
            elif barrier <= 3.5:
                stage = "middle"
            else:
                stage = "deep"
            results.append({
                "id": entry.get("id"),
                "coord": [x, y],
                "stage": stage,
                "barrier_cost_proxy": round(barrier, 2),
                "steps": max(len(path) - 1, 0),
                "gate_sequence": gates[:12],
            })
    return sorted(results, key=lambda item: (item["barrier_cost_proxy"], item["steps"], item["coord"][1], item["coord"][0]))


def _find_tile(matrix: list[list[int]], maps: dict[str, Any], tile_id: str) -> tuple[int, int] | None:
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if maps.get(str(code), {}).get("id") == tile_id:
                return x, y
    return None


def _used_enemy_stats(matrix: list[list[int]], maps: dict[str, Any], enemys: dict[str, Any]) -> dict[str, Any]:
    used_ids = {
        str(maps.get(str(code), {}).get("id"))
        for row in matrix
        for code in row
        if _is_enemy(maps.get(str(code), {}))
    }
    result: dict[str, Any] = {}
    for enemy_id in sorted(used_ids):
        enemy = enemys.get(enemy_id, {})
        result[enemy_id] = {
            key: enemy.get(key)
            for key in (
                "name", "hp", "atk", "def", "money", "exp", "point", "special",
                "value", "zone", "repulse", "range", "zoneSquare", "notBomb",
            )
            if key in enemy
        }
    return result


def _floor_example(
    project_name: str,
    project_dir: Path,
    floor_id: str,
    floor_index: int,
    floor_count: int,
    floor: dict[str, Any],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    project_context: dict[str, Any],
) -> dict[str, Any]:
    matrix = floor.get("map", [])
    if not isinstance(matrix, list) or not matrix or not all(isinstance(row, list) for row in matrix):
        raise FewShotError(f"invalid map for {project_name}/{floor_id}")
    height = len(matrix)
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise FewShotError(f"ragged map for {project_name}/{floor_id}")
    start = _find_tile(matrix, maps, "downFloor")
    goal = _find_tile(matrix, maps, "upFloor")
    if start is None and floor_index == 0:
        loc = project_context.get("initial_hero", {}).get("loc", {})
        if isinstance(loc, dict) and isinstance(loc.get("x"), int) and isinstance(loc.get("y"), int):
            candidate = (loc["x"], loc["y"])
            if 0 <= candidate[0] < width and 0 <= candidate[1] < height:
                start = candidate

    used_codes = sorted({code for row in matrix for code in row if isinstance(code, int)})
    legend = {
        str(code): {
            "id": maps.get(str(code), {}).get("id", "ground" if code == 0 else "unknown"),
            "cls": maps.get(str(code), {}).get("cls", "terrains" if code == 0 else "unknown"),
            "kind": _kind(code, maps.get(str(code), {})),
        }
        for code in used_codes
    }
    semantic_map = [
        [_semantic_token(code, maps.get(str(code), {})) for code in row]
        for row in matrix
    ]
    topology_map = [
        "".join(
            "D" if maps.get(str(code), {}).get("id") == "downFloor"
            else "U" if maps.get(str(code), {}).get("id") == "upFloor"
            else "#" if _is_wall(maps.get(str(code), {}))
            else "."
            for code in row
        )
        for row in matrix
    ]
    counts = Counter(_kind(code, maps.get(str(code), {})) for row in matrix for code in row)
    used_enemies = _used_enemy_stats(matrix, maps, enemys)
    route_graph = _route_graph(matrix, maps, enemys, start, goal)
    role = "entrance" if floor_index == 0 else "final" if floor_index == floor_count - 1 else "middle"
    return {
        "reference_id": f"{project_name}/{floor_id}",
        "project": project_name,
        "tower_style": BUNDLED_STYLE_PROJECTS.get(project_name, "unclassified"),
        "floor_id": floor_id,
        "floor_index": floor_index,
        "floor_count": floor_count,
        "relative_position": round(floor_index / max(floor_count - 1, 1), 3),
        "role": role,
        "quality_tier": "format_only" if project_name.startswith(FORMAT_ONLY_PREFIXES) else "design_reference",
        "source_path": str(project_dir / "floors" / f"{floor_id}.js"),
        "width": width,
        "height": height,
        "title": floor.get("title", ""),
        "map_codes": matrix,
        "tile_legend": legend,
        "semantic_map": semantic_map,
        "topology_map": topology_map,
        "entrance": list(start) if start else None,
        "exit": list(goal) if goal else None,
        "metrics": {
            "wall_ratio": round(counts["wall"] / max(width * height, 1), 3),
            "ground_count": counts["ground"],
            "door_count": counts["door"],
            "resource_count": counts["resource"],
            "enemy_count": counts["enemy"],
            "hazard_count": counts["hazard"],
            "enemy_type_count": len(used_enemies),
            "special_enemy_type_count": sum(1 for enemy in used_enemies.values() if _specials(enemy)),
            "junction_count": sum(1 for node in route_graph["nodes"] if node["kind"] == "junction"),
            "cycle_rank": route_graph["cycle_rank"],
        },
        "candidate_routes": _candidate_routes(matrix, maps, enemys, start, goal),
        "route_graph": route_graph,
        "resource_reachability": _resource_reachability(matrix, maps, enemys, start),
        "used_enemy_stats": used_enemies,
        "project_context": project_context,
    }


def _project_context(data: dict[str, Any]) -> dict[str, Any]:
    first_data = data.get("firstData", {}) if isinstance(data.get("firstData"), dict) else {}
    hero = first_data.get("hero", {}) if isinstance(first_data.get("hero"), dict) else {}
    values = data.get("values", {}) if isinstance(data.get("values"), dict) else {}
    return {
        "title": first_data.get("title", ""),
        "initial_hero": {
            key: hero.get(key)
            for key in ("hp", "atk", "def", "mdef", "money", "loc", "items")
            if key in hero
        },
        "values": {
            key: values.get(key)
            for key in (
                "redGem", "blueGem", "greenGem", "redPotion", "bluePotion",
                "yellowPotion", "greenPotion", "lavaDamage", "poisonDamage",
            )
            if key in values
        },
    }


def build_reference_corpus(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FewShotError(f"few-shot root does not exist: {root}")
    floors: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    fingerprint = hashlib.sha256(CORPUS_VERSION.encode("utf-8"))
    for project_dir in sorted(root.glob("*/project")):
        project_name = project_dir.parent.name
        try:
            maps = load_js_assignment(project_dir / "maps.js")
            enemys_path = project_dir / "enemys.js"
            if not enemys_path.exists():
                enemys_path = project_dir / "enemy.js"
            enemys = load_js_assignment(enemys_path)
            data = load_js_assignment(project_dir / "data.js")
        except Exception as exc:  # noqa: BLE001 - keep all other reference projects usable.
            skipped.append({"reference": project_name, "reason": str(exc)})
            continue
        floor_ids = data.get("main", {}).get("floorIds", []) if isinstance(data.get("main"), dict) else []
        if not isinstance(floor_ids, list):
            floor_ids = []
        floor_ids = [str(value) for value in floor_ids if isinstance(value, (str, int)) and not str(value).startswith("sample")]
        if not floor_ids:
            floor_ids = sorted(path.stem for path in (project_dir / "floors").glob("*.js") if not path.stem.startswith("sample"))
        context = _project_context(data)
        project_floor_ids: list[str] = []
        for floor_index, floor_id in enumerate(floor_ids):
            floor_path = project_dir / "floors" / f"{floor_id}.js"
            if not floor_path.exists():
                skipped.append({"reference": f"{project_name}/{floor_id}", "reason": "floor file missing"})
                continue
            try:
                floor = load_js_assignment(floor_path)
                example = _floor_example(
                    project_name, project_dir, floor_id, floor_index, len(floor_ids),
                    floor, maps, enemys, context,
                )
            except Exception as exc:  # noqa: BLE001 - one malformed floor must not drop the project.
                skipped.append({"reference": f"{project_name}/{floor_id}", "reason": str(exc)})
                continue
            floors.append(example)
            project_floor_ids.append(example["reference_id"])
            for path in (floor_path, project_dir / "maps.js", enemys_path, project_dir / "data.js"):
                fingerprint.update(path.read_bytes())
        projects.append({
            "name": project_name,
            "project_dir": str(project_dir),
            "tower_style": BUNDLED_STYLE_PROJECTS.get(project_name, "unclassified"),
            "quality_tier": "format_only" if project_name.startswith(FORMAT_ONLY_PREFIXES) else "design_reference",
            "floor_count": len(project_floor_ids),
            "floors": project_floor_ids,
            "context": context,
        })
    return {
        "version": CORPUS_VERSION,
        "source_root": str(root),
        "fingerprint": fingerprint.hexdigest(),
        "analysis_method": {
            "route_graph": "Collapse traversable grid corridors between endpoints and junctions; keep gates and rewards on each edge.",
            "candidate_routes": "Pressure-minimal, geometric-shortest, and prior-path-penalized alternatives when distinct.",
            "resource_reachability": "Static Dijkstra proxy from the entrance; yellow/blue/red doors cost 1/2/4, enemies cost 1 plus 0.5 for specials, hazards cost 0.5.",
            "limitations": "Reference access order is a structural calibration signal, not a full cross-floor inventory or exact battle simulation.",
        },
        "project_count": len(projects),
        "floor_count": len(floors),
        "projects": projects,
        "floors": floors,
        "skipped": skipped,
    }


def build_bundled_reference_corpus(root: Path) -> dict[str, Any]:
    """Build the reproducible, style-labelled subset used by default."""
    full = build_reference_corpus(root)
    selected_floors = [
        json.loads(json.dumps(item, ensure_ascii=False))
        for item in full.get("floors", [])
        if isinstance(item, dict) and str(item.get("project")) in BUNDLED_STYLE_PROJECTS
    ]
    found = {str(item.get("reference_id")) for item in selected_floors}
    found_projects = {str(item.get("project")) for item in selected_floors}
    missing_projects = sorted(set(BUNDLED_STYLE_PROJECTS) - found_projects)
    if missing_projects:
        raise FewShotError("missing bundled reference projects: " + ", ".join(missing_projects))
    for item in selected_floors:
        project = str(item.get("project"))
        floor_id = str(item.get("floor_id"))
        item["source_path"] = f"{project}/project/floors/{floor_id}.js"
    selected_projects = []
    for project in full.get("projects", []):
        if not isinstance(project, dict):
            continue
        project_name = str(project.get("name"))
        floor_ids = [
            reference_id
            for reference_id in project.get("floors", [])
            if reference_id in found
        ]
        if not floor_ids:
            continue
        selected_projects.append({
            "name": project_name,
            "project_dir": f"{project_name}/project",
            "tower_style": BUNDLED_STYLE_PROJECTS[project_name],
            "quality_tier": project.get("quality_tier", "design_reference"),
            "floor_count": len(floor_ids),
            "floors": floor_ids,
            "context": project.get("context", {}),
        })
    bundled = {
        "version": CORPUS_VERSION,
        "source_root": "repository-bundled:selected-mota-reference-projects",
        "analysis_method": full.get("analysis_method", {}),
        "selection_policy": {
            "reference_ids": sorted(found),
            "style_projects": BUNDLED_STYLE_PROJECTS,
            "notes": [
                "Traditional references: 寒云谷2103, 溯, and CCW.",
                "Red-sea references: 红蓝的记忆2.10, 星月神话 2.10.3, dist, 剑阁2.9, and 出塞V2.10.0.",
                "Includes every non-sample main-floor id from the classified projects.",
                "Contains extracted maps and design data only; source scripts, events, media, and saves are not bundled.",
            ],
        },
        "project_count": len(selected_projects),
        "floor_count": len(selected_floors),
        "projects": selected_projects,
        "floors": selected_floors,
        "skipped": [],
    }
    fingerprint_payload = json.dumps(bundled, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    bundled["fingerprint"] = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
    return bundled


def _selection_score(
    example: dict[str, Any],
    stage: str,
    target_position: float,
    floor_size: int,
    allow_curated_size_mismatch: bool = False,
) -> float:
    size_penalty = 0.0
    if example.get("width") != floor_size or example.get("height") != floor_size:
        if (
            allow_curated_size_mismatch
            and str(example.get("reference_id")) in TRADITIONAL_LAYOUT_REFERENCE_IDS
        ):
            # The curated traditional set is 13x13. Keep its route/resource
            # grammar available to smaller requested maps, but rank exact-size
            # examples higher whenever the curated set gains them later.
            size_penalty = 2.5
        else:
            return -1000.0
    score = 5.0 * (1.0 - abs(float(example.get("relative_position", 0.0)) - target_position))
    score -= size_penalty
    if example.get("quality_tier") == "format_only":
        score -= 30.0
    metrics = example.get("metrics", {})
    if stage == "topology":
        score += min(float(metrics.get("cycle_rank", 0)), 12.0) * 0.18
        score += min(float(metrics.get("junction_count", 0)), 16.0) * 0.08
    elif stage == "economy":
        score += min(float(metrics.get("door_count", 0)), 12.0) * 0.12
        score += min(float(metrics.get("resource_count", 0)), 24.0) * 0.06
        score += min(len(example.get("resource_reachability", [])), 24) * 0.05
    else:
        score += min(float(metrics.get("enemy_type_count", 0)), 10.0) * 0.15
        score += min(float(metrics.get("special_enemy_type_count", 0)), 6.0) * 0.3
    score += ANCHOR_BONUSES.get(stage, {}).get((str(example.get("project")), str(example.get("floor_id"))), 0.0)
    if not example.get("entrance") or not example.get("exit"):
        score -= 6.0
    return score


def _select_ranked_references(
    ranked: list[dict[str, Any]],
    stage: str,
    target_position: float,
    floor_size: int,
    count: int,
    excluded_ids: set[str] | None = None,
    avoided_projects: set[str] | None = None,
    allow_curated_size_mismatch: bool = False,
) -> list[str]:
    """Select deterministic references, preferring project diversity before fallback."""
    if count <= 0:
        return []
    excluded_ids = set(excluded_ids or set())
    used_projects = set(avoided_projects or set())
    selected: list[str] = []
    for prefer_new_project in (True, False):
        for item in ranked:
            reference_id = str(item.get("reference_id"))
            project = str(item.get("project"))
            if (
                reference_id in excluded_ids
                or reference_id in selected
                or _selection_score(
                    item,
                    stage,
                    target_position,
                    floor_size,
                    allow_curated_size_mismatch,
                ) < -100
            ):
                continue
            if prefer_new_project and project in used_projects:
                continue
            selected.append(reference_id)
            used_projects.add(project)
            if len(selected) >= count:
                return selected
    return selected


def _consumer_selection_for_floor(
    floors: list[dict[str, Any]],
    project_by_id: dict[str, str],
    stage: str,
    target_position: float,
    floor_size: int,
    count: int,
    allow_curated_size_mismatch: bool = False,
) -> dict[str, list[str]]:
    ranked = sorted(
        floors,
        key=lambda item: (
            -_selection_score(
                item,
                stage,
                target_position,
                floor_size,
                allow_curated_size_mismatch,
            ),
            str(item.get("reference_id")),
        ),
    )
    shared = _select_ranked_references(
        ranked,
        stage,
        target_position,
        floor_size,
        1,
        allow_curated_size_mismatch=allow_curated_size_mismatch,
    )
    shared_projects = {project_by_id[value] for value in shared if value in project_by_id}
    generator_only = _select_ranked_references(
        ranked,
        stage,
        target_position,
        floor_size,
        count - len(shared),
        excluded_ids=set(shared),
        avoided_projects=shared_projects,
        allow_curated_size_mismatch=allow_curated_size_mismatch,
    )
    generator = shared + generator_only
    generator_projects = {
        project_by_id[value] for value in generator if value in project_by_id
    }
    reviewer_holdout = _select_ranked_references(
        ranked,
        stage,
        target_position,
        floor_size,
        count - len(shared),
        excluded_ids=set(generator),
        avoided_projects=generator_projects,
        allow_curated_size_mismatch=allow_curated_size_mismatch,
    )
    reviewer_fallback = _select_ranked_references(
        ranked,
        stage,
        target_position,
        floor_size,
        count - len(shared) - len(reviewer_holdout),
        excluded_ids=set(shared + reviewer_holdout),
        allow_curated_size_mismatch=allow_curated_size_mismatch,
    )
    return {
        "shared": shared,
        "generator_only": generator_only,
        "reviewer_holdout": reviewer_holdout,
        "reviewer_fallback": reviewer_fallback,
        "generator": generator,
        "reviewer": shared + reviewer_holdout + reviewer_fallback,
    }


def build_selection_plan(
    corpus: dict[str, Any],
    floor_count: int,
    floor_size: int,
    count: int,
    tower_style: str = DEFAULT_TOWER_STYLE,
) -> dict[str, Any]:
    if tower_style not in TOWER_STYLES:
        raise FewShotError(f"unsupported tower style: {tower_style}")
    count = max(1, min(int(count), 5))
    plan: dict[str, Any] = {
        "version": (
            TRADITIONAL_LAYOUT_SELECTION_PLAN_VERSION
            if tower_style == "traditional"
            else SELECTION_PLAN_VERSION
        ),
        "corpus_version": corpus.get("version"),
        "corpus_fingerprint": corpus.get("fingerprint"),
        "examples_per_consumer": count,
        "tower_style": tower_style,
        "selection_policy": {
            "style_filter": "strict; never fall back to the other tower style",
            "shared_anchor_count": 1,
            "generator": "shared anchor plus construction-oriented exclusive references",
            "reviewer": "same shared anchor plus references withheld from the generator",
            "small_corpus_fallback": "reuse generator references only when there are not enough withheld floors to preserve examples_per_consumer",
            "retry_stability": "selection is computed once per run and reused for all repairs",
        },
        "stages": {},
    }
    style_floors = [
        item
        for item in corpus.get("floors", [])
        if isinstance(item, dict) and item.get("tower_style") == tower_style
    ]
    if not style_floors:
        raise FewShotError(f"few-shot corpus has no {tower_style} reference floors")
    layout_floors = style_floors
    if tower_style == "traditional":
        layout_floors = [
            item
            for item in style_floors
            if str(item.get("reference_id")) in TRADITIONAL_LAYOUT_REFERENCE_IDS
        ]
        missing = sorted(
            TRADITIONAL_LAYOUT_REFERENCE_IDS
            - {str(item.get("reference_id")) for item in layout_floors}
        )
        if missing:
            raise FewShotError(
                "traditional layout corpus is missing curated references: " + ", ".join(missing)
            )
        plan["selection_policy"].update(
            {
                "layout_reference_filter": "user-curated traditional floors only",
                "layout_reference_ids": sorted(TRADITIONAL_LAYOUT_REFERENCE_IDS),
                "layout_normalization": (
                    "寒云谷 debuff cures, money pickups, and equipment become red/blue gems; "
                    "溯 green/yellow gems and equipment become red/blue gems, and red doors/keys become blue."
                ),
                "enemy_design_scope": "full traditional style corpus; unaffected by layout curation",
            }
        )
    project_by_id = {
        str(item.get("reference_id")): str(item.get("project"))
        for item in style_floors
        if item.get("reference_id")
    }
    for stage in ("topology", "economy", "monster", "integration"):
        stage_plan: dict[str, dict[str, list[str]]] = {}
        for floor_index in range(floor_count):
            target_position = floor_index / max(floor_count - 1, 1)
            stage_plan[str(floor_index)] = _consumer_selection_for_floor(
                layout_floors,
                project_by_id,
                stage,
                target_position,
                floor_size,
                count,
                allow_curated_size_mismatch=tower_style == "traditional",
            )
        plan["stages"][stage] = stage_plan

    # Monster placement is a layout stage and uses the curated floors above,
    # but enemy-table design must retain its prior, full-style calibration.
    enemy_stage_plan = {
        str(floor_index): _consumer_selection_for_floor(
            style_floors,
            project_by_id,
            "monster",
            floor_index / max(floor_count - 1, 1),
            floor_size,
            count,
        )
        for floor_index in range(floor_count)
    }
    unique_monster_ids: list[str] = []
    unique_monster_reviewer_ids: list[str] = []
    for selection in enemy_stage_plan.values():
        for value in selection["generator"]:
            if value not in unique_monster_ids:
                unique_monster_ids.append(value)
        for value in selection["reviewer"]:
            if value not in unique_monster_reviewer_ids:
                unique_monster_reviewer_ids.append(value)
    enemy_example_count = max(count + 1, 4)
    plan["enemy_design"] = {
        "generator": unique_monster_ids[:enemy_example_count],
        "reviewer": unique_monster_reviewer_ids[:enemy_example_count],
        "shared": [
            value for value in unique_monster_ids
            if value in set(unique_monster_reviewer_ids)
        ][:1],
    }
    return plan


def _lookup(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("reference_id")): item
        for item in corpus.get("floors", [])
        if isinstance(item, dict) and item.get("reference_id")
    }


def _traditional_layout_replacement_id(project: str, item_id: str) -> str:
    replacements = TRADITIONAL_LAYOUT_RESOURCE_REWRITES.get(project, {})
    if item_id in replacements:
        return replacements[item_id]
    # Equipment is normalized by the stat it grants. This covers the actual
    # sword/shield ids used by the curated floors without baking in tiers.
    if item_id.startswith("sword") or item_id in {"dagger", "hammer"}:
        return "redGem"
    if item_id.startswith("shield"):
        return "blueGem"
    return item_id


def _rewrite_layout_value(value: Any, project: str) -> Any:
    if isinstance(value, str):
        replacement = _traditional_layout_replacement_id(project, value)
        if replacement != value:
            return replacement
        rewritten = value
        replacements = dict(TRADITIONAL_LAYOUT_RESOURCE_REWRITES.get(project, {}))
        for item_id in ("sword0", "sword1", "sword2", "sword3", "sword4", "sword5"):
            replacements[item_id] = "redGem"
        for item_id in ("shield0", "shield1", "shield2", "shield3", "shield4", "shield5"):
            replacements[item_id] = "blueGem"
        for source_id, target_id in replacements.items():
            rewritten = rewritten.replace(f"R:{source_id}", f"R:{target_id}")
            rewritten = rewritten.replace(f"D:{source_id}", f"D:{target_id}")
        return rewritten
    if isinstance(value, list):
        return [_rewrite_layout_value(item, project) for item in value]
    if isinstance(value, dict):
        rewritten: dict[str, Any] = {}
        for key, item in value.items():
            new_key = _traditional_layout_replacement_id(project, str(key))
            new_value = _rewrite_layout_value(item, project)
            # Prefer an original canonical red/blue value when normalization
            # makes multiple source ids converge on the same key.
            if new_key not in rewritten or new_key == key:
                rewritten[new_key] = new_value
        return rewritten
    return value


def _normalize_traditional_layout_projection(
    projection: dict[str, Any],
    example: dict[str, Any],
    stage: str,
) -> dict[str, Any]:
    reference_id = str(example.get("reference_id"))
    if (
        stage == "enemy_design"
        or example.get("tower_style") != "traditional"
        or reference_id not in TRADITIONAL_LAYOUT_REFERENCE_IDS
    ):
        return projection
    project = str(example.get("project"))
    normalized = _rewrite_layout_value(projection, project)
    if not isinstance(normalized, dict):
        return projection
    explicit = dict(TRADITIONAL_LAYOUT_RESOURCE_REWRITES.get(project, {}))
    explicit["sword*"] = "redGem"
    explicit["shield*"] = "blueGem"
    normalized["layout_reference_normalization"] = {
        "scope": "traditional layout generator/reviewer prompts only",
        "project": project,
        "replacements": explicit,
        "purpose": (
            "Preserve the reference floor's access-control geometry while expressing rewards "
            "using the generated tower's red/blue-gem and blue-key economy."
        ),
    }
    return normalized


def _prompt_projection(example: dict[str, Any], stage: str) -> dict[str, Any]:
    graph = example.get("route_graph", {})
    graph_edges = [
        {
            "from": edge.get("from"),
            "to": edge.get("to"),
            "length": edge.get("length"),
            "gates": edge.get("gates", [])[:8],
            "rewards": edge.get("rewards", [])[:8],
        }
        for edge in graph.get("edges", [])[:24]
        if isinstance(edge, dict)
    ]
    resource_order = [
        {
            **{key: item.get(key) for key in ("id", "coord", "stage", "barrier_cost_proxy", "steps")},
            "gate_sequence": item.get("gate_sequence", [])[:4],
        }
        for item in example.get("resource_reachability", [])[:16]
        if isinstance(item, dict)
    ]
    projection: dict[str, Any] = {
        "reference_id": example.get("reference_id"),
        "tower_style": example.get("tower_style"),
        "source_path": example.get("source_path"),
        "floor_position": {
            "index": example.get("floor_index"),
            "count": example.get("floor_count"),
            "relative": example.get("relative_position"),
            "role": example.get("role"),
        },
        "project_context": example.get("project_context"),
        "metrics": example.get("metrics"),
        "map_codes": example.get("map_codes"),
        "tile_legend": example.get("tile_legend"),
        "topology_map": example.get("topology_map"),
        "entrance": example.get("entrance"),
        "exit": example.get("exit"),
        "candidate_routes": example.get("candidate_routes", [])[:3],
        "route_graph": {
            "node_count": graph.get("node_count", 0),
            "edge_count": graph.get("edge_count", 0),
            "cycle_rank": graph.get("cycle_rank", 0),
            "nodes": graph.get("nodes", [])[:24],
            "edges": graph_edges,
            "truncated": len(graph.get("nodes", [])) > 24 or len(graph.get("edges", [])) > 24,
        },
        "resource_reachability_order": resource_order,
    }
    if stage in {"monster", "integration", "enemy_design"}:
        projection["used_enemy_stats_from_enemys_js"] = example.get("used_enemy_stats", {})
    return _normalize_traditional_layout_projection(projection, example, stage)


def stage_examples_payload(
    corpus: dict[str, Any] | None,
    plan: dict[str, Any] | None,
    stage: str,
    floor_index: int,
    consumer: str = "generator",
) -> dict[str, Any]:
    if not corpus or not plan:
        return {}
    if consumer not in {"generator", "reviewer"}:
        raise FewShotError(f"unsupported few-shot consumer: {consumer}")
    selection = plan.get("stages", {}).get(stage, {}).get(str(floor_index), [])
    # Accept v1 list-shaped plans so old saved fixtures remain readable.
    if isinstance(selection, list):
        ids = selection
        shared_ids = selection
        exclusive_ids: list[str] = []
        fallback_ids: list[str] = []
    elif isinstance(selection, dict):
        ids = selection.get(consumer, [])
        shared_ids = selection.get("shared", [])
        exclusive_key = "generator_only" if consumer == "generator" else "reviewer_holdout"
        exclusive_ids = selection.get(exclusive_key, [])
        fallback_ids = selection.get("reviewer_fallback", []) if consumer == "reviewer" else []
    else:
        return {}
    lookup = _lookup(corpus)
    examples = [_prompt_projection(lookup[value], stage) for value in ids if value in lookup]
    if not examples:
        return {}
    payload = {
        "selection_role": consumer,
        "selected_reference_ids": ids,
        "shared_reference_ids": shared_ids,
        "exclusive_reference_ids": exclusive_ids,
        "fallback_reference_ids": fallback_ids,
        "contract": [
            "These are real reference floors, not names or prose-only anchors.",
            "Study their route grammar, cost/reward staging, and resource access order.",
            "Numeric tile codes are local to each source project; use tile_legend and topology_map.",
            "barrier_cost_proxy and resource order are structural calibration signals, not an exact cross-floor playthrough.",
            "Do not copy scripts, events, unsupported terrain, or source tile codes into the generated tower.",
            "Do not clone a reference map cell-for-cell; transfer the design relationship into the requested floor.",
        ],
        "examples": examples,
    }
    if plan.get("tower_style") == "traditional":
        payload["contract"].extend(
            [
                "Traditional layout should be relatively low-density, with readable negative space and a small number of legible route commitments rather than a packed lattice of objects or micro-branches.",
                "Low density must not weaken resource control: concentrate meaningful rewards behind doors, combat thresholds, detours, or tool commitments, preserve distinct early/middle/deep access stages, and avoid evenly sprinkled free resources.",
                "For the curated traditional references, use layout_reference_normalization as the semantic source of truth for replaced rewards and red-door/key conversions.",
            ]
        )
    if consumer == "reviewer":
        payload["contract"].append(
            "The holdout examples were not shown to the generator; use them to test generalization, not literal similarity."
        )
        payload["contract"].append(
            "Few-shot floors calibrate only this review stage's design relationships; they never set exact wall ratio, resource totals, or enemy count."
        )
        payload["contrastive_rejection_cases"] = REVIEWER_CONTRASTIVE_REJECTION_CASES.get(stage, [])
    return payload


def enemy_design_examples_payload(
    corpus: dict[str, Any] | None,
    plan: dict[str, Any] | None,
    consumer: str = "generator",
) -> dict[str, Any]:
    if not corpus or not plan:
        return {}
    if consumer not in {"generator", "reviewer"}:
        raise FewShotError(f"unsupported enemy-design few-shot consumer: {consumer}")
    lookup = _lookup(corpus)
    selection = plan.get("enemy_design", [])
    ids = selection.get(consumer, []) if isinstance(selection, dict) else selection
    examples = [
        _prompt_projection(lookup[value], "enemy_design")
        for value in ids
        if value in lookup
    ]
    if not examples:
        return {}
    return {
        "selection_role": consumer,
        "selected_reference_ids": ids,
        "contract": [
            "Use the actual enemys.js records only to learn relative monster roles and progression.",
            "Scale values to the new tower's hero, gem, potion, and whitelist settings.",
            "The tower style controls placement grammar only; never infer numeric difficulty from it.",
            "Do not copy unsupported specials or assume source-project numeric scale is compatible.",
            "Few-shot enemy tables calibrate relative roles and progression only; projected hero bands and the confirmed tower policy control this tower's numeric scale.",
        ],
        "examples": examples,
    }


def brief_examples_payload(
    corpus: dict[str, Any] | None,
    tower_style: str = DEFAULT_TOWER_STYLE,
    max_projects: int = 12,
) -> dict[str, Any]:
    if not corpus:
        return {}
    lookup = _lookup(corpus)
    projects = []
    for project in corpus.get("projects", []):
        if (
            not isinstance(project, dict)
            or project.get("quality_tier") != "design_reference"
            or project.get("tower_style") != tower_style
        ):
            continue
        floor_profiles = []
        for reference_id in project.get("floors", []):
            example = lookup.get(str(reference_id))
            if not example:
                continue
            floor_profiles.append({
                "reference_id": reference_id,
                "size": [example.get("width"), example.get("height")],
                "relative_position": example.get("relative_position"),
                "role": example.get("role"),
                "metrics": example.get("metrics"),
                "route_costs": [
                    {
                        "mode": route.get("mode"),
                        "steps": route.get("steps"),
                        "barrier_cost_proxy": route.get("barrier_cost_proxy"),
                    }
                    for route in example.get("candidate_routes", [])
                ],
                "resource_access_stages": dict(Counter(
                    item.get("stage", "unknown") for item in example.get("resource_reachability", [])
                )),
            })
        projects.append({
            "project": project.get("name"),
            "context": project.get("context"),
            "floor_progression": floor_profiles,
        })
        if len(projects) >= max_projects:
            break
    return {
        "tower_style": tower_style,
        "contract": [
            "Use only the requested tower style; do not infer numeric difficulty from the style label.",
            "Use these real tower progressions to avoid evenly cloning the same per-floor recipe.",
            "Infer distinct floor roles and uneven pacing; keep the user's explicit totals and rules authoritative.",
        ],
        "tower_profiles": projects,
    }

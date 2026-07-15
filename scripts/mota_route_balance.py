#!/usr/bin/env python3
"""Bounded route-family balance search for generated mota floors.

The search deliberately models only mechanics used by the generator: ordinary
combat, first strike, magic attack, solid defense, zone, repulse, doors, and
red/blue/green gems.  HP and keys are assumed sufficient; their consumption is
measured instead of used as a feasibility constraint.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import heapq
import json
import math
from pathlib import Path
import time
from typing import Any


GEM_IDS = ("redGem", "blueGem", "greenGem")
SUPPORTED_BATTLE_SPECIALS = {1, 2, 3}
SUPPORTED_RANGE_SPECIALS = {15, 18}


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _specials(value: Any) -> set[int]:
    if value in (None, 0):
        return set()
    if isinstance(value, list):
        return {int(item) for item in value if isinstance(item, (int, float)) and not isinstance(item, bool)}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {int(value)}
    return set()


def _is_enemy(entry: dict[str, Any]) -> bool:
    return entry.get("cls") in {"enemys", "enemy48"}


def _is_wall(entry: dict[str, Any]) -> bool:
    return entry.get("id") in {"yellowWall", "whiteWall", "blueWall", "star", "wall"} or (
        entry.get("cls") == "animates" and str(entry.get("id", "")).endswith("Wall")
    )


def _door_kind(entry: dict[str, Any]) -> str | None:
    entry_id = str(entry.get("id", ""))
    if entry_id in {"yellowDoor", "tallYellowDoor"}:
        return "yellow"
    if entry_id in {"blueDoor", "tallBlueDoor"}:
        return "blue"
    if entry_id in {"redDoor", "tallRedDoor"}:
        return "red"
    return None


def _passable(code: int, entry: dict[str, Any]) -> bool:
    if code == 0:
        return True
    if not entry or _is_wall(entry):
        return False
    if _is_enemy(entry) or _door_kind(entry):
        return True
    if entry.get("cls") == "items" or entry.get("canPass") is True:
        return True
    return entry.get("id") in {"upFloor", "downFloor", "ground", "grass", "grass2"}


def _free_passable(code: int, entry: dict[str, Any]) -> bool:
    return _passable(code, entry) and not _is_enemy(entry) and _door_kind(entry) is None


def _battle_damage(enemy: dict[str, Any], atk: float, defense: float, mdef: float) -> float:
    hp = _number(enemy.get("hp"))
    mon_atk = _number(enemy.get("atk"))
    mon_def = _number(enemy.get("def"))
    specials = _specials(enemy.get("special"))
    if 3 in specials:
        mon_def = max(mon_def, atk - 1)
    hero_hit = atk - mon_def
    if hp <= 0:
        return 0.0
    if hero_hit <= 0:
        return math.inf
    turns = max(1, math.ceil(hp / hero_hit))
    per_damage = mon_atk if 2 in specials else max(mon_atk - defense, 0.0)
    damage = per_damage * max(turns - 1, 0)
    if 1 in specials:
        damage += per_damage
    # mota-js subtracts shield once from each battle, but does not subtract it
    # from map-wide zone/repulse damage by default.
    return max(0.0, damage - max(mdef, 0.0))


@dataclass
class Label:
    node_id: int
    gems_mask: int
    cleared_mask: int
    repulse_mask: int
    hp_loss: float
    yellow_doors: int
    blue_doors: int
    red_doors: int
    steps: int
    parent: int | None
    pressure_sequence: tuple[int, ...]
    active: bool = True


def _dominates(a: Label, b: Label) -> bool:
    no_worse = (
        a.hp_loss <= b.hp_loss
        and a.yellow_doors <= b.yellow_doors
        and a.blue_doors <= b.blue_doors
        and a.red_doors <= b.red_doors
    )
    strictly_better_cost = (
        a.hp_loss < b.hp_loss
        or a.yellow_doors < b.yellow_doors
        or a.blue_doors < b.blue_doors
        or a.red_doors < b.red_doors
    )
    return no_worse and (strictly_better_cost or a.steps <= b.steps)


def _resource_signature(mask: int, gems: list[dict[str, Any]]) -> tuple[int, int, int]:
    counts = {gem_id: 0 for gem_id in GEM_IDS}
    for index, gem in enumerate(gems):
        if mask & (1 << index):
            counts[str(gem["id"])] += 1
    return counts["redGem"], counts["blueGem"], counts["greenGem"]


def _cost(label: Label, red_potion_hp: float, yellow_weight: float, blue_weight: float, red_weight: float | None) -> float:
    cost = label.hp_loss / max(red_potion_hp, 1.0)
    cost += label.yellow_doors * yellow_weight + label.blue_doors * blue_weight
    if red_weight is not None:
        cost += label.red_doors * red_weight
    elif label.red_doors:
        return math.inf
    return cost


def _find_regions(
    matrix: list[list[int]], maps: dict[str, Any], gem_index_by_coord: dict[tuple[int, int], int]
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], int]]:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    seen: set[tuple[int, int]] = set()
    regions: list[dict[str, Any]] = []
    region_by_coord: dict[tuple[int, int], int] = {}
    for y in range(height):
        for x in range(width):
            start = (x, y)
            entry = maps.get(str(matrix[y][x]), {})
            if start in seen or not _free_passable(matrix[y][x], entry):
                continue
            stack = [start]
            seen.add(start)
            cells: list[tuple[int, int]] = []
            gem_mask = 0
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                gem_index = gem_index_by_coord.get((cx, cy))
                if gem_index is not None:
                    gem_mask |= 1 << gem_index
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nxt = (cx + dx, cy + dy)
                    nx, ny = nxt
                    if not (0 <= nx < width and 0 <= ny < height) or nxt in seen:
                        continue
                    next_entry = maps.get(str(matrix[ny][nx]), {})
                    if _free_passable(matrix[ny][nx], next_entry):
                        seen.add(nxt)
                        stack.append(nxt)
            region_id = len(regions)
            for coord in cells:
                region_by_coord[coord] = region_id
            xs = [coord[0] for coord in cells]
            ys = [coord[1] for coord in cells]
            regions.append(
                {
                    "region_id": region_id,
                    "cells": cells,
                    "gem_mask": gem_mask,
                    "bbox": [[min(xs), min(ys)], [max(xs), max(ys)]],
                }
            )
    return regions, region_by_coord


def _build_special_coverage(
    width: int,
    height: int,
    special_sources: list[dict[str, Any]],
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    coverage: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for source in special_sources:
        sx, sy = source["coord"]
        enemy = source["enemy"]
        specials = source["specials"]
        obstacle_index = int(source["obstacle_index"])
        if 15 in specials:
            range_value = max(1, int(enemy.get("range") or 1))
            for x in range(max(0, sx - range_value), min(width, sx + range_value + 1)):
                for y in range(max(0, sy - range_value), min(height, sy + range_value + 1)):
                    if (x, y) == (sx, sy):
                        continue
                    in_zone = (
                        max(abs(x - sx), abs(y - sy)) <= range_value
                        if enemy.get("zoneSquare")
                        else abs(x - sx) + abs(y - sy) <= range_value
                    )
                    if in_zone:
                        coverage.setdefault((x, y), []).append({
                            "kind": "zone",
                            "obstacle_index": obstacle_index,
                            "damage": max(0.0, _number(enemy.get("zone", enemy.get("value", 0)))),
                        })
        if 18 in specials:
            directions = (
                ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
                if enemy.get("zoneSquare")
                else ((1, 0), (-1, 0), (0, 1), (0, -1))
            )
            for dx, dy in directions:
                coord = (sx + dx, sy + dy)
                if 0 <= coord[0] < width and 0 <= coord[1] < height:
                    coverage.setdefault(coord, []).append({
                        "kind": "repulse",
                        "obstacle_index": obstacle_index,
                        "damage": max(0.0, _number(enemy.get("repulse", enemy.get("value", 0)))),
                    })
    return coverage


def _build_search_graph(
    matrix: list[list[int]],
    maps: dict[str, Any],
    gem_index_by_coord: dict[tuple[int, int], int],
    obstacle_index_by_coord: dict[tuple[int, int], int],
    coverage_by_coord: dict[tuple[int, int], list[dict[str, Any]]],
    region_by_coord: dict[tuple[int, int], int],
) -> tuple[list[dict[str, Any]], list[list[int]], dict[tuple[int, int], int], dict[str, Any]]:
    """Collapse safe empty space while preserving every stateful interaction.

    Gates and every zone/repulse-covered cell remain singleton micro-nodes.
    Gems in an uncovered zero-cost component are auto-collected together: once
    the component is entered, collecting all beneficial gems is dominant.
    """
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    passable = {
        (x, y)
        for y, row in enumerate(matrix)
        for x, raw_code in enumerate(row)
        if _passable(int(raw_code), maps.get(str(int(raw_code)), {}))
    }
    sensitive = (
        set(obstacle_index_by_coord)
        | (set(coverage_by_coord) & passable)
    )
    nodes: list[dict[str, Any]] = []
    node_by_coord: dict[tuple[int, int], int] = {}

    def add_node(kind: str, coords: list[tuple[int, int]]) -> None:
        node_id = len(nodes)
        representative = min(coords, key=lambda coord: (coord[1], coord[0]))
        gem_mask = 0
        for coord in coords:
            gem_index = gem_index_by_coord.get(coord)
            if gem_index is not None:
                gem_mask |= 1 << gem_index
            node_by_coord[coord] = node_id
        region_ids = sorted({region_by_coord[coord] for coord in coords if coord in region_by_coord})
        obstacle_index = next(
            (obstacle_index_by_coord[coord] for coord in coords if coord in obstacle_index_by_coord),
            None,
        )
        nodes.append({
            "node_id": node_id,
            "kind": kind,
            "coord": representative,
            "coords": coords,
            "gem_mask": gem_mask,
            "obstacle_index": obstacle_index,
            "region_ids": region_ids,
            "damage_events": list(coverage_by_coord.get(representative, [])),
        })

    for coord in sorted(sensitive, key=lambda item: (item[1], item[0])):
        if coord not in passable:
            continue
        if coord in obstacle_index_by_coord:
            kind = "gate"
        elif coord in gem_index_by_coord:
            kind = "gem"
        else:
            kind = "special_cell"
        add_node(kind, [coord])

    seen: set[tuple[int, int]] = set(node_by_coord)
    safe_area_count = 0
    for start in sorted(passable - seen, key=lambda item: (item[1], item[0])):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        coords: list[tuple[int, int]] = []
        while stack:
            x, y = stack.pop()
            coords.append((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (x + dx, y + dy)
                if nxt in passable and nxt not in sensitive and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        add_node("safe_area", coords)
        safe_area_count += 1

    adjacency_sets: list[set[int]] = [set() for _ in nodes]
    edge_count = 0
    for x, y in passable:
        source = node_by_coord[(x, y)]
        for dx, dy in ((1, 0), (0, 1)):
            nxt = (x + dx, y + dy)
            if nxt not in passable:
                continue
            target = node_by_coord[nxt]
            if source == target or target in adjacency_sets[source]:
                continue
            adjacency_sets[source].add(target)
            adjacency_sets[target].add(source)
            edge_count += 1
    adjacency = [sorted(neighbors) for neighbors in adjacency_sets]
    metrics = {
        "passable_cells": len(passable),
        "graph_nodes": len(nodes),
        "graph_edges": edge_count,
        "safe_area_nodes": safe_area_count,
        "micro_nodes": len(nodes) - safe_area_count,
        "special_covered_cells": len(set(coverage_by_coord) & passable),
        "auto_collected_safe_gems": sum(
            1 for coord in gem_index_by_coord if coord not in sensitive
        ),
        "compression_ratio": round(len(nodes) / max(len(passable), 1), 4),
        "max_degree": max((len(neighbors) for neighbors in adjacency), default=0),
    }
    return nodes, adjacency, node_by_coord, metrics


def _reconstruct_path(
    labels: list[Label], nodes: list[dict[str, Any]], label_id: int
) -> list[list[int]]:
    path: list[list[int]] = []
    current: int | None = label_id
    while current is not None:
        label = labels[current]
        path.append(list(nodes[label.node_id]["coord"]))
        current = label.parent
    path.reverse()
    return path


def _route_record(
    labels: list[Label],
    label_id: int,
    obstacles: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    gems: list[dict[str, Any]],
    red_potion_hp: float,
    yellow_weight: float,
    blue_weight: float,
    red_weight: float | None,
) -> dict[str, Any]:
    label = labels[label_id]
    sequence = list(label.pressure_sequence)
    pressure_tiles = [
        {
            "coord": obstacles[index]["coord"],
            "kind": obstacles[index]["kind"],
            "id": obstacles[index]["id"],
        }
        for index in sequence
    ]
    signature = _resource_signature(label.gems_mask, gems)
    return {
        "label_id": label_id,
        "resource_signature": {
            "redGem": signature[0],
            "blueGem": signature[1],
            "greenGem": signature[2],
        },
        "cost": round(_cost(label, red_potion_hp, yellow_weight, blue_weight, red_weight), 6),
        "hp_loss": round(label.hp_loss, 3),
        "yellow_doors": label.yellow_doors,
        "blue_doors": label.blue_doors,
        "red_doors": label.red_doors,
        "steps": label.steps,
        "pressure_mask": label.cleared_mask,
        "pressure_sequence": sequence,
        "pressure_tiles": pressure_tiles,
        "path": _reconstruct_path(labels, nodes, label_id),
    }


def _route_fully_dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
    # A route with a subset of B's pressure interactions and no greater cost is
    # an ornamental detour, not a distinct route family.
    subset = int(a["pressure_mask"]) & int(b["pressure_mask"]) == int(a["pressure_mask"])
    return subset and (
        a["hp_loss"] <= b["hp_loss"]
        and a["yellow_doors"] <= b["yellow_doors"]
        and a["blue_doors"] <= b["blue_doors"]
        and a["red_doors"] <= b["red_doors"]
        and int(a["pressure_mask"]) != int(b["pressure_mask"])
    )


def _compact_routes(routes: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    by_family: dict[tuple[int, ...], dict[str, Any]] = {}
    for route in routes:
        family = tuple(route["pressure_sequence"])
        old = by_family.get(family)
        if old is None or route["cost"] < old["cost"]:
            by_family[family] = route
    ordered = sorted(by_family.values(), key=lambda route: (route["cost"], route["steps"]))
    kept: list[dict[str, Any]] = []
    for route in ordered:
        if any(_route_fully_dominates(other, route) for other in kept):
            continue
        kept.append(route)
        if len(kept) >= limit:
            break
    return kept


def _compact_label_ids(
    labels: list[Label],
    label_ids: list[int],
    limit: int,
    red_potion_hp: float,
    yellow_weight: float,
    blue_weight: float,
    red_weight: float | None,
) -> list[int]:
    by_family: dict[tuple[int, ...], int] = {}
    for label_id in label_ids:
        label = labels[label_id]
        if not label.active:
            continue
        family = label.pressure_sequence
        old_id = by_family.get(family)
        if old_id is None or (
            label.hp_loss,
            label.yellow_doors,
            label.blue_doors,
            label.red_doors,
        ) < (
            labels[old_id].hp_loss,
            labels[old_id].yellow_doors,
            labels[old_id].blue_doors,
            labels[old_id].red_doors,
        ):
            by_family[family] = label_id
    ordered = sorted(
        by_family.values(),
        key=lambda item: (
            _cost(labels[item], red_potion_hp, yellow_weight, blue_weight, red_weight),
            labels[item].steps,
        ),
    )
    kept: list[int] = []
    for label_id in ordered:
        candidate = labels[label_id]
        dominated = False
        for kept_id in kept:
            other = labels[kept_id]
            subset = other.cleared_mask & candidate.cleared_mask == other.cleared_mask
            if subset and other.cleared_mask != candidate.cleared_mask and (
                other.hp_loss <= candidate.hp_loss
                and other.yellow_doors <= candidate.yellow_doors
                and other.blue_doors <= candidate.blue_doors
                and other.red_doors <= candidate.red_doors
            ):
                dominated = True
                break
        if not dominated:
            kept.append(label_id)
            if len(kept) >= limit:
                break
    return kept


def analyze_route_balance(request: dict[str, Any]) -> dict[str, Any]:
    floor_output = request.get("floor_output", {})
    floor = floor_output.get("floor", floor_output)
    matrix = floor.get("map", []) if isinstance(floor, dict) else []
    maps = request.get("maps", {})
    enemys = request.get("enemys", {})
    if not isinstance(matrix, list) or not matrix or not isinstance(matrix[0], list):
        raise ValueError("floor.map must be a non-empty rectangular matrix")
    height = len(matrix)
    width = len(matrix[0])
    if any(not isinstance(row, list) or len(row) != width for row in matrix):
        raise ValueError("floor.map must be rectangular")

    config = request.get("config", {}) if isinstance(request.get("config"), dict) else {}
    required_routes = max(3, int(config.get("required_routes", 3)))
    ratio_threshold = float(config.get("ratio_threshold", 0.8))
    yellow_weight = float(config.get("yellow_key_weight", 1.5))
    blue_weight = float(config.get("blue_key_weight", 2.5))
    red_weight_raw = config.get("red_key_weight")
    red_weight = float(red_weight_raw) if isinstance(red_weight_raw, (int, float)) and not isinstance(red_weight_raw, bool) else None
    max_expansions = max(1000, int(config.get("max_expansions", 40000)))
    max_seconds = max(0.1, float(config.get("max_seconds", 3.0)))
    max_steps_raw = config.get("max_steps")
    max_routes = max(required_routes, int(config.get("max_routes", 10)))
    labels_per_state = max(1, int(config.get("labels_per_state", 4)))
    red_potion_hp = max(1.0, float(request.get("red_potion_hp", 100.0)))
    hero = request.get("hero", {}) if isinstance(request.get("hero"), dict) else {}
    gem_values_raw = request.get("gem_values", {}) if isinstance(request.get("gem_values"), dict) else {}
    gem_values = {gem_id: _number(gem_values_raw.get(gem_id), 1.0) for gem_id in GEM_IDS}
    ratio = max(_number(floor.get("ratio"), 1.0), 0.0001)

    gems: list[dict[str, Any]] = []
    obstacles: list[dict[str, Any]] = []
    gem_index_by_coord: dict[tuple[int, int], int] = {}
    obstacle_index_by_coord: dict[tuple[int, int], int] = {}
    starts: list[tuple[int, int]] = []
    unsupported_specials: set[int] = set()
    for y, row in enumerate(matrix):
        for x, raw_code in enumerate(row):
            code = int(raw_code)
            entry = maps.get(str(code), {})
            entry_id = str(entry.get("id", ""))
            if entry_id == "downFloor":
                starts.append((x, y))
            if entry_id in GEM_IDS:
                gem_index_by_coord[(x, y)] = len(gems)
                gems.append({"id": entry_id, "coord": [x, y]})
            kind = None
            if _is_enemy(entry):
                kind = "enemy"
                unsupported_specials.update(
                    _specials(enemys.get(entry_id, {}).get("special"))
                    - SUPPORTED_BATTLE_SPECIALS
                    - SUPPORTED_RANGE_SPECIALS
                )
            elif _door_kind(entry):
                kind = f"{_door_kind(entry)}_door"
            if kind:
                obstacle_index_by_coord[(x, y)] = len(obstacles)
                obstacles.append({"kind": kind, "id": entry_id, "coord": [x, y]})

    requested_start = request.get("start")
    if (
        isinstance(requested_start, list)
        and len(requested_start) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) for value in requested_start)
        and 0 <= requested_start[0] < width
        and 0 <= requested_start[1] < height
    ):
        start = (requested_start[0], requested_start[1])
    elif starts:
        start = starts[0]
    else:
        raise ValueError("floor has no valid start coordinate or downFloor entrance")
    regions, region_by_coord = _find_regions(matrix, maps, gem_index_by_coord)
    start_region = region_by_coord.get(start)
    target_regions = [
        region for region in regions
        if region["gem_mask"] and region["region_id"] != start_region
    ]

    special_sources: list[dict[str, Any]] = []
    for obstacle_index, obstacle in enumerate(obstacles):
        if obstacle["kind"] != "enemy":
            continue
        enemy = enemys.get(str(obstacle["id"]), {})
        specials = _specials(enemy.get("special"))
        if specials & SUPPORTED_RANGE_SPECIALS:
            special_sources.append({
                "obstacle_index": obstacle_index,
                "coord": tuple(obstacle["coord"]),
                "enemy": enemy,
                "specials": specials,
            })
    coverage_by_coord = _build_special_coverage(width, height, special_sources)
    nodes, adjacency, node_by_coord, graph_metrics = _build_search_graph(
        matrix,
        maps,
        gem_index_by_coord,
        obstacle_index_by_coord,
        coverage_by_coord,
        region_by_coord,
    )
    if start not in node_by_coord:
        raise ValueError(f"start coordinate {start} is not passable")
    start_node = node_by_coord[start]
    max_steps = (
        max(len(nodes), int(max_steps_raw))
        if isinstance(max_steps_raw, (int, float)) and not isinstance(max_steps_raw, bool)
        else max(len(nodes) * 2, 1)
    )

    initial_gem_mask = int(nodes[start_node]["gem_mask"])
    initial = Label(start_node, initial_gem_mask, 0, 0, 0.0, 0, 0, 0, 0, None, ())
    labels: list[Label] = [initial]
    states: dict[tuple[int, int, int, int], list[int]] = {
        (initial.node_id, initial.gems_mask, initial.cleared_mask, initial.repulse_mask): [0]
    }
    heap: list[tuple[float, int, int]] = [
        (_cost(initial, red_potion_hp, yellow_weight, blue_weight, red_weight), 0, 0)
    ]
    target_candidates: dict[int, dict[tuple[int, int, int], list[int]]] = {
        int(region["region_id"]): {} for region in target_regions
    }
    passing_targets: set[int] = set()
    signature_cache: dict[int, tuple[int, int, int]] = {}
    hero_stats_cache: dict[int, tuple[float, float, float]] = {}

    def signature_for(mask: int) -> tuple[int, int, int]:
        if mask not in signature_cache:
            signature_cache[mask] = _resource_signature(mask, gems)
        return signature_cache[mask]

    def stats_for(mask: int) -> tuple[float, float, float]:
        if mask not in hero_stats_cache:
            red, blue, green = signature_for(mask)
            hero_stats_cache[mask] = (
                _number(hero.get("atk"), 10.0) + red * gem_values["redGem"] * ratio,
                _number(hero.get("def"), 10.0) + blue * gem_values["blueGem"] * ratio,
                _number(hero.get("mdef"), 0.0) + green * gem_values["greenGem"] * ratio,
            )
        return hero_stats_cache[mask]

    start_time = time.monotonic()
    expanded = 0
    truncated = False
    early_stopped = False
    sequence_counter = 1
    while heap:
        if expanded >= max_expansions or time.monotonic() - start_time >= max_seconds:
            truncated = True
            break
        _, _, label_id = heapq.heappop(heap)
        label = labels[label_id]
        if not label.active:
            continue
        expanded += 1

        for region_id in nodes[label.node_id]["region_ids"]:
            if region_id not in target_candidates:
                continue
            target = regions[int(region_id)]
            if label.gems_mask & int(target["gem_mask"]) == int(target["gem_mask"]):
                signature = signature_for(label.gems_mask)
                bucket = target_candidates[int(region_id)].setdefault(signature, [])
                bucket.append(label_id)
                if len(bucket) > max_routes * 4:
                    bucket.sort(key=lambda item: _cost(labels[item], red_potion_hp, yellow_weight, blue_weight, red_weight))
                    del bucket[max_routes * 4 :]
                if region_id not in passing_targets and len(bucket) >= required_routes:
                    checkpoint_ids = _compact_label_ids(
                        labels,
                        bucket,
                        required_routes,
                        red_potion_hp,
                        yellow_weight,
                        blue_weight,
                        red_weight,
                    )
                    if len(checkpoint_ids) >= required_routes:
                        checkpoint_costs = sorted(
                            _cost(labels[candidate_id], red_potion_hp, yellow_weight, blue_weight, red_weight)
                            for candidate_id in checkpoint_ids
                        )
                        best_cost = checkpoint_costs[0]
                        third_cost = checkpoint_costs[required_routes - 1]
                        checkpoint_score = 1.0 if third_cost == 0 else (0.0 if best_cost == 0 else best_cost / third_cost)
                        if checkpoint_score >= ratio_threshold:
                            passing_targets.add(int(region_id))

        if target_candidates and len(passing_targets) == len(target_candidates):
            early_stopped = True
            break

        if label.steps >= max_steps:
            continue
        atk, defense, mdef = stats_for(label.gems_mask)
        for next_node_id in adjacency[label.node_id]:
            next_node = nodes[next_node_id]
            gems_mask = label.gems_mask
            cleared_mask = label.cleared_mask
            repulse_mask = label.repulse_mask
            hp_loss = label.hp_loss
            yellow_doors = label.yellow_doors
            blue_doors = label.blue_doors
            red_doors = label.red_doors
            pressure_sequence = label.pressure_sequence

            # Map damage is evaluated against currently alive sources before
            # the destination monster is defeated.
            for event in next_node["damage_events"]:
                bit = 1 << int(event["obstacle_index"])
                if cleared_mask & bit:
                    continue
                if event["kind"] == "zone":
                    hp_loss += float(event["damage"])
                elif event["kind"] == "repulse" and not (repulse_mask & bit):
                    hp_loss += float(event["damage"])
                    repulse_mask |= bit

            obstacle_index = next_node["obstacle_index"]
            if obstacle_index is not None:
                bit = 1 << obstacle_index
                if not (cleared_mask & bit):
                    obstacle = obstacles[obstacle_index]
                    kind = obstacle["kind"]
                    if kind == "enemy":
                        damage = _battle_damage(enemys.get(str(obstacle["id"]), {}), atk, defense, mdef)
                        if not math.isfinite(damage):
                            continue
                        hp_loss += damage
                    elif kind == "yellow_door":
                        yellow_doors += 1
                    elif kind == "blue_door":
                        blue_doors += 1
                    elif kind == "red_door":
                        if red_weight is None:
                            continue
                        red_doors += 1
                    cleared_mask |= bit
                    pressure_sequence = pressure_sequence + (obstacle_index,)

            gems_mask |= int(next_node["gem_mask"])

            new_label = Label(
                next_node_id,
                gems_mask,
                cleared_mask,
                repulse_mask,
                hp_loss,
                yellow_doors,
                blue_doors,
                red_doors,
                label.steps + 1,
                label_id,
                pressure_sequence,
            )
            key = (next_node_id, gems_mask, cleared_mask, repulse_mask)
            old_ids = [old_id for old_id in states.get(key, []) if labels[old_id].active]
            if any(_dominates(labels[old_id], new_label) or (
                labels[old_id].hp_loss == new_label.hp_loss
                and labels[old_id].yellow_doors == new_label.yellow_doors
                and labels[old_id].blue_doors == new_label.blue_doors
                and labels[old_id].red_doors == new_label.red_doors
                and labels[old_id].steps == new_label.steps
            ) for old_id in old_ids):
                continue
            for old_id in old_ids:
                if _dominates(new_label, labels[old_id]):
                    labels[old_id].active = False
            kept_ids = [old_id for old_id in old_ids if labels[old_id].active]
            new_id = len(labels)
            labels.append(new_label)
            kept_ids.append(new_id)
            if len(kept_ids) > labels_per_state:
                kept_ids.sort(
                    key=lambda item: (
                        _cost(labels[item], red_potion_hp, yellow_weight, blue_weight, red_weight),
                        labels[item].steps,
                    )
                )
                for dropped_id in kept_ids[labels_per_state:]:
                    labels[dropped_id].active = False
                kept_ids = kept_ids[:labels_per_state]
                if not labels[new_id].active:
                    continue
            states[key] = kept_ids
            heapq.heappush(
                heap,
                (
                    _cost(new_label, red_potion_hp, yellow_weight, blue_weight, red_weight),
                    sequence_counter,
                    new_id,
                ),
            )
            sequence_counter += 1

    group_reports: list[dict[str, Any]] = []
    for target in target_regions:
        region_id = int(target["region_id"])
        signature_groups: list[dict[str, Any]] = []
        for signature, label_ids in target_candidates[region_id].items():
            raw_routes = [
                _route_record(
                    labels, label_id, obstacles, nodes, gems, red_potion_hp,
                    yellow_weight, blue_weight, red_weight,
                )
                for label_id in label_ids
                if labels[label_id].active
            ]
            routes = _compact_routes(raw_routes, max_routes)
            if not routes:
                continue
            top = routes[:required_routes]
            balance_score = 0.0
            if len(top) >= required_routes:
                best = float(top[0]["cost"])
                kth = float(top[required_routes - 1]["cost"])
                balance_score = 1.0 if kth == 0 else (0.0 if best == 0 else best / kth)
            signature_groups.append(
                {
                    "resource_signature": {
                        "redGem": signature[0],
                        "blueGem": signature[1],
                        "greenGem": signature[2],
                    },
                    "route_family_count": len(routes),
                    "balance_score": round(balance_score, 6),
                    "passed": len(routes) >= required_routes and balance_score >= ratio_threshold,
                    "routes": routes[:max_routes],
                }
            )
        signature_groups.sort(
            key=lambda group: (
                bool(group["passed"]),
                min(int(group["route_family_count"]), required_routes),
                float(group["balance_score"]),
            ),
            reverse=True,
        )
        selected = signature_groups[0] if signature_groups else {
            "resource_signature": {"redGem": 0, "blueGem": 0, "greenGem": 0},
            "route_family_count": 0,
            "balance_score": 0.0,
            "passed": False,
            "routes": [],
        }
        required_signature = _resource_signature(int(target["gem_mask"]), gems)
        group_reports.append(
            {
                "target_region_id": region_id,
                "target_bbox": target["bbox"],
                "target_gems": {
                    "redGem": required_signature[0],
                    "blueGem": required_signature[1],
                    "greenGem": required_signature[2],
                },
                "selected_signature_group": selected,
                "alternative_signature_group_count": max(0, len(signature_groups) - 1),
            }
        )

    passed = bool(group_reports) and all(group["selected_signature_group"]["passed"] for group in group_reports)
    floor_score = min(
        (float(group["selected_signature_group"]["balance_score"]) for group in group_reports),
        default=0.0,
    )
    status = "pass" if passed else "fail"
    return {
        "status": status,
        "balance_score": round(floor_score, 6),
        "required_routes": required_routes,
        "ratio_threshold": ratio_threshold,
        "cost_model": {
            "red_potion_hp": red_potion_hp,
            "yellow_key_weight": yellow_weight,
            "blue_key_weight": blue_weight,
            "red_key_weight": red_weight,
        },
        "estimated_hero_before_floor": {
            "atk": _number(hero.get("atk"), 10.0),
            "def": _number(hero.get("def"), 10.0),
            "mdef": _number(hero.get("mdef"), 0.0),
        },
        "target_group_count": len(group_reports),
        "groups": group_reports,
        "graph": graph_metrics,
        "search": {
            "algorithm": "BFS-compressed region graph + bounded Pareto Dijkstra-DP",
            "heuristic": "zero admissible heuristic (Dijkstra mode; A* hook reserved)",
            "expanded_labels": expanded,
            "created_labels": len(labels),
            "state_count": len(states),
            "distinct_gem_states": len(hero_stats_cache),
            "truncated": truncated,
            "early_stopped_after_all_targets_passed": early_stopped,
            "elapsed_seconds": round(time.monotonic() - start_time, 4),
            "max_expansions": max_expansions,
            "max_seconds": max_seconds,
        },
        "warnings": (
            ([f"unsupported enemy specials were ignored: {sorted(unsupported_specials)}"] if unsupported_specials else [])
            + (["search limit reached; report contains the best route families found so far"] if truncated else [])
            + (["red doors are treated as blocked until red_key_weight is configured"] if red_weight is None else [])
        ),
        "summary": (
            f"Route balance {'passed' if passed else 'failed'}: score={floor_score:.3f}, "
            f"gem regions={len(group_reports)}, expanded={expanded}, truncated={truncated}."
        ),
    }


def compact_report(report: dict[str, Any]) -> dict[str, Any]:
    compact_groups: list[dict[str, Any]] = []
    ordered_groups = sorted(
        [group for group in report.get("groups", []) if isinstance(group, dict)],
        key=lambda group: (
            bool(group.get("selected_signature_group", {}).get("passed")),
            float(group.get("selected_signature_group", {}).get("balance_score", 0.0)),
        ),
    )
    for group in ordered_groups[:4]:
        selected = group.get("selected_signature_group", {}) if isinstance(group, dict) else {}
        routes: list[dict[str, Any]] = []
        for route in selected.get("routes", [])[:3] if isinstance(selected, dict) else []:
            routes.append({
                "cost": route.get("cost"),
                "hp_loss": route.get("hp_loss"),
                "yellow_doors": route.get("yellow_doors"),
                "blue_doors": route.get("blue_doors"),
                "pressure_tiles": route.get("pressure_tiles", [])[:8],
            })
        compact_groups.append({
            "target_region_id": group.get("target_region_id"),
            "target_bbox": group.get("target_bbox"),
            "target_gems": group.get("target_gems"),
            "resource_signature": selected.get("resource_signature") if isinstance(selected, dict) else None,
            "route_family_count": selected.get("route_family_count", 0) if isinstance(selected, dict) else 0,
            "balance_score": selected.get("balance_score", 0) if isinstance(selected, dict) else 0,
            "passed": selected.get("passed", False) if isinstance(selected, dict) else False,
            "routes": routes,
        })
    return {
        "status": report.get("status"),
        "balance_score": report.get("balance_score"),
        "required_routes": report.get("required_routes"),
        "ratio_threshold": report.get("ratio_threshold"),
        "cost_model": report.get("cost_model"),
        "estimated_hero_before_floor": report.get("estimated_hero_before_floor"),
        "groups": compact_groups,
        "omitted_group_count": max(0, len(ordered_groups) - len(compact_groups)),
        "graph": report.get("graph"),
        "search": report.get("search"),
        "warnings": report.get("warnings", []),
        "summary": report.get("summary"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON request containing floor, maps, enemies, and config.")
    parser.add_argument("--output", type=Path, help="Optional JSON report path; stdout is always written.")
    parser.add_argument("--compact", action="store_true", help="Print only the top-three compact reviewer report.")
    args = parser.parse_args(argv)
    request = json.loads(args.input.read_text(encoding="utf-8"))
    report = analyze_route_balance(request)
    text = json.dumps(compact_report(report) if args.compact else report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

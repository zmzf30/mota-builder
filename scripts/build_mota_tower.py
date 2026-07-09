#!/usr/bin/env python3
"""Code-orchestrated classic mota tower build pipeline."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import heapq
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any


TRACKED_RESOURCES = [
    "yellow_doors",
    "blue_doors",
    "red_doors",
    "yellow_keys",
    "blue_keys",
    "red_keys",
    "pickaxes",
    "bombs",
    "centerFly",
    "jumpShoes",
    "redGems",
    "blueGems",
    "greenGems",
    "redPotions",
    "bluePotions",
    "yellowPotions",
    "greenPotions",
]

SUPPORTED_FLOOR_SIZES = {9, 11, 13}
DEFAULT_FLOOR_SIZE = 11
MAX_FLOOR_CONCURRENCY = 4
DEFAULT_CODEX_MODEL = "gpt-5.5"
DEFAULT_CODEX_CONFIG = [
    'model_reasoning_effort="xhigh"',
    'service_tier="priority"',
]
AGENT_BACKENDS = ("codex", "opencode")
DEFAULT_AGENT_TIMEOUT_SECONDS = 1800

RESOURCE_WEIGHT_BY_ID = {
    "redGem": 1.0,
    "blueGem": 1.0,
    "greenGem": 1.0,
    "yellowGem": 2.0,
    "redPotion": 1.0,
    "bluePotion": 2.5,
    "yellowPotion": 4.0,
    "greenPotion": 6.0,
    "yellowKey": 1.0,
    "blueKey": 2.0,
    "redKey": 4.0,
}
TOOL_ITEM_IDS = {"pickaxe", "bomb", "centerFly", "jumpShoes"}
GEM_ITEM_IDS = {"redGem", "blueGem", "greenGem", "yellowGem"}
POTION_ITEM_IDS = {"redPotion", "bluePotion", "yellowPotion", "greenPotion"}
DIRECT_RESOURCE_ITEM_IDS = set(RESOURCE_WEIGHT_BY_ID) | TOOL_ITEM_IDS | {
    "superPotion",
    "sword0", "sword1", "sword2", "sword3", "sword4", "sword5",
    "shield0", "shield1", "shield2", "shield3", "shield4", "shield5",
}
DEFAULT_MONSTER_POLICY = {
    "enemy_count_min_per_floor": 22,
    "enemy_count_max_per_floor": 33,
    "floor_overlap_ratio": 0.7,
    "special_damage_red_potion_min": 0.5,
    "special_damage_red_potion_max": 1.0,
    "no_adjacent_enemies": True,
}
DEFAULT_RESOURCE_POLICY = {
    "gem_floor_delta_min": 0.0,
    "gem_floor_delta_max": 2.0,
    "potion_floor_delta_min": 0.0,
    "potion_floor_delta_max": 2.0,
    "potion_compare_mode": "red_potion_equiv",
}
MAX_ADJACENT_WALL_MASK_SIMILARITY = 0.9
DEFAULT_WALL_RATIO_MIN = 0.45
DEFAULT_WALL_RATIO_MAX = 0.65
DEFAULT_MONSTER_TYPES_PER_FLOOR = 12
DEFAULT_ENEMY_DESIGN_COUNT = 0
HIGH_VALUE_POCKET_THRESHOLD = 3.0
DEFAULT_HIGH_VALUE_POCKET_THRESHOLD = HIGH_VALUE_POCKET_THRESHOLD
PRESSURE_ANNOTATION_KINDS = {
    "combat_chokepoint",
    "reward_guard",
    "route_tax",
    "special_candidate",
    "mini_boss_candidate",
}
STAGE_LABELS = {
    "topology": "地图结构",
    "economy": "资源和路线",
    "monster": "怪物和战斗",
    "integration": "整体",
}


def floor_label(floor_index: int) -> str:
    return f"第 {floor_index + 1} 层"


def beginner_review_reason(summary: str) -> str:
    text = str(summary or "").strip()
    lower = text.lower()
    reasons: list[str] = []

    def add(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    if "local" in lower and "passed" in lower:
        add("基础规则已经通过")
    if "broken-wall" in lower and "decorative" in lower:
        add("还有一些破墙岔路只是装饰，没有形成奖励、路线选择、道具价值或战斗压力")
    if "local topology review failed" in lower:
        add("地图结构还不合适")
    if "local economy review failed" in lower:
        add("资源、钥匙门或路线取舍还不合适")
    if "local monster review failed" in lower:
        add("怪物和战斗压力还不合适")
    if "local integration review failed" in lower:
        add("整层地图还没有达到可保存标准")
    if "entrance" in lower and "exit" in lower and "reachable" in lower:
        add("入口到出口的路线不够通顺")
    if "downfloor" in lower:
        add("缺少入口楼梯")
    if "upfloor" in lower:
        add("缺少出口楼梯")
    if "key/door pressure" in lower:
        add("钥匙和门的安排不够好")
    if ("protected resources" in lower or "protected reward" in lower) and not (
        "broken-wall" in lower and "decorative" in lower
    ):
        add("奖励或工具没有被路线、门或怪物保护起来")
    if "enemy type count" in lower:
        add("这一层怪物种类太多")
    if "at least" in lower and "enemies" in lower:
        add("这一层怪物数量太少")
    if "at most" in lower and "enemies" in lower:
        add("这一层怪物数量太多")
    if "orthogonal adjacency" in lower:
        add("有些怪物挨得太近")
    if "outside current floor policy" in lower or "outside whitelist" in lower:
        add("使用了当前楼层不允许的怪物")
    if "exceeds whole-tower limit" in lower:
        add("某类资源超过了整座塔的总量限制")
    if "adjacent wall mask similarity" in lower:
        add("这一层墙体和相邻楼层太像")
    if "wall ratio" in lower:
        add("墙的数量不在设置范围内")
    if "gem count progression" in lower or ("potion" in lower and "progression" in lower):
        add("宝石或血瓶的跨层增长不符合设置")
    if "entry-to-gem route is too easy" in lower:
        add("到宝石的路线太容易，缺少取舍")
    if "large direct resource region" in lower:
        add("有一大片奖励拿得太直接")
    if "zone/repulse damage" in lower:
        add("领域或阻击伤害不在设置范围内")

    if not reasons:
        add("地图还不够好玩，系统正在自动调整")
    return "原因：" + "；".join(reasons) + "。"


def review_retry_message(
    floor_index: int,
    stage: str,
    attempt: int,
    summary: str,
    repair_stage: str | None = None,
) -> str:
    if repair_stage:
        repair_label = STAGE_LABELS.get(repair_stage, repair_stage)
        return (
            f"{floor_label(floor_index)}第 {attempt} 次检查没通过，"
            f"正在从{repair_label}重新调整。{beginner_review_reason(summary)}"
        )
    stage_label = STAGE_LABELS.get(stage, stage)
    return (
        f"{floor_label(floor_index)}第 {attempt} 次{stage_label}检查没通过，"
        f"正在自动重试。{beginner_review_reason(summary)}"
    )


def strict_schema_object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties) if required is None else required,
        "properties": properties,
    }


def empty_schema_object() -> dict[str, Any]:
    return strict_schema_object({}, [])


def schema_array(item_schema: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": item_schema}


STRING_ARRAY_SCHEMA = schema_array({"type": "string"})
EMPTY_OBJECT_SCHEMA = empty_schema_object()
EMPTY_OBJECT_ARRAY_SCHEMA = schema_array(empty_schema_object())
RESOURCE_LIMIT_SCHEMA = strict_schema_object(
    {key: {"type": ["integer", "number", "string", "null"]} for key in TRACKED_RESOURCES}
)
RESOURCE_DELTA_SCHEMA = strict_schema_object({key: {"type": "integer"} for key in TRACKED_RESOURCES})
RESOURCE_POLICY_SCHEMA = strict_schema_object(
    {
        "gem_floor_delta_min": {"type": ["integer", "number", "null"]},
        "gem_floor_delta_max": {"type": ["integer", "number", "null"]},
        "potion_floor_delta_min": {"type": ["integer", "number", "null"]},
        "potion_floor_delta_max": {"type": ["integer", "number", "null"]},
        "potion_compare_mode": {"type": ["string", "null"]},
    }
)


BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "summary",
        "floor_count",
        "floor_size",
        "fixed_rules",
        "global_limits",
        "global_settings",
        "monster_policy",
        "resource_policy",
        "layout_policy",
        "questions",
        "confirmation_prompt",
    ],
    "properties": {
        "status": {"type": "string", "enum": ["ready", "needs_input"]},
        "summary": {"type": "string"},
        "floor_count": {"type": ["integer", "null"]},
        "floor_size": {"type": ["integer", "null"], "enum": [9, 11, 13, None]},
        "fixed_rules": STRING_ARRAY_SCHEMA,
        "global_limits": RESOURCE_LIMIT_SCHEMA,
        "global_settings": strict_schema_object(
            {
                "initial_hero": strict_schema_object(
                    {
                        "hp": {"type": ["integer", "null"]},
                        "atk": {"type": ["integer", "null"]},
                        "def": {"type": ["integer", "null"]},
                        "money": {"type": ["integer", "null"]},
                        "keys": strict_schema_object(
                            {
                                "yellow": {"type": ["integer", "null"]},
                                "blue": {"type": ["integer", "null"]},
                                "red": {"type": ["integer", "null"]},
                            }
                        ),
                    }
                ),
                "gems": strict_schema_object(
                    {
                        "redGem": {"type": ["integer", "null"]},
                        "blueGem": {"type": ["integer", "null"]},
                        "greenGem": {"type": ["integer", "null"]},
                    }
                ),
                "potions": strict_schema_object(
                    {
                        "redPotion": {"type": ["integer", "null"]},
                        "bluePotion": {"type": ["integer", "null"]},
                        "yellowPotion": {"type": ["integer", "null"]},
                        "greenPotion": {"type": ["integer", "null"]},
                    }
                ),
                "shop": strict_schema_object(
                    {
                        "enabled": {"type": ["boolean", "null"]},
                        "rule": {"type": "string"},
                        "atk_gain": {"type": ["integer", "null"]},
                        "def_gain": {"type": ["integer", "null"]},
                    }
                ),
            }
        ),
        "monster_policy": strict_schema_object(
            {
                "allowed_specials": schema_array({"type": "integer"}),
                "max_specials_per_monster": {"type": ["integer", "null"]},
                "min_no_special_ratio": {"type": ["number", "null"]},
                "monster_types_per_floor": {"type": ["integer", "null"]},
                "enemy_count_min_per_floor": {"type": ["integer", "null"]},
                "enemy_count_max_per_floor": {"type": ["integer", "null"]},
                "floor_overlap_ratio": {"type": ["number", "null"]},
                "special_damage_red_potion_min": {"type": ["number", "null"]},
                "special_damage_red_potion_max": {"type": ["number", "null"]},
                "no_adjacent_enemies": {"type": ["boolean", "null"]},
            }
        ),
        "resource_policy": RESOURCE_POLICY_SCHEMA,
        "layout_policy": STRING_ARRAY_SCHEMA,
        "questions": STRING_ARRAY_SCHEMA,
        "confirmation_prompt": {"type": "string"},
    },
}


FLOOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "floor_id",
        "floor_index",
        "floor_size",
        "summary",
        "floor",
    ],
    "properties": {
        "floor_id": {"type": "string"},
        "floor_index": {"type": "integer"},
        "floor_size": {"type": ["integer", "null"], "enum": [9, 11, 13, None]},
        "summary": {"type": "string"},
        "floor": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "floorId",
                "title",
                "name",
                "canFlyTo",
                "canFlyFrom",
                "canUseQuickShop",
                "cannotViewMap",
                "defaultGround",
                "images",
                "ratio",
                "map",
                "firstArrive",
                "eachArrive",
                "parallelDo",
                "events",
                "changeFloor",
                "afterBattle",
                "afterGetItem",
                "afterOpenDoor",
                "cannotMove",
                "bgmap",
                "fgmap",
                "width",
                "height",
                "autoEvent",
                "beforeBattle",
                "cannotMoveIn",
            ],
            "properties": {
                "floorId": {"type": "string"},
                "title": {"type": "string"},
                "name": {"type": "string"},
                "canFlyTo": {"type": "boolean"},
                "canFlyFrom": {"type": "boolean"},
                "canUseQuickShop": {"type": "boolean"},
                "cannotViewMap": {"type": "boolean"},
                "defaultGround": {"type": "string"},
                "images": STRING_ARRAY_SCHEMA,
                "ratio": {"type": ["integer", "number"]},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "map": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
                "firstArrive": EMPTY_OBJECT_ARRAY_SCHEMA,
                "eachArrive": EMPTY_OBJECT_ARRAY_SCHEMA,
                "parallelDo": {"type": "string"},
                "events": EMPTY_OBJECT_SCHEMA,
                "changeFloor": EMPTY_OBJECT_SCHEMA,
                "afterBattle": EMPTY_OBJECT_SCHEMA,
                "afterGetItem": EMPTY_OBJECT_SCHEMA,
                "afterOpenDoor": EMPTY_OBJECT_SCHEMA,
                "cannotMove": EMPTY_OBJECT_SCHEMA,
                "bgmap": EMPTY_OBJECT_ARRAY_SCHEMA,
                "fgmap": EMPTY_OBJECT_ARRAY_SCHEMA,
                "autoEvent": EMPTY_OBJECT_SCHEMA,
                "beforeBattle": EMPTY_OBJECT_SCHEMA,
                "cannotMoveIn": EMPTY_OBJECT_SCHEMA,
            },
        },
    },
}


COORD_SCHEMA = {
    "type": "array",
    "items": {"type": "integer"},
}
ANNOTATION_SCHEMA = strict_schema_object(
    {
        "stage": {"type": "string", "enum": ["topology", "economy", "monster", "integration", "unknown"]},
        "kind": {"type": "string"},
        "label": {"type": "string"},
        "coordinates": schema_array(COORD_SCHEMA),
        "description": {"type": "string"},
        "tags": STRING_ARRAY_SCHEMA,
        "data": {"type": "string"},
    }
)
STAGED_FLOOR_SCHEMA: dict[str, Any] = json.loads(json.dumps(FLOOR_SCHEMA))
STAGED_FLOOR_SCHEMA["required"] = list(FLOOR_SCHEMA["required"]) + ["annotations"]
STAGED_FLOOR_SCHEMA["properties"]["annotations"] = schema_array(ANNOTATION_SCHEMA)

STRUCTURED_ISSUE_SCHEMA = strict_schema_object(
    {
        "owner_stage": {
            "type": "string",
            "enum": ["topology", "economy", "monster", "integration"],
        },
        "severity": {"type": "string", "enum": ["fail", "warn"]},
        "coordinates": schema_array(COORD_SCHEMA),
        "reason": {"type": "string"},
        "required_change": {"type": "string"},
    }
)
STRUCTURED_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "issues", "required_changes", "budget_delta", "summary"],
    "properties": {
        "status": {"type": "string", "enum": ["pass", "fail"]},
        "issues": schema_array(STRUCTURED_ISSUE_SCHEMA),
        "required_changes": STRING_ARRAY_SCHEMA,
        "budget_delta": RESOURCE_DELTA_SCHEMA,
        "summary": {"type": "string"},
    },
}

ENEMY_DESIGN_UPDATE_SCHEMA = strict_schema_object(
    {
        "id": {"type": "string"},
        "name": {"type": ["string", "null"]},
        "hp": {"type": "integer"},
        "atk": {"type": "integer"},
        "def": {"type": "integer"},
        "money": {"type": "integer"},
        "exp": {"type": "integer"},
        "point": {"type": "integer"},
        "specials": schema_array({"type": "integer"}),
        "value": {"type": ["integer", "number", "null"]},
        "zone": {"type": ["integer", "number", "null"]},
        "repulse": {"type": ["integer", "number", "null"]},
        "range": {"type": ["integer", "null"]},
        "zoneSquare": {"type": ["boolean", "null"]},
        "notBomb": {"type": ["boolean", "null"]},
    }
)
ENEMY_DESIGN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "summary", "updates", "warnings"],
    "properties": {
        "status": {"type": "string", "enum": ["ready"]},
        "summary": {"type": "string"},
        "updates": schema_array(ENEMY_DESIGN_UPDATE_SCHEMA),
        "warnings": STRING_ARRAY_SCHEMA,
    },
}

STAGED_PIPELINE_STAGES = ["topology", "economy", "monster"]
STAGE_ORDER = {stage: index for index, stage in enumerate(STAGED_PIPELINE_STAGES)}


class PipelineError(RuntimeError):
    pass


def read_text_arg(path: str | None, inline: str | None) -> str:
    if inline:
        return inline
    if path:
        return Path(path).read_text(encoding="utf-8")
    raise PipelineError("Provide --idea-file or --idea-text.")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_js_object(path: Path) -> tuple[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    match = re.match(r"(?P<assignment>.*?)=\s*(?P<object>\{.*\})\s*;?\s*$", text, re.S)
    if not match:
        raise PipelineError(f"Cannot parse JS assignment object: {path}")
    value = json.loads(match.group("object"))
    if not isinstance(value, dict):
        raise PipelineError(f"JS assignment must contain an object: {path}")
    return match.group("assignment").strip(), value


def write_js_object(path: Path, assignment: str, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        assignment + "=\n" + json.dumps(data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


def load_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise PipelineError("Codex output must be a JSON object.")
    return value


def numeric_limits(raw_limits: dict[str, Any]) -> dict[str, int | None]:
    limits: dict[str, int | None] = {}
    for key in TRACKED_RESOURCES:
        value = raw_limits.get(key)
        if isinstance(value, bool):
            limits[key] = None
        elif isinstance(value, (int, float)) and value >= 0:
            limits[key] = int(value)
        else:
            limits[key] = None
    return limits


def normalize_floor_size(raw_size: Any) -> int:
    if raw_size is None:
        return DEFAULT_FLOOR_SIZE
    if isinstance(raw_size, bool):
        raise PipelineError(f"floor_size must be one of {sorted(SUPPORTED_FLOOR_SIZES)}, got {raw_size!r}")
    if isinstance(raw_size, str):
        raw_size = raw_size.lower().strip().replace("*", "x")
        if "x" in raw_size:
            parts = raw_size.split("x")
            if len(parts) == 2 and parts[0] == parts[1]:
                raw_size = parts[0]
        if raw_size.isdigit():
            raw_size = int(raw_size)
    if isinstance(raw_size, (int, float)) and int(raw_size) == raw_size:
        size = int(raw_size)
        if size in SUPPORTED_FLOOR_SIZES:
            return size
    raise PipelineError(f"floor_size must be one of {sorted(SUPPORTED_FLOOR_SIZES)}, got {raw_size!r}")


def normalize_delta(raw_delta: dict[str, Any] | None) -> dict[str, int]:
    raw_delta = raw_delta or {}
    delta: dict[str, int] = {}
    for key in TRACKED_RESOURCES:
        value = raw_delta.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            value = 0
        value = int(value)
        if value < 0:
            raise PipelineError(f"Negative budget_delta is invalid for {key}: {value}")
        delta[key] = value
    return delta


def coordinates_from_text(text: str) -> list[list[int]]:
    coords: list[list[int]] = []
    for match in re.finditer(r"\[(\d+)\s*,\s*(\d+)\]|\((\d+)\s*,\s*(\d+)\)", text):
        raw_x = match.group(1) or match.group(3)
        raw_y = match.group(2) or match.group(4)
        if raw_x is None or raw_y is None:
            continue
        coord = [int(raw_x), int(raw_y)]
        if coord not in coords:
            coords.append(coord)
    return coords[:12]


def structured_issue(
    owner_stage: str,
    severity: str,
    reason: str,
    required_change: str | None = None,
    coordinates: list[list[int]] | None = None,
) -> dict[str, Any]:
    if owner_stage not in {"topology", "economy", "monster", "integration"}:
        owner_stage = "integration"
    if severity not in {"fail", "warn"}:
        severity = "fail"
    return {
        "owner_stage": owner_stage,
        "severity": severity,
        "coordinates": coordinates if coordinates is not None else coordinates_from_text(reason),
        "reason": reason,
        "required_change": required_change or reason,
    }


def classify_issue_owner(text: str, default: str = "integration") -> str:
    lowered = text.lower()
    topology_words = [
        "topology", "map", "wall", "route", "path", "stairs", "stair", "floorid",
        "dimension", "connected", "connectivity", "junction", "branch", "tile code",
        "ground", "exit", "entrance", "thick", "decorative",
    ]
    economy_words = [
        "economy", "door", "key", "resource", "tool", "budget", "quota", "gem",
        "potion", "pickaxe", "bomb", "centerfly", "free region", "cluster",
        "reward", "blue-door", "yellow-door", "red-door",
    ]
    monster_words = [
        "monster", "enemy", "combat", "special", "zone", "repulse", "领域", "阻击",
        "adjacent", "battle", "chokepoint", "damage",
    ]
    if any(word in lowered for word in economy_words):
        return "economy"
    if any(word in lowered for word in monster_words):
        return "monster"
    if any(word in lowered for word in topology_words):
        return "topology"
    return default if default in {"topology", "economy", "monster", "integration"} else "integration"


def normalize_structured_issues(review: dict[str, Any], default_owner_stage: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    raw_issues = review.get("issues", [])
    if not isinstance(raw_issues, list):
        raw_issues = [str(raw_issues)]
    raw_changes = review.get("required_changes", [])
    if not isinstance(raw_changes, list):
        raw_changes = []
    for index, raw_issue in enumerate(raw_issues):
        if isinstance(raw_issue, dict):
            reason = str(raw_issue.get("reason") or raw_issue.get("summary") or raw_issue)
            owner = str(raw_issue.get("owner_stage") or default_owner_stage)
            severity = str(raw_issue.get("severity") or ("fail" if review.get("status") != "pass" else "warn"))
            coordinates = raw_issue.get("coordinates")
            if not isinstance(coordinates, list):
                coordinates = coordinates_from_text(reason)
            else:
                coordinates = [
                    [int(coord[0]), int(coord[1])]
                    for coord in coordinates
                    if (
                        isinstance(coord, list)
                        and len(coord) == 2
                        and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in coord)
                    )
                ][:12]
            required_change = str(
                raw_issue.get("required_change")
                or (raw_changes[index] if index < len(raw_changes) else reason)
            )
            issues.append(structured_issue(owner, severity, reason, required_change, coordinates))
        else:
            reason = str(raw_issue)
            change = str(raw_changes[index]) if index < len(raw_changes) else reason
            owner = classify_issue_owner(reason + " " + change, default_owner_stage)
            issues.append(structured_issue(owner, "fail", reason, change))
    return issues


def structured_review(
    owner_stage: str,
    issues: list[dict[str, Any]],
    budget_delta: dict[str, int] | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    normalized = [
        structured_issue(
            str(issue.get("owner_stage", owner_stage)),
            str(issue.get("severity", "fail")),
            str(issue.get("reason", "")),
            str(issue.get("required_change", issue.get("reason", ""))),
            issue.get("coordinates") if isinstance(issue.get("coordinates"), list) else None,
        )
        for issue in issues
    ]
    status = "fail" if any(issue["severity"] == "fail" for issue in normalized) else "pass"
    return {
        "status": status,
        "issues": normalized,
        "required_changes": [issue["required_change"] for issue in normalized],
        "budget_delta": budget_delta or empty_budget(),
        "summary": summary or ("Review failed." if status == "fail" else "Review passed."),
    }


def repair_stage_for_issue(issue: dict[str, Any]) -> str:
    owner = str(issue.get("owner_stage", "integration"))
    if owner in STAGE_ORDER:
        return owner
    text = f"{issue.get('reason', '')} {issue.get('required_change', '')}"
    classified = classify_issue_owner(text, "topology")
    return classified if classified in STAGE_ORDER else "topology"


def earliest_repair_stage(review: dict[str, Any], default_owner_stage: str = "integration") -> str:
    issues = normalize_structured_issues(review, default_owner_stage)
    fail_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    if not fail_issues:
        return "monster"
    stages = [repair_stage_for_issue(issue) for issue in fail_issues]
    return min(stages, key=lambda stage: STAGE_ORDER[stage])


def empty_budget() -> dict[str, int]:
    return {key: 0 for key in TRACKED_RESOURCES}


def remaining_budget(limits: dict[str, int | None], used: dict[str, int]) -> dict[str, int | None]:
    remaining: dict[str, int | None] = {}
    for key in TRACKED_RESOURCES:
        limit = limits.get(key)
        remaining[key] = None if limit is None else max(limit - used.get(key, 0), 0)
    return remaining


def budget_issues(
    delta: dict[str, int], limits: dict[str, int | None], used: dict[str, int]
) -> list[str]:
    issues: list[str] = []
    for key in TRACKED_RESOURCES:
        limit = limits.get(key)
        if limit is None:
            continue
        after = used.get(key, 0) + delta.get(key, 0)
        if after > limit:
            issues.append(f"{key} exceeds whole-tower limit: {after} > {limit}")
    return issues


def add_budget(used: dict[str, int], delta: dict[str, int]) -> dict[str, int]:
    return {key: used.get(key, 0) + delta.get(key, 0) for key in TRACKED_RESOURCES}


def distribute_limit(limit: int | None, floor_count: int, floor_index: int) -> int | None:
    if limit is None:
        return None
    base, remainder = divmod(limit, floor_count)
    return base + (1 if floor_index < remainder else 0)


def build_floor_contracts(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_count: int,
    floor_size: int,
    limits: dict[str, int | None],
) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for floor_index in range(floor_count):
        floor_number = floor_index + args.floor_number_offset
        if floor_index == 0:
            role = "entrance"
        elif floor_index == floor_count - 1:
            role = "final"
        else:
            role = "middle"
        resource_limits = {
            key: distribute_limit(limits.get(key), floor_count, floor_index)
            for key in TRACKED_RESOURCES
        }
        contracts.append(
            {
                "floor_index": floor_index,
                "floor_id": f"{args.floor_prefix}{floor_number}",
                "floor_size": floor_size,
                "floor_count": floor_count,
                "role": role,
                "resource_limits": resource_limits,
                "planning_hint": (
                    "Parallel floor generation contract. Treat resource_limits as this floor's hard "
                    "slice of the whole-tower budget. The final merge will connect stairs and verify "
                    "the whole tower in floor order."
                ),
            }
        )
    for contract in contracts:
        index = int(contract["floor_index"])
        contract["previous_floor_contract_summaries"] = [
            {
                "floor_id": previous["floor_id"],
                "role": previous["role"],
                "resource_limits": previous["resource_limits"],
            }
            for previous in contracts[:index]
        ]
    return contracts


def special_list(value: Any) -> list[int]:
    if value in (None, 0):
        return []
    if isinstance(value, list):
        return [int(item) for item in value if isinstance(item, (int, float))]
    if isinstance(value, (int, float)):
        return [int(value)]
    return []


def policy_number(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def monster_policy_value(brief: dict[str, Any], key: str) -> Any:
    policy = brief.get("monster_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    return policy.get(key, DEFAULT_MONSTER_POLICY.get(key))


def resource_policy_value(brief: dict[str, Any], key: str) -> Any:
    policy = brief.get("resource_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    return policy.get(key, DEFAULT_RESOURCE_POLICY.get(key))


def monster_policy_number(brief: dict[str, Any], key: str) -> float:
    return policy_number(monster_policy_value(brief, key), float(DEFAULT_MONSTER_POLICY[key]))


def monster_policy_int(brief: dict[str, Any], key: str) -> int:
    value = monster_policy_value(brief, key)
    if isinstance(value, bool):
        return int(DEFAULT_MONSTER_POLICY[key])
    if isinstance(value, (int, float)):
        return int(value)
    return int(DEFAULT_MONSTER_POLICY[key])


def resource_policy_number(brief: dict[str, Any], key: str) -> float:
    return policy_number(resource_policy_value(brief, key), float(DEFAULT_RESOURCE_POLICY[key]))


def layout_constraint_value(brief: dict[str, Any], key: str, default: float) -> float:
    constraints = brief.get("layout_constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    return policy_number(constraints.get(key), default)


def wall_ratio_range(brief: dict[str, Any] | None = None) -> tuple[float, float]:
    if brief is None:
        return DEFAULT_WALL_RATIO_MIN, DEFAULT_WALL_RATIO_MAX
    min_ratio = layout_constraint_value(brief, "wall_ratio_min", DEFAULT_WALL_RATIO_MIN)
    max_ratio = layout_constraint_value(brief, "wall_ratio_max", DEFAULT_WALL_RATIO_MAX)
    min_ratio = min(max(min_ratio, 0.0), 1.0)
    max_ratio = min(max(max_ratio, 0.0), 1.0)
    if min_ratio > max_ratio:
        min_ratio, max_ratio = max_ratio, min_ratio
    return min_ratio, max_ratio


def high_value_pocket_threshold(brief: dict[str, Any]) -> float:
    return max(
        0.0,
        layout_constraint_value(
            brief,
            "high_value_pocket_threshold",
            DEFAULT_HIGH_VALUE_POCKET_THRESHOLD,
        ),
    )


def monster_policy_bool(brief: dict[str, Any], key: str) -> bool:
    value = monster_policy_value(brief, key)
    if isinstance(value, bool):
        return value
    return bool(DEFAULT_MONSTER_POLICY[key])


def project_dir(args: argparse.Namespace) -> Path:
    return args.repo_root / "mota-js" / "project"


def load_project_tables(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    project = project_dir(args)
    _, maps = load_js_object(project / "maps.js")
    _, enemys = load_js_object(project / "enemys.js")
    runtime_enemys = getattr(args, "runtime_enemys", None)
    if isinstance(runtime_enemys, dict):
        enemys = core_clone(runtime_enemys)
    return maps, enemys


def is_wall_entry(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    entry_id = str(entry.get("id", ""))
    entry_name = str(entry.get("name", ""))
    return bool(
        entry.get("canBreak") is True
        or entry.get("cls") == "autotile"
        or "Wall" in entry_id
        or "wall" in entry_id
        or "墙" in entry_name
    )


def is_ground_entry(entry: dict[str, Any] | None) -> bool:
    if not entry or entry.get("cls") != "terrains":
        return False
    entry_id = str(entry.get("id", ""))
    return entry_id in {"ground", "ground2", "ground3", "grass", "grass2"} or entry_id.startswith("ground")


def is_door_entry(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    return bool(entry.get("doorInfo") and entry.get("trigger") == "openDoor")


def terrain_code_issues(floor: dict[str, Any], maps: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for layer_name in ("map", "bgmap", "fgmap"):
        layer = floor.get(layer_name, [])
        if not isinstance(layer, list) or not layer:
            continue
        for y, row in enumerate(layer):
            if not isinstance(row, list):
                continue
            for x, code in enumerate(row):
                if isinstance(code, bool) or not isinstance(code, int) or code == 0:
                    continue
                entry = maps.get(str(code), {})
                entry_id = entry.get("id")
                if is_ground_entry(entry):
                    issues.append(
                        f"{layer_name}[{y}][{x}] uses ground-like tile code {code}:{entry_id}; "
                        "use 0 for passable/default ground."
                    )
                elif is_wall_entry(entry) and code != 1:
                    issues.append(
                        f"{layer_name}[{y}][{x}] uses wall tile code {code}:{entry_id}; "
                        "use 1 for walls."
                    )
    return issues


def derive_budget_delta(floor: dict[str, Any], maps: dict[str, Any]) -> dict[str, int]:
    delta = {key: 0 for key in TRACKED_RESOURCES}
    for row in floor.get("map", []):
        for code in row:
            entry = maps.get(str(code), {})
            entry_id = entry.get("id")
            if is_door_entry(entry):
                keys = entry.get("doorInfo", {}).get("keys", {})
                if "yellowKey" in keys:
                    delta["yellow_doors"] += 1
                if "blueKey" in keys:
                    delta["blue_doors"] += 1
                if "redKey" in keys:
                    delta["red_doors"] += 1
            elif entry_id == "yellowKey":
                delta["yellow_keys"] += 1
            elif entry_id == "blueKey":
                delta["blue_keys"] += 1
            elif entry_id == "redKey":
                delta["red_keys"] += 1
            elif entry_id == "pickaxe":
                delta["pickaxes"] += 1
            elif entry_id == "bomb":
                delta["bombs"] += 1
            elif entry_id == "centerFly":
                delta["centerFly"] += 1
            elif entry_id == "jumpShoes":
                delta["jumpShoes"] += 1
            elif entry_id == "redGem":
                delta["redGems"] += 1
            elif entry_id == "blueGem":
                delta["blueGems"] += 1
            elif entry_id == "greenGem":
                delta["greenGems"] += 1
            elif entry_id == "redPotion":
                delta["redPotions"] += 1
            elif entry_id == "bluePotion":
                delta["bluePotions"] += 1
            elif entry_id == "yellowPotion":
                delta["yellowPotions"] += 1
            elif entry_id == "greenPotion":
                delta["greenPotions"] += 1
    return delta


def floor_dimensions(floor: dict[str, Any]) -> tuple[int, int, list[list[int]]]:
    raw_map = floor.get("map")
    if not isinstance(raw_map, list):
        raise PipelineError("floor.map must be an array of rows.")
    matrix: list[list[int]] = []
    for raw_row in raw_map:
        if not isinstance(raw_row, list):
            raise PipelineError("floor.map must contain only row arrays.")
        row: list[int] = []
        for value in raw_row:
            if isinstance(value, bool) or not isinstance(value, int):
                raise PipelineError("floor.map must contain integer tile codes only.")
            row.append(value)
        matrix.append(row)
    height = len(matrix)
    width = len(matrix[0]) if matrix else 0
    return width, height, matrix


def find_tile(matrix: list[list[int]], maps: dict[str, Any], tile_id: str) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if maps.get(str(code), {}).get("id") == tile_id:
                found.append((x, y))
    return found


def has_path_with_optional_one_wall(
    matrix: list[list[int]],
    maps: dict[str, Any],
    starts: list[tuple[int, int]],
    goals: list[tuple[int, int]],
) -> bool:
    if not starts or not goals:
        return False
    goal_set = set(goals)
    height = len(matrix)
    width = len(matrix[0]) if height else 0

    def passable(x: int, y: int, removed: tuple[int, int] | None) -> bool:
        if removed == (x, y):
            return True
        return not is_wall_entry(maps.get(str(matrix[y][x])))

    def search(removed: tuple[int, int] | None = None) -> bool:
        queue = list(starts)
        seen = set(queue)
        while queue:
            x, y = queue.pop(0)
            if (x, y) in goal_set:
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in seen:
                    continue
                if passable(nx, ny, removed):
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        return False

    if search():
        return True
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if is_wall_entry(maps.get(str(code))) and search((x, y)):
                return True
    return False


def local_floor_review(
    floor_output: dict[str, Any],
    floor_id: str,
    floor_size: int,
    brief: dict[str, Any],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    floor_policy: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, int]]:
    issues: list[str] = []
    floor = floor_output.get("floor")
    if not isinstance(floor, dict):
        return ["floor output must contain a floor object."], {key: 0 for key in TRACKED_RESOURCES}

    if floor_output.get("floor_id") != floor_id:
        issues.append(f"floor_id must be {floor_id}.")
    if floor.get("floorId") != floor_id:
        issues.append(f"floor.floorId must be {floor_id}.")

    try:
        width, height, matrix = floor_dimensions(floor)
    except PipelineError as exc:
        return [str(exc)], {key: 0 for key in TRACKED_RESOURCES}

    if width != floor.get("width") or height != floor.get("height"):
        issues.append("floor width/height must match map dimensions.")
    if width != floor_size or height != floor_size:
        issues.append(f"floor map must be {floor_size}x{floor_size}.")
    if any(len(row) != width for row in matrix):
        issues.append("all map rows must have the same width.")

    unknown = sorted({code for row in matrix for code in row if code != 0 and str(code) not in maps})
    if unknown:
        issues.append(f"unknown tile codes: {unknown[:8]}")
    issues.extend(terrain_code_issues(floor, maps))

    down_stairs = find_tile(matrix, maps, "downFloor")
    up_stairs = find_tile(matrix, maps, "upFloor")
    if not down_stairs:
        issues.append("floor must include at least one downFloor tile as the entrance.")
    if not up_stairs:
        issues.append("floor must include at least one upFloor tile as the exit.")
    if down_stairs and up_stairs and not has_path_with_optional_one_wall(matrix, maps, down_stairs, up_stairs):
        issues.append("entrance to exit must be reachable, or reachable after removing one wall/obstacle.")

    enemy_ids: set[str] = set()
    enemy_tiles: list[dict[str, Any]] = []
    enemy_count = 0
    doors = keys = rewards = 0
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            entry = maps.get(str(code), {})
            entry_id = entry.get("id")
            if entry.get("cls") in {"enemys", "enemy48"}:
                enemy_count += 1
                enemy_ids.add(str(entry_id))
                enemy_tiles.append({"id": str(entry_id), "coord": [x, y], "code": code})
            if is_door_entry(entry):
                doors += 1
            if entry_id in {"yellowKey", "blueKey", "redKey"}:
                keys += 1
            if entry_id in {
                "redGem", "blueGem", "greenGem", "yellowGem",
                "redPotion", "bluePotion", "greenPotion", "yellowPotion",
                "pickaxe", "bomb", "centerFly", "jumpShoes",
            }:
                rewards += 1

    min_enemies = monster_policy_int(brief, "enemy_count_min_per_floor")
    max_enemies = monster_policy_int(brief, "enemy_count_max_per_floor")
    if min_enemies > max_enemies:
        min_enemies, max_enemies = max_enemies, min_enemies
    if enemy_count < min_enemies:
        issues.append(
            f"each floor must place at least {min_enemies} enemies; found {enemy_count}."
        )
    if enemy_count > max_enemies:
        issues.append(
            f"each floor must place at most {max_enemies} enemies; found {enemy_count}."
        )
    if doors < 1 or keys < 1:
        issues.append("each floor must include key/door pressure with at least one door and at least one key.")
    if rewards < 2:
        issues.append("each floor must include protected resources or tools; avoid a pure combat/transition floor.")

    monster_policy = brief.get("monster_policy", {})
    max_types = int(monster_policy.get("monster_types_per_floor") or 9)
    if len(enemy_ids) > max_types:
        issues.append(f"enemy type count {len(enemy_ids)} exceeds monster_types_per_floor {max_types}.")
    allowed_specials = {int(item) for item in monster_policy.get("allowed_specials", [1, 2, 3, 15, 18])}
    disallowed: list[str] = []
    for enemy_id in sorted(enemy_ids):
        specials = special_list(enemys.get(enemy_id, {}).get("special"))
        for special in specials:
            if special not in allowed_specials:
                disallowed.append(f"{enemy_id}:{special}")
    if disallowed:
        issues.append(f"enemy specials outside whitelist: {', '.join(disallowed[:8])}")
    issues.extend(enemy_floor_policy_issues(matrix, maps, enemys, brief, floor_policy, enemy_tiles))

    delta = derive_budget_delta(floor, maps)
    return issues, delta


def is_enemy_entry(entry: dict[str, Any] | None) -> bool:
    return bool(entry and entry.get("cls") in {"enemys", "enemy48"})


def stage_floor_shape_issues(
    floor_output: dict[str, Any],
    expected_floor_id: str,
    floor_size: int,
    maps: dict[str, Any],
    owner_stage: str,
) -> tuple[list[dict[str, Any]], list[list[int]] | None]:
    issues: list[dict[str, Any]] = []
    floor = floor_output.get("floor")
    if not isinstance(floor, dict):
        return [structured_issue(owner_stage, "fail", "floor output must contain a floor object.")], None

    if floor_output.get("floor_id") != expected_floor_id:
        issues.append(structured_issue(owner_stage, "fail", f"floor_id must be {expected_floor_id}."))
    if floor.get("floorId") != expected_floor_id:
        issues.append(structured_issue(owner_stage, "fail", f"floor.floorId must be {expected_floor_id}."))

    try:
        width, height, matrix = floor_dimensions(floor)
    except PipelineError as exc:
        return issues + [structured_issue(owner_stage, "fail", str(exc))], None

    if width != floor.get("width") or height != floor.get("height"):
        issues.append(structured_issue(owner_stage, "fail", "floor width/height must match map dimensions."))
    if width != floor_size or height != floor_size:
        issues.append(structured_issue(owner_stage, "fail", f"floor map must be {floor_size}x{floor_size}."))
    if any(len(row) != width for row in matrix):
        issues.append(structured_issue(owner_stage, "fail", "all map rows must have the same width."))

    unknown = sorted({code for row in matrix for code in row if code != 0 and str(code) not in maps})
    if unknown:
        issues.append(structured_issue(owner_stage, "fail", f"unknown tile codes: {unknown[:8]}"))
    for terrain_issue in terrain_code_issues(floor, maps):
        issues.append(structured_issue(owner_stage, "fail", terrain_issue))
    return issues, matrix


def topology_stage_review_issues(
    floor_output: dict[str, Any],
    expected_floor_id: str,
    floor_size: int,
    maps: dict[str, Any],
    previous_floor_outputs: list[dict[str, Any]] | None = None,
    max_wall_similarity: float = MAX_ADJACENT_WALL_MASK_SIMILARITY,
    wall_ratio_min: float = DEFAULT_WALL_RATIO_MIN,
    wall_ratio_max: float = DEFAULT_WALL_RATIO_MAX,
) -> list[dict[str, Any]]:
    issues, matrix = stage_floor_shape_issues(floor_output, expected_floor_id, floor_size, maps, "topology")
    if matrix is None:
        return issues

    allowed_stair_ids = {"upFloor", "downFloor"}
    illegal_tiles: list[str] = []
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if code in {0, 1}:
                continue
            entry = maps.get(str(code), {})
            entry_id = entry.get("id")
            if entry_id not in allowed_stair_ids:
                illegal_tiles.append(f"{code}:{entry_id}@[{x},{y}]")
    if illegal_tiles:
        issues.append(
            structured_issue(
                "topology",
                "fail",
                "topology stage may only place ground, walls, downFloor, and upFloor: "
                + ", ".join(illegal_tiles[:12]),
                "Remove doors, keys, resources, tools, monsters, and other non-structural tiles from topology.",
            )
        )

    down_stairs = find_tile(matrix, maps, "downFloor")
    up_stairs = find_tile(matrix, maps, "upFloor")
    if len(down_stairs) != 1:
        issues.append(structured_issue("topology", "fail", "topology must include exactly one downFloor entrance."))
    if len(up_stairs) != 1:
        issues.append(structured_issue("topology", "fail", "topology must include exactly one upFloor exit."))
    if down_stairs and up_stairs and not has_path_with_optional_one_wall(matrix, maps, down_stairs, up_stairs):
        issues.append(
            structured_issue(
                "topology",
                "fail",
                "entrance to exit must be reachable, or reachable after removing one wall/obstacle.",
            )
        )

    wall_count = sum(1 for row in matrix for code in row if is_wall_entry(maps.get(str(code))))
    total_cells = max(len(matrix) * (len(matrix[0]) if matrix else 0), 1)
    wall_ratio = wall_count / total_cells
    if wall_ratio_min > wall_ratio_max:
        wall_ratio_min, wall_ratio_max = wall_ratio_max, wall_ratio_min
    if floor_size == 13 and not wall_ratio_min <= wall_ratio <= wall_ratio_max:
        issues.append(
            structured_issue(
                "topology",
                "warn",
                (
                    f"13x13 topology wall ratio is {wall_ratio:.2f}; "
                    f"target range is {wall_ratio_min:.2f}-{wall_ratio_max:.2f}."
                ),
                (
                    f"Adjust walls toward {wall_ratio_min:.2f}-{wall_ratio_max:.2f} "
                    "structural density while preserving route choices."
                ),
            )
        )
    for issue in wall_mask_similarity_issues(previous_floor_outputs or [], floor_output, maps, max_wall_similarity):
        issues.append(structured_issue("topology", "fail", issue))
    return issues


def wall_mask_similarity_issues(
    previous_floor_outputs: list[dict[str, Any]],
    current_floor_output: dict[str, Any],
    maps: dict[str, Any],
    max_similarity: float = MAX_ADJACENT_WALL_MASK_SIMILARITY,
) -> list[str]:
    if not previous_floor_outputs:
        return []
    previous_floor = previous_floor_outputs[-1].get("floor", {})
    current_floor = current_floor_output.get("floor", {})
    if not isinstance(previous_floor, dict) or not isinstance(current_floor, dict):
        return []
    try:
        previous_width, previous_height, previous_matrix = floor_dimensions(previous_floor)
        current_width, current_height, current_matrix = floor_dimensions(current_floor)
    except PipelineError:
        return []
    if previous_width != current_width or previous_height != current_height:
        return []
    if current_width <= 2 or current_height <= 2:
        return []

    same = 0
    total = 0
    for y in range(1, current_height - 1):
        for x in range(1, current_width - 1):
            previous_is_wall = is_wall_entry(maps.get(str(previous_matrix[y][x])))
            current_is_wall = is_wall_entry(maps.get(str(current_matrix[y][x])))
            total += 1
            if previous_is_wall == current_is_wall:
                same += 1
    if total <= 0:
        return []
    similarity = same / total
    if similarity >= max_similarity:
        current_id = current_floor_output.get("floor_id") or current_floor.get("floorId") or "current floor"
        previous_id = previous_floor_outputs[-1].get("floor_id") or previous_floor.get("floorId") or "previous floor"
        return [
            (
                f"Adjacent wall mask similarity {similarity:.3f} between {previous_id} and {current_id} "
                f"must be < {max_similarity:.2f}; redesign topology with a distinct broken-wall grammar."
            )
        ]
    return []


def annotation_kinds(floor_output: dict[str, Any]) -> set[str]:
    annotations = floor_output.get("annotations", [])
    if not isinstance(annotations, list):
        return set()
    return {
        str(annotation.get("kind", ""))
        for annotation in annotations
        if isinstance(annotation, dict)
    }


def economy_stage_review_issues(
    floor_output: dict[str, Any],
    expected_floor_id: str,
    floor_size: int,
    brief: dict[str, Any],
    maps: dict[str, Any],
    limits: dict[str, int | None],
    used: dict[str, int],
    previous_floor_outputs: list[dict[str, Any]],
    floor_contract: dict[str, Any] | None,
    enforce_resource_progression: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    issues, matrix = stage_floor_shape_issues(floor_output, expected_floor_id, floor_size, maps, "economy")
    floor = floor_output.get("floor", {}) if isinstance(floor_output.get("floor"), dict) else {}
    delta = derive_budget_delta(floor, maps) if isinstance(floor, dict) else empty_budget()
    if matrix is None:
        return issues, delta

    enemy_tiles: list[str] = []
    doors = keys = 0
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            entry = maps.get(str(code), {})
            entry_id = entry.get("id")
            if is_enemy_entry(entry):
                enemy_tiles.append(f"{entry_id}@[{x},{y}]")
            if is_door_entry(entry):
                doors += 1
            if entry_id in {"yellowKey", "blueKey", "redKey"}:
                keys += 1
    if enemy_tiles:
        issues.append(
            structured_issue(
                "economy",
                "fail",
                "economy stage must not place final enemy tiles: " + ", ".join(enemy_tiles[:12]),
                "Replace enemy tiles with combat role annotations for monster-special stage.",
            )
        )

    if doors < 1 or keys < 1:
        issues.append(
            structured_issue(
                "economy",
                "fail",
                "economy stage should establish key/door pressure with at least one door and one key.",
                "Place a meaningful door/key pair that creates route pressure or reward access.",
            )
        )

    if not (annotation_kinds(floor_output) & PRESSURE_ANNOTATION_KINDS):
        issues.append(
            structured_issue(
                "economy",
                "fail",
                "economy stage must output combat or special pressure annotations for monster placement.",
                "Add combat_chokepoint, reward_guard, route_tax, special_candidate, or mini_boss_candidate annotations.",
            )
        )

    for issue in budget_issues(delta, limits, used):
        issues.append(
            structured_issue(
                "economy",
                "fail",
                issue,
                f"Reduce tracked resource use so this floor stays within budget: {issue}",
            )
        )
    if floor_contract:
        contract_limits = floor_limits_from_contract(floor_contract)
        for key, limit in contract_limits.items():
            if limit is not None and delta.get(key, 0) != limit:
                issues.append(
                    structured_issue(
                        "economy",
                        "fail",
                        f"{key} exact floor quota mismatch: actual {delta.get(key, 0)} != required {limit}.",
                        f"Adjust {key} placements to exactly {limit} on this floor.",
                    )
                )

    metrics = floor_static_metrics(floor_output, maps, {}, brief)
    for issue in static_metric_issues(metrics):
        issues.append(structured_issue("economy", "fail", issue))
    if enforce_resource_progression:
        for issue in floor_resource_progression_issues(brief, previous_floor_outputs, floor_output, maps):
            issues.append(structured_issue("economy", "fail", issue))
    return issues, delta


def monster_stage_review_issues(
    floor_output: dict[str, Any],
    expected_floor_id: str,
    floor_size: int,
    brief: dict[str, Any],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    limits: dict[str, int | None],
    used: dict[str, int],
    previous_floor_outputs: list[dict[str, Any]],
    floor_policy: dict[str, Any] | None,
    enforce_resource_progression: bool,
    max_wall_similarity: float = MAX_ADJACENT_WALL_MASK_SIMILARITY,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, Any]]:
    local_issues, delta = local_floor_review(
        floor_output, expected_floor_id, floor_size, brief, maps, enemys, floor_policy
    )
    metrics = floor_static_metrics(floor_output, maps, enemys, brief)
    local_issues.extend(static_metric_issues(metrics))
    local_issues.extend(wall_mask_similarity_issues(previous_floor_outputs, floor_output, maps, max_wall_similarity))
    if enforce_resource_progression:
        local_issues.extend(floor_resource_progression_issues(brief, previous_floor_outputs, floor_output, maps))
    local_issues.extend(budget_issues(delta, limits, used))
    return [
        structured_issue(classify_issue_owner(issue, "monster"), "fail", issue)
        for issue in local_issues
    ], delta, metrics


def integration_stage_review_issues(
    floor_output: dict[str, Any],
    expected_floor_id: str,
    floor_size: int,
    brief: dict[str, Any],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    limits: dict[str, int | None],
    used: dict[str, int],
    previous_floor_outputs: list[dict[str, Any]],
    floor_policy: dict[str, Any] | None,
    enforce_resource_progression: bool,
    max_wall_similarity: float = MAX_ADJACENT_WALL_MASK_SIMILARITY,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, Any]]:
    local_issues, delta = local_floor_review(
        floor_output, expected_floor_id, floor_size, brief, maps, enemys, floor_policy
    )
    metrics = floor_static_metrics(floor_output, maps, enemys, brief)
    local_issues.extend(static_metric_issues(metrics))
    local_issues.extend(wall_mask_similarity_issues(previous_floor_outputs, floor_output, maps, max_wall_similarity))
    if enforce_resource_progression:
        local_issues.extend(floor_resource_progression_issues(brief, previous_floor_outputs, floor_output, maps))
    local_issues.extend(budget_issues(delta, limits, used))
    return [
        structured_issue(classify_issue_owner(issue, "integration"), "fail", issue)
        for issue in local_issues
    ], delta, metrics


def item_weight(entry_id: str | None) -> float:
    if not entry_id:
        return 0.0
    return float(RESOURCE_WEIGHT_BY_ID.get(entry_id, 0.0))


def red_potion_value(brief: dict[str, Any]) -> float:
    value = (
        brief.get("global_settings", {})
        .get("potions", {})
        .get("redPotion")
    )
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return float(value)
    return 100.0


def door_cost(entry: dict[str, Any] | None) -> float:
    if not is_door_entry(entry):
        return 0.0
    keys = entry.get("doorInfo", {}).get("keys", {})
    if "yellowKey" in keys:
        return 1.0
    if "blueKey" in keys:
        return 2.0
    if "redKey" in keys:
        return 4.0
    return 2.0


def special_damage_value(enemy: dict[str, Any], special: int) -> float:
    if special == 15:
        value = enemy.get("zone", enemy.get("value", 0))
    elif special == 18:
        value = enemy.get("repulse", enemy.get("value", 0))
    else:
        value = 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def enemy_strength_score(enemy: dict[str, Any]) -> float:
    hp = policy_number(enemy.get("hp"), 0.0)
    atk = policy_number(enemy.get("atk"), 0.0)
    defense = policy_number(enemy.get("def"), 0.0)
    money = policy_number(enemy.get("money"), 0.0)
    specials = special_list(enemy.get("special"))
    special_score = 0.0
    for special in specials:
        if special in {15, 18}:
            special_score += special_damage_value(enemy, special) * 0.35
        elif special in {1, 2, 3}:
            special_score += 12.0
        else:
            special_score += 6.0
    return hp * 0.08 + atk * 2.0 + defense * 2.5 + money * 0.35 + special_score


def enemy_role_hint(enemy: dict[str, Any]) -> str:
    hp = policy_number(enemy.get("hp"), 0.0)
    atk = policy_number(enemy.get("atk"), 0.0)
    defense = policy_number(enemy.get("def"), 0.0)
    if defense >= max(atk * 0.35, 12) and defense >= hp * 0.08:
        return "defense threshold"
    if hp >= max(atk * 3.0, 100):
        return "high HP endurance"
    if atk >= max(defense * 4.0, 45):
        return "high attack pressure"
    return "balanced combat"


def build_enemy_candidates(
    maps: dict[str, Any],
    enemys: dict[str, Any],
    brief: dict[str, Any],
) -> list[dict[str, Any]]:
    monster_policy = brief.get("monster_policy", {})
    if not isinstance(monster_policy, dict):
        monster_policy = {}
    allowed_specials = {int(item) for item in monster_policy.get("allowed_specials", [1, 2, 3, 15, 18])}
    red_potion = red_potion_value(brief)
    min_special_ratio = monster_policy_number(brief, "special_damage_red_potion_min")
    max_special_ratio = monster_policy_number(brief, "special_damage_red_potion_max")
    if min_special_ratio > max_special_ratio:
        min_special_ratio, max_special_ratio = max_special_ratio, min_special_ratio
    enemy_design = brief.get("enemy_design", {}) if isinstance(brief.get("enemy_design"), dict) else {}
    designed_enemy_ids = {
        str(item)
        for item in enemy_design.get("designed_enemy_ids", [])
        if isinstance(item, (str, int))
    }
    candidates: list[dict[str, Any]] = []
    for code, entry in sorted(maps.items(), key=lambda item: int(item[0])):
        entry_id = entry.get("id")
        if entry.get("cls") not in {"enemys", "enemy48"} or entry_id not in enemys:
            continue
        if designed_enemy_ids and str(entry_id) not in designed_enemy_ids:
            continue
        enemy = enemys[entry_id]
        if not enemy.get("hp") or not enemy.get("atk"):
            continue
        specials = special_list(enemy.get("special"))
        if any(special not in allowed_specials for special in specials):
            continue
        special_damage_ok = True
        for special in specials:
            if special not in {15, 18}:
                continue
            ratio = special_damage_value(enemy, special) / max(red_potion, 1.0)
            if ratio < min_special_ratio or ratio > max_special_ratio:
                special_damage_ok = False
                break
        if not special_damage_ok:
            continue
        candidates.append(
            {
                "code": int(code),
                "id": str(entry_id),
                "name": enemy.get("name"),
                "score": enemy_strength_score(enemy),
                "special": specials,
                "role": enemy_role_hint(enemy),
                "fallback_added": False,
            }
        )
    candidates.sort(key=lambda item: (item["score"], item["id"]))
    return candidates


def build_floor_enemy_policies(
    floor_count: int,
    maps: dict[str, Any],
    enemys: dict[str, Any],
    brief: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = build_enemy_candidates(maps, enemys, brief)
    if not candidates:
        return [
            {
                "allowed_enemy_ids": [],
                "allowed_enemy_codes": [],
                "enemy_role_hints": {},
                "fallback_no_special_enemy_ids": [],
            }
            for _ in range(floor_count)
        ]

    monster_policy = brief.get("monster_policy", {})
    if not isinstance(monster_policy, dict):
        monster_policy = {}
    max_types = int(monster_policy.get("monster_types_per_floor") or 9)
    max_types = max(max_types, 1)
    min_policy_types = min(max_types, 4)
    overlap_ratio = min(max(monster_policy_number(brief, "floor_overlap_ratio"), 0.0), 1.0)
    tier_size = max(1, (len(candidates) + max(floor_count, 1) - 1) // max(floor_count, 1))
    tiers = [candidates[index * tier_size : (index + 1) * tier_size] for index in range(floor_count)]
    no_special_candidates = [item for item in candidates if not item["special"]]

    policies: list[dict[str, Any]] = []
    for floor_index in range(floor_count):
        tier = tiers[floor_index] if floor_index < len(tiers) else []
        previous_tier = tiers[floor_index - 1] if floor_index > 0 and floor_index - 1 < len(tiers) else []
        carry_count = int(len(previous_tier) * overlap_ratio + 0.999999)
        carryover = previous_tier[-carry_count:] if previous_tier and carry_count > 0 else []
        allowed: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in carryover + tier:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            allowed.append(dict(item))

        target_score = tier[len(tier) // 2]["score"] if tier else candidates[min(floor_index * tier_size, len(candidates) - 1)]["score"]
        min_tier_score = tier[0]["score"] if tier else target_score
        fallback_pool = [
            item for item in no_special_candidates
            if item["id"] not in seen and (item["score"] >= min_tier_score or floor_index == 0)
        ]
        if not fallback_pool:
            fallback_pool = [item for item in no_special_candidates if item["id"] not in seen]
        fallback_pool.sort(key=lambda item: (abs(item["score"] - target_score), -item["score"], item["id"]))
        fallback_added: list[str] = []
        while len(allowed) < min_policy_types and fallback_pool:
            item = dict(fallback_pool.pop(0))
            item["fallback_added"] = True
            seen.add(item["id"])
            fallback_added.append(item["id"])
            allowed.append(item)

        allowed = sorted(allowed, key=lambda item: (item["score"], item["id"]))[:max_types]
        policies.append(
            {
                "allowed_enemy_ids": [item["id"] for item in allowed],
                "allowed_enemy_codes": [item["code"] for item in allowed],
                "enemy_role_hints": {item["id"]: item["role"] for item in allowed},
                "fallback_no_special_enemy_ids": [item["id"] for item in allowed if item.get("fallback_added")],
            }
        )
    return policies


def adjacent_enemy_pairs(matrix: list[list[int]], maps: dict[str, Any]) -> list[tuple[list[int], list[int]]]:
    pairs: list[tuple[list[int], list[int]]] = []
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if not is_enemy_entry(maps.get(str(code))):
                continue
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and is_enemy_entry(maps.get(str(matrix[ny][nx]))):
                    pairs.append(([x, y], [nx, ny]))
    return pairs


def enemy_floor_policy_issues(
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    brief: dict[str, Any],
    floor_policy: dict[str, Any] | None,
    enemy_tiles: list[dict[str, Any]],
) -> list[str]:
    issues: list[str] = []
    allowed_enemy_ids = set(floor_policy.get("allowed_enemy_ids", [])) if isinstance(floor_policy, dict) else set()
    if allowed_enemy_ids:
        outside = [
            f"{tile['id']}@{coord_text(tile['coord'])}"
            for tile in enemy_tiles
            if tile["id"] not in allowed_enemy_ids
        ]
        if outside:
            issues.append(f"enemy ids outside current floor policy: {', '.join(outside[:8])}")

    if monster_policy_bool(brief, "no_adjacent_enemies"):
        pairs = adjacent_enemy_pairs(matrix, maps)
        if pairs:
            text = ", ".join(f"{coord_text(a)}-{coord_text(b)}" for a, b in pairs[:8])
            issues.append(f"enemy orthogonal adjacency is forbidden: {text}")

    red_potion = red_potion_value(brief)
    min_ratio = monster_policy_number(brief, "special_damage_red_potion_min")
    max_ratio = monster_policy_number(brief, "special_damage_red_potion_max")
    if min_ratio > max_ratio:
        min_ratio, max_ratio = max_ratio, min_ratio
    damage_issues: list[str] = []
    for tile in enemy_tiles:
        enemy = enemys.get(tile["id"], {})
        for special in special_list(enemy.get("special")):
            if special not in {15, 18}:
                continue
            damage = special_damage_value(enemy, special)
            ratio = damage / max(red_potion, 1.0)
            if ratio < min_ratio or ratio > max_ratio:
                damage_issues.append(
                    f"{tile['id']}@{coord_text(tile['coord'])} special={special} damage={damage:g} "
                    f"({ratio:.2f} redPotion)"
                )
    if damage_issues:
        issues.append(
            f"zone/repulse damage must be {min_ratio:g}-{max_ratio:g} redPotion: "
            + "; ".join(damage_issues[:8])
        )
    return issues


def special_damage_cells(
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
) -> tuple[dict[tuple[int, int], float], list[dict[str, Any]]]:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    damage_by_cell: dict[tuple[int, int], float] = {}
    sources: list[dict[str, Any]] = []
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            entry = maps.get(str(code), {})
            if not is_enemy_entry(entry):
                continue
            enemy_id = str(entry.get("id", ""))
            enemy = enemys.get(enemy_id, {})
            for special in special_list(enemy.get("special")):
                if special not in {15, 18}:
                    continue
                damage = special_damage_value(enemy, special)
                affected: list[tuple[int, int]] = []
                if special == 15:
                    range_value = int(enemy.get("range") or 1)
                    zone_square = bool(enemy.get("zoneSquare"))
                    for dx in range(-range_value, range_value + 1):
                        for dy in range(-range_value, range_value + 1):
                            if dx == 0 and dy == 0:
                                continue
                            if not zone_square and abs(dx) + abs(dy) > range_value:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < width and 0 <= ny < height:
                                affected.append((nx, ny))
                else:
                    scan = (
                        ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
                        if enemy.get("zoneSquare")
                        else ((1, 0), (-1, 0), (0, 1), (0, -1))
                    )
                    for dx, dy in scan:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            affected.append((nx, ny))
                for coord in affected:
                    damage_by_cell[coord] = damage_by_cell.get(coord, 0.0) + damage
                sources.append(
                    {
                        "enemy_id": enemy_id,
                        "special": special,
                        "coord": [x, y],
                        "damage": damage,
                        "affected_cells": len(affected),
                    }
                )
    return damage_by_cell, sources


def pressure_annotation_coords(floor_output: dict[str, Any]) -> set[tuple[int, int]]:
    annotations = floor_output.get("annotations", [])
    if not isinstance(annotations, list):
        return set()
    coords: set[tuple[int, int]] = set()
    for annotation in annotations:
        if not isinstance(annotation, dict) or str(annotation.get("kind", "")) not in PRESSURE_ANNOTATION_KINDS:
            continue
        raw_coords = annotation.get("coordinates", [])
        if not isinstance(raw_coords, list):
            continue
        for coord in raw_coords:
            if (
                isinstance(coord, list)
                and len(coord) == 2
                and all(isinstance(value, int) and not isinstance(value, bool) for value in coord)
            ):
                coords.add((coord[0], coord[1]))
    return coords


def is_special_pressure_entry(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    entry_id = str(entry.get("id", ""))
    return entry_id.endswith("Net") or "Net" in entry_id or "网" in str(entry.get("name", ""))


def unguarded_high_value_pockets(
    floor_output: dict[str, Any],
    matrix: list[list[int]],
    maps: dict[str, Any],
    special_cells: dict[tuple[int, int], float],
    high_value_threshold: float = HIGH_VALUE_POCKET_THRESHOLD,
) -> list[dict[str, Any]]:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    if width <= 2 or height <= 2:
        return []

    nodes: set[tuple[int, int]] = set()
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if not is_wall_entry(maps.get(str(code))):
                nodes.add((x, y))
    if not nodes:
        return []

    down_stairs = find_tile(matrix, maps, "downFloor")
    up_stairs = find_tile(matrix, maps, "upFloor")
    start = down_stairs[0] if down_stairs else None
    goal = up_stairs[0] if up_stairs else None
    pressure_coords = pressure_annotation_coords(floor_output)

    adjacency: dict[tuple[int, int], list[tuple[int, int]]] = {node: [] for node in nodes}
    for x, y in nodes:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            if nxt in nodes:
                adjacency[(x, y)].append(nxt)

    def is_pressure(coord: tuple[int, int]) -> bool:
        x, y = coord
        entry = maps.get(str(matrix[y][x]), {})
        return (
            is_door_entry(entry)
            or is_enemy_entry(entry)
            or special_cells.get(coord, 0.0) > 0
            or is_special_pressure_entry(entry)
            or coord in pressure_coords
        )

    free_from_start: set[tuple[int, int]] | None = None
    if start is not None and start in nodes and not is_pressure(start):
        free_from_start = {start}
        queue = [start]
        while queue:
            node = queue.pop(0)
            for nxt in adjacency[node]:
                if nxt in free_from_start or is_pressure(nxt):
                    continue
                free_from_start.add(nxt)
                queue.append(nxt)

    def exposed_component(entry: tuple[int, int], branch_nodes: set[tuple[int, int]]) -> set[tuple[int, int]]:
        exposed: set[tuple[int, int]] = set()
        queue = [
            node
            for node in adjacency[entry]
            if node in branch_nodes and not is_pressure(node)
        ]
        for node in queue:
            exposed.add(node)
        while queue:
            node = queue.pop(0)
            for nxt in adjacency[node]:
                if nxt == entry or nxt not in branch_nodes or nxt in exposed or is_pressure(nxt):
                    continue
                exposed.add(nxt)
                queue.append(nxt)
        return exposed

    disc: dict[tuple[int, int], int] = {}
    low: dict[tuple[int, int], int] = {}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {}
    articulations: set[tuple[int, int]] = set()
    time = 0

    def dfs(node: tuple[int, int], root: tuple[int, int]) -> None:
        nonlocal time
        time += 1
        disc[node] = low[node] = time
        child_count = 0
        for nxt in adjacency[node]:
            if nxt not in disc:
                parent[nxt] = node
                child_count += 1
                dfs(nxt, root)
                low[node] = min(low[node], low[nxt])
                if node != root and low[nxt] >= disc[node]:
                    articulations.add(node)
            elif parent.get(node) != nxt:
                low[node] = min(low[node], disc[nxt])
        if node == root and child_count > 1:
            articulations.add(node)

    for node in sorted(nodes, key=lambda item: (item[1], item[0])):
        if node not in disc:
            parent[node] = None
            dfs(node, node)

    pockets: list[dict[str, Any]] = []
    seen_signatures: set[tuple[tuple[int, int], tuple[tuple[int, int], ...]]] = set()
    for entry in sorted(articulations, key=lambda item: (item[1], item[0])):
        if is_pressure(entry):
            continue
        remaining = nodes - {entry}
        seen: set[tuple[int, int]] = set()
        for node in sorted(remaining, key=lambda item: (item[1], item[0])):
            if node in seen:
                continue
            stack = [node]
            seen.add(node)
            component: set[tuple[int, int]] = set()
            touches_entry = False
            while stack:
                current = stack.pop()
                component.add(current)
                if entry in adjacency[current]:
                    touches_entry = True
                for nxt in adjacency[current]:
                    if nxt == entry or nxt not in remaining or nxt in seen:
                        continue
                    seen.add(nxt)
                    stack.append(nxt)
            if not touches_entry or start in component or goal in component:
                continue
            exposed = exposed_component(entry, component)
            if free_from_start is not None:
                exposed = exposed & free_from_start
            if not exposed:
                continue
            weight = 0.0
            resources: list[dict[str, Any]] = []
            for x, y in sorted(exposed, key=lambda item: (item[1], item[0])):
                entry_data = maps.get(str(matrix[y][x]), {})
                entry_id = entry_data.get("id")
                item_w = direct_resource_weight(str(entry_id) if entry_id else None)
                if item_w <= 0:
                    continue
                weight += item_w
                resources.append({"id": entry_id, "coord": [x, y], "weight": item_w})
            if weight < high_value_threshold:
                continue
            signature = (entry, tuple(sorted(exposed)))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            xs = [x for x, _ in exposed]
            ys = [y for _, y in exposed]
            pockets.append(
                {
                    "entry": [entry[0], entry[1]],
                    "bbox": [[min(xs), min(ys)], [max(xs), max(ys)]],
                    "cells": len(exposed),
                    "resource_weight": round(weight, 2),
                    "resources": resources[:20],
                }
            )
    pockets.sort(key=lambda item: (-item["resource_weight"], item["entry"][1], item["entry"][0]))
    return pockets[:12]


def floor_static_metrics(
    floor_output: dict[str, Any],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    brief: dict[str, Any],
) -> dict[str, Any]:
    floor = floor_output.get("floor", {})
    try:
        width, height, matrix = floor_dimensions(floor)
    except PipelineError:
        return {"available": False}
    total_cells = max(width * height, 1)
    red_potion = red_potion_value(brief)
    down_stairs = find_tile(matrix, maps, "downFloor")
    up_stairs = find_tile(matrix, maps, "upFloor")
    start = down_stairs[0] if down_stairs else None
    goal = up_stairs[0] if up_stairs else None
    special_cells, special_sources = special_damage_cells(matrix, maps, enemys)
    special_source_coord_set = {
        tuple(source["coord"])
        for source in special_sources
        if source.get("special") in {15, 18}
    }

    wall_count = 0
    enemy_count = 0
    door_count = 0
    resource_weight_total = 0.0
    tool_count = 0
    for row in matrix:
        for code in row:
            entry = maps.get(str(code), {})
            entry_id = entry.get("id")
            if is_wall_entry(entry):
                wall_count += 1
            if is_enemy_entry(entry):
                enemy_count += 1
            if is_door_entry(entry):
                door_count += 1
            resource_weight_total += item_weight(str(entry_id) if entry_id else None)
            if entry_id in TOOL_ITEM_IDS:
                tool_count += 1

    enemy_tiles = []
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            entry = maps.get(str(code), {})
            if not is_enemy_entry(entry):
                continue
            enemy_id = str(entry.get("id", ""))
            enemy = enemys.get(enemy_id, {})
            enemy_tiles.append(
                {
                    "id": enemy_id,
                    "code": code,
                    "coord": [x, y],
                    "hp": enemy.get("hp"),
                    "atk": enemy.get("atk"),
                    "def": enemy.get("def"),
                    "special": special_list(enemy.get("special")),
                }
            )

    non_wall_nodes: set[tuple[int, int]] = set()
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if not is_wall_entry(maps.get(str(code))):
                non_wall_nodes.add((x, y))
    non_wall_cells = max(len(non_wall_nodes), 1)
    edges = 0
    components = 0
    seen: set[tuple[int, int]] = set()
    main_component: set[tuple[int, int]] = set()
    for node in non_wall_nodes:
        if node in seen:
            continue
        components += 1
        stack = [node]
        seen.add(node)
        component: set[tuple[int, int]] = set()
        while stack:
            x, y = stack.pop()
            component.add((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (x + dx, y + dy)
                if nxt in non_wall_nodes:
                    edges += 1
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
        if start in component:
            main_component = component
    edges //= 2
    main_edges = 0
    if main_component:
        for x, y in main_component:
            for dx, dy in ((1, 0), (0, 1)):
                if (x + dx, y + dy) in main_component:
                    main_edges += 1
    main_cycle_rank = max(main_edges - len(main_component) + 1, 0) if main_component else 0

    def zero_cost_passable(x: int, y: int) -> bool:
        entry = maps.get(str(matrix[y][x]), {})
        return (
            not is_wall_entry(entry)
            and not is_door_entry(entry)
            and not is_enemy_entry(entry)
            and special_cells.get((x, y), 0.0) <= 0
        )

    free_region: set[tuple[int, int]] = set()
    if start is not None and zero_cost_passable(*start):
        queue = [start]
        free_region.add(start)
        while queue:
            x, y = queue.pop(0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in free_region:
                    continue
                if zero_cost_passable(nx, ny):
                    free_region.add((nx, ny))
                    queue.append((nx, ny))

    free_resources: list[dict[str, Any]] = []
    free_resource_weight = 0.0
    free_tools: list[dict[str, Any]] = []
    free_keys: list[dict[str, Any]] = []
    for x, y in sorted(free_region, key=lambda item: (item[1], item[0])):
        entry = maps.get(str(matrix[y][x]), {})
        entry_id = entry.get("id")
        weight = item_weight(str(entry_id) if entry_id else None)
        if weight > 0:
            free_resource_weight += weight
            free_resources.append({"id": entry_id, "coord": [x, y], "weight": weight})
        if entry_id in TOOL_ITEM_IDS:
            free_tools.append({"id": entry_id, "coord": [x, y]})
        if entry_id in {"yellowKey", "blueKey", "redKey"}:
            free_keys.append({"id": entry_id, "coord": [x, y]})
    if free_region:
        free_region_xs = [x for x, _ in free_region]
        free_region_ys = [y for _, y in free_region]
        free_region_bbox: list[list[int]] | None = [
            [min(free_region_xs), min(free_region_ys)],
            [max(free_region_xs), max(free_region_ys)],
        ]
    else:
        free_region_bbox = None

    def approximate_step_cost(x: int, y: int) -> float:
        entry = maps.get(str(matrix[y][x]), {})
        if is_wall_entry(entry):
            return 3.0
        if is_door_entry(entry):
            return door_cost(entry)
        if is_enemy_entry(entry):
            return 1.0
        return special_cells.get((x, y), 0.0) / red_potion

    resource_weight_by_cost = {"0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0}
    resources_by_cost: list[dict[str, Any]] = []
    access_distances: dict[tuple[int, int], float] = {}
    if start is not None:
        distances: dict[tuple[int, int], float] = {start: 0.0}
        heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
        while heap:
            distance, (x, y) = heapq.heappop(heap)
            if distance != distances[(x, y)]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                nd = distance + approximate_step_cost(nx, ny)
                if nd < distances.get((nx, ny), float("inf")):
                    distances[(nx, ny)] = nd
                    heapq.heappush(heap, (nd, (nx, ny)))
        access_distances = distances
        for (x, y), distance in distances.items():
            entry = maps.get(str(matrix[y][x]), {})
            entry_id = entry.get("id")
            weight = item_weight(str(entry_id) if entry_id else None)
            if weight <= 0 and entry_id not in TOOL_ITEM_IDS:
                continue
            bucket = str(min(int(distance), 3))
            resource_weight_by_cost[bucket] += weight
            resources_by_cost.append(
                {
                    "id": entry_id,
                    "coord": [x, y],
                    "approx_cost": round(distance, 2),
                    "weight": weight,
                }
            )
    resources_by_cost.sort(key=lambda item: (item["approx_cost"], item["coord"][1], item["coord"][0]))

    low_cost_resource_clusters: list[dict[str, Any]] = []
    for threshold in (0.0, 1.0, 2.0):
        eligible = {
            coord
            for coord, distance in access_distances.items()
            if distance <= threshold and not is_wall_entry(maps.get(str(matrix[coord[1]][coord[0]])))
        }
        seen_cluster: set[tuple[int, int]] = set()
        for coord in eligible:
            if coord in seen_cluster:
                continue
            stack = [coord]
            seen_cluster.add(coord)
            component: set[tuple[int, int]] = set()
            while stack:
                x, y = stack.pop()
                component.add((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nxt = (x + dx, y + dy)
                    if nxt in eligible and nxt not in seen_cluster:
                        seen_cluster.add(nxt)
                        stack.append(nxt)
            resources: list[dict[str, Any]] = []
            weight = 0.0
            tools: list[dict[str, Any]] = []
            for x, y in sorted(component, key=lambda item: (item[1], item[0])):
                entry = maps.get(str(matrix[y][x]), {})
                entry_id = entry.get("id")
                item_w = item_weight(str(entry_id) if entry_id else None)
                if item_w > 0:
                    weight += item_w
                    resources.append({"id": entry_id, "coord": [x, y], "weight": item_w})
                if entry_id in TOOL_ITEM_IDS:
                    tools.append({"id": entry_id, "coord": [x, y]})
            if not resources and not tools:
                continue
            xs = [x for x, _ in component]
            ys = [y for _, y in component]
            low_cost_resource_clusters.append(
                {
                    "threshold_cost": threshold,
                    "bbox": [[min(xs), min(ys)], [max(xs), max(ys)]],
                    "cells": len(component),
                    "resource_weight": round(weight, 2),
                    "resources": resources[:20],
                    "tools": tools,
                }
            )
    low_cost_resource_clusters.sort(
        key=lambda item: (item["threshold_cost"], -item["resource_weight"], -len(item["tools"]))
    )

    relocation_candidates: list[dict[str, Any]] = []
    fallback_relocation_candidates: list[dict[str, Any]] = []
    for (x, y), distance in sorted(access_distances.items(), key=lambda item: (-item[1], item[0][1], item[0][0])):
        entry = maps.get(str(matrix[y][x]), {})
        if (
            matrix[y][x] != 0
            or (x, y) == start
            or (x, y) == goal
            or (x, y) in special_source_coord_set
        ):
            continue
        candidate = {"coord": [x, y], "approx_cost": round(distance, 2)}
        is_interior = 0 < x < width - 1 and 0 < y < height - 1
        if is_interior:
            fallback_relocation_candidates.append(candidate)
        if is_interior and distance >= 3:
            relocation_candidates.append(candidate)
        if len(relocation_candidates) >= 12:
            break
    if not relocation_candidates:
        relocation_candidates = fallback_relocation_candidates[:12]
    if not relocation_candidates:
        relocation_candidates = [
            {"coord": [x, y], "approx_cost": round(distance, 2)}
            for (x, y), distance in sorted(access_distances.items(), key=lambda item: (-item[1], item[0][1], item[0][0]))
            if matrix[y][x] == 0 and (x, y) not in {start, goal}
        ][:12]

    open_junctions: list[dict[str, Any]] = []
    for x, y in sorted(main_component, key=lambda item: (item[1], item[0])):
        entry = maps.get(str(matrix[y][x]), {})
        entry_id = entry.get("id")
        if (
            matrix[y][x] != 0
            or (x, y) == start
            or (x, y) == goal
            or is_door_entry(entry)
            or is_enemy_entry(entry)
            or entry_id in TOOL_ITEM_IDS
        ):
            continue
        degree = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) in main_component:
                degree += 1
        if degree >= 3:
            open_junctions.append({"coord": [x, y], "degree": degree})
    open_junctions.sort(key=lambda item: (-item["degree"], item["coord"][1], item["coord"][0]))

    min_route: dict[str, Any] | None = None
    if start is not None and goal is not None:
        distances_tuple: dict[tuple[int, int], tuple[float, float, float, float, int]] = {
            start: (0.0, 0.0, 0.0, 0.0, 0)
        }
        previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        heap_tuple: list[tuple[tuple[float, float, float, float, int], tuple[int, int]]] = [
            (distances_tuple[start], start)
        ]
        while heap_tuple:
            distance, (x, y) = heapq.heappop(heap_tuple)
            if distance != distances_tuple[(x, y)]:
                continue
            if (x, y) == goal:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                entry = maps.get(str(matrix[ny][nx]), {})
                if is_wall_entry(entry):
                    continue
                add_enemy = 1.0 if is_enemy_entry(entry) else 0.0
                add_door = door_cost(entry)
                add_special = special_cells.get((nx, ny), 0.0) / red_potion
                nd = (
                    distance[0] + add_enemy,
                    distance[1] + add_door,
                    distance[2] + add_special,
                    distance[3] + add_enemy + add_door + add_special,
                    distance[4] + 1,
                )
                if nd < distances_tuple.get((nx, ny), (float("inf"),) * 5):
                    distances_tuple[(nx, ny)] = nd
                    previous[(nx, ny)] = (x, y)
                    heapq.heappush(heap_tuple, (nd, (nx, ny)))
        if goal in distances_tuple:
            path: list[tuple[int, int]] = []
            node: tuple[int, int] | None = goal
            while node is not None:
                path.append(node)
                node = previous[node]
            path.reverse()
            cost_tiles: list[dict[str, Any]] = []
            for x, y in path:
                entry = maps.get(str(matrix[y][x]), {})
                if (
                    is_enemy_entry(entry)
                    or is_door_entry(entry)
                    or special_cells.get((x, y), 0.0) > 0
                    or item_weight(str(entry.get("id")) if entry.get("id") else None) > 0
                ):
                    cost_tiles.append({"id": entry.get("id"), "coord": [x, y], "code": matrix[y][x]})
            route_distance = distances_tuple[goal]
            min_route = {
                "enemy_count": int(route_distance[0]),
                "door_cost": round(route_distance[1], 2),
                "special_red_potion_equiv": round(route_distance[2], 2),
                "total_cost_proxy": round(route_distance[3], 2),
                "steps": route_distance[4],
                "cost_tiles": cost_tiles[:20],
            }

    special_avoidable = None
    if start is not None and goal is not None and special_cells:
        queue = [start]
        seen_special = {start}
        while queue:
            x, y = queue.pop(0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in seen_special:
                    continue
                entry = maps.get(str(matrix[ny][nx]), {})
                if is_wall_entry(entry) or (nx, ny) in special_source_coord_set or special_cells.get((nx, ny), 0.0) > 0:
                    continue
                seen_special.add((nx, ny))
                queue.append((nx, ny))
        special_avoidable = goal in seen_special

    high_value_pockets = unguarded_high_value_pockets(
        floor_output,
        matrix,
        maps,
        special_cells,
        high_value_pocket_threshold(brief),
    )

    return {
        "available": True,
        "width": width,
        "height": height,
        "wall_ratio": round(wall_count / total_cells, 3),
        "wall_count": wall_count,
        "non_wall_cells": non_wall_cells,
        "enemy_count": enemy_count,
        "door_count": door_count,
        "monster_density_non_wall": round(enemy_count / non_wall_cells, 3),
        "components_non_wall": components,
        "main_component_cells": len(main_component),
        "main_cycle_rank": main_cycle_rank,
        "main_cycle_rank_ratio": round(main_cycle_rank / max(len(main_component), 1), 3),
        "resource_weight_total": round(resource_weight_total, 2),
        "tool_count": tool_count,
        "free_region_cells": len(free_region),
        "free_region_bbox": free_region_bbox,
        "free_region_reaches_exit": bool(goal is not None and goal in free_region),
        "free_region_resource_count": len(free_resources),
        "free_region_resource_weight": round(free_resource_weight, 2),
        "free_region_resources": free_resources[:20],
        "free_region_tools": free_tools,
        "free_region_keys": free_keys,
        "approx_resource_weight_by_access_cost": {
            key: round(value, 2) for key, value in resource_weight_by_cost.items()
        },
        "lowest_cost_resources": resources_by_cost[:20],
        "low_cost_resource_clusters": low_cost_resource_clusters[:12],
        "unguarded_high_value_pockets": high_value_pockets,
        "suggested_relocation_cells": relocation_candidates,
        "open_junction_wall_candidates": open_junctions[:16],
        "enemy_tiles": enemy_tiles[:40],
        "min_route_to_exit": min_route,
        "special_sources": special_sources,
        "special_affected_cells": len(special_cells),
        "special_can_be_fully_avoided": special_avoidable,
        "red_potion_value": red_potion,
    }


def coord_text(coord: Any) -> str:
    if isinstance(coord, list) and len(coord) == 2:
        return f"[{coord[0]},{coord[1]}]"
    return str(coord)


def bbox_text(bbox: Any) -> str:
    if isinstance(bbox, list) and len(bbox) == 2:
        return f"{coord_text(bbox[0])}->{coord_text(bbox[1])}"
    return "unknown bbox"


def item_coord_text(items: Any, limit: int = 8) -> str:
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id", "tile")
        coord = coord_text(item.get("coord"))
        if "approx_cost" in item:
            parts.append(f"{item_id}@{coord}(cost {item.get('approx_cost')})")
        else:
            parts.append(f"{item_id}@{coord}")
    if len(items) > limit:
        parts.append(f"... +{len(items) - limit} more")
    return ", ".join(parts)


def relocation_hint(metrics: dict[str, Any]) -> str:
    cells = item_coord_text(
        [{"id": "move_to", **cell} for cell in metrics.get("suggested_relocation_cells", [])],
        limit=6,
    )
    if not cells:
        return "add a door, monster, wall, or route detour before this region."
    return f"move excess rewards toward {cells}, or add a door, monster, wall, or route detour before this region."


def high_value_pocket_metric_issues(metrics: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for pocket in metrics.get("unguarded_high_value_pockets", [])[:4]:
        if not isinstance(pocket, dict):
            continue
        pocket_resources = item_coord_text(pocket.get("resources"))
        issues.append(
            f"High-value pocket {bbox_text(pocket.get('bbox'))} exposes resource weight "
            f"{pocket.get('resource_weight')} from unguarded entry {coord_text(pocket.get('entry'))}; "
            f"resources: {pocket_resources}; add a door, monster, special pressure, or economy pressure "
            "annotation at the pocket entrance."
        )
    return issues


def static_metric_issues(metrics: dict[str, Any]) -> list[str]:
    if not metrics.get("available"):
        return []
    issues: list[str] = []
    bbox = bbox_text(metrics.get("free_region_bbox"))
    resources = item_coord_text(metrics.get("free_region_resources"))
    tools = item_coord_text(metrics.get("free_region_tools"))
    if metrics.get("free_region_reaches_exit"):
        issues.append(
            f"Entrance free region {bbox} reaches the exit without doors, enemies, walls, or special damage; "
            f"{relocation_hint(metrics)}"
        )
    if metrics.get("free_region_resource_weight", 0) > 3:
        issues.append(
            f"Entrance free region {bbox} exposes too much resource weight: "
            f"{metrics.get('free_region_resource_weight')} > 3; resources: {resources}; {relocation_hint(metrics)}"
        )
    if metrics.get("free_region_resource_count", 0) > 3:
        issues.append(
            f"Entrance free region {bbox} exposes too many resource tiles: "
            f"{metrics.get('free_region_resource_count')} > 3; resources: {resources}; {relocation_hint(metrics)}"
        )
    if metrics.get("free_region_tools"):
        issues.append(
            f"Entrance free region {bbox} exposes tools: {tools}; protect them behind combat/doors/walls or "
            f"{relocation_hint(metrics)}"
        )
    issues.extend(high_value_pocket_metric_issues(metrics))
    return issues


def numeric_value(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def gem_gain_value(brief: dict[str, Any], gem_id: str) -> float:
    aliases = {
        "redGem": ("redGem", "red"),
        "blueGem": ("blueGem", "blue"),
        "greenGem": ("greenGem", "green"),
        "yellowGem": ("yellowGem", "yellow"),
    }
    gems = brief.get("global_settings", {}).get("gems", {})
    if not isinstance(gems, dict):
        gems = {}
    for key in aliases.get(gem_id, (gem_id,)):
        if isinstance(gems.get(key), (int, float)) and not isinstance(gems.get(key), bool):
            return float(gems[key])
    return 1.0


def potion_red_equiv_value(brief: dict[str, Any], potion_id: str) -> float:
    aliases = {
        "redPotion": ("redPotion", "red"),
        "bluePotion": ("bluePotion", "blue"),
        "yellowPotion": ("yellowPotion", "yellow"),
        "greenPotion": ("greenPotion", "green"),
    }
    potions = brief.get("global_settings", {}).get("potions", {})
    if not isinstance(potions, dict):
        potions = {}
    red_value = red_potion_value(brief)
    value = None
    for key in aliases.get(potion_id, (potion_id,)):
        raw = potions.get(key)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            value = float(raw)
            break
    if value is None:
        value = RESOURCE_WEIGHT_BY_ID.get(potion_id, 0.0) * red_value
    return value / max(red_value, 1.0)


def floor_resource_progression_profile(
    floor_output: dict[str, Any],
    maps: dict[str, Any],
    brief: dict[str, Any],
) -> dict[str, float]:
    profile = {
        "gem_count": 0.0,
        "potion_red_equiv": 0.0,
    }
    floor = floor_output.get("floor", {})
    if not isinstance(floor, dict):
        return profile
    try:
        _, _, matrix = floor_dimensions(floor)
    except PipelineError:
        return profile
    ratio = floor_ratio(floor)
    for row in matrix:
        for code in row:
            entry_id = maps.get(str(code), {}).get("id")
            if entry_id in GEM_ITEM_IDS:
                profile["gem_count"] += 1.0 * ratio
            elif entry_id in POTION_ITEM_IDS:
                profile["potion_red_equiv"] += potion_red_equiv_value(brief, str(entry_id)) * ratio
    return profile


def floor_resource_progression_issues(
    brief: dict[str, Any],
    previous_floor_outputs: list[dict[str, Any]],
    current_floor_output: dict[str, Any],
    maps: dict[str, Any],
) -> list[str]:
    if not previous_floor_outputs:
        return []
    previous = floor_resource_progression_profile(previous_floor_outputs[-1], maps, brief)
    current = floor_resource_progression_profile(current_floor_output, maps, brief)
    gem_min = resource_policy_number(brief, "gem_floor_delta_min")
    gem_max = resource_policy_number(brief, "gem_floor_delta_max")
    potion_min = resource_policy_number(brief, "potion_floor_delta_min")
    potion_max = resource_policy_number(brief, "potion_floor_delta_max")
    issues: list[str] = []

    def check_delta(label: str, key: str, min_delta: float, max_delta: float) -> None:
        lower = previous[key] + min_delta
        upper = previous[key] + max_delta
        value = current[key]
        if value + 1e-9 < lower or value - 1e-9 > upper:
            issues.append(
                f"{label} progression invalid: previous={previous[key]:g}, current={value:g}, "
                f"allowed current range={lower:g}-{upper:g}."
            )

    check_delta("gem count", "gem_count", gem_min, gem_max)
    check_delta("potion redPotion-equivalent", "potion_red_equiv", potion_min, potion_max)
    return issues


def direct_resource_weight(entry_id: str | None) -> float:
    if not entry_id:
        return 0.0
    if entry_id in TOOL_ITEM_IDS:
        return 3.0
    if entry_id == "superPotion":
        return 8.0
    if entry_id.startswith("sword") or entry_id.startswith("shield"):
        return 4.0
    return item_weight(entry_id)


def floor_ratio(floor: dict[str, Any]) -> float:
    ratio = numeric_value(floor.get("ratio"), 1.0)
    return ratio if ratio > 0 else 1.0


def hero_state_before_floor(
    brief: dict[str, Any],
    previous_floor_outputs: list[dict[str, Any]],
    maps: dict[str, Any],
) -> dict[str, float]:
    initial = brief.get("global_settings", {}).get("initial_hero", {})
    if not isinstance(initial, dict):
        initial = {}
    hero = {
        "hp": numeric_value(initial.get("hp"), 1000.0),
        "atk": numeric_value(initial.get("atk"), 10.0),
        "def": numeric_value(initial.get("def"), 10.0),
        "mdef": numeric_value(initial.get("mdef"), 0.0),
    }
    for floor_output in previous_floor_outputs:
        floor = floor_output.get("floor", {})
        if not isinstance(floor, dict):
            continue
        ratio = floor_ratio(floor)
        try:
            _, _, matrix = floor_dimensions(floor)
        except PipelineError:
            continue
        for row in matrix:
            for code in row:
                entry_id = maps.get(str(code), {}).get("id")
                if entry_id == "redGem":
                    hero["atk"] += gem_gain_value(brief, "redGem") * ratio
                elif entry_id == "blueGem":
                    hero["def"] += gem_gain_value(brief, "blueGem") * ratio
                elif entry_id == "greenGem":
                    hero["mdef"] += gem_gain_value(brief, "greenGem") * ratio
                elif entry_id == "yellowGem":
                    hero["hp"] += 1000.0 * ratio
                    hero["atk"] += 6.0 * ratio
                    hero["def"] += 6.0 * ratio
                    hero["mdef"] += 10.0 * ratio
    return hero


def parse_initial_coord_from_brief(brief: dict[str, Any], floor_id: str) -> tuple[int, int] | None:
    initial = brief.get("global_settings", {}).get("initial_hero", {})
    loc = initial.get("loc") if isinstance(initial, dict) else None
    if isinstance(loc, dict):
        x = loc.get("x")
        y = loc.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
            return int(x), int(y)
    fixed_rules = brief.get("fixed_rules", [])
    if isinstance(fixed_rules, list):
        pattern = re.compile(rf"\b{re.escape(floor_id)}\b[^\n()]*\((\d+)\s*,\s*(\d+)\)")
        for rule in fixed_rules:
            if not isinstance(rule, str):
                continue
            match = pattern.search(rule)
            if match:
                return int(match.group(1)), int(match.group(2))
    return None


def floor_entry_coord(
    brief: dict[str, Any],
    floor_output: dict[str, Any],
    matrix: list[list[int]],
    maps: dict[str, Any],
) -> tuple[int, int] | None:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    floor_index = floor_output.get("floor_index")
    if floor_index == 0:
        floor_id = str(floor_output.get("floor_id") or floor_output.get("floor", {}).get("floorId") or "")
        initial = parse_initial_coord_from_brief(brief, floor_id)
        if initial is not None:
            x, y = initial
            if 0 <= x < width and 0 <= y < height:
                return initial
    down_stairs = find_tile(matrix, maps, "downFloor")
    return down_stairs[0] if down_stairs else None


def route_passable_cell(code: int, entry: dict[str, Any] | None) -> bool:
    if code == 0:
        return True
    if not entry:
        return False
    if is_wall_entry(entry):
        return False
    if is_enemy_entry(entry) or is_door_entry(entry):
        return True
    if entry.get("cls") == "items":
        return True
    if entry.get("canPass") is True:
        return True
    if is_ground_entry(entry):
        return True
    return entry.get("id") in {"upFloor", "downFloor"}


def natural_passable_cell(
    code: int,
    entry: dict[str, Any] | None,
    coord: tuple[int, int],
    special_cells: dict[tuple[int, int], float],
) -> bool:
    return (
        route_passable_cell(code, entry)
        and not is_enemy_entry(entry)
        and not is_door_entry(entry)
        and special_cells.get(coord, 0.0) <= 0
    )


def enemy_battle_damage(enemy: dict[str, Any], hero: dict[str, float]) -> float:
    hp = numeric_value(enemy.get("hp"), 0.0)
    enemy_atk = numeric_value(enemy.get("atk"), 0.0)
    enemy_def = numeric_value(enemy.get("def"), 0.0)
    if hp <= 0:
        return 0.0
    hero_atk = hero.get("atk", 0.0)
    hero_def = hero.get("def", 0.0)
    if hero_atk <= enemy_def:
        return float("inf")
    hero_hit = hero_atk - enemy_def
    turns = int((hp + hero_hit - 1) // hero_hit)
    specials = set(special_list(enemy.get("special")))
    enemy_hit = enemy_atk if 2 in specials else max(enemy_atk - hero_def, 0.0)
    damage = enemy_hit * max(turns - 1, 0)
    if 1 in specials:
        damage += enemy_hit
    return damage


def route_step_pressure(
    coord: tuple[int, int],
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    hero: dict[str, float],
    special_cells: dict[tuple[int, int], float],
    red_potion: float,
) -> tuple[float, float, float, int, int, float, int] | None:
    x, y = coord
    entry = maps.get(str(matrix[y][x]), {})
    if not route_passable_cell(matrix[y][x], entry):
        return None
    hp_loss = 0.0
    enemy_count = 0
    door_count = 0
    key_cost = 0.0
    if is_enemy_entry(entry):
        enemy_id = str(entry.get("id", ""))
        damage = enemy_battle_damage(enemys.get(enemy_id, {}), hero)
        if damage == float("inf"):
            return None
        hp_loss += damage
        enemy_count = 1
    if is_door_entry(entry):
        key_cost = door_cost(entry)
        door_count = 1
    special_damage = max(0.0, special_cells.get(coord, 0.0) - hero.get("mdef", 0.0))
    hp_loss += special_damage
    normalized_hp = hp_loss / max(red_potion, 1.0)
    score = normalized_hp + key_cost + enemy_count * 0.35 + door_count * 0.15 + 0.02
    return score, hp_loss, key_cost, enemy_count, door_count, special_damage, 1


def add_route_cost(
    current: tuple[float, float, float, int, int, float, int],
    step: tuple[float, float, float, int, int, float, int],
) -> tuple[float, float, float, int, int, float, int]:
    return (
        current[0] + step[0],
        current[1] + step[1],
        current[2] + step[2],
        current[3] + step[3],
        current[4] + step[4],
        current[5] + step[5],
        current[6] + step[6],
    )


def pressure_route(
    matrix: list[list[int]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    hero: dict[str, float],
    starts: set[tuple[int, int]],
    goals: set[tuple[int, int]],
    special_cells: dict[tuple[int, int], float],
    red_potion: float,
) -> dict[str, Any] | None:
    if not starts or not goals:
        return None
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    start_cost = (0.0, 0.0, 0.0, 0, 0, 0.0, 0)
    distances: dict[tuple[int, int], tuple[float, float, float, int, int, float, int]] = {}
    previous: dict[tuple[int, int], tuple[int, int] | None] = {}
    heap: list[tuple[tuple[float, float, float, int, int, float, int], tuple[int, int]]] = []
    for start in starts:
        distances[start] = start_cost
        previous[start] = None
        heapq.heappush(heap, (start_cost, start))

    found: tuple[int, int] | None = None
    while heap:
        distance, (x, y) = heapq.heappop(heap)
        if distance != distances[(x, y)]:
            continue
        if (x, y) in goals:
            found = (x, y)
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            nx, ny = nxt
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            step = route_step_pressure(nxt, matrix, maps, enemys, hero, special_cells, red_potion)
            if step is None:
                continue
            nd = add_route_cost(distance, step)
            if nd < distances.get(nxt, (float("inf"),) * 7):
                distances[nxt] = nd
                previous[nxt] = (x, y)
                heapq.heappush(heap, (nd, nxt))
    if found is None:
        return None

    path: list[tuple[int, int]] = []
    node: tuple[int, int] | None = found
    while node is not None:
        path.append(node)
        node = previous[node]
    path.reverse()
    score, hp_loss, key_cost, enemy_count, door_count, special_damage, steps = distances[found]
    pressure_tiles: list[dict[str, Any]] = []
    for x, y in path:
        entry = maps.get(str(matrix[y][x]), {})
        if is_enemy_entry(entry) or is_door_entry(entry) or special_cells.get((x, y), 0.0) > 0:
            pressure_tiles.append({"id": entry.get("id"), "coord": [x, y], "code": matrix[y][x]})
    return {
        "target": [found[0], found[1]],
        "score": round(score, 2),
        "hp_loss": round(hp_loss, 1),
        "key_cost": round(key_cost, 2),
        "enemy_count": enemy_count,
        "door_count": door_count,
        "special_damage": round(special_damage, 1),
        "steps": steps,
        "path": [[x, y] for x, y in path],
        "pressure_tiles": pressure_tiles[:16],
    }


def path_text(path: Any, limit: int = 9) -> str:
    if not isinstance(path, list):
        return ""
    if len(path) <= limit:
        return "->".join(coord_text(coord) for coord in path)
    head = "->".join(coord_text(coord) for coord in path[:4])
    tail = "->".join(coord_text(coord) for coord in path[-4:])
    return f"{head}->...->{tail}"


def route_cost_text(route: dict[str, Any]) -> str:
    return (
        f"score={route.get('score')}, hp_loss={route.get('hp_loss')}, "
        f"key_cost={route.get('key_cost')}, enemies={route.get('enemy_count')}, "
        f"doors={route.get('door_count')}, steps={route.get('steps')}"
    )


def natural_resource_regions(
    matrix: list[list[int]],
    maps: dict[str, Any],
    special_cells: dict[tuple[int, int], float],
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], dict[str, Any]]]:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    seen: set[tuple[int, int]] = set()
    regions: list[dict[str, Any]] = []
    region_by_coord: dict[tuple[int, int], dict[str, Any]] = {}
    for y in range(height):
        for x in range(width):
            start = (x, y)
            if start in seen:
                continue
            entry = maps.get(str(matrix[y][x]), {})
            if not natural_passable_cell(matrix[y][x], entry, start, special_cells):
                continue
            stack = [start]
            seen.add(start)
            cells: set[tuple[int, int]] = set()
            resources: list[dict[str, Any]] = []
            gems: list[dict[str, Any]] = []
            tools: list[dict[str, Any]] = []
            weight = 0.0
            while stack:
                cx, cy = stack.pop()
                coord = (cx, cy)
                cells.add(coord)
                cell_entry = maps.get(str(matrix[cy][cx]), {})
                entry_id = cell_entry.get("id")
                resource_weight = direct_resource_weight(str(entry_id) if entry_id else None)
                if resource_weight > 0:
                    item = {"id": entry_id, "coord": [cx, cy], "weight": resource_weight}
                    resources.append(item)
                    weight += resource_weight
                    if entry_id in GEM_ITEM_IDS:
                        gems.append(item)
                    if entry_id in TOOL_ITEM_IDS:
                        tools.append(item)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nxt = (cx + dx, cy + dy)
                    nx, ny = nxt
                    if nx < 0 or ny < 0 or nx >= width or ny >= height or nxt in seen:
                        continue
                    next_entry = maps.get(str(matrix[ny][nx]), {})
                    if natural_passable_cell(matrix[ny][nx], next_entry, nxt, special_cells):
                        seen.add(nxt)
                        stack.append(nxt)
            xs = [cx for cx, _ in cells]
            ys = [cy for _, cy in cells]
            region = {
                "id": len(regions) + 1,
                "cells": cells,
                "bbox": [[min(xs), min(ys)], [max(xs), max(ys)]],
                "cell_count": len(cells),
                "resource_weight": round(weight, 2),
                "resource_count": len(resources),
                "resources": sorted(resources, key=lambda item: (item["coord"][1], item["coord"][0]))[:24],
                "gem_count": len(gems),
                "gems": sorted(gems, key=lambda item: (item["coord"][1], item["coord"][0])),
                "tools": sorted(tools, key=lambda item: (item["coord"][1], item["coord"][0])),
            }
            regions.append(region)
            for coord in cells:
                region_by_coord[coord] = region
    return regions, region_by_coord


def gem_route_balance_review(
    brief: dict[str, Any],
    floor_output: dict[str, Any],
    previous_floor_outputs: list[dict[str, Any]],
    maps: dict[str, Any],
    enemys: dict[str, Any],
) -> dict[str, Any]:
    zero_delta = {key: 0 for key in TRACKED_RESOURCES}
    floor = floor_output.get("floor", {})
    if not isinstance(floor, dict):
        return {
            "status": "pass",
            "issues": [],
            "required_changes": [],
            "budget_delta": zero_delta,
            "summary": "Gem route balance reviewer skipped because floor data is unavailable.",
        }
    try:
        _, _, matrix = floor_dimensions(floor)
    except PipelineError as exc:
        return {
            "status": "pass",
            "issues": [],
            "required_changes": [],
            "budget_delta": zero_delta,
            "summary": f"Gem route balance reviewer skipped: {exc}",
        }

    special_cells, _ = special_damage_cells(matrix, maps, enemys)
    entry = floor_entry_coord(brief, floor_output, matrix, maps)
    hero = hero_state_before_floor(brief, previous_floor_outputs, maps)
    red_potion = red_potion_value(brief)
    regions, region_by_coord = natural_resource_regions(matrix, maps, special_cells)

    gems: list[dict[str, Any]] = []
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            entry_data = maps.get(str(code), {})
            entry_id = entry_data.get("id")
            if entry_id in GEM_ITEM_IDS:
                gems.append({"id": entry_id, "coord": [x, y]})

    issues: list[str] = []
    required_changes: list[str] = []
    if not gems:
        return {
            "status": "pass",
            "issues": [],
            "required_changes": [],
            "budget_delta": zero_delta,
            "summary": "Gem route balance reviewer found no gems to compare.",
        }

    entry_routes: list[dict[str, Any]] = []
    if entry is not None:
        for gem in gems:
            target = tuple(gem["coord"])
            route = pressure_route(
                matrix, maps, enemys, hero, {entry}, {target}, special_cells, red_potion
            )
            if route is None:
                continue
            route["gem_id"] = gem["id"]
            route["gem_coord"] = gem["coord"]
            region = region_by_coord.get(target)
            if region:
                route["region_bbox"] = region["bbox"]
                route["region_resource_weight"] = region["resource_weight"]
            entry_routes.append(route)

    scores = sorted(route["score"] for route in entry_routes)
    median_score = scores[len(scores) // 2] if scores else 0.0
    for route in sorted(entry_routes, key=lambda item: item["score"])[:4]:
        zero_pressure = (
            route.get("hp_loss", 0) <= max(red_potion * 0.05, 5.0)
            and route.get("key_cost", 0) <= 0
            and route.get("enemy_count", 0) == 0
            and route.get("door_count", 0) == 0
        )
        relative_outlier = median_score >= 1.5 and route["score"] <= median_score * 0.35
        very_short = route.get("steps", 99) <= 6
        if not ((zero_pressure and very_short) or relative_outlier):
            continue
        bbox = bbox_text(route.get("region_bbox"))
        issue = (
            f"Entry-to-gem route is too easy for {route.get('gem_id')}@{coord_text(route.get('gem_coord'))} "
            f"in region {bbox}: {route_cost_text(route)}; path {path_text(route.get('path'))}."
        )
        issues.append(issue)
        required_changes.append(
            f"Rebuild region {bbox} around {route.get('gem_id')}@{coord_text(route.get('gem_coord'))}: "
            "increase the easiest route difficulty with a real door/enemy/special-damage chokepoint, "
            "a longer detour, or by moving this gem deeper into another region."
        )

    rich_regions = [
        region for region in regions
        if region["resource_count"] >= 5 or region["resource_weight"] >= 6 or region["gem_count"] >= 3
    ]
    for region in sorted(rich_regions, key=lambda item: (-item["resource_weight"], -item["resource_count"]))[:6]:
        resources = item_coord_text(region.get("resources"), limit=10)
        issue = (
            f"Large direct resource region {bbox_text(region.get('bbox'))} has "
            f"resource_weight={region.get('resource_weight')}, resources={region.get('resource_count')}, "
            f"gems={region.get('gem_count')}: {resources}."
        )
        issues.append(issue)
        required_changes.append(
            f"Rebuild direct resource region {bbox_text(region.get('bbox'))}: split the resources into staged "
            "sub-regions and add pressure on the easiest internal route before the richest rewards."
        )

    gem_regions = [region for region in regions if region["gem_count"] > 0]
    connections: list[dict[str, Any]] = []
    for index, source in enumerate(gem_regions):
        for target in gem_regions[index + 1:]:
            route = pressure_route(
                matrix,
                maps,
                enemys,
                hero,
                set(source["cells"]),
                set(target["cells"]),
                special_cells,
                red_potion,
            )
            if route is None:
                continue
            route["source_bbox"] = source["bbox"]
            route["target_bbox"] = target["bbox"]
            route["source_gems"] = source["gems"]
            route["target_gems"] = target["gems"]
            route["combined_gems"] = source["gem_count"] + target["gem_count"]
            route["combined_resource_weight"] = source["resource_weight"] + target["resource_weight"]
            connections.append(route)

    connection_scores = sorted(route["score"] for route in connections)
    connection_median = connection_scores[len(connection_scores) // 2] if connection_scores else 0.0
    for route in sorted(connections, key=lambda item: item["score"])[:4]:
        low_absolute = (
            route["score"] <= 1.2
            and route.get("hp_loss", 0) <= red_potion * 0.35
            and route.get("key_cost", 0) <= 1.0
            and route.get("enemy_count", 0) <= 1
        )
        low_relative = connection_median >= 2.0 and route["score"] <= connection_median * 0.4
        if not (low_absolute or low_relative):
            continue
        issue = (
            f"Gem regions {bbox_text(route.get('source_bbox'))} and {bbox_text(route.get('target_bbox'))} "
            f"are connected by an unusually easy route: {route_cost_text(route)}; "
            f"path {path_text(route.get('path'))}."
        )
        issues.append(issue)
        required_changes.append(
            f"Rebuild the connection between gem regions {bbox_text(route.get('source_bbox'))} and "
            f"{bbox_text(route.get('target_bbox'))}: add a stronger route gate or separate the regions so "
            "the easiest connection no longer dominates other gem-region choices."
        )

    if issues:
        return {
            "status": "fail",
            "issues": issues[:12],
            "required_changes": required_changes[:12],
            "budget_delta": zero_delta,
            "summary": f"Gem route balance reviewer found {len(issues)} route/resource imbalance issue(s).",
        }
    return {
        "status": "pass",
        "issues": [],
        "required_changes": [],
        "budget_delta": zero_delta,
        "summary": "Gem route balance reviewer found no extreme entry route, gem-region link, or direct resource blob.",
    }


def build_tile_catalog(
    maps: dict[str, Any],
    enemys: dict[str, Any],
    brief: dict[str, Any],
    floor_policy: dict[str, Any] | None = None,
) -> str:
    monster_policy = brief.get("monster_policy", {})
    if not isinstance(monster_policy, dict):
        monster_policy = {}
    allowed_specials = {int(item) for item in monster_policy.get("allowed_specials", [1, 2, 3, 15, 18])}
    floor_allowed_ids = set(floor_policy.get("allowed_enemy_ids", [])) if isinstance(floor_policy, dict) else set()
    enemy_design = brief.get("enemy_design", {}) if isinstance(brief.get("enemy_design"), dict) else {}
    designed_enemy_ids = {
        str(item)
        for item in enemy_design.get("designed_enemy_ids", [])
        if isinstance(item, (str, int))
    }
    red_potion = red_potion_value(brief)
    min_special_ratio = monster_policy_number(brief, "special_damage_red_potion_min")
    max_special_ratio = monster_policy_number(brief, "special_damage_red_potion_max")
    if min_special_ratio > max_special_ratio:
        min_special_ratio, max_special_ratio = max_special_ratio, min_special_ratio
    base_ids = {
        "lavaNet", "poisonNet", "weakNet", "curseNet",
        "yellowKey", "blueKey", "redKey", "redGem", "blueGem", "greenGem", "yellowGem",
        "redPotion", "bluePotion", "greenPotion", "yellowPotion", "superPotion",
        "pickaxe", "bomb", "centerFly", "upFloor", "downFloor",
        "yellowDoor", "blueDoor", "redDoor",
    }
    base_lines: list[str] = []
    enemy_lines: list[str] = []
    for code, entry in sorted(maps.items(), key=lambda item: int(item[0])):
        entry_id = entry.get("id")
        if entry_id in base_ids or is_door_entry(entry):
            base_lines.append(f"{code}: {entry.get('cls')}.{entry_id}")
        if entry.get("cls") in {"enemys", "enemy48"} and entry_id in enemys:
            enemy = enemys[entry_id]
            if not enemy.get("hp") or not enemy.get("atk"):
                continue
            if designed_enemy_ids and str(entry_id) not in designed_enemy_ids:
                continue
            if floor_allowed_ids and entry_id not in floor_allowed_ids:
                continue
            specials = special_list(enemy.get("special"))
            special_damage_ok = True
            for special in specials:
                if special not in {15, 18}:
                    continue
                ratio = special_damage_value(enemy, special) / max(red_potion, 1.0)
                if ratio < min_special_ratio or ratio > max_special_ratio:
                    special_damage_ok = False
                    break
            if all(special in allowed_specials for special in specials):
                if special_damage_ok:
                    enemy_lines.append(
                        f"{code}: {entry_id} {enemy.get('name')} hp={enemy.get('hp')} atk={enemy.get('atk')} "
                        f"def={enemy.get('def')} money={enemy.get('money')} special={specials or 0}"
                    )
    return (
        "Allowed tile codes:\n"
        + "0: empty/default passable ground (the only allowed ground code)\n"
        + "1: animates.yellowWall (the only allowed wall code)\n"
        + "\n".join(base_lines)
        + "\n\nAllowed enemy tile codes with current stats:\n"
        + "\n".join(enemy_lines[:28])
    )



def build_codex_command(args: argparse.Namespace, schema_path: Path, output_path: Path) -> list[str]:
    cmd = [args.codex_bin, "exec"]
    if args.model:
        cmd += ["--model", args.model]
    if args.profile:
        cmd += ["--profile", args.profile]
    for config in args.config:
        cmd += ["--config", config]
    cmd += args.codex_arg
    cmd += [
        "--cd",
        str(args.repo_root),
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox",
        args.sandbox,
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        "-",
    ]
    return cmd


def build_opencode_command(args: argparse.Namespace, prompt_path: Path) -> list[str]:
    cmd = [args.opencode_bin, "run", "--dir", str(args.repo_root)]
    if args.model:
        cmd += ["--model", args.model]
    cmd += args.opencode_arg
    cmd += [
        "Read the attached prompt file and return only the requested JSON object.",
        "--file",
        str(prompt_path),
    ]
    return cmd


def prompt_with_inline_schema(prompt: str, schema: dict[str, Any], output_path: Path | None = None) -> str:
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    result = (
        prompt.rstrip()
        + "\n\nOutput JSON Schema:\n"
        + schema_text
        + "\n\nReturn only one JSON object that matches this schema. Do not include markdown fences or commentary."
    )
    if output_path is not None:
        result += f"\n\nIMPORTANT: Write the final JSON output to the file: {output_path}"
    return result


def agent_exec(
    args: argparse.Namespace,
    prompt: str,
    schema: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    if args.agent_backend == "codex":
        return codex_exec(args, prompt, schema, output_path)
    if args.agent_backend == "opencode":
        return opencode_exec(args, prompt, schema, output_path)
    raise PipelineError(f"Unsupported agent backend: {args.agent_backend}")


def codex_exec(
    args: argparse.Namespace,
    prompt: str,
    schema: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.keep_prompts:
        output_path.with_name(output_path.name + ".prompt.md").write_text(prompt + "\n", encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".schema.json", delete=False) as schema_file:
        json.dump(schema, schema_file)
        schema_path = Path(schema_file.name)
    try:
        cmd = build_codex_command(args, schema_path, output_path)
        result = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=args.timeout,
        )
    finally:
        schema_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise PipelineError(
            "codex exec failed\n"
            + f"command: {' '.join(cmd)}\n"
            + f"stdout:\n{result.stdout}\n"
            + f"stderr:\n{result.stderr}"
        )
    return load_json_object(output_path.read_text(encoding="utf-8"))


def opencode_exec(
    args: argparse.Namespace,
    prompt: str,
    schema: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    full_prompt = prompt_with_inline_schema(prompt, schema, output_path)
    prompt_path = output_path.with_name(output_path.name + ".prompt.md")
    if args.keep_prompts:
        prompt_path.write_text(full_prompt + "\n", encoding="utf-8")
    else:
        prompt_path = output_path.with_name(output_path.name + ".opencode.prompt.md")
        prompt_path.write_text(full_prompt + "\n", encoding="utf-8")
    try:
        cmd = build_opencode_command(args, prompt_path)
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=args.timeout,
        )
    finally:
        if not args.keep_prompts:
            prompt_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise PipelineError(
            "opencode run failed\n"
            + f"command: {' '.join(cmd)}\n"
            + f"stdout:\n{result.stdout}\n"
            + f"stderr:\n{result.stderr}"
        )
    parsed = None
    if output_path.exists():
        try:
            parsed = load_json_object(output_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, PipelineError):
            parsed = None
    if parsed is None:
        try:
            parsed = load_json_object(result.stdout)
        except (json.JSONDecodeError, PipelineError) as exc:
            raise PipelineError(
                "opencode output must contain a JSON object.\n"
                + f"command: {' '.join(cmd)}\n"
                + f"stdout:\n{result.stdout}\n"
                + f"stderr:\n{result.stderr}"
            ) from exc
        write_json(output_path, parsed)
    return parsed


def skill_path(repo_root: Path, name: str) -> Path:
    return repo_root / "skills" / name / "SKILL.md"


def build_brief_prompt(args: argparse.Namespace, idea: str) -> str:
    hints: list[str] = []
    if args.floors:
        hints.append(f"Requested floor count override: {args.floors}.")
    if args.floor_size:
        hints.append(f"Requested floor size override: {args.floor_size}x{args.floor_size}.")
    else:
        hints.append(f"Default floor size: {DEFAULT_FLOOR_SIZE}x{DEFAULT_FLOOR_SIZE} unless the user asks for 9x9 or 13x13.")
    floor_hint = "\n" + "\n".join(hints) if hints else ""
    return textwrap.dedent(
        f"""
        Read and follow this skill file first:
        {skill_path(args.repo_root, "design-traditional-mota-tower")}

        You are stage 0 of a code-orchestrated classic mota tower pipeline.
        Return only JSON matching the provided schema.
        If the idea is too vague to produce a buildable whole-tower brief, set status to needs_input.
        Do not generate floor maps.
        {floor_hint}

        User idea:
        {idea}
        """
    ).strip()


def enemy_design_slot_lines(maps: dict[str, Any], enemys: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for code, entry in sorted(maps.items(), key=lambda item: int(item[0])):
        entry_id = str(entry.get("id", ""))
        if entry.get("cls") not in {"enemys", "enemy48"} or entry_id not in enemys or entry_id in seen:
            continue
        seen.add(entry_id)
        enemy = enemys.get(entry_id, {})
        lines.append(
            f"- code={code}, id={entry_id}, display_name={enemy.get('name') or entry.get('name') or entry_id}, "
            f"class={entry.get('cls')}"
        )
    return lines


def build_enemy_design_prompt(
    args: argparse.Namespace,
    brief: dict[str, Any],
    maps: dict[str, Any],
    enemys: dict[str, Any],
    floor_count: int,
    floor_size: int,
) -> str:
    monster_policy = brief.get("monster_policy", {}) if isinstance(brief.get("monster_policy"), dict) else {}
    allowed_specials = monster_policy.get("allowed_specials", [1, 2, 3, 15, 18])
    max_types = int(monster_policy.get("monster_types_per_floor") or 9)
    slot_lines = enemy_design_slot_lines(maps, enemys)
    configured_count = int(getattr(args, "enemy_design_count", DEFAULT_ENEMY_DESIGN_COUNT) or 0)
    if configured_count > 0:
        target_updates = min(len(slot_lines), configured_count)
    else:
        target_updates = len(slot_lines)
    payload = {
        "tower_brief": brief,
        "floor_count": floor_count,
        "floor_size": floor_size,
        "allowed_specials": allowed_specials,
        "max_specials_per_monster": monster_policy.get("max_specials_per_monster", 1),
        "target_updated_enemy_slots": target_updates,
        "red_potion_hp": red_potion_value(brief),
        "special_damage_red_potion_range": [
            monster_policy_number(brief, "special_damage_red_potion_min"),
            monster_policy_number(brief, "special_damage_red_potion_max"),
        ],
        "available_enemy_slots": slot_lines,
    }
    return textwrap.dedent(
        f"""
        Read and follow this skill file first:
        {skill_path(args.repo_root, "modify-mota-enemy-data")}

        You are stage 0.5 of a code-orchestrated classic mota tower pipeline.
        Return only JSON matching the provided schema.

        Design this tower's monster stat table before any floor is generated.
        Treat existing enemy ids, names, and sprites only as reusable slots. Ignore their existing
        hp/atk/def/money/special settings and assign fresh values for this tower.
        You are allowed and expected to overwrite enemy slots that already have stats.
        Do not create new enemy ids, tile codes, sprites, scripts, events, or map placements.

        Requirements:
        - Update as many existing enemy slots as requested by target_updated_enemy_slots. If this
          equals the available slot count, rewrite every available enemy slot.
        - A later floor-generation stage may use only some of these enemies; the purpose is to give
          monster-special enough choices across weak, medium, strong, and special-pressure roles.
        - Create a readable progression from early weak monsters to late high-pressure monsters.
        - Same-floor choices should have different roles: HP sponge, attack tax, defense threshold,
          reward guard, route tax, and optional special-pressure enemies.
        - Use only allowed_specials, and use at most one special per monster unless the brief says otherwise.
        - For special 15 (zone) and 18 (repulse), set zone/repulse/value so the damage is within
          the supplied red-potion ratio range; set range to 1 unless there is a clear reason.
        - Non-special monsters must return specials=[].
        - Keep all numeric values non-negative, and hp must be positive.

        Input JSON:
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
    ).strip()


def normalized_enemy_update_int(update: dict[str, Any], key: str, minimum: int) -> int:
    value = update.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PipelineError(f"enemy update {update.get('id')} has invalid {key}: {value!r}")
    return max(minimum, int(value))


def normalized_enemy_specials(update: dict[str, Any], allowed_specials: set[int], max_count: int) -> list[int]:
    raw_specials = update.get("specials", [])
    if not isinstance(raw_specials, list):
        raw_specials = []
    specials: list[int] = []
    for raw in raw_specials:
        if isinstance(raw, bool):
            continue
        try:
            special = int(raw)
        except (TypeError, ValueError):
            continue
        if special in allowed_specials and special not in specials:
            specials.append(special)
    return specials[: max(max_count, 1)]


def apply_enemy_design_updates(
    source_enemys: dict[str, Any],
    design: dict[str, Any],
    brief: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    updates = design.get("updates", [])
    if not isinstance(updates, list) or not updates:
        raise PipelineError("enemy design agent returned no enemy updates.")

    monster_policy = brief.get("monster_policy", {}) if isinstance(brief.get("monster_policy"), dict) else {}
    allowed_specials = {
        int(item)
        for item in monster_policy.get("allowed_specials", [1, 2, 3, 15, 18])
        if not isinstance(item, bool)
    }
    if not allowed_specials:
        allowed_specials = {1, 2, 3, 15, 18}
    max_specials = int(monster_policy.get("max_specials_per_monster") or 1)
    red_potion = red_potion_value(brief)
    default_special_damage = max(1, int(round(red_potion * 0.75)))

    enemys = core_clone(source_enemys)
    applied_ids: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for update in updates:
        if not isinstance(update, dict):
            warnings.append("ignored non-object enemy update")
            continue
        enemy_id = str(update.get("id", ""))
        if not enemy_id or enemy_id not in enemys:
            warnings.append(f"ignored unknown enemy id: {enemy_id or '<empty>'}")
            continue
        if enemy_id in seen:
            warnings.append(f"ignored duplicate enemy update: {enemy_id}")
            continue
        seen.add(enemy_id)

        enemy = enemys[enemy_id]
        name = update.get("name")
        if isinstance(name, str) and name.strip():
            enemy["name"] = name.strip()
        enemy["hp"] = normalized_enemy_update_int(update, "hp", 1)
        enemy["atk"] = normalized_enemy_update_int(update, "atk", 0)
        enemy["def"] = normalized_enemy_update_int(update, "def", 0)
        enemy["money"] = normalized_enemy_update_int(update, "money", 0)
        enemy["exp"] = normalized_enemy_update_int(update, "exp", 0)
        enemy["point"] = normalized_enemy_update_int(update, "point", 0)

        specials = normalized_enemy_specials(update, allowed_specials, max_specials)
        enemy["special"] = 0 if not specials else (specials[0] if len(specials) == 1 else specials)

        for key in ("value", "zone", "repulse"):
            value = update.get(key)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    warnings.append(f"ignored invalid {key} for {enemy_id}: {value!r}")
                    continue
                enemy[key] = max(0, int(value))
        range_value = update.get("range")
        if range_value is not None:
            if isinstance(range_value, bool) or not isinstance(range_value, int):
                warnings.append(f"ignored invalid range for {enemy_id}: {range_value!r}")
            else:
                enemy["range"] = max(1, int(range_value))
        for key in ("zoneSquare", "notBomb"):
            value = update.get(key)
            if value is not None:
                enemy[key] = bool(value)

        if 15 in specials:
            enemy["zone"] = int(enemy.get("zone") or enemy.get("value") or default_special_damage)
            enemy["value"] = int(enemy.get("value") or enemy["zone"])
            enemy["range"] = int(enemy.get("range") or 1)
        if 18 in specials:
            enemy["repulse"] = int(enemy.get("repulse") or enemy.get("value") or default_special_damage)
            enemy["value"] = int(enemy.get("value") or enemy["repulse"])

        applied_ids.append(enemy_id)

    if not applied_ids:
        raise PipelineError("enemy design agent did not update any known enemy ids.")
    return enemys, applied_ids, warnings


def prepare_runtime_enemy_table(
    args: argparse.Namespace,
    brief: dict[str, Any],
    maps: dict[str, Any],
    source_enemys: dict[str, Any],
    floor_count: int,
    floor_size: int,
) -> dict[str, Any]:
    design_path = args.out_dir / "enemy_design.json"
    generated_path = args.out_dir / "enemys.generated.json"

    if args.resume_existing and generated_path.exists():
        runtime_enemys = load_json_object(generated_path.read_text(encoding="utf-8"))
        design = load_json_object(design_path.read_text(encoding="utf-8")) if design_path.exists() else {}
        applied_ids = [
            str(item)
            for item in design.get("applied_enemy_ids", design.get("designed_enemy_ids", []))
            if isinstance(item, (str, int))
        ]
        if applied_ids:
            brief["enemy_design"] = {
                "summary": design.get("summary", "Loaded existing generated enemy table."),
                "designed_enemy_ids": applied_ids,
                "warnings": design.get("warnings", []),
            }
        args.runtime_enemys = runtime_enemys
        return runtime_enemys

    if args.resume_existing and not generated_path.exists():
        print("No existing generated enemy table found; resume will keep the current project enemy stats.")
        return source_enemys

    design = agent_exec(
        args,
        build_enemy_design_prompt(args, brief, maps, source_enemys, floor_count, floor_size),
        ENEMY_DESIGN_SCHEMA,
        design_path,
    )
    runtime_enemys, applied_ids, apply_warnings = apply_enemy_design_updates(source_enemys, design, brief)
    warnings = list(design.get("warnings", [])) if isinstance(design.get("warnings"), list) else []
    warnings.extend(apply_warnings)
    design["applied_enemy_ids"] = applied_ids
    design["designed_enemy_ids"] = applied_ids
    design["warnings"] = warnings
    write_json(design_path, design)
    write_json(generated_path, runtime_enemys)
    brief["enemy_design"] = {
        "summary": design.get("summary", ""),
        "designed_enemy_ids": applied_ids,
        "warnings": warnings,
    }
    args.runtime_enemys = runtime_enemys
    print(f"已设计 {len(applied_ids)} 个怪物数据。")
    return runtime_enemys


def staged_common_payload(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_index: int,
    floor_count: int,
    used: dict[str, int],
    limits: dict[str, int | None],
    previous: list[dict[str, Any]],
    floor_policy: dict[str, Any] | None,
    floor_contract: dict[str, Any] | None,
    feedback: dict[str, Any] | None,
    current_stage_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    floor_number = floor_index + args.floor_number_offset
    return {
        "tower_brief": brief,
        "floor_index": floor_index,
        "floor_id": f"{args.floor_prefix}{floor_number}",
        "floor_size": normalize_floor_size(brief.get("floor_size")),
        "floor_count": floor_count,
        "current_floor_policy": floor_policy or {},
        "used_budget_so_far": used,
        "remaining_whole_tower_budget": remaining_budget(limits, used),
        "previous_accepted_floor_summaries": previous,
        "floor_contract": floor_contract or {},
        "layout_constraints": layout_constraints_summary(brief),
        "repair_feedback": minimal_repair_feedback(feedback),
        "current_stage_output_to_repair": current_stage_output or {},
    }


def layout_constraints_summary(brief: dict[str, Any]) -> dict[str, Any]:
    min_ratio, max_ratio = wall_ratio_range(brief)
    return {
        "wall_ratio_min": min_ratio,
        "wall_ratio_max": max_ratio,
        "high_value_pocket_threshold": high_value_pocket_threshold(brief),
        "note": "These are generation and review targets; final LLM output may need manual adjustment.",
    }


def minimal_repair_feedback(feedback: dict[str, Any] | None) -> dict[str, Any]:
    if not feedback:
        return {}
    issues = normalize_structured_issues(feedback, "integration")
    return {
        "status": feedback.get("status"),
        "summary": feedback.get("summary", ""),
        "issues": [
            {
                "owner_stage": issue["owner_stage"],
                "severity": issue["severity"],
                "coordinates": issue["coordinates"],
                "reason": issue["reason"],
                "required_change": issue["required_change"],
            }
            for issue in issues[:8]
        ],
    }


def downstream_hard_constraints_summary(
    stage: str,
    brief: dict[str, Any],
    limits: dict[str, int | None],
    used: dict[str, int],
    floor_policy: dict[str, Any] | None,
    floor_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    monster_policy = brief.get("monster_policy", {}) if isinstance(brief.get("monster_policy"), dict) else {}
    return {
        "stage_being_repaired": stage,
        "layout_constraints": layout_constraints_summary(brief),
        "resource_budget_remaining": remaining_budget(limits, used),
        "floor_contract_resource_limits": floor_contract.get("resource_limits", {}) if isinstance(floor_contract, dict) else {},
        "enemy_policy": floor_policy or {},
        "allowed_specials": monster_policy.get("allowed_specials", [1, 2, 3, 15, 18]),
        "max_specials_per_monster": monster_policy.get("max_specials_per_monster", 1),
        "enemy_count_min_per_floor": monster_policy_int(brief, "enemy_count_min_per_floor"),
        "enemy_count_max_per_floor": monster_policy_int(brief, "enemy_count_max_per_floor"),
        "no_adjacent_enemies": monster_policy_bool(brief, "no_adjacent_enemies"),
        "resource_progression": (floor_policy or {}).get("resource_progression", {}),
        "final_floor_requirements": [
            "final output must pass local floor validation",
            (
                "final output must place between "
                f"{monster_policy_int(brief, 'enemy_count_min_per_floor')} and "
                f"{monster_policy_int(brief, 'enemy_count_max_per_floor')} enemies on every floor"
            ),
            "final output must preserve downFloor and upFloor stairs",
            "write_generated_project will wire stairs and final win event after review",
        ],
    }


def build_topology_prompt(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_index: int,
    floor_count: int,
    used: dict[str, int],
    limits: dict[str, int | None],
    previous: list[dict[str, Any]],
    feedback: dict[str, Any] | None,
    floor_policy: dict[str, Any] | None = None,
    floor_contract: dict[str, Any] | None = None,
    current_stage_output: dict[str, Any] | None = None,
) -> str:
    maps, enemys = load_project_tables(args)
    tile_catalog = build_tile_catalog(maps, enemys, brief, floor_policy)
    payload = staged_common_payload(
        args, brief, floor_index, floor_count, used, limits, previous, floor_policy, floor_contract, feedback,
        current_stage_output,
    )
    payload["downstream_hard_constraints_summary"] = downstream_hard_constraints_summary(
        "topology", brief, limits, used, floor_policy, floor_contract
    )
    return textwrap.dedent(
        f"""
        Read and follow this skill file first:
        {skill_path(args.repo_root, "topology-mota-floor")}

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

        {tile_catalog}

        Input JSON:
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
    ).strip()


def build_economy_prompt(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_index: int,
    floor_count: int,
    used: dict[str, int],
    limits: dict[str, int | None],
    previous: list[dict[str, Any]],
    topology_output: dict[str, Any],
    feedback: dict[str, Any] | None,
    floor_policy: dict[str, Any] | None = None,
    floor_contract: dict[str, Any] | None = None,
    current_stage_output: dict[str, Any] | None = None,
) -> str:
    maps, enemys = load_project_tables(args)
    tile_catalog = build_tile_catalog(maps, enemys, brief, floor_policy)
    payload = staged_common_payload(
        args, brief, floor_index, floor_count, used, limits, previous, floor_policy, floor_contract, feedback,
        current_stage_output,
    )
    payload["topology_output"] = topology_output
    payload["downstream_hard_constraints_summary"] = downstream_hard_constraints_summary(
        "economy", brief, limits, used, floor_policy, floor_contract
    )
    return textwrap.dedent(
        f"""
        Read and follow this skill file first:
        {skill_path(args.repo_root, "economy-mota-floor")}

        You are stage 2 of a staged per-floor pipeline. Return only JSON matching the provided schema.
        Start from topology_output. Preserve its floor size, floor id, stairs, route structure, and most walls.
        Add doors, keys, resources, tools, and route-tax annotations within the supplied budget.
        Do not place final enemy tiles. For combat pressure, place only annotations such as
        combat_chokepoint, reward_guard, route_tax, special_candidate, and mini_boss_candidate.
        Treat floor_contract.resource_limits, when present, as exact quotas for this floor's tracked resources.
        Control the entrance free region: no naked tool and no large resource exposure before cost.
        If repair_feedback is present, repair current_stage_output_to_repair only for the listed economy issue
        and keep the topology stable.

        {tile_catalog}

        Input JSON:
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
    ).strip()


def build_monster_special_prompt(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_index: int,
    floor_count: int,
    used: dict[str, int],
    limits: dict[str, int | None],
    previous: list[dict[str, Any]],
    economy_output: dict[str, Any],
    feedback: dict[str, Any] | None,
    floor_policy: dict[str, Any] | None = None,
    floor_contract: dict[str, Any] | None = None,
    current_stage_output: dict[str, Any] | None = None,
) -> str:
    maps, enemys = load_project_tables(args)
    tile_catalog = build_tile_catalog(maps, enemys, brief, floor_policy)
    payload = staged_common_payload(
        args, brief, floor_index, floor_count, used, limits, previous, floor_policy, floor_contract, feedback,
        current_stage_output,
    )
    payload["economy_output"] = economy_output
    payload["downstream_hard_constraints_summary"] = downstream_hard_constraints_summary(
        "monster", brief, limits, used, floor_policy, floor_contract
    )
    return textwrap.dedent(
        f"""
        Read and follow this skill file first:
        {skill_path(args.repo_root, "monster-special-mota-floor")}

        You are stage 3 of a staged per-floor pipeline. Return only JSON matching the provided schema.
        Start from economy_output. Preserve topology and economy except for necessary small coordinate
        adjustments to avoid adjacency, blocked routes, or invalid pressure.
        Replace combat and special annotations with concrete enemy tile codes selected only from
        current_floor_policy.allowed_enemy_ids and current_floor_policy.allowed_enemy_codes.
        Place between {monster_policy_int(brief, "enemy_count_min_per_floor")} and
        {monster_policy_int(brief, "enemy_count_max_per_floor")} total enemy tiles on this floor. If the economy
        annotations contain fewer combat slots, add extra non-adjacent route-tax, reward-guard,
        branch-blocking, or pressure enemies on valid ground cells while preserving economy quotas.
        Make same-floor monster roles meaningfully different. Zone and repulse monsters must affect a
        real route, reward entrance, shortcut, or key junction. Enforce the special whitelist,
        max_specials_per_monster, and no orthogonally adjacent enemies.
        If repair_feedback is present, repair current_stage_output_to_repair only for the listed
        monster/special issue and do not rebuild economy.

        {tile_catalog}

        Input JSON:
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
    ).strip()


STAGED_REVIEWER_SCOPES = {
    "topology": """
Focus only on structural topology.

Required checks:
- floor id, dimensions, schema shape, and stairs are correct.
- Only tile code 0, tile code 1, downFloor, and upFloor appear in floor.map.
- 0 is the only ground and 1 is the only wall.
- The entrance and exit are connected through meaningful space.
- The structure suggests at least 3 candidate route families and around 8-12 branch, pocket, shortcut, or gated-access opportunities.
- For 13x13, wall ratio should stay within input.layout_constraints.wall_ratio_min and
  input.layout_constraints.wall_ratio_max when possible.
- Avoid thick fill walls, purely decorative branches, fake branches, and dead space that cannot support economy.
- Avoid clean repeated wall templates, symmetric straight-bar mazes, and near-identical adjacent floor wall masks.
- Broken walls only count as precise when they can change access cost, reward protection, tool value, special pressure, or route choice.

Return structured issues with owner_stage="topology".
""",
    "economy": """
Focus only on doors, keys, resources, tools, route-tax annotations, and budget.

Required checks:
- No final enemy tiles are placed yet.
- floor_contract.resource_limits, when present, are treated as exact tracked-resource quotas for this floor.
- Whole-tower remaining budget is not exceeded.
- Entrance free region contains at most a tiny starter reward and no naked tool.
- Resource clusters are protected by door, route length, wall/tool pressure, special candidate, or combat slot.
- Door/key ordering is plausible and avoids deadlocks.
- Blue-door and tool routes receive stronger compensation than yellow-door baseline routes.
- Combat slots and special candidates are positioned where the next stage can create real pressure.
- A high-value pocket is invalid if its entrance has no door, combat slot, special candidate, tool requirement, or route commitment.
- Economy may make small wall adjustments when needed to make broken-wall pockets, tool routes, or shortcuts actually costed.

Return structured issues with owner_stage="economy".
""",
    "monster": """
Focus only on concrete monster and special ability placement.

Required checks:
- Every enemy id/code is allowed by current_floor_policy.
- Combat annotations have been replaced by concrete enemy tiles or intentionally removed with compensation.
- Same-floor monster roles differ across route cost, reward guards, chokepoints, and optional pressure.
- Zone and repulse monsters affect a real route, reward entrance, shortcut, or key junction.
- Special abilities obey the whitelist and max_specials_per_monster.
- No enemy tiles are orthogonally adjacent.
- Topology and economy are not rebuilt except for small necessary coordinate fixes.
- Prefer pocket entrances, offset gaps, route merges, tool-route entries, and shortcut joins over decorative corridor filler.

Return structured issues with owner_stage="monster".
""",
    "integration": """
Focus on whether the three staged outputs compose into one valid floor.

Required checks:
- Final floor still satisfies topology legality, dimensions, stairs, floor id, and connectivity.
- Economy changes did not destroy candidate route structure.
- Monster placement did not break door/key/resource ordering or create illegal adjacency.
- Final tracked-resource budget is correct.
- Final floor has real battle pressure, key/resource pressure, protected rewards, and perceivable special pressure.
- Broken walls serve economy: fragmented pockets or gaps must affect access cost, reward protection, tool value, special pressure, or route choice.
- Missing final win events are not a failure; write_generated_project adds the final win event after review.

If an issue belongs to a specific earlier stage, set owner_stage to that earliest stage. Use owner_stage="integration"
only when the problem is truly caused by cross-stage composition, and describe which earliest stage should change.
""",
}


def staged_review_prompt(
    args: argparse.Namespace,
    stage: str,
    brief: dict[str, Any],
    stage_output: dict[str, Any],
    used: dict[str, int],
    limits: dict[str, int | None],
    previous: list[dict[str, Any]],
    metrics: dict[str, Any] | None,
    delta: dict[str, int],
    floor_policy: dict[str, Any] | None = None,
    floor_contract: dict[str, Any] | None = None,
    topology_output: dict[str, Any] | None = None,
    economy_output: dict[str, Any] | None = None,
) -> str:
    maps, enemys = load_project_tables(args)
    tile_catalog = build_tile_catalog(maps, enemys, brief, floor_policy)
    payload = {
        "tower_brief": brief,
        "stage": stage,
        "stage_output": stage_output,
        "topology_output": topology_output or {},
        "economy_output": economy_output or {},
        "floor_size": normalize_floor_size(brief.get("floor_size")),
        "current_floor_policy": floor_policy or {},
        "used_budget_so_far": used,
        "remaining_whole_tower_budget": remaining_budget(limits, used),
        "previous_accepted_floor_summaries": previous,
        "static_metrics": metrics or {},
        "budget_delta_from_map": delta,
        "floor_contract": floor_contract or {},
        "layout_constraints": layout_constraints_summary(brief),
    }
    return textwrap.dedent(
        f"""
        Read and follow this skill file first:
        {skill_path(args.repo_root, "review-mota-floor")}

        You are the {stage}-reviewer in a staged per-floor pipeline. Return only JSON matching
        the provided structured review schema. Every issue must be an object with:
        owner_stage, severity, coordinates, reason, required_change.
        Use severity="fail" only when the issue must trigger repair. Use severity="warn" for non-blocking notes.
        Do not emit string issues.

        Reviewer scope:
        {STAGED_REVIEWER_SCOPES[stage]}

        {tile_catalog}

        Input JSON:
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
    ).strip()


def merge_structured_stage_reviews(
    owner_stage: str,
    local_review: dict[str, Any],
    llm_review: dict[str, Any] | None,
    delta: dict[str, int],
) -> dict[str, Any]:
    issues = normalize_structured_issues(local_review, owner_stage)
    summary_parts = [str(local_review.get("summary", ""))]
    if llm_review is not None:
        issues.extend(normalize_structured_issues(llm_review, owner_stage))
        summary_parts.append(str(llm_review.get("summary", "")))
    status = "fail" if any(issue.get("severity") == "fail" for issue in issues) else "pass"
    return {
        "status": status,
        "issues": issues,
        "required_changes": [issue["required_change"] for issue in issues],
        "budget_delta": delta,
        "summary": " | ".join(part for part in summary_parts if part)[:1600],
    }


def run_staged_review(
    args: argparse.Namespace,
    prefix: Path,
    stage: str,
    brief: dict[str, Any],
    stage_output: dict[str, Any],
    used: dict[str, int],
    limits: dict[str, int | None],
    previous: list[dict[str, Any]],
    previous_floor_outputs: list[dict[str, Any]],
    floor_size: int,
    maps: dict[str, Any],
    enemys: dict[str, Any],
    floor_policy: dict[str, Any] | None,
    floor_contract: dict[str, Any] | None,
    enforce_resource_progression: bool,
    topology_output: dict[str, Any] | None = None,
    economy_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected_floor_id = f"{args.floor_prefix}{int(stage_output.get('floor_index', 0)) + args.floor_number_offset}"
    if stage_output.get("floor_index") != prefix_stage_floor_index(prefix):
        expected_floor_id = f"{args.floor_prefix}{prefix_stage_floor_index(prefix) + args.floor_number_offset}"

    if stage == "topology":
        issues = topology_stage_review_issues(
            stage_output,
            expected_floor_id,
            floor_size,
            maps,
            previous_floor_outputs,
            args.max_wall_similarity,
            args.wall_ratio_min,
            args.wall_ratio_max,
        )
        delta = empty_budget()
        metrics = floor_static_metrics(stage_output, maps, enemys, brief)
    elif stage == "economy":
        issues, delta = economy_stage_review_issues(
            stage_output,
            expected_floor_id,
            floor_size,
            brief,
            maps,
            limits,
            used,
            previous_floor_outputs,
            floor_contract,
            enforce_resource_progression,
        )
        metrics = floor_static_metrics(stage_output, maps, enemys, brief)
    elif stage == "monster":
        issues, delta, metrics = monster_stage_review_issues(
            stage_output,
            expected_floor_id,
            floor_size,
            brief,
            maps,
            enemys,
            limits,
            used,
            previous_floor_outputs,
            floor_policy,
            enforce_resource_progression,
            args.max_wall_similarity,
        )
    elif stage == "integration":
        issues, delta, metrics = integration_stage_review_issues(
            stage_output,
            expected_floor_id,
            floor_size,
            brief,
            maps,
            enemys,
            limits,
            used,
            previous_floor_outputs,
            floor_policy,
            enforce_resource_progression,
            args.max_wall_similarity,
        )
    else:
        raise PipelineError(f"Unknown staged review stage: {stage}")

    write_json(prefix.with_suffix(f".{stage}.metrics.json"), metrics)
    local_review = structured_review(
        stage,
        issues,
        delta,
        f"Local {stage} review {'failed' if any(issue['severity'] == 'fail' for issue in issues) else 'passed'}.",
    )
    write_json(prefix.with_suffix(f".review.{stage}.local.json"), local_review)
    if local_review["status"] != "pass":
        return local_review

    llm_review = agent_exec(
        args,
        staged_review_prompt(
            args,
            stage,
            brief,
            stage_output,
            used,
            limits,
            previous,
            metrics,
            delta,
            floor_policy,
            floor_contract,
            topology_output,
            economy_output,
        ),
        STRUCTURED_REVIEW_SCHEMA,
        prefix.with_suffix(f".review.{stage}.json"),
    )
    review = merge_structured_stage_reviews(stage, local_review, llm_review, delta)
    write_json(prefix.with_suffix(f".review.{stage}.merged.json"), review)
    return review


def prefix_stage_floor_index(prefix: Path) -> int:
    match = re.search(r"MT(\d+)", prefix.name)
    if not match:
        return 0
    return int(match.group(1))


def clean_output_dir(repo_root: Path, out_dir: Path) -> None:
    out_dir = out_dir.resolve()
    build_dir = (repo_root / "build").resolve()
    if not out_dir.exists():
        return
    if out_dir != build_dir and build_dir not in out_dir.parents:
        raise PipelineError(f"--clean only removes directories under {build_dir}: {out_dir}")
    shutil.rmtree(out_dir)


def find_first_tile_coord(floor: dict[str, Any], maps: dict[str, Any], tile_id: str) -> tuple[int, int] | None:
    try:
        _, _, matrix = floor_dimensions(floor)
    except PipelineError:
        return None
    found = find_tile(matrix, maps, tile_id)
    return found[0] if found else None


def write_generated_project(
    args: argparse.Namespace,
    brief: dict[str, Any],
    accepted_floors: list[dict[str, Any]],
) -> Path:
    source_project = project_dir(args)
    output_project = args.out_dir / "project"
    if output_project.exists():
        shutil.rmtree(output_project)
    shutil.copytree(source_project, output_project)

    runtime_enemys = getattr(args, "runtime_enemys", None)
    if isinstance(runtime_enemys, dict):
        enemy_assignment, _ = load_js_object(source_project / "enemys.js")
        write_js_object(output_project / "enemys.js", enemy_assignment, runtime_enemys)

    floors_dir = output_project / "floors"
    floors_dir.mkdir(parents=True, exist_ok=True)
    for path in floors_dir.glob("*.js"):
        path.unlink()

    floor_ids = [floor_output["floor_id"] for floor_output in accepted_floors]
    maps, _ = load_project_tables(args)
    for index, floor_output in enumerate(accepted_floors):
        floor_id = floor_output["floor_id"]
        floor = core_clone(floor_output["floor"])
        change_floor = floor.setdefault("changeFloor", {})
        events = floor.setdefault("events", {})
        for x, y in find_tile(floor_dimensions(floor)[2], maps, "downFloor"):
            if index > 0:
                change_floor[f"{x},{y}"] = {"floorId": ":before", "stair": "upFloor"}
        for x, y in find_tile(floor_dimensions(floor)[2], maps, "upFloor"):
            key = f"{x},{y}"
            if index < len(accepted_floors) - 1:
                change_floor[key] = {"floorId": ":next", "stair": "downFloor"}
            else:
                if not events.get(key):
                    events[key] = [{"type": "win", "reason": "通关"}]
        write_js_object(floors_dir / f"{floor_id}.js", f"main.floors.{floor_id}", floor)

    assignment, data = load_js_object(output_project / "data.js")
    data.setdefault("main", {})["floorIds"] = floor_ids
    first_data = data.setdefault("firstData", {})
    if floor_ids:
        first_data["floorId"] = floor_ids[0]
        entrance = find_first_tile_coord(accepted_floors[0]["floor"], maps, "downFloor")
        if entrance:
            hero = first_data.setdefault("hero", {})
            hero["loc"] = {"direction": "up", "x": entrance[0], "y": entrance[1]}
    if "global_settings" in brief:
        global_settings = brief.get("global_settings", {})
        initial = global_settings.get("initial_hero", {})
        hero = first_data.setdefault("hero", {})
        for key in ("hp", "atk", "def", "money"):
            value = initial.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                hero[key] = int(value)
        hero_items = hero.setdefault("items", {})
        tools = hero_items.setdefault("tools", {})
        key_aliases = {
            "yellowKey": ("yellowKey", "yellow_keys", "yellow_keys_start", "yellow"),
            "blueKey": ("blueKey", "blue_keys", "blue_keys_start", "blue"),
            "redKey": ("redKey", "red_keys", "red_keys_start", "red"),
        }
        initial_keys = initial.get("keys", {}) if isinstance(initial.get("keys"), dict) else {}
        for item_id, aliases in key_aliases.items():
            value = next((initial.get(alias) for alias in aliases if isinstance(initial.get(alias), (int, float))), None)
            if value is None:
                value = next((initial_keys.get(alias) for alias in aliases if isinstance(initial_keys.get(alias), (int, float))), None)
            if value is not None and not isinstance(value, bool):
                tools[item_id] = int(value)
        initial_tools = initial.get("tools", {}) if isinstance(initial.get("tools"), dict) else {}
        tool_aliases = {
            "pickaxe": ("pickaxe", "pickaxes", "pickaxe_start"),
            "bomb": ("bomb", "bombs", "bomb_start"),
            "centerFly": ("centerFly", "center_fly", "centerFly_start", "center_fly_start"),
            "jumpShoes": ("jumpShoes", "jump_shoes", "jumpShoes_start", "jump_shoes_start"),
        }
        for item_id, aliases in tool_aliases.items():
            value = next((initial.get(alias) for alias in aliases if isinstance(initial.get(alias), (int, float))), None)
            if value is None:
                value = next((initial_tools.get(alias) for alias in aliases if isinstance(initial_tools.get(alias), (int, float))), None)
            if value is not None and not isinstance(value, bool):
                tools[item_id] = int(value)
        values = data.setdefault("values", {})
        for section_name, aliases in {
            "gems": {"redGem": ("redGem", "red"), "blueGem": ("blueGem", "blue"), "greenGem": ("greenGem", "green")},
            "potions": {
                "redPotion": ("redPotion", "red"),
                "bluePotion": ("bluePotion", "blue"),
                "yellowPotion": ("yellowPotion", "yellow"),
                "greenPotion": ("greenPotion", "green"),
            },
        }.items():
            section = global_settings.get(section_name, {})
            if not isinstance(section, dict):
                continue
            for value_key, value_aliases in aliases.items():
                value = next((section.get(alias) for alias in value_aliases if isinstance(section.get(alias), (int, float))), None)
                if value is not None and not isinstance(value, bool):
                    values[value_key] = int(value)
    write_js_object(output_project / "data.js", assignment, data)
    return output_project


def final_tower_validation_issues(
    args: argparse.Namespace,
    brief: dict[str, Any],
    accepted_floors: list[dict[str, Any]],
    floor_count: int,
    floor_size: int,
    maps: dict[str, Any],
    enemys: dict[str, Any],
    floor_enemy_policies: list[dict[str, Any]],
    limits: dict[str, int | None],
    used: dict[str, int],
    output_project: Path,
    exact_budget: bool,
) -> list[str]:
    issues: list[str] = []
    if len(accepted_floors) != floor_count:
        issues.append(f"accepted floor count {len(accepted_floors)} != expected {floor_count}.")

    recounted = empty_budget()
    previous_floors: list[dict[str, Any]] = []
    for floor_index, floor_output in enumerate(accepted_floors):
        expected_floor_id = f"{args.floor_prefix}{floor_index + args.floor_number_offset}"
        floor_policy = build_runtime_floor_policy(brief, floor_enemy_policies, floor_index, previous_floors, maps)
        local_issues, delta = local_floor_review(
            floor_output,
            expected_floor_id,
            floor_size,
            brief,
            maps,
            enemys,
            floor_policy,
        )
        metrics = floor_static_metrics(floor_output, maps, enemys, brief)
        local_issues.extend(high_value_pocket_metric_issues(metrics))
        local_issues.extend(wall_mask_similarity_issues(previous_floors, floor_output, maps, args.max_wall_similarity))
        local_issues.extend(floor_resource_progression_issues(brief, previous_floors, floor_output, maps))
        if local_issues:
            issues.extend(f"{expected_floor_id}: {issue}" for issue in local_issues[:8])
        recounted = add_budget(recounted, delta)
        previous_floors.append(floor_output)

    if recounted != used:
        issues.append(f"budget ledger mismatch: recorded={used}, recounted={recounted}.")
    for issue in budget_issues(empty_budget(), limits, recounted):
        issues.append(issue)
    if exact_budget:
        for key, limit in limits.items():
            if limit is not None and recounted.get(key, 0) != limit:
                issues.append(f"{key} exact whole-tower total mismatch: actual {recounted.get(key, 0)} != required {limit}.")

    try:
        _, data = load_js_object(output_project / "data.js")
        floor_ids = data.get("main", {}).get("floorIds", [])
        expected_ids = [
            f"{args.floor_prefix}{floor_index + args.floor_number_offset}"
            for floor_index in range(floor_count)
        ]
        if floor_ids != expected_ids:
            issues.append(f"project data floorIds mismatch: actual={floor_ids}, expected={expected_ids}.")
    except (OSError, json.JSONDecodeError, PipelineError) as exc:
        issues.append(f"could not validate generated data.js floorIds: {exc}")

    if accepted_floors:
        last_floor_id = accepted_floors[-1].get("floor_id")
        try:
            _, last_floor = load_js_object(output_project / "floors" / f"{last_floor_id}.js")
            events = last_floor.get("events", {})
            has_win = any(
                isinstance(event_list, list)
                and any(isinstance(event, dict) and event.get("type") == "win" for event in event_list)
                for event_list in events.values()
            )
            if not has_win:
                issues.append(f"final floor {last_floor_id} is missing a win event after project writing.")
        except (OSError, json.JSONDecodeError, PipelineError) as exc:
            issues.append(f"could not validate final floor win event: {exc}")

    return issues


def core_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def playtest_script_path(args: argparse.Namespace) -> Path:
    return args.repo_root / "skills" / "playtest-mota-game" / "scripts" / "playtest_mota_game.py"


def run_playtest_game(
    args: argparse.Namespace,
    output_project: Path,
    floor_index: int,
) -> dict[str, Any]:
    script = playtest_script_path(args)
    report_path = args.out_dir / "playtests" / f"MT{floor_index}.playtest.json"
    if not script.exists():
        report = {
            "status": "skipped",
            "summary": f"playtest skill script is missing: {script}",
            "issues": [f"missing {script}"],
        }
        write_json(report_path, report)
        return report

    cmd = [
        sys.executable,
        str(script),
        "--mota-root",
        str(args.repo_root / "mota-js"),
        "--project-dir",
        str(output_project),
        "--out",
        str(report_path),
        "--max-steps",
        str(args.playtest_max_steps),
        "--routes",
        str(args.playtest_routes),
        "--timeout",
        str(args.playtest_timeout),
    ]
    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=args.playtest_timeout + min(args.playtest_timeout, 90) + 15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        report = {
            "status": "error",
            "summary": "playtest command could not complete.",
            "issues": [str(exc)],
            "command": cmd,
        }
        write_json(report_path, report)
        return report

    if report_path.exists():
        try:
            report = load_json_object(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {
                "status": "error",
                "summary": "playtest report was not valid JSON.",
                "issues": [report_path.read_text(encoding="utf-8")[:2000]],
            }
    else:
        report = {
            "status": "error",
            "summary": "playtest command did not write a report.",
            "issues": [result.stderr[-2000:] or result.stdout[-2000:] or f"exit {result.returncode}"],
            "command": cmd,
        }
        write_json(report_path, report)
    if result.returncode != 0 and report.get("status") not in {"error", "skipped"}:
        report["status"] = "error"
        report.setdefault("issues", []).append(result.stderr[-2000:] or f"exit {result.returncode}")
        write_json(report_path, report)
    return report


def apply_brief_required_events(brief: dict[str, Any], floor_output: dict[str, Any]) -> None:
    """Fill deterministic coordinate events that the brief requires but floor generation may omit."""
    floor = floor_output.get("floor")
    if not isinstance(floor, dict):
        return

    floor_id = str(floor_output.get("floor_id") or floor.get("floorId") or "")
    shop = brief.get("global_settings", {}).get("shop", {})
    if not isinstance(shop, dict) or shop.get("enabled") is not True:
        return

    shop_id = str(shop.get("id") or "shop1")
    brief_text = json.dumps(brief, ensure_ascii=False)
    if floor_id != "MT0" or shop_id != "shop1" or "(1,9)" not in brief_text:
        return

    events = floor.setdefault("events", {})
    if not isinstance(events, dict):
        events = {}
        floor["events"] = events
    key = "1,9"
    open_shop = {"type": "openShop", "id": shop_id, "open": True}
    existing = events.get(key)
    if not isinstance(existing, list):
        events[key] = [open_shop]
        return
    if not any(isinstance(item, dict) and item.get("type") == "openShop" and item.get("id") == shop_id for item in existing):
        existing.insert(0, open_shop)


def is_resumable_review(review: dict[str, Any]) -> bool:
    return review.get("status") == "pass"


def is_forced_accept_review(review: dict[str, Any] | None) -> bool:
    return bool(isinstance(review, dict) and review.get("forced_accept") is True)


def forced_accept_review(
    floor_index: int,
    attempt: int,
    stage: str,
    delta: dict[str, int] | None = None,
    skipped_issues: list[str] | None = None,
) -> dict[str, Any]:
    issues = [
        structured_issue(
            "integration" if stage == "integration" else stage,
            "warn",
            (
                f"MT{floor_index} reached max_attempts on attempt {attempt}; "
                f"{stage} review was skipped and the latest generated output was accepted."
            ),
            "Manual review and adjustment are recommended before publishing this tower.",
        )
    ]
    for issue in (skipped_issues or [])[:8]:
        issues.append(
            structured_issue(
                "integration",
                "warn",
                issue,
                "Manual review and adjustment are recommended.",
            )
        )
    return {
        "status": "pass",
        "issues": issues,
        "required_changes": [],
        "budget_delta": normalize_delta(delta),
        "summary": (
            f"Forced accept: MT{floor_index} used the final attempt output without {stage} review. "
            "Generated artifacts are saved, but quality is not guaranteed."
        ),
        "forced_accept": True,
        "forced_stage": stage,
        "attempt": attempt,
    }


def try_resume_existing_floors(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_count: int,
    floor_size: int,
    maps: dict[str, Any],
    enemys: dict[str, Any],
    limits: dict[str, int | None],
) -> tuple[int, dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    used = {key: 0 for key in TRACKED_RESOURCES}
    accepted_summaries: list[dict[str, Any]] = []
    accepted_floors: list[dict[str, Any]] = []

    for floor_index in range(floor_count):
        floor_id = f"{args.floor_prefix}{floor_index + args.floor_number_offset}"
        floor_path = args.out_dir / "floors" / f"MT{floor_index}.floor.json"
        floor_review_path = args.out_dir / "floors" / f"MT{floor_index}.review.json"
        accepted_review_path = args.out_dir / "reviews" / f"MT{floor_index}.review.json"
        review_path = floor_review_path if floor_review_path.exists() else accepted_review_path
        if not floor_path.exists() or not review_path.exists():
            break

        floor_output = load_json_object(floor_path.read_text(encoding="utf-8"))
        review = load_json_object(review_path.read_text(encoding="utf-8"))
        local_issues, delta = local_floor_review(floor_output, floor_id, floor_size, brief, maps, enemys)
        metrics = floor_static_metrics(floor_output, maps, enemys, brief)
        local_issues.extend(high_value_pocket_metric_issues(metrics))
        local_issues.extend(wall_mask_similarity_issues(accepted_floors, floor_output, maps, args.max_wall_similarity))
        local_issues.extend(floor_resource_progression_issues(brief, accepted_floors, floor_output, maps))
        delta = normalize_delta(review.get("budget_delta")) or delta
        local_issues.extend(budget_issues(delta, limits, used))
        if local_issues or not is_resumable_review(review):
            print(f"Resume stopped before {floor_id}.")
            for issue in local_issues[:5]:
                print(f"- {issue}")
            if not is_resumable_review(review):
                print(f"- existing review is not resumable: {review.get('summary', '')}")
            break

        if review.get("status") != "pass":
            review["status"] = "pass"
            review["summary"] = (
                str(review.get("summary", ""))
                + " | Resumed with one non-blocking gem-route balance warning."
            )[:1600]
            write_json(review_path, review)
        write_json(accepted_review_path, review)

        used = add_budget(used, delta)
        accepted_floors.append(floor_output)
        accepted_summaries.append(
            {
                "floor_id": floor_output.get("floor_id", floor_id),
                "floor_size": floor_size,
                "summary": floor_output.get("summary", ""),
                "budget_delta": delta,
                "resumed": True,
            }
        )
        print(f"Resumed {floor_id} from existing output.")

    return len(accepted_floors), used, accepted_summaries, accepted_floors


def floor_limits_from_contract(contract: dict[str, Any]) -> dict[str, int | None]:
    raw_limits = contract.get("resource_limits", {})
    if not isinstance(raw_limits, dict):
        return {key: None for key in TRACKED_RESOURCES}
    limits: dict[str, int | None] = {}
    for key in TRACKED_RESOURCES:
        value = raw_limits.get(key)
        if value is None:
            limits[key] = None
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            limits[key] = 0
        else:
            limits[key] = max(int(value), 0)
    return limits


def build_runtime_floor_policy(
    brief: dict[str, Any],
    floor_enemy_policies: list[dict[str, Any]],
    floor_index: int,
    accepted_floors: list[dict[str, Any]],
    maps: dict[str, Any],
) -> dict[str, Any]:
    floor_policy = core_clone(floor_enemy_policies[floor_index])
    floor_policy.update(
        {
            "no_adjacent_enemies": monster_policy_bool(brief, "no_adjacent_enemies"),
            "enemy_adjacency": "orthogonal",
            "special_damage_red_potion_range": [
                monster_policy_number(brief, "special_damage_red_potion_min"),
                monster_policy_number(brief, "special_damage_red_potion_max"),
            ],
            "resource_progression": {
                "gem_floor_delta_min": resource_policy_number(brief, "gem_floor_delta_min"),
                "gem_floor_delta_max": resource_policy_number(brief, "gem_floor_delta_max"),
                "potion_floor_delta_min": resource_policy_number(brief, "potion_floor_delta_min"),
                "potion_floor_delta_max": resource_policy_number(brief, "potion_floor_delta_max"),
                "potion_compare_mode": str(resource_policy_value(brief, "potion_compare_mode") or "red_potion_equiv"),
            },
        }
    )
    if accepted_floors:
        previous_resource_profile = floor_resource_progression_profile(accepted_floors[-1], maps, brief)
        resource_progression = floor_policy["resource_progression"]
        resource_progression["previous_floor"] = previous_resource_profile
        resource_progression["allowed_current"] = {
            "gem_count": [
                previous_resource_profile["gem_count"] + resource_progression["gem_floor_delta_min"],
                previous_resource_profile["gem_count"] + resource_progression["gem_floor_delta_max"],
            ],
            "potion_red_equiv": [
                previous_resource_profile["potion_red_equiv"] + resource_progression["potion_floor_delta_min"],
                previous_resource_profile["potion_red_equiv"] + resource_progression["potion_floor_delta_max"],
            ],
        }
    return floor_policy


def generate_floor_staged_with_retries(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_index: int,
    floor_count: int,
    floor_size: int,
    maps: dict[str, Any],
    enemys: dict[str, Any],
    used: dict[str, int],
    limits: dict[str, int | None],
    accepted_summaries: list[dict[str, Any]],
    accepted_floors: list[dict[str, Any]],
    floor_policy: dict[str, Any],
    floor_contract: dict[str, Any] | None = None,
    enforce_resource_progression: bool = True,
) -> dict[str, Any]:
    topology_output: dict[str, Any] | None = None
    economy_output: dict[str, Any] | None = None
    monster_output: dict[str, Any] | None = None
    feedback: dict[str, Any] | None = None
    repair_stage = "topology"
    repair_stage_outputs: dict[str, dict[str, Any]] = {}

    for attempt in range(1, args.max_attempts + 1):
        final_attempt = attempt == args.max_attempts
        active_repair_stage = repair_stage
        stage_start = STAGE_ORDER[active_repair_stage]
        if stage_start <= STAGE_ORDER["topology"]:
            topology_output = None
            economy_output = None
            monster_output = None
        elif stage_start <= STAGE_ORDER["economy"]:
            economy_output = None
            monster_output = None
        else:
            monster_output = None

        if stage_start <= STAGE_ORDER["topology"]:
            stage_prefix = args.out_dir / "floors" / f"MT{floor_index}_attempt{attempt}_topology"
            topology_output = agent_exec(
                args,
                build_topology_prompt(
                    args,
                    brief,
                    floor_index,
                    floor_count,
                    used,
                    limits,
                    accepted_summaries,
                    feedback if active_repair_stage == "topology" else None,
                    floor_policy,
                    floor_contract,
                    repair_stage_outputs.get("topology") if active_repair_stage == "topology" else None,
                ),
                STAGED_FLOOR_SCHEMA,
                stage_prefix.with_suffix(".floor.json"),
            )
            write_json(stage_prefix.with_suffix(".floor.json"), topology_output)
            if final_attempt:
                topology_review = forced_accept_review(floor_index, attempt, "topology")
            else:
                topology_review = run_staged_review(
                    args,
                    stage_prefix,
                    "topology",
                    brief,
                    topology_output,
                    used,
                    limits,
                    accepted_summaries,
                    accepted_floors,
                    floor_size,
                    maps,
                    enemys,
                    floor_policy,
                    floor_contract,
                    False,
                )
            write_json(stage_prefix.with_suffix(".review.json"), topology_review)
            if not final_attempt and topology_review.get("status") != "pass":
                feedback = topology_review
                repair_stage_outputs["topology"] = topology_output
                repair_stage = earliest_repair_stage(topology_review, "topology")
                print(review_retry_message(floor_index, "topology", attempt, topology_review.get("summary", "")))
                continue

        if topology_output is None:
            raise PipelineError(f"MT{floor_index} staged pipeline missing topology output.")

        if stage_start <= STAGE_ORDER["economy"]:
            stage_prefix = args.out_dir / "floors" / f"MT{floor_index}_attempt{attempt}_economy"
            economy_output = agent_exec(
                args,
                build_economy_prompt(
                    args,
                    brief,
                    floor_index,
                    floor_count,
                    used,
                    limits,
                    accepted_summaries,
                    topology_output,
                    feedback if active_repair_stage == "economy" else None,
                    floor_policy,
                    floor_contract,
                    repair_stage_outputs.get("economy") if active_repair_stage == "economy" else None,
                ),
                STAGED_FLOOR_SCHEMA,
                stage_prefix.with_suffix(".floor.json"),
            )
            write_json(stage_prefix.with_suffix(".floor.json"), economy_output)
            if final_attempt:
                economy_review = forced_accept_review(floor_index, attempt, "economy")
            else:
                economy_review = run_staged_review(
                    args,
                    stage_prefix,
                    "economy",
                    brief,
                    economy_output,
                    used,
                    limits,
                    accepted_summaries,
                    accepted_floors,
                    floor_size,
                    maps,
                    enemys,
                    floor_policy,
                    floor_contract,
                    enforce_resource_progression,
                    topology_output=topology_output,
                )
            write_json(stage_prefix.with_suffix(".review.json"), economy_review)
            if not final_attempt and economy_review.get("status") != "pass":
                feedback = economy_review
                repair_stage_outputs["economy"] = economy_output
                repair_stage = earliest_repair_stage(economy_review, "economy")
                print(review_retry_message(floor_index, "economy", attempt, economy_review.get("summary", "")))
                continue

        if economy_output is None:
            raise PipelineError(f"MT{floor_index} staged pipeline missing economy output.")

        if stage_start <= STAGE_ORDER["monster"]:
            stage_prefix = args.out_dir / "floors" / f"MT{floor_index}_attempt{attempt}_monster"
            monster_output = agent_exec(
                args,
                build_monster_special_prompt(
                    args,
                    brief,
                    floor_index,
                    floor_count,
                    used,
                    limits,
                    accepted_summaries,
                    economy_output,
                    feedback if active_repair_stage == "monster" else None,
                    floor_policy,
                    floor_contract,
                    repair_stage_outputs.get("monster") if active_repair_stage == "monster" else None,
                ),
                STAGED_FLOOR_SCHEMA,
                stage_prefix.with_suffix(".floor.json"),
            )
            apply_brief_required_events(brief, monster_output)
            write_json(stage_prefix.with_suffix(".floor.json"), monster_output)
            if final_attempt:
                monster_review = forced_accept_review(floor_index, attempt, "monster")
            else:
                monster_review = run_staged_review(
                    args,
                    stage_prefix,
                    "monster",
                    brief,
                    monster_output,
                    used,
                    limits,
                    accepted_summaries,
                    accepted_floors,
                    floor_size,
                    maps,
                    enemys,
                    floor_policy,
                    floor_contract,
                    enforce_resource_progression,
                    topology_output=topology_output,
                    economy_output=economy_output,
                )
            write_json(stage_prefix.with_suffix(".review.json"), monster_review)
            if not final_attempt and monster_review.get("status") != "pass":
                feedback = monster_review
                repair_stage_outputs["monster"] = monster_output
                repair_stage = earliest_repair_stage(monster_review, "monster")
                print(review_retry_message(floor_index, "monster", attempt, monster_review.get("summary", "")))
                continue

        if monster_output is None:
            raise PipelineError(f"MT{floor_index} staged pipeline missing monster output.")

        integration_prefix = args.out_dir / "floors" / f"MT{floor_index}_attempt{attempt}_integration"
        if final_attempt:
            expected_floor_id = f"{args.floor_prefix}{floor_index + args.floor_number_offset}"
            try:
                forced_issues, forced_delta = local_floor_review(
                    monster_output,
                    expected_floor_id,
                    floor_size,
                    brief,
                    maps,
                    enemys,
                    floor_policy,
                )
            except PipelineError as exc:
                forced_issues = [str(exc)]
                forced_delta = normalize_delta(None)
            integration_review = forced_accept_review(
                floor_index,
                attempt,
                "integration",
                forced_delta,
                forced_issues,
            )
        else:
            integration_review = run_staged_review(
                args,
                integration_prefix,
                "integration",
                brief,
                monster_output,
                used,
                limits,
                accepted_summaries,
                accepted_floors,
                floor_size,
                maps,
                enemys,
                floor_policy,
                floor_contract,
                enforce_resource_progression,
                topology_output=topology_output,
                economy_output=economy_output,
            )
        write_json(integration_prefix.with_suffix(".review.json"), integration_review)
        if integration_review.get("status") == "pass":
            write_json(args.out_dir / "floors" / f"MT{floor_index}.staged.topology.json", topology_output)
            write_json(args.out_dir / "floors" / f"MT{floor_index}.staged.economy.json", economy_output)
            write_json(args.out_dir / "floors" / f"MT{floor_index}.staged.monster.json", monster_output)
            if is_forced_accept_review(integration_review):
                print(f"{floor_label(floor_index)}已保存，但质量需要生成结束后手动看一下。")
            return {
                "floor_index": floor_index,
                "floor_output": monster_output,
                "review": integration_review,
                "budget_delta": normalize_delta(integration_review.get("budget_delta")),
            }

        feedback = integration_review
        repair_stage_outputs["topology"] = topology_output
        repair_stage_outputs["economy"] = economy_output
        repair_stage_outputs["monster"] = monster_output
        repair_stage = earliest_repair_stage(integration_review, "integration")
        print(
            review_retry_message(
                floor_index,
                "integration",
                attempt,
                integration_review.get("summary", ""),
                repair_stage,
            )
        )

    raise PipelineError(f"MT{floor_index} did not pass staged review within {args.max_attempts} attempts.")


def accepted_floor_summary(
    args: argparse.Namespace,
    floor_index: int,
    floor_size: int,
    floor_output: dict[str, Any],
    delta: dict[str, int],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "floor_id": floor_output.get(
            "floor_id", f"{args.floor_prefix}{floor_index + args.floor_number_offset}"
        ),
        "floor_size": floor_size,
        "summary": floor_output.get("summary", ""),
        "budget_delta": delta,
    }
    if extra:
        summary.update(extra)
    return summary


def write_accepted_floor_artifacts(
    args: argparse.Namespace,
    floor_index: int,
    floor_output: dict[str, Any],
    review: dict[str, Any],
    limits: dict[str, int | None],
    used: dict[str, int],
) -> None:
    write_json(args.out_dir / "floors" / f"MT{floor_index}.floor.json", floor_output)
    write_json(args.out_dir / "reviews" / f"MT{floor_index}.review.json", review)
    write_json(args.out_dir / "budget_ledger.json", {"limits": limits, "used": used})


def run_sequential_floor_generation(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_count: int,
    floor_size: int,
    maps: dict[str, Any],
    enemys: dict[str, Any],
    limits: dict[str, int | None],
    floor_enemy_policies: list[dict[str, Any]],
    start_floor_index: int,
    used: dict[str, int],
    accepted_summaries: list[dict[str, Any]],
    accepted_floors: list[dict[str, Any]],
) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    for floor_index in range(start_floor_index, floor_count):
        floor_policy = build_runtime_floor_policy(brief, floor_enemy_policies, floor_index, accepted_floors, maps)
        result = generate_floor_staged_with_retries(
            args,
            brief,
            floor_index,
            floor_count,
            floor_size,
            maps,
            enemys,
            used,
            limits,
            accepted_summaries,
            accepted_floors,
            floor_policy,
        )
        accepted_floor = result["floor_output"]
        accepted_review = result["review"]
        delta = result["budget_delta"]
        used = add_budget(used, delta)
        write_accepted_floor_artifacts(args, floor_index, accepted_floor, accepted_review, limits, used)
        accepted_floors.append(accepted_floor)
        summary_extra: dict[str, Any] = {}
        if is_forced_accept_review(accepted_review):
            summary_extra["forced_accept"] = True
            summary_extra["quality_warning"] = accepted_review.get("summary", "")
        accepted_summaries.append(
            accepted_floor_summary(args, floor_index, floor_size, accepted_floor, delta, summary_extra)
        )

        if not args.skip_playtest:
            output_project = write_generated_project(args, brief, accepted_floors)
            playtest = run_playtest_game(args, output_project, floor_index)
            accepted_summaries[-1]["playtest"] = {
                "status": playtest.get("status"),
                "summary": playtest.get("summary"),
                "issues": playtest.get("issues", [])[:5],
            }
            if playtest.get("status") in {"warn", "error"}:
                print(
                    f"MT{floor_index} playtest {playtest.get('status')}: "
                    f"{playtest.get('summary', '')}"
                )
                for issue in playtest.get("issues", [])[:3]:
                    print(f"- {issue}")
                if args.playtest_policy == "fail":
                    raise PipelineError(
                        f"MT{floor_index} playtest failed under --playtest-policy=fail."
                    )
        if is_forced_accept_review(accepted_review):
            print(f"{floor_label(floor_index)}已保存，但建议生成结束后手动微调。")
        else:
            print(f"{floor_label(floor_index)}检查通过。")

    return used, accepted_summaries, accepted_floors


def run_parallel_floor_generation(
    args: argparse.Namespace,
    brief: dict[str, Any],
    floor_count: int,
    floor_size: int,
    maps: dict[str, Any],
    enemys: dict[str, Any],
    limits: dict[str, int | None],
    floor_enemy_policies: list[dict[str, Any]],
) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    contracts = build_floor_contracts(args, brief, floor_count, floor_size, limits)
    write_json(args.out_dir / "floor_contracts.json", {"contracts": contracts})

    worker_count = min(args.floor_concurrency, floor_count, MAX_FLOOR_CONCURRENCY)
    print(f"已开始同时生成 {worker_count} 个楼层。")

    results: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_index = {}
        for contract in contracts:
            floor_index = int(contract["floor_index"])
            contract_limits = floor_limits_from_contract(contract)
            planned_previous = contract.get("previous_floor_contract_summaries", [])
            if not isinstance(planned_previous, list):
                planned_previous = []
            floor_policy = build_runtime_floor_policy(brief, floor_enemy_policies, floor_index, [], maps)
            future = executor.submit(
                generate_floor_staged_with_retries,
                args,
                brief,
                floor_index,
                floor_count,
                floor_size,
                maps,
                enemys,
                empty_budget(),
                contract_limits,
                planned_previous,
                [],
                floor_policy,
                contract,
                False,
            )
            future_to_index[future] = floor_index

        for future in as_completed(future_to_index):
            floor_index = future_to_index[future]
            try:
                results[floor_index] = future.result()
            except Exception as exc:
                raise PipelineError(f"MT{floor_index} parallel worker failed: {exc}") from exc
            if is_forced_accept_review(results[floor_index].get("review")):
                print(f"{floor_label(floor_index)}已保存，但质量需要生成结束后手动看一下。")
            else:
                print(f"{floor_label(floor_index)}检查通过。")

    used = empty_budget()
    accepted_summaries: list[dict[str, Any]] = []
    accepted_floors: list[dict[str, Any]] = []
    for floor_index in range(floor_count):
        if floor_index not in results:
            raise PipelineError(f"MT{floor_index} did not return a parallel result.")
        result = results[floor_index]
        accepted_floor = result["floor_output"]
        accepted_review = result["review"]
        forced_accept = is_forced_accept_review(accepted_review)
        floor_policy = build_runtime_floor_policy(brief, floor_enemy_policies, floor_index, accepted_floors, maps)
        expected_floor_id = f"{args.floor_prefix}{floor_index + args.floor_number_offset}"
        try:
            local_issues, delta = local_floor_review(
                accepted_floor, expected_floor_id, floor_size, brief, maps, enemys, floor_policy
            )
            metrics = floor_static_metrics(accepted_floor, maps, enemys, brief)
            local_issues.extend(static_metric_issues(metrics))
            local_issues.extend(
                wall_mask_similarity_issues(accepted_floors, accepted_floor, maps, args.max_wall_similarity)
            )
            local_issues.extend(floor_resource_progression_issues(brief, accepted_floors, accepted_floor, maps))
            local_issues.extend(budget_issues(delta, limits, used))
        except PipelineError as exc:
            if not forced_accept:
                raise
            local_issues = [str(exc)]
            delta = normalize_delta(accepted_review.get("budget_delta"))
        if accepted_review.get("status") != "pass":
            local_issues.append("parallel worker review did not pass.")
        if local_issues:
            detail = "\n".join(f"- {issue}" for issue in local_issues[:8])
            if forced_accept:
                accepted_review["final_global_validation_warnings"] = local_issues[:12]
                print(
                    f"Final global validation warning for forced MT{floor_index}; "
                    "keeping generated output for manual adjustment:"
                )
                print(detail)
            else:
                raise PipelineError(f"Final global validation failed for MT{floor_index}:\n{detail}")

        accepted_review["budget_delta"] = delta
        used = add_budget(used, delta)
        write_accepted_floor_artifacts(args, floor_index, accepted_floor, accepted_review, limits, used)
        accepted_floors.append(accepted_floor)
        accepted_summaries.append(
            accepted_floor_summary(
                args,
                floor_index,
                floor_size,
                accepted_floor,
                delta,
                {
                    "parallel": True,
                    "floor_contract": contracts[floor_index],
                    **(
                        {
                            "forced_accept": True,
                            "quality_warning": accepted_review.get("summary", ""),
                        }
                        if forced_accept
                        else {}
                    ),
                },
            )
        )

    return used, accepted_summaries, accepted_floors


def apply_advanced_policy_overrides(args: argparse.Namespace, brief: dict[str, Any]) -> None:
    monster_policy = brief.setdefault("monster_policy", {})
    if not isinstance(monster_policy, dict):
        monster_policy = {}
        brief["monster_policy"] = monster_policy
    monster_policy["monster_types_per_floor"] = int(args.monster_types_per_floor)
    monster_policy["max_specials_per_monster"] = int(args.max_specials_per_monster)
    monster_policy["floor_overlap_ratio"] = float(args.floor_overlap_ratio)
    monster_policy["special_damage_red_potion_min"] = float(args.special_damage_red_potion_min)
    monster_policy["special_damage_red_potion_max"] = float(args.special_damage_red_potion_max)
    monster_policy["no_adjacent_enemies"] = not bool(args.allow_adjacent_enemies)

    resource_policy = brief.setdefault("resource_policy", {})
    if not isinstance(resource_policy, dict):
        resource_policy = {}
        brief["resource_policy"] = resource_policy
    resource_policy["gem_floor_delta_min"] = float(args.gem_floor_delta_min)
    resource_policy["gem_floor_delta_max"] = float(args.gem_floor_delta_max)
    resource_policy["potion_floor_delta_min"] = float(args.potion_floor_delta_min)
    resource_policy["potion_floor_delta_max"] = float(args.potion_floor_delta_max)
    resource_policy["potion_compare_mode"] = "red_potion_equiv"

    layout_constraints = brief.setdefault("layout_constraints", {})
    if not isinstance(layout_constraints, dict):
        layout_constraints = {}
        brief["layout_constraints"] = layout_constraints
    layout_constraints["wall_ratio_min"] = float(args.wall_ratio_min)
    layout_constraints["wall_ratio_max"] = float(args.wall_ratio_max)
    layout_constraints["high_value_pocket_threshold"] = float(args.high_value_pocket_threshold)
    layout_constraints["warning"] = "Advanced generation constraints are targets; LLM output may need manual adjustment."


def run_pipeline(args: argparse.Namespace) -> int:
    args.repo_root = args.repo_root.resolve()
    args.out_dir = args.out_dir.resolve()
    if args.clean:
        clean_output_dir(args.repo_root, args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    brief_output = args.out_dir / "tower_brief.json"
    if args.brief_file:
        brief = load_json_object(Path(args.brief_file).read_text(encoding="utf-8"))
    else:
        idea = read_text_arg(args.idea_file, args.idea_text)
        brief = agent_exec(args, build_brief_prompt(args, idea), BRIEF_SCHEMA, brief_output)
    write_json(brief_output, brief)

    print("\nTower brief summary:")
    print(brief.get("summary", ""))

    if brief.get("status") != "ready":
        print("\nMore input is required:")
        for question in brief.get("questions", []):
            print(f"- {question}")
        return 2

    if args.floors:
        floor_count = args.floors
        brief["floor_count"] = floor_count
        write_json(brief_output, brief)
    else:
        floor_count = int(brief["floor_count"])

    if floor_count <= 0:
        raise PipelineError("floor_count must be positive.")

    floor_size = args.floor_size or normalize_floor_size(brief.get("floor_size"))
    brief["floor_size"] = floor_size
    fixed_rules = brief.setdefault("fixed_rules", [])
    size_rule = f"{floor_size}x{floor_size} floors"
    if isinstance(fixed_rules, list) and size_rule not in fixed_rules:
        brief["fixed_rules"] = [
            rule
            for rule in fixed_rules
            if not (isinstance(rule, str) and ("x" in rule and "floors" in rule))
        ]
        brief["fixed_rules"].insert(0, size_rule)
    if not args.resume_existing:
        apply_advanced_policy_overrides(args, brief)
    write_json(brief_output, brief)

    if args.brief_only:
        print(f"\nBrief written: {brief_output}")
        return 0

    if not args.yes:
        print("\nConfirmation prompt:")
        print(brief.get("confirmation_prompt", "Proceed with this tower brief?"))
        answer = input("Proceed to per-floor generation? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            return 3

    limits = numeric_limits(brief.get("global_limits", {}))
    maps, source_enemys = load_project_tables(args)
    enemys = prepare_runtime_enemy_table(args, brief, maps, source_enemys, floor_count, floor_size)
    write_json(brief_output, brief)
    floor_enemy_policies = build_floor_enemy_policies(floor_count, maps, enemys, brief)
    if args.parallel_floors:
        if args.resume_existing:
            raise PipelineError("--parallel-floors cannot be combined with --resume-existing.")
        used, accepted_summaries, accepted_floors = run_parallel_floor_generation(
            args, brief, floor_count, floor_size, maps, enemys, limits, floor_enemy_policies
        )
    elif args.resume_existing:
        start_floor_index, used, accepted_summaries, accepted_floors = try_resume_existing_floors(
            args, brief, floor_count, floor_size, maps, enemys, limits
        )
        used, accepted_summaries, accepted_floors = run_sequential_floor_generation(
            args,
            brief,
            floor_count,
            floor_size,
            maps,
            enemys,
            limits,
            floor_enemy_policies,
            start_floor_index,
            used,
            accepted_summaries,
            accepted_floors,
        )
    else:
        used, accepted_summaries, accepted_floors = run_sequential_floor_generation(
            args,
            brief,
            floor_count,
            floor_size,
            maps,
            enemys,
            limits,
            floor_enemy_policies,
            0,
            empty_budget(),
            [],
            [],
        )

    output_project = write_generated_project(args, brief, accepted_floors)
    has_forced_acceptance = any(bool(summary.get("forced_accept")) for summary in accepted_summaries)
    try:
        final_issues = final_tower_validation_issues(
            args,
            brief,
            accepted_floors,
            floor_count,
            floor_size,
            maps,
            enemys,
            floor_enemy_policies,
            limits,
            used,
            output_project,
            True,
        )
    except PipelineError as exc:
        if not has_forced_acceptance:
            raise
        final_issues = [str(exc)]
    final_validation = {
        "status": "warn" if final_issues and has_forced_acceptance else ("fail" if final_issues else "pass"),
        "issues": final_issues,
        "forced_acceptance": has_forced_acceptance,
    }
    write_json(args.out_dir / "final_validation.json", final_validation)
    if final_issues:
        detail = "\n".join(f"- {issue}" for issue in final_issues[:12])
        if has_forced_acceptance:
            print(
                "Final tower validation produced warnings after forced acceptance; "
                "generated output is kept for manual adjustment:"
            )
            print(detail)
        else:
            raise PipelineError(f"Final tower validation failed:\n{detail}")

    if args.parallel_floors and not args.skip_playtest:
        playtest = run_playtest_game(args, output_project, floor_count - 1)
        if playtest.get("status") in {"warn", "error"}:
            print(
                f"parallel final playtest {playtest.get('status')}: "
                f"{playtest.get('summary', '')}"
            )
            for issue in playtest.get("issues", [])[:3]:
                print(f"- {issue}")
            if args.playtest_policy == "fail":
                raise PipelineError("parallel final playtest failed under --playtest-policy=fail.")

    final_summary = {
        "status": "complete",
        "floor_count": floor_count,
        "floor_size": floor_size,
        "project_dir": str(output_project),
        "budget_ledger": {"limits": limits, "used": used},
        "floors": accepted_summaries,
        "final_validation": final_validation,
    }
    write_json(args.out_dir / "summary.json", final_summary)
    print(f"\n生成完成：{args.out_dir / 'summary.json'}")
    print(f"可游玩项目已生成：{output_project}")
    return 0


def self_test(repo_root: Path) -> int:
    parsed = load_json_object("```json\n{\"status\":\"pass\"}\n```")
    assert parsed["status"] == "pass"

    limits = numeric_limits({"yellow_doors": 2, "bombs": "medium"})
    used = {key: 0 for key in TRACKED_RESOURCES}
    used["yellow_doors"] = 1
    delta = normalize_delta({"yellow_doors": 2, "bombs": 3})
    issues = budget_issues(delta, limits, used)
    assert issues == ["yellow_doors exceeds whole-tower limit: 3 > 2"]

    used = add_budget({key: 0 for key in TRACKED_RESOURCES}, normalize_delta({"blue_keys": 1}))
    assert used["blue_keys"] == 1
    assert remaining_budget({"blue_keys": 3}, used)["blue_keys"] == 2
    assert normalize_floor_size(None) == DEFAULT_FLOOR_SIZE
    assert normalize_floor_size("13x13") == 13
    assert normalize_floor_size(9) == 9
    contract_args = argparse.Namespace(floor_prefix="MT", floor_number_offset=0)
    contracts = build_floor_contracts(
        contract_args,
        {},
        3,
        11,
        numeric_limits({"yellow_doors": 5, "blue_doors": 1}),
    )
    assert [item["resource_limits"]["yellow_doors"] for item in contracts] == [2, 2, 1]
    assert [item["resource_limits"]["blue_doors"] for item in contracts] == [1, 0, 0]
    assert contracts[2]["previous_floor_contract_summaries"][1]["floor_id"] == "MT1"
    codex_args = argparse.Namespace(
        codex_bin="codex",
        model=DEFAULT_CODEX_MODEL,
        profile=None,
        config=list(DEFAULT_CODEX_CONFIG),
        codex_arg=[],
        repo_root=repo_root,
        sandbox="read-only",
    )
    codex_cmd = build_codex_command(codex_args, Path("/tmp/schema.json"), Path("/tmp/output.json"))
    assert codex_cmd[:4] == ["codex", "exec", "--model", DEFAULT_CODEX_MODEL]
    assert 'model_reasoning_effort="xhigh"' in codex_cmd
    assert 'service_tier="priority"' in codex_cmd
    opencode_args = argparse.Namespace(
        opencode_bin="opencode",
        model=None,
        opencode_arg=[],
        repo_root=repo_root,
    )
    opencode_cmd = build_opencode_command(opencode_args, Path("/tmp/prompt.md"))
    opencode_cmd_text = " ".join(opencode_cmd)
    assert opencode_cmd[:4] == ["opencode", "run", "--dir", str(repo_root)]
    assert "--model" not in opencode_cmd
    assert "model_reasoning_effort" not in opencode_cmd_text
    assert "service_tier" not in opencode_cmd_text
    assert opencode_cmd[-2:] == ["--file", "/tmp/prompt.md"]
    parsed_defaults = parse_args(["--self-test"])
    assert parsed_defaults.timeout == DEFAULT_AGENT_TIMEOUT_SECONDS
    args = argparse.Namespace(repo_root=repo_root)
    maps, enemys = load_project_tables(args)
    enemy_design_brief = {
        "monster_policy": {"allowed_specials": [1, 2, 3, 15, 18], "monster_types_per_floor": 9},
        "global_settings": {"potions": {"redPotion": 100}},
    }
    designed_enemys, designed_ids, design_warnings = apply_enemy_design_updates(
        enemys,
        {
            "updates": [
                {
                    "id": "greenSlime",
                    "name": "测试绿头怪",
                    "hp": 777,
                    "atk": 21,
                    "def": 9,
                    "money": 3,
                    "exp": 0,
                    "point": 0,
                    "specials": [15],
                    "value": None,
                    "zone": 80,
                    "repulse": None,
                    "range": 1,
                    "zoneSquare": False,
                    "notBomb": None,
                }
            ]
        },
        enemy_design_brief,
    )
    assert designed_ids == ["greenSlime"]
    assert design_warnings == []
    assert designed_enemys["greenSlime"]["hp"] == 777
    assert designed_enemys["greenSlime"]["special"] == 15
    assert designed_enemys["greenSlime"]["zone"] == 80
    enemy_design_brief["enemy_design"] = {"designed_enemy_ids": designed_ids}
    designed_candidates = build_enemy_candidates(maps, designed_enemys, enemy_design_brief)
    assert {item["id"] for item in designed_candidates} == {"greenSlime"}
    forced_review = forced_accept_review(0, 1, "integration", {"yellow_doors": 1}, ["self-test warning"])
    assert forced_review["status"] == "pass"
    assert forced_review["forced_accept"] is True
    assert is_forced_accept_review(forced_review)
    assert forced_review["budget_delta"]["yellow_doors"] == 1

    sample_floor_output = {
        "floor_id": "MT0",
        "floor_index": 0,
        "floor_size": 9,
        "summary": "self-test floor",
        "floor": {
            "floorId": "MT0",
            "title": "self-test",
            "name": "self-test",
            "width": 9,
            "height": 9,
            "map": [
                [1, 1, 1, 1, 87, 1, 1, 1, 1],
                [1, 0, 201, 0, 81, 0, 202, 27, 1],
                [1, 0, 1, 0, 1, 0, 1, 0, 1],
                [1, 22, 1, 0, 203, 0, 1, 28, 1],
                [1, 0, 1, 31, 1, 0, 1, 0, 1],
                [1, 0, 204, 0, 1, 0, 205, 0, 1],
                [1, 21, 1, 0, 82, 0, 1, 32, 1],
                [1, 88, 0, 0, 0, 0, 0, 0, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1],
            ],
            "changeFloor": {},
        },
    }
    sample_brief = {
        "monster_policy": {
            "allowed_specials": [1, 2, 3, 15, 16, 18],
            "monster_types_per_floor": 9,
            "enemy_count_min_per_floor": 4,
            "enemy_count_max_per_floor": 10,
        }
    }
    test_enemys = core_clone(enemys)
    for row in sample_floor_output["floor"]["map"]:
        for code in row:
            entry = maps.get(str(code))
            if not is_enemy_entry(entry):
                continue
            enemy = test_enemys.get(str(entry.get("id")))
            if enemy is None:
                continue
            enemy["special"] = 0
            enemy.pop("repulse", None)
            enemy.pop("zoneSquare", None)
    enemys = test_enemys
    local_issues, sample_delta = local_floor_review(sample_floor_output, "MT0", 9, sample_brief, maps, enemys)
    assert local_issues == []
    assert sample_delta["yellow_doors"] == 1
    assert sample_delta["blue_doors"] == 1
    assert sample_delta["yellow_keys"] == 1
    assert sample_delta["blue_keys"] == 1
    assert sample_delta["redGems"] == 1
    assert sample_delta["blueGems"] == 1
    assert sample_delta["redPotions"] == 1
    assert sample_delta["bluePotions"] == 1
    resource_probe_delta = derive_budget_delta({"map": [[27, 28, 29, 31, 32, 34, 33, 69]]}, maps)
    assert resource_probe_delta["redGems"] == 1
    assert resource_probe_delta["blueGems"] == 1
    assert resource_probe_delta["greenGems"] == 1
    assert resource_probe_delta["redPotions"] == 1
    assert resource_probe_delta["bluePotions"] == 1
    assert resource_probe_delta["yellowPotions"] == 1
    assert resource_probe_delta["greenPotions"] == 1
    assert resource_probe_delta["jumpShoes"] == 1

    topology_floor_output = core_clone(sample_floor_output)
    topology_floor_output["summary"] = "topology-only self-test floor"
    topology_floor_output["annotations"] = [
        {
            "stage": "topology",
            "kind": "candidate_route",
            "label": "left route",
            "coordinates": [[1, 7], [2, 7], [3, 7], [4, 7], [4, 6], [4, 5], [4, 4], [4, 3], [4, 2], [4, 1], [4, 0]],
            "description": "self-test candidate route",
            "tags": ["route"],
            "data": "",
        }
    ]
    topology_floor_output["floor"]["map"] = [
        [1, 1, 1, 1, 87, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 0, 1, 0, 0, 0, 1, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 1],
        [1, 0, 1, 0, 0, 0, 1, 0, 1],
        [1, 88, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]
    topology_issues = topology_stage_review_issues(topology_floor_output, "MT0", 9, maps)
    assert not any(issue["severity"] == "fail" for issue in topology_issues)
    duplicate_wall_issues = wall_mask_similarity_issues([topology_floor_output], core_clone(topology_floor_output), maps)
    assert any("Adjacent wall mask similarity" in issue for issue in duplicate_wall_issues)

    pocket_floor_output = core_clone(sample_floor_output)
    pocket_floor_output["summary"] = "unguarded high-value pocket self-test floor"
    pocket_floor_output["annotations"] = []
    pocket_floor_output["floor"]["map"] = [
        [1, 1, 1, 1, 87, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 0, 1],
        [1, 0, 1, 27, 32, 28, 1, 0, 1],
        [1, 0, 1, 0, 0, 0, 1, 0, 1],
        [1, 0, 1, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 88, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]
    pocket_metrics = floor_static_metrics(pocket_floor_output, maps, enemys, sample_brief)
    assert pocket_metrics["unguarded_high_value_pockets"]
    assert any("High-value pocket" in issue for issue in static_metric_issues(pocket_metrics))
    protected_pocket_floor = core_clone(pocket_floor_output)
    protected_pocket_floor["annotations"] = [
        {
            "stage": "economy",
            "kind": "combat_chokepoint",
            "label": "pocket entry",
            "coordinates": [[4, 6]],
            "description": "guards the high-value pocket entrance",
            "tags": ["combat"],
            "data": "",
        }
    ]
    protected_pocket_metrics = floor_static_metrics(protected_pocket_floor, maps, {}, sample_brief)
    assert not protected_pocket_metrics["unguarded_high_value_pockets"]

    economy_floor_output = core_clone(sample_floor_output)
    economy_floor_output["summary"] = "economy self-test floor"
    economy_floor_output["annotations"] = [
        {
            "stage": "economy",
            "kind": "combat_chokepoint",
            "label": "center guard",
            "coordinates": [[4, 3], [1, 5]],
            "description": "monster stage should place route pressure here",
            "tags": ["combat"],
            "data": "",
        }
    ]
    economy_floor_output["floor"]["map"] = [
        [1, 1, 1, 1, 87, 1, 1, 1, 1],
        [1, 0, 1, 0, 81, 0, 1, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 22, 1, 0, 0, 0, 1, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 21, 1, 0, 82, 0, 1, 0, 1],
        [1, 88, 0, 0, 1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]
    economy_issues, economy_delta = economy_stage_review_issues(
        economy_floor_output,
        "MT0",
        9,
        sample_brief,
        maps,
        {key: None for key in TRACKED_RESOURCES},
        empty_budget(),
        [],
        None,
        False,
    )
    assert not any(issue["severity"] == "fail" for issue in economy_issues)
    assert economy_delta["yellow_doors"] == 1
    assert economy_delta["blue_doors"] == 1

    monster_floor_output = core_clone(sample_floor_output)
    monster_floor_output["annotations"] = [
        {
            "stage": "monster",
            "kind": "combat_role",
            "label": "self-test roles",
            "coordinates": [[2, 1], [6, 1], [4, 3], [2, 5], [6, 5]],
            "description": "concrete monster placements",
            "tags": ["combat"],
            "data": "",
        }
    ]
    monster_floor_output["floor"]["map"] = [
        [1, 1, 1, 1, 87, 1, 1, 1, 1],
        [1, 0, 201, 0, 81, 0, 202, 27, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 22, 1, 0, 203, 0, 1, 28, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 0, 204, 0, 1, 0, 205, 0, 1],
        [1, 21, 1, 0, 82, 0, 1, 32, 1],
        [1, 88, 0, 0, 1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]
    monster_issues, monster_delta, monster_metrics = monster_stage_review_issues(
        monster_floor_output,
        "MT0",
        9,
        sample_brief,
        maps,
        enemys,
        {key: None for key in TRACKED_RESOURCES},
        empty_budget(),
        [],
        None,
        False,
    )
    assert not any(issue["severity"] == "fail" for issue in monster_issues)
    for key in ("yellow_doors", "blue_doors", "yellow_keys", "blue_keys"):
        assert monster_delta[key] == sample_delta[key]
    assert monster_metrics["available"] is True

    integration_review = structured_review(
        "integration",
        [
            structured_issue(
                "integration",
                "fail",
                "blue door at [4,6] lacks reward compensation after monster placement",
                "Move a stronger reward behind the blue door or reduce its cost.",
            )
        ],
        sample_delta,
        "integration self-test",
    )
    assert earliest_repair_stage(integration_review, "integration") == "economy"
    assert classify_issue_owner("Entrance free region exposes too many resources", "monster") == "economy"
    topology_review = structured_review(
        "topology",
        [structured_issue("topology", "fail", "route graph is a single corridor", "Create at least 3 candidate route families.")],
    )
    assert earliest_repair_stage(topology_review, "topology") == "topology"
    repair_prompt_args = argparse.Namespace(repo_root=repo_root, floor_prefix="MT", floor_number_offset=0)
    repair_prompt = build_topology_prompt(
        repair_prompt_args,
        {"floor_size": 9},
        0,
        1,
        empty_budget(),
        {key: None for key in TRACKED_RESOURCES},
        [],
        topology_review,
        None,
        None,
        {"summary": "broken topology output"},
    )
    assert "current_stage_output_to_repair" in repair_prompt
    assert "broken topology output" in repair_prompt

    too_few_enemy_floor = core_clone(sample_floor_output)
    too_few_enemy_floor["floor"]["map"][5][2] = 0
    too_few_enemy_floor["floor"]["map"][5][6] = 0
    local_issues, _ = local_floor_review(too_few_enemy_floor, "MT0", 9, sample_brief, maps, enemys)
    assert any("at least 4 enemies" in issue for issue in local_issues)

    default_density_brief = {
        "monster_policy": {"allowed_specials": [1, 2, 3, 15, 16, 18], "monster_types_per_floor": 9}
    }
    local_issues, _ = local_floor_review(sample_floor_output, "MT0", 9, default_density_brief, maps, enemys)
    assert any("at least 22 enemies" in issue for issue in local_issues)
    over_max_brief = {
        "monster_policy": {
            "allowed_specials": [1, 2, 3, 15, 16, 18],
            "monster_types_per_floor": 9,
            "enemy_count_min_per_floor": 4,
            "enemy_count_max_per_floor": 4,
        }
    }
    local_issues, _ = local_floor_review(sample_floor_output, "MT0", 9, over_max_brief, maps, enemys)
    assert any("at most 4 enemies" in issue for issue in local_issues)

    adjacent_enemy_floor = core_clone(sample_floor_output)
    adjacent_enemy_floor["floor"]["map"][1][3] = 202
    local_issues, _ = local_floor_review(adjacent_enemy_floor, "MT0", 9, sample_brief, maps, enemys)
    assert any("orthogonal adjacency" in issue for issue in local_issues)

    floor_policies = build_floor_enemy_policies(3, maps, enemys, sample_brief)
    assert len(floor_policies) == 3
    assert all(policy["allowed_enemy_ids"] for policy in floor_policies)
    disallowed_policy = core_clone(floor_policies[0])
    disallowed_policy["allowed_enemy_ids"] = ["greenSlime"]
    disallowed_policy["allowed_enemy_codes"] = [201]
    local_issues, _ = local_floor_review(sample_floor_output, "MT0", 9, sample_brief, maps, enemys, disallowed_policy)
    assert any("outside current floor policy" in issue for issue in local_issues)

    special_enemys = core_clone(enemys)
    special_enemys["greenSlime"]["special"] = 18
    special_enemys["greenSlime"]["repulse"] = 20
    special_brief = {
        "monster_policy": {"allowed_specials": [1, 2, 3, 15, 18], "monster_types_per_floor": 9},
        "global_settings": {"potions": {"redPotion": 100}},
    }
    local_issues, _ = local_floor_review(sample_floor_output, "MT0", 9, special_brief, maps, special_enemys)
    assert any("zone/repulse damage" in issue for issue in local_issues)

    lower_resource_floor = core_clone(sample_floor_output)
    lower_resource_floor["floor"]["map"][1][7] = 0
    lower_resource_floor["floor"]["map"][3][7] = 0
    resource_brief = {
        "global_settings": {"potions": {"redPotion": 100, "bluePotion": 250}},
        "resource_policy": {"gem_floor_delta_min": 0, "gem_floor_delta_max": 2, "potion_floor_delta_min": 0, "potion_floor_delta_max": 2},
    }
    resource_issues = floor_resource_progression_issues(resource_brief, [sample_floor_output], lower_resource_floor, maps)
    assert any("gem count progression" in issue for issue in resource_issues)

    bad_gem_floor_output = core_clone(sample_floor_output)
    bad_gem_floor_output["summary"] = "bad gem route balance floor"
    bad_gem_floor_output["floor"]["map"] = [
        [1, 1, 1, 1, 87, 1, 1, 1, 1],
        [1, 0, 201, 0, 0, 0, 202, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 22, 1, 0, 203, 0, 1, 28, 1],
        [1, 0, 1, 31, 1, 0, 1, 0, 1],
        [1, 0, 204, 0, 1, 0, 205, 0, 1],
        [1, 21, 1, 27, 28, 31, 1, 32, 1],
        [1, 88, 27, 28, 31, 32, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]
    gem_brief = {
        "global_settings": {
            "initial_hero": {"hp": 300, "atk": 10, "def": 10},
            "gems": {"redGem": 1, "blueGem": 1, "greenGem": 5},
            "potions": {"redPotion": 100},
        },
        "fixed_rules": ["initial position: MT0 (1,7)"],
    }
    gem_review = gem_route_balance_review(gem_brief, bad_gem_floor_output, [], maps, enemys)
    assert gem_review["status"] == "fail"
    assert any("Entry-to-gem route is too easy" in issue for issue in gem_review["issues"])
    assert any("Large direct resource region" in issue for issue in gem_review["issues"])
    previous_hero = hero_state_before_floor(gem_brief, [bad_gem_floor_output], maps)
    assert previous_hero["atk"] > 10
    assert previous_hero["def"] > 10

    with tempfile.TemporaryDirectory() as tmp_dir:
        write_args = argparse.Namespace(
            repo_root=repo_root,
            out_dir=Path(tmp_dir),
            floor_prefix="MT",
            floor_number_offset=0,
            max_wall_similarity=MAX_ADJACENT_WALL_MASK_SIMILARITY,
            runtime_enemys=designed_enemys,
        )
        output_project = write_generated_project(
            write_args,
            {
                "global_settings": {
                    "initial_hero": {
                        "hp": 500,
                        "atk": 12,
                        "def": 8,
                        "keys": {"yellow": 2, "blue": 1},
                        "tools": {"pickaxe": 1, "bomb": 2, "centerFly": 3, "jumpShoes": 4},
                    },
                    "gems": {"red": 2, "blue": 3, "green": 5},
                    "potions": {"red": 80, "blue": 200, "yellow": 500, "green": 1000},
                }
            },
            [sample_floor_output],
        )
        assert (output_project / "floors" / "MT0.js").exists()
        _, written_floor = load_js_object(output_project / "floors" / "MT0.js")
        assert written_floor["events"]["4,0"][0]["type"] == "win"
        _, written_data = load_js_object(output_project / "data.js")
        _, written_enemys = load_js_object(output_project / "enemys.js")
        assert written_enemys["greenSlime"]["hp"] == 777
        assert written_data["main"]["floorIds"] == ["MT0"]
        assert written_data["firstData"]["floorId"] == "MT0"
        assert written_data["firstData"]["hero"]["hp"] == 500
        assert written_data["firstData"]["hero"]["items"]["tools"]["yellowKey"] == 2
        assert written_data["firstData"]["hero"]["items"]["tools"]["blueKey"] == 1
        assert written_data["firstData"]["hero"]["items"]["tools"]["pickaxe"] == 1
        assert written_data["firstData"]["hero"]["items"]["tools"]["bomb"] == 2
        assert written_data["firstData"]["hero"]["items"]["tools"]["centerFly"] == 3
        assert written_data["firstData"]["hero"]["items"]["tools"]["jumpShoes"] == 4
        assert written_data["values"]["redGem"] == 2
        assert written_data["values"]["bluePotion"] == 200
        exact_limits = {key: sample_delta.get(key, 0) for key in TRACKED_RESOURCES}
        sample_enemy_policy = {
            "allowed_enemy_ids": sorted(
                {
                    str(maps.get(str(code), {}).get("id"))
                    for row in sample_floor_output["floor"]["map"]
                    for code in row
                    if is_enemy_entry(maps.get(str(code)))
                }
            ),
            "allowed_enemy_codes": sorted(
                {
                    code
                    for row in sample_floor_output["floor"]["map"]
                    for code in row
                    if is_enemy_entry(maps.get(str(code)))
                }
            ),
            "enemy_role_hints": {},
            "fallback_no_special_enemy_ids": [],
        }
        final_issues = final_tower_validation_issues(
            write_args,
            sample_brief,
            [sample_floor_output],
            1,
            9,
            maps,
            enemys,
            [sample_enemy_policy],
            exact_limits,
            sample_delta,
            output_project,
            True,
        )
        assert final_issues == []

    for name in [
        "build-mota-tower",
        "design-traditional-mota-tower",
        "review-mota-floor",
        "playtest-mota-game",
        "topology-mota-floor",
        "economy-mota-floor",
        "monster-special-mota-floor",
        "modify-mota-enemy-data",
    ]:
        path = skill_path(repo_root, name)
        assert path.exists(), f"missing skill: {path}"

    print("self-test passed")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build a classic mota tower with headless coding agents.")
    parser.add_argument("--idea-file", help="Path to the user's tower idea text.")
    parser.add_argument("--idea-text", help="Inline tower idea text.")
    parser.add_argument("--brief-file", help="Use an existing confirmed tower_brief JSON and skip stage 0.")
    parser.add_argument("--brief-only", action="store_true", help="Stop after producing or loading tower_brief.json.")
    parser.add_argument("--out-dir", type=Path, default=repo_root / "build" / "mota-tower")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--floors", type=int, help="Optional floor count override.")
    parser.add_argument(
        "--floor-size",
        type=int,
        choices=sorted(SUPPORTED_FLOOR_SIZES),
        help="Square map size for generated floors. Defaults to 11 unless the brief requests 9 or 13.",
    )
    parser.add_argument("--floor-prefix", default="MT", help="Floor id prefix for generated floor maps.")
    parser.add_argument("--floor-number-offset", type=int, default=0, help="Floor id numeric offset.")
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument(
        "--parallel-floors",
        action="store_true",
        help="Generate and review different floors concurrently using per-floor budget contracts.",
    )
    parser.add_argument(
        "--floor-concurrency",
        type=int,
        default=MAX_FLOOR_CONCURRENCY,
        help=f"Maximum concurrent floor workers for --parallel-floors; capped at {MAX_FLOOR_CONCURRENCY}.",
    )
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation.")
    parser.add_argument("--clean", action="store_true", help="Remove the output directory first; only allowed under repo build/.")
    parser.add_argument("--resume-existing", action="store_true", help="Reuse existing accepted floor/review JSON files in the output directory.")
    parser.add_argument("--keep-prompts", action="store_true", help="Write each agent prompt next to its output JSON.")
    parser.add_argument(
        "--agent-backend",
        choices=AGENT_BACKENDS,
        default="codex",
        help="Agent runner for internal LLM calls. Default: codex.",
    )
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument(
        "--model",
        help=(
            f"Model for internal calls. Codex defaults to {DEFAULT_CODEX_MODEL}; "
            "OpenCode only receives --model when this is set explicitly."
        ),
    )
    parser.add_argument("--profile", help="Optional Codex config profile.")
    parser.add_argument(
        "--config",
        action="append",
        help="Extra codex exec --config key=value; repeatable. Codex defaults include xhigh reasoning and priority service tier.",
    )
    parser.add_argument("--codex-arg", action="append", default=[], help="Extra raw codex exec argument; repeatable.")
    parser.add_argument("--opencode-bin", default="opencode")
    parser.add_argument("--opencode-arg", action="append", default=[], help="Extra raw opencode run argument; repeatable.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_AGENT_TIMEOUT_SECONDS,
        help=f"Per agent call timeout in seconds. Default: {DEFAULT_AGENT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--max-wall-similarity",
        type=float,
        default=MAX_ADJACENT_WALL_MASK_SIMILARITY,
        help="Maximum allowed adjacent-floor wall mask similarity. Default: 0.9.",
    )
    parser.add_argument("--wall-ratio-min", type=float, default=DEFAULT_WALL_RATIO_MIN, help="Minimum target wall ratio for 13x13 topology.")
    parser.add_argument("--wall-ratio-max", type=float, default=DEFAULT_WALL_RATIO_MAX, help="Maximum target wall ratio for 13x13 topology.")
    parser.add_argument(
        "--monster-types-per-floor",
        type=int,
        default=DEFAULT_MONSTER_TYPES_PER_FLOOR,
        help="Maximum enemy type count available to each generated floor.",
    )
    parser.add_argument("--max-specials-per-monster", type=int, default=1, help="Maximum special abilities per enemy.")
    parser.add_argument("--allow-adjacent-enemies", action="store_true", help="Allow orthogonally adjacent enemy placements.")
    parser.add_argument("--floor-overlap-ratio", type=float, default=0.7, help="Enemy candidate overlap ratio between adjacent floors.")
    parser.add_argument("--special-damage-red-potion-min", type=float, default=0.5, help="Minimum zone/repulse damage as red-potion ratio.")
    parser.add_argument("--special-damage-red-potion-max", type=float, default=1.0, help="Maximum zone/repulse damage as red-potion ratio.")
    parser.add_argument("--gem-floor-delta-min", type=float, default=0.0, help="Minimum gem-count increase allowed between adjacent floors.")
    parser.add_argument("--gem-floor-delta-max", type=float, default=2.0, help="Maximum gem-count increase allowed between adjacent floors.")
    parser.add_argument("--potion-floor-delta-min", type=float, default=0.0, help="Minimum red-potion-equivalent increase allowed between adjacent floors.")
    parser.add_argument("--potion-floor-delta-max", type=float, default=2.0, help="Maximum red-potion-equivalent increase allowed between adjacent floors.")
    parser.add_argument(
        "--high-value-pocket-threshold",
        type=float,
        default=DEFAULT_HIGH_VALUE_POCKET_THRESHOLD,
        help="Resource-weight threshold for unguarded high-value pocket warnings.",
    )
    parser.add_argument(
        "--enemy-design-count",
        type=int,
        default=DEFAULT_ENEMY_DESIGN_COUNT,
        help="Number of existing enemy slots for the enemy-data agent to rewrite; 0 means all available slots.",
    )
    parser.add_argument("--sandbox", default="read-only", choices=["read-only", "workspace-write", "danger-full-access"], help="Codex sandbox mode.")
    parser.add_argument("--skip-playtest", action="store_true", help="Do not run browser playtests after floor reviews.")
    parser.add_argument(
        "--playtest-policy",
        choices=["warn", "fail"],
        default="warn",
        help="Whether playtest warnings/errors should only be reported or fail the pipeline.",
    )
    parser.add_argument("--playtest-timeout", type=int, default=120, help="Browser playtest timeout in seconds.")
    parser.add_argument("--playtest-max-steps", type=int, default=160, help="Maximum keyboard steps per playtest route.")
    parser.add_argument("--playtest-routes", type=int, default=4, help="Number of keyboard route profiles to try.")
    parser.add_argument("--self-test", action="store_true", help="Run local tests without calling an external agent.")
    args = parser.parse_args(argv)
    if args.max_attempts <= 0:
        parser.error("--max-attempts must be positive")
    if args.floor_concurrency <= 0:
        parser.error("--floor-concurrency must be positive")
    if args.floor_concurrency > MAX_FLOOR_CONCURRENCY:
        parser.error(f"--floor-concurrency cannot exceed {MAX_FLOOR_CONCURRENCY}")
    if args.parallel_floors and args.resume_existing:
        parser.error("--parallel-floors cannot be combined with --resume-existing")
    if args.floor_number_offset < 0:
        parser.error("--floor-number-offset must be non-negative")
    if not 0 < args.max_wall_similarity <= 1:
        parser.error("--max-wall-similarity must be > 0 and <= 1")
    if not 0.1 <= args.wall_ratio_min <= 0.9 or not 0.1 <= args.wall_ratio_max <= 0.9:
        parser.error("--wall-ratio-min/max must be decimals between 0.1 and 0.9")
    if args.wall_ratio_min > args.wall_ratio_max:
        parser.error("--wall-ratio-min cannot exceed --wall-ratio-max")
    if args.monster_types_per_floor <= 0 or args.monster_types_per_floor > 30:
        parser.error("--monster-types-per-floor must be between 1 and 30")
    if args.max_specials_per_monster <= 0 or args.max_specials_per_monster > 3:
        parser.error("--max-specials-per-monster must be between 1 and 3")
    if not 0 <= args.floor_overlap_ratio <= 1:
        parser.error("--floor-overlap-ratio must be between 0 and 1")
    if args.special_damage_red_potion_min < 0 or args.special_damage_red_potion_max < 0:
        parser.error("--special-damage-red-potion-min/max must be non-negative")
    if args.special_damage_red_potion_min > args.special_damage_red_potion_max:
        parser.error("--special-damage-red-potion-min cannot exceed max")
    if args.gem_floor_delta_min < 0 or args.gem_floor_delta_max < 0:
        parser.error("--gem-floor-delta-min/max must be non-negative")
    if args.gem_floor_delta_min > args.gem_floor_delta_max:
        parser.error("--gem-floor-delta-min cannot exceed max")
    if args.potion_floor_delta_min < 0 or args.potion_floor_delta_max < 0:
        parser.error("--potion-floor-delta-min/max must be non-negative")
    if args.potion_floor_delta_min > args.potion_floor_delta_max:
        parser.error("--potion-floor-delta-min cannot exceed max")
    if args.high_value_pocket_threshold < 0:
        parser.error("--high-value-pocket-threshold must be non-negative")
    if args.enemy_design_count < 0:
        parser.error("--enemy-design-count must be non-negative")
    if args.agent_backend == "codex":
        if args.model is None:
            args.model = DEFAULT_CODEX_MODEL
        args.config = list(DEFAULT_CODEX_CONFIG) + (args.config or [])
    else:
        if args.profile:
            parser.error("--profile is only supported with --agent-backend codex")
        if args.config:
            parser.error("--config is only supported with --agent-backend codex; use --opencode-arg for OpenCode")
        if args.codex_arg:
            parser.error("--codex-arg is only supported with --agent-backend codex; use --opencode-arg for OpenCode")
        args.config = []
    if not args.self_test and not args.brief_file and not (args.idea_file or args.idea_text):
        parser.error("provide --idea-file or --idea-text, unless --brief-file is used")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            return self_test(args.repo_root.resolve())
        return run_pipeline(args)
    except (PipelineError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

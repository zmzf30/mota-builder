#!/usr/bin/env python3
"""Local zero-Node web UI for creating generated mota towers."""

from __future__ import annotations

import argparse
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import urlretrieve
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_mota_tower.py"
MOTA_ROOT = REPO_ROOT / "mota-js"
RUNS_DIR = REPO_ROOT / "build" / "ui-runs"
BRIEFS_DIR = REPO_ROOT / "build" / "ui-briefs"
PROMPTS_DIR = REPO_ROOT / "build" / "ui-prompts"
STATUS_FILENAME = "run_status.json"
LOG_FILENAME = "run.log"
LOCAL_MOTA_ZIPS = ["mota-js.zip", "mota-js 2.zip"]
MOTA_JS_ZIP_URL = "https://github.com/ckcz123/mota-js/archive/refs/heads/master.zip"
RUN_LOCK = threading.Lock()
RUN_PROCESSES: dict[str, subprocess.Popen[str]] = {}
CANCELLED_RUNS: set[str] = set()
LOG_TAIL_LINES = 80
ALLOWED_SPECIALS = {1, 2, 3, 15, 18}
TIMEOUT_OPTIONS = {10, 20, 30, 60, 90, 120}
RESUME_CONTROL_FIELDS = ("maxAttempts", "agentBackend", "timeoutMinutes")
STAGE_LABELS = {
    "topology": "地图结构",
    "economy": "资源和路线",
    "monster": "怪物和战斗",
    "integration": "整体",
}


def floor_label(raw_index: str) -> str:
    try:
        index = int(raw_index) + 1
    except ValueError:
        return f"第 {raw_index} 层"
    return f"第 {index} 层"


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
    if "gem count progression" in lower or "potion" in lower and "progression" in lower:
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


def beginner_log_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return line
    integration_match = re.match(
        r"^MT(\d+) integration review failed on attempt (\d+);\s*"
        r"repair will restart at ([^:]+):\s*(.*)$",
        stripped,
        re.IGNORECASE,
    )
    if integration_match:
        floor, attempt, repair_stage, summary = integration_match.groups()
        repair_label = STAGE_LABELS.get(repair_stage, repair_stage)
        return (
            f"{floor_label(floor)}第 {attempt} 次检查没通过，"
            f"正在从{repair_label}重新调整。{beginner_review_reason(summary)}"
        )

    stage_match = re.match(r"^MT(\d+) (\w+) review failed on attempt (\d+):\s*(.*)$", stripped, re.IGNORECASE)
    if stage_match:
        floor, stage, attempt, summary = stage_match.groups()
        stage_label = STAGE_LABELS.get(stage, stage)
        return (
            f"{floor_label(floor)}第 {attempt} 次{stage_label}检查没通过，"
            f"正在自动重试。{beginner_review_reason(summary)}"
        )

    forced_match = re.match(r"^MT(\d+) forced accepted.*review skipped", stripped, re.IGNORECASE)
    if forced_match:
        return f"{floor_label(forced_match.group(1))}已保存，但质量需要生成结束后手动看一下。"
    generated_forced_match = re.match(r"^MT(\d+) generated with forced acceptance", stripped, re.IGNORECASE)
    if generated_forced_match:
        return f"{floor_label(generated_forced_match.group(1))}已保存，但建议生成结束后手动微调。"
    passed_match = re.match(r"^MT(\d+) passed review", stripped, re.IGNORECASE)
    if passed_match:
        return f"{floor_label(passed_match.group(1))}检查通过。"
    parallel_match = re.match(r"^Parallel floor generation enabled with (\d+) worker", stripped, re.IGNORECASE)
    if parallel_match:
        return f"已开始同时生成 {parallel_match.group(1)} 个楼层。"
    enemy_match = re.match(r"^Enemy data agent designed (\d+) monster slot", stripped, re.IGNORECASE)
    if enemy_match:
        return f"已设计 {enemy_match.group(1)} 个怪物数据。"
    if stripped.startswith("Build complete:"):
        return "生成完成：" + stripped.split(":", 1)[1].strip()
    if stripped.startswith("Generated project:"):
        return "可游玩项目已生成：" + stripped.split(":", 1)[1].strip()
    if stripped.lower().startswith("error:"):
        return "出错：" + stripped.split(":", 1)[1].strip()
    saved_cn_match = re.match(r"^MT(\d+)\s+已保存", stripped)
    if saved_cn_match:
        return f"{floor_label(saved_cn_match.group(1))}已保存，质量需要手动检查。"
    passed_cn_match = re.match(r"^MT(\d+)\s+已通过审查", stripped)
    if passed_cn_match:
        return f"{floor_label(passed_cn_match.group(1))}检查通过。"
    return line


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_int(value: Any, default: int, minimum: int = 0, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(parsed, minimum)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def safe_float(value: Any, default: float, minimum: float = 0.0, maximum: float | None = None) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(parsed, minimum)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def form_value(form: dict[str, Any], key: str, default: Any = None) -> Any:
    return form.get(key, default)


def bool_field(form: dict[str, Any], key: str, default: bool = False) -> bool:
    raw = form.get(key, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return raw != 0
    return default


def int_field(
    form: dict[str, Any],
    key: str,
    label: str,
    default: int,
    minimum: int,
    maximum: int | None,
    errors: list[str],
) -> int:
    raw = form.get(key, default)
    if raw in (None, ""):
        raw = default
    value: int | None = None
    if isinstance(raw, bool):
        value = None
    elif isinstance(raw, int):
        value = raw
    elif isinstance(raw, float) and raw.is_integer():
        value = int(raw)
    elif isinstance(raw, str) and re.fullmatch(r"\d+", raw.strip()):
        value = int(raw.strip())
    if value is None:
        errors.append(f"{label}必须是整数。")
        return default
    if value < minimum:
        errors.append(f"{label}不能小于 {minimum}。")
    if maximum is not None and value > maximum:
        errors.append(f"{label}不能大于 {maximum}。")
    return value


def float_field(
    form: dict[str, Any],
    key: str,
    label: str,
    default: float,
    minimum: float,
    maximum: float | None,
    errors: list[str],
) -> float:
    raw = form.get(key, default)
    if raw in (None, ""):
        raw = default
    value: float | None = None
    if isinstance(raw, bool):
        value = None
    elif isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        try:
            value = float(raw.strip())
        except ValueError:
            value = None
    if value is None or not math.isfinite(value):
        errors.append(f"{label}必须是数字。")
        return default
    if value < minimum:
        errors.append(f"{label}不能小于 {minimum:g}。")
    if maximum is not None and value > maximum:
        errors.append(f"{label}不能大于 {maximum:g}。")
    return value


def normalize_form(form: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    floors = int_field(form, "floors", "楼层数", 4, 1, 20, errors)
    floor_size = int_field(form, "floorSize", "地图尺寸", 13, 13, 13, errors)
    if floor_size != 13:
        errors.append("地图尺寸固定为 13x13。")

    defaults = default_resources(floors)
    normalized: dict[str, Any] = {
        "floors": floors,
        "floorSize": 13,
        "hp": int_field(form, "hp", "HP", 300, 1, None, errors),
        "atk": int_field(form, "atk", "ATK", 10, 0, None, errors),
        "defense": int_field(form, "defense", "DEF", 10, 0, None, errors),
        "initialPickaxe": int_field(form, "initialPickaxe", "初始破墙镐", 0, 0, None, errors),
        "initialCenterFly": int_field(form, "initialCenterFly", "初始中心对称飞行器", 0, 0, None, errors),
        "initialBomb": int_field(form, "initialBomb", "初始炸弹", 0, 0, None, errors),
        "initialJumpShoes": int_field(form, "initialJumpShoes", "初始跳跃靴", 0, 0, None, errors),
        "initialYellowKey": int_field(form, "initialYellowKey", "初始黄钥匙", 0, 0, None, errors),
        "initialBlueKey": int_field(form, "initialBlueKey", "初始蓝钥匙", 0, 0, None, errors),
        "yellowDoors": int_field(form, "yellowDoors", "黄门", defaults["yellowDoors"], 0, None, errors),
        "blueDoors": int_field(form, "blueDoors", "蓝门", defaults["blueDoors"], 0, None, errors),
        "yellowKeys": int_field(form, "yellowKeys", "黄钥匙", defaults["yellowKeys"], 0, None, errors),
        "blueKeys": int_field(form, "blueKeys", "蓝钥匙", defaults["blueKeys"], 0, None, errors),
        "pickaxes": int_field(form, "pickaxes", "破墙镐", defaults["pickaxes"], 0, None, errors),
        "bombs": int_field(form, "bombs", "炸弹", defaults["bombs"], 0, None, errors),
        "centerFly": int_field(form, "centerFly", "中心对称飞行器", defaults["centerFly"], 0, None, errors),
        "jumpShoes": int_field(form, "jumpShoes", "跳跃靴", defaults["jumpShoes"], 0, None, errors),
        "redGems": int_field(form, "redGems", "红宝石数量", defaults["redGems"], 0, None, errors),
        "blueGems": int_field(form, "blueGems", "蓝宝石数量", defaults["blueGems"], 0, None, errors),
        "greenGems": int_field(form, "greenGems", "绿宝石数量", defaults["greenGems"], 0, None, errors),
        "redPotions": int_field(form, "redPotions", "红血瓶数量", defaults["redPotions"], 0, None, errors),
        "bluePotions": int_field(form, "bluePotions", "蓝血瓶数量", defaults["bluePotions"], 0, None, errors),
        "yellowPotions": int_field(form, "yellowPotions", "黄血瓶数量", defaults["yellowPotions"], 0, None, errors),
        "greenPotions": int_field(form, "greenPotions", "绿血瓶数量", defaults["greenPotions"], 0, None, errors),
        "redGem": int_field(form, "redGem", "红宝石 ATK", 1, 0, None, errors),
        "blueGem": int_field(form, "blueGem", "蓝宝石 DEF", 1, 0, None, errors),
        "greenGem": int_field(form, "greenGem", "绿宝石 MDEF", 5, 0, None, errors),
        "redPotion": int_field(form, "redPotion", "红血瓶 HP", 100, 0, None, errors),
        "bluePotion": int_field(form, "bluePotion", "蓝血瓶 HP", 200, 0, None, errors),
        "yellowPotion": int_field(form, "yellowPotion", "黄血瓶 HP", 300, 0, None, errors),
        "greenPotion": int_field(form, "greenPotion", "绿血瓶 HP", 400, 0, None, errors),
        "maxAttempts": int_field(form, "maxAttempts", "最大尝试次数", 4, 1, 10, errors),
        "floorConcurrency": int_field(form, "floorConcurrency", "并发数", min(4, floors), 1, 4, errors),
        "enemyMin": int_field(form, "enemyMin", "每层怪物数量下限", 22, 1, 60, errors),
        "enemyMax": int_field(form, "enemyMax", "每层怪物数量上限", 33, 1, 60, errors),
        "maxWallSimilarity": float_field(form, "maxWallSimilarity", "层相似度上限", 0.9, 0.1, 1.0, errors),
        "wallRatioMin": float_field(form, "wallRatioMin", "墙比例下限", 0.45, 0.1, 0.9, errors),
        "wallRatioMax": float_field(form, "wallRatioMax", "墙比例上限", 0.65, 0.1, 0.9, errors),
        "monsterTypesPerFloor": int_field(form, "monsterTypesPerFloor", "每层怪物种类上限", 12, 1, 30, errors),
        "maxSpecialsPerMonster": int_field(form, "maxSpecialsPerMonster", "每怪特殊能力上限", 1, 1, 3, errors),
        "floorOverlapRatio": float_field(form, "floorOverlapRatio", "楼层怪物重叠率", 0.7, 0.0, 1.0, errors),
        "specialDamageMin": float_field(form, "specialDamageMin", "领域/阻击伤害下限倍率", 0.5, 0.0, None, errors),
        "specialDamageMax": float_field(form, "specialDamageMax", "领域/阻击伤害上限倍率", 1.0, 0.0, None, errors),
        "gemFloorDeltaMin": float_field(form, "gemFloorDeltaMin", "宝石跨层增长下限", 0.0, 0.0, 10.0, errors),
        "gemFloorDeltaMax": float_field(form, "gemFloorDeltaMax", "宝石跨层增长上限", 2.0, 0.0, 10.0, errors),
        "potionFloorDeltaMin": float_field(form, "potionFloorDeltaMin", "药水跨层增长下限", 0.0, 0.0, 10.0, errors),
        "potionFloorDeltaMax": float_field(form, "potionFloorDeltaMax", "药水跨层增长上限", 2.0, 0.0, 10.0, errors),
        "highValuePocketThreshold": float_field(form, "highValuePocketThreshold", "高价值口袋阈值", 3.0, 0.0, 20.0, errors),
        "enemyDesignCount": int_field(form, "enemyDesignCount", "怪物表重写槽位数", 0, 0, 200, errors),
        "timeoutMinutes": int_field(form, "timeoutMinutes", "超时时间", 30, 10, 120, errors),
        "description": str(form.get("description") or "").strip(),
        "agentBackend": str(form.get("agentBackend") or "codex"),
        "resumeExisting": bool_field(form, "resumeExisting", False),
        "noAdjacentEnemies": bool_field(form, "noAdjacentEnemies", True),
    }
    red_potion_base = max(float(normalized["redPotion"]), 1.0)
    if "specialDamageValueMin" in form or "specialDamageValueMax" in form:
        special_value_min = float_field(
            form,
            "specialDamageValueMin",
            "领域/阻击伤害下限",
            normalized["redPotion"] * 0.5,
            0.0,
            None,
            errors,
        )
        special_value_max = float_field(
            form,
            "specialDamageValueMax",
            "领域/阻击伤害上限",
            normalized["redPotion"],
            0.0,
            None,
            errors,
        )
        normalized["specialDamageValueMin"] = special_value_min
        normalized["specialDamageValueMax"] = special_value_max
        normalized["specialDamageMin"] = special_value_min / red_potion_base
        normalized["specialDamageMax"] = special_value_max / red_potion_base
    else:
        normalized["specialDamageValueMin"] = normalized["specialDamageMin"] * red_potion_base
        normalized["specialDamageValueMax"] = normalized["specialDamageMax"] * red_potion_base
    if normalized["floorConcurrency"] > floors:
        errors.append("并发数不能高于楼层数。")
    if normalized["enemyMin"] > normalized["enemyMax"]:
        errors.append("每层怪物数量下限不能大于上限。")
    if normalized["wallRatioMin"] > normalized["wallRatioMax"]:
        errors.append("墙比例下限不能大于上限。")
    if normalized["specialDamageMin"] > normalized["specialDamageMax"]:
        errors.append("领域/阻击伤害下限不能大于上限。")
    if normalized["gemFloorDeltaMin"] > normalized["gemFloorDeltaMax"]:
        errors.append("宝石跨层增长下限不能大于上限。")
    if normalized["potionFloorDeltaMin"] > normalized["potionFloorDeltaMax"]:
        errors.append("药水跨层增长下限不能大于上限。")
    if normalized["agentBackend"] not in {"codex", "opencode"}:
        errors.append("Agent 只能选择 codex 或 opencode。")
    if normalized["timeoutMinutes"] not in TIMEOUT_OPTIONS:
        errors.append("超时时间只能选择 10、20、30、60、90、120 分钟。")

    raw_specials = form.get("allowedSpecials", [1, 2, 3, 15, 18])
    if not isinstance(raw_specials, list):
        raw_specials = []
    specials: list[int] = []
    for raw in raw_specials:
        if isinstance(raw, bool):
            continue
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if value in ALLOWED_SPECIALS and value not in specials:
            specials.append(value)
    if not specials:
        errors.append("至少选择一个怪物能力。")
    normalized["allowedSpecials"] = specials

    if errors:
        raise ValueError("；".join(errors))
    return normalized


def default_resources(floors: int) -> dict[str, int]:
    return {
        "yellowDoors": floors * 4,
        "blueDoors": floors * 2,
        "yellowKeys": floors * 2,
        "blueKeys": floors,
        "pickaxes": floors,
        "bombs": floors,
        "centerFly": floors,
        "jumpShoes": 0,
        "redGems": floors * 5,
        "blueGems": floors * 5,
        "greenGems": 0,
        "redPotions": floors * 5,
        "bluePotions": floors * 2,
        "yellowPotions": 0,
        "greenPotions": 0,
    }


def build_brief(form: dict[str, Any]) -> dict[str, Any]:
    form = normalize_form(form)
    floors = safe_int(form_value(form, "floors"), 4, 1, 99)
    floor_size = safe_int(form_value(form, "floorSize"), 13, 9, 13)
    if floor_size not in {9, 11, 13}:
        floor_size = 13
    resources = default_resources(floors)
    allowed_specials = form_value(form, "allowedSpecials", [1, 2, 3, 15, 18])
    if not isinstance(allowed_specials, list):
        allowed_specials = [1, 2, 3, 15, 18]
    allowed_specials = [
        int(item)
        for item in allowed_specials
        if isinstance(item, (int, float)) and int(item) in {1, 2, 3, 15, 18}
    ]
    if not allowed_specials:
        raise ValueError("至少选择一个怪物能力。")

    description = str(form_value(form, "description", "") or "").strip()
    enemy_min = safe_int(form_value(form, "enemyMin"), 22, 0, 120)
    enemy_max = safe_int(form_value(form, "enemyMax"), 33, enemy_min, 160)
    wall_ratio_min = safe_float(form_value(form, "wallRatioMin"), 0.45, 0.1, 0.9)
    wall_ratio_max = safe_float(form_value(form, "wallRatioMax"), 0.65, wall_ratio_min, 0.9)
    special_damage_min = safe_float(form_value(form, "specialDamageMin"), 0.5, 0.0)
    special_damage_max = safe_float(form_value(form, "specialDamageMax"), 1.0, special_damage_min)
    gem_delta_min = safe_float(form_value(form, "gemFloorDeltaMin"), 0.0, 0.0, 10.0)
    gem_delta_max = safe_float(form_value(form, "gemFloorDeltaMax"), 2.0, gem_delta_min, 10.0)
    potion_delta_min = safe_float(form_value(form, "potionFloorDeltaMin"), 0.0, 0.0, 10.0)
    potion_delta_max = safe_float(form_value(form, "potionFloorDeltaMax"), 2.0, potion_delta_min, 10.0)

    global_limits = {
        "yellow_doors": safe_int(form_value(form, "yellowDoors"), resources["yellowDoors"], 0),
        "blue_doors": safe_int(form_value(form, "blueDoors"), resources["blueDoors"], 0),
        "red_doors": 0,
        "yellow_keys": safe_int(form_value(form, "yellowKeys"), resources["yellowKeys"], 0),
        "blue_keys": safe_int(form_value(form, "blueKeys"), resources["blueKeys"], 0),
        "red_keys": 0,
        "pickaxes": safe_int(form_value(form, "pickaxes"), resources["pickaxes"], 0),
        "bombs": safe_int(form_value(form, "bombs"), resources["bombs"], 0),
        "centerFly": safe_int(form_value(form, "centerFly"), resources["centerFly"], 0),
        "jumpShoes": safe_int(form_value(form, "jumpShoes"), resources["jumpShoes"], 0),
        "redGems": safe_int(form_value(form, "redGems"), resources["redGems"], 0),
        "blueGems": safe_int(form_value(form, "blueGems"), resources["blueGems"], 0),
        "greenGems": safe_int(form_value(form, "greenGems"), resources["greenGems"], 0),
        "redPotions": safe_int(form_value(form, "redPotions"), resources["redPotions"], 0),
        "bluePotions": safe_int(form_value(form, "bluePotions"), resources["bluePotions"], 0),
        "yellowPotions": safe_int(form_value(form, "yellowPotions"), resources["yellowPotions"], 0),
        "greenPotions": safe_int(form_value(form, "greenPotions"), resources["greenPotions"], 0),
    }
    initial_tools = {
        "pickaxe": safe_int(form_value(form, "initialPickaxe"), 0, 0),
        "bomb": safe_int(form_value(form, "initialBomb"), 0, 0),
        "centerFly": safe_int(form_value(form, "initialCenterFly"), 0, 0),
        "jumpShoes": safe_int(form_value(form, "initialJumpShoes"), 0, 0),
    }
    fixed_rules = [
        f"{floor_size}x{floor_size} floors",
        f"{floors} floors",
        "traditional key-door route pressure",
        "low story; prioritize playable routes, resource pressure, and branch choices",
        "do not use red doors or red keys unless the user later adds them explicitly",
    ]
    if description:
        fixed_rules.append(description)

    special_names = {
        1: "先攻",
        2: "魔攻",
        3: "坚固",
        15: "领域",
        18: "阻击",
    }
    special_summary = "、".join(f"{item}{special_names[item]}" for item in allowed_specials)
    summary_parts = [
        f"{floors}层 {floor_size}x{floor_size} 传统魔塔",
        f"初始 HP {safe_int(form_value(form, 'hp'), 300, 1)} / ATK {safe_int(form_value(form, 'atk'), 10, 0)} / DEF {safe_int(form_value(form, 'defense'), 10, 0)}",
        (
            f"整塔资源：黄门 {global_limits['yellow_doors']}、蓝门 {global_limits['blue_doors']}、"
            f"黄钥匙 {global_limits['yellow_keys']}、蓝钥匙 {global_limits['blue_keys']}、"
            f"红宝石 {global_limits['redGems']}、蓝宝石 {global_limits['blueGems']}、"
            f"红血瓶 {global_limits['redPotions']}、蓝血瓶 {global_limits['bluePotions']}"
        ),
        f"允许怪物能力：{special_summary}",
    ]
    if description:
        summary_parts.append(description)

    return {
        "status": "ready",
        "summary": "；".join(summary_parts),
        "floor_count": floors,
        "floor_size": floor_size,
        "fixed_rules": fixed_rules,
        "global_limits": global_limits,
        "global_settings": {
            "initial_hero": {
                "hp": safe_int(form_value(form, "hp"), 300, 1),
                "atk": safe_int(form_value(form, "atk"), 10, 0),
                "def": safe_int(form_value(form, "defense"), 10, 0),
                "money": 0,
                "keys": {
                    "yellow": safe_int(form_value(form, "initialYellowKey"), 0, 0),
                    "blue": safe_int(form_value(form, "initialBlueKey"), 0, 0),
                    "red": 0,
                },
                "tools": initial_tools,
            },
            "gems": {
                "redGem": safe_int(form_value(form, "redGem"), 1, 0),
                "blueGem": safe_int(form_value(form, "blueGem"), 1, 0),
                "greenGem": safe_int(form_value(form, "greenGem"), 5, 0),
            },
            "potions": {
                "redPotion": safe_int(form_value(form, "redPotion"), 100, 0),
                "bluePotion": safe_int(form_value(form, "bluePotion"), 200, 0),
                "yellowPotion": safe_int(form_value(form, "yellowPotion"), 300, 0),
                "greenPotion": safe_int(form_value(form, "greenPotion"), 400, 0),
            },
            "shop": {
                "enabled": False,
                "rule": "",
                "atk_gain": None,
                "def_gain": None,
            },
        },
        "monster_policy": {
            "allowed_specials": allowed_specials,
            "max_specials_per_monster": safe_int(form_value(form, "maxSpecialsPerMonster"), 1, 1, 3),
            "min_no_special_ratio": None,
            "monster_types_per_floor": safe_int(form_value(form, "monsterTypesPerFloor"), 12, 1, 30),
            "enemy_count_min_per_floor": enemy_min,
            "enemy_count_max_per_floor": enemy_max,
            "floor_overlap_ratio": safe_float(form_value(form, "floorOverlapRatio"), 0.7, 0.0, 1.0),
            "special_damage_red_potion_min": special_damage_min,
            "special_damage_red_potion_max": special_damage_max,
            "no_adjacent_enemies": bool_field(form, "noAdjacentEnemies", True),
        },
        "resource_policy": {
            "gem_floor_delta_min": gem_delta_min,
            "gem_floor_delta_max": gem_delta_max,
            "potion_floor_delta_min": potion_delta_min,
            "potion_floor_delta_max": potion_delta_max,
            "potion_compare_mode": "red_potion_equiv",
        },
        "layout_constraints": {
            "wall_ratio_min": wall_ratio_min,
            "wall_ratio_max": wall_ratio_max,
            "high_value_pocket_threshold": safe_float(form_value(form, "highValuePocketThreshold"), 3.0, 0.0, 20.0),
            "warning": "高级配置会作为生成和校验目标传入，但大模型输出不一定能完全遵循。",
        },
        "layout_policy": [
            "每层至少 3 条可感知分支路线",
            "楼层之间拓扑结构要明显不同",
            "用门、怪物、破墙镐、炸弹和中心对称飞行器制造资源取舍",
        ],
        "questions": [],
        "confirmation_prompt": "确认这个全塔 brief 后开始生成整座塔。",
    }


def build_idea_prompt(form: dict[str, Any]) -> str:
    form = normalize_form(form)
    special_names = {1: "先攻", 2: "魔攻", 3: "坚固", 15: "领域", 18: "阻击"}
    specials = "、".join(f"{item}{special_names[item]}" for item in form["allowedSpecials"])
    description = form["description"] or "无"
    return f"""我想直接一步生成一座 {form['floors']} 层、13x13、低剧情、传统钥匙门博弈的魔塔。

请严格使用以下参数，不要自行改动规模和数值口径：

规模：
- 楼层数：{form['floors']}
- 地图尺寸：13x13

初始勇士：
- HP={form['hp']}
- ATK={form['atk']}
- DEF={form['defense']}
- 初始破墙镐={form['initialPickaxe']}
- 初始中心对称飞行器={form['initialCenterFly']}
- 初始炸弹={form['initialBomb']}
- 初始跳跃靴={form['initialJumpShoes']}
- 初始黄钥匙={form['initialYellowKey']}
- 初始蓝钥匙={form['initialBlueKey']}

整塔资源总量：
- 黄门={form['yellowDoors']}
- 蓝门={form['blueDoors']}
- 黄钥匙={form['yellowKeys']}
- 蓝钥匙={form['blueKeys']}
- 破墙镐={form['pickaxes']}
- 炸弹={form['bombs']}
- 中心对称飞行器={form['centerFly']}
- 跳跃靴={form['jumpShoes']}
- 红宝石={form['redGems']}
- 蓝宝石={form['blueGems']}
- 绿宝石={form['greenGems']}
- 红血瓶={form['redPotions']}
- 蓝血瓶={form['bluePotions']}
- 黄血瓶={form['yellowPotions']}
- 绿血瓶={form['greenPotions']}
- 红门=0
- 红钥匙=0

道具数值：
- 红宝石：ATK +{form['redGem']}
- 蓝宝石：DEF +{form['blueGem']}
- 绿宝石：MDEF +{form['greenGem']}
- 红血瓶：HP +{form['redPotion']}
- 蓝血瓶：HP +{form['bluePotion']}
- 黄血瓶：HP +{form['yellowPotion']}
- 绿血瓶：HP +{form['greenPotion']}

怪物约束：
- 怪物能力白名单：{specials}
- 每层怪物数量范围：{form['enemyMin']} 到 {form['enemyMax']}
- 每只怪物最多 {form['maxSpecialsPerMonster']} 个特殊能力
- {"避免正交相邻怪物" if form['noAdjacentEnemies'] else "允许少量正交相邻怪物"}
- 怪物 HP/ATK/DEF/金币/特殊属性由生成脚本的怪物数据 Agent 重新设计；只复用现有怪物 id 和素材槽位，不沿用样板默认怪物数值
- 每层可用怪物种类上限：{form['monsterTypesPerFloor']}
- 相邻楼层怪物池重叠率目标：{form['floorOverlapRatio']:.2f}
- 领域/阻击伤害范围：{form['specialDamageValueMin']:g} 到 {form['specialDamageValueMax']:g}

布局和体验：
- 每层至少 3 条可感知分支路线
- 楼层之间墙体结构要明显不同，相邻楼层墙体相似度必须低于 {form['maxWallSimilarity']:.2f}
- 13x13 拓扑墙比例目标：{form['wallRatioMin']:.2f} 到 {form['wallRatioMax']:.2f}
- 上述高级配置会作为生成和校验目标传入，但由于大模型不确定性，生成结果不一定能完全遵循，需要生成后手动查看和调整
- 重点体现门钥匙博弈、路线选择、资源取舍、战斗压力
- 不做复杂剧情、Boss 事件、自定义脚本或特殊图块

补充描述：
{description}
"""


def build_command(
    output_dir: Path,
    input_path: Path,
    form: dict[str, Any],
    input_mode: str = "idea",
) -> list[str]:
    form = normalize_form(form)
    floors = form["floors"]
    floor_size = form["floorSize"]
    max_attempts = form["maxAttempts"]
    concurrency = form["floorConcurrency"]
    timeout_minutes = form["timeoutMinutes"]
    backend = form["agentBackend"]
    max_wall_similarity = form["maxWallSimilarity"]

    cmd = [
        sys.executable,
        str(BUILD_SCRIPT),
        "--brief-file" if input_mode == "brief" else "--idea-file",
        str(input_path),
        "--yes",
        "--skip-playtest",
        "--repo-root",
        str(REPO_ROOT),
        "--out-dir",
        str(output_dir),
        "--max-attempts",
        str(max_attempts),
        "--agent-backend",
        backend,
        "--timeout",
        str(timeout_minutes * 60),
        "--max-wall-similarity",
        str(max_wall_similarity),
        "--wall-ratio-min",
        str(form["wallRatioMin"]),
        "--wall-ratio-max",
        str(form["wallRatioMax"]),
        "--monster-types-per-floor",
        str(form["monsterTypesPerFloor"]),
        "--max-specials-per-monster",
        str(form["maxSpecialsPerMonster"]),
        "--floor-overlap-ratio",
        str(form["floorOverlapRatio"]),
        "--special-damage-red-potion-min",
        str(form["specialDamageMin"]),
        "--special-damage-red-potion-max",
        str(form["specialDamageMax"]),
        "--gem-floor-delta-min",
        str(form["gemFloorDeltaMin"]),
        "--gem-floor-delta-max",
        str(form["gemFloorDeltaMax"]),
        "--potion-floor-delta-min",
        str(form["potionFloorDeltaMin"]),
        "--potion-floor-delta-max",
        str(form["potionFloorDeltaMax"]),
        "--high-value-pocket-threshold",
        str(form["highValuePocketThreshold"]),
        "--enemy-design-count",
        str(form["enemyDesignCount"]),
    ]
    if not form["noAdjacentEnemies"]:
        cmd.append("--allow-adjacent-enemies")
    if form["resumeExisting"]:
        cmd.append("--resume-existing")
    else:
        cmd.extend(["--clean", "--floors", str(floors), "--floor-size", str(floor_size)])
    if concurrency > 1 and not form["resumeExisting"]:
        cmd.extend(["--parallel-floors", "--floor-concurrency", str(concurrency)])
    return cmd


def status_path(run_dir: Path) -> Path:
    return run_dir / STATUS_FILENAME


def log_path(run_dir: Path) -> Path:
    return run_dir / LOG_FILENAME


def output_dir_for(run_dir: Path) -> Path:
    return run_dir / "output"


def project_dir_for(run_dir: Path) -> Path:
    return output_dir_for(run_dir) / "project"


def status_payload(run_id: str, run_dir: Path, reconcile_process: bool = False) -> dict[str, Any]:
    status_file = status_path(run_dir)
    if not status_file.exists():
        raise FileNotFoundError("run not found")
    status = read_json(status_file)
    status.setdefault("run_id", run_id)
    status["logs"] = log_tail(log_path(run_dir))
    if isinstance(status.get("message"), str):
        status["message"] = beginner_log_line(status["message"])
    if reconcile_process:
        status = reconcile_run_status(run_id, run_dir, status)
    return status


def find_latest_resumable_run() -> tuple[str, Path, dict[str, Any]]:
    if not RUNS_DIR.exists():
        raise ValueError("没有找到可继续的生成记录。")
    candidates = sorted(
        [path for path in RUNS_DIR.iterdir() if path.is_dir()],
        key=lambda path: path.name,
        reverse=True,
    )
    for run_dir in candidates:
        run_id = run_dir.name
        with RUN_LOCK:
            if run_id in RUN_PROCESSES:
                continue
        brief_path = output_dir_for(run_dir) / "tower_brief.json"
        floors_dir = output_dir_for(run_dir) / "floors"
        if not brief_path.exists() or not floors_dir.exists():
            continue
        try:
            brief = read_json(brief_path)
        except (OSError, json.JSONDecodeError):
            continue
        if brief.get("status") == "ready":
            return run_id, run_dir, brief
    raise ValueError("没有找到可继续的生成记录。")


def load_request_form(run_dir: Path) -> dict[str, Any] | None:
    request_path = run_dir / "request.json"
    if not request_path.exists():
        return None
    try:
        request = read_json(request_path)
    except (OSError, json.JSONDecodeError):
        return None
    form = request.get("form")
    return form if isinstance(form, dict) else None


def build_resume_command_form(run_dir: Path, current_form: dict[str, Any]) -> dict[str, Any]:
    original_form = load_request_form(run_dir) or current_form
    merged = dict(original_form)
    for key in RESUME_CONTROL_FIELDS:
        merged[key] = current_form[key]
    merged["resumeExisting"] = True
    return normalize_form(merged)


def update_status(run_dir: Path, **changes: Any) -> dict[str, Any]:
    with RUN_LOCK:
        run_id = str(changes.get("run_id") or run_dir.name)
        if run_id in CANCELLED_RUNS:
            return {}
        path = status_path(run_dir)
        status = read_json(path) if path.exists() else {}
        status.update(changes)
        status["updated_at"] = datetime.now().isoformat(timespec="seconds")
        write_json(path, status)
        return status


def log_tail(path: Path, limit: int = LOG_TAIL_LINES) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [beginner_log_line(line) for line in lines[-limit:]]


def parse_progress(line: str, floors: int, current: float) -> tuple[float, str | None]:
    message = None
    progress = current
    simple_line = beginner_log_line(line)
    if "Tower brief summary" in line:
        return max(progress, 8), "brief 已确认"
    if "Enemy data agent designed" in line or "怪物数据" in simple_line and "已设计" in simple_line:
        return max(progress, 10), "怪物数据已设计"
    if "Parallel floor generation enabled" in line or "已开始同时生成" in simple_line:
        return max(progress, 12), "并发楼层生成已开始"
    if "passed review" in line or "forced accepted" in line or "generated with forced acceptance" in line:
        for index in range(floors):
            if f"MT{index} " in line or f"MT{index} passed" in line:
                done = index + 1
                progress = max(progress, 15 + done / max(floors, 1) * 70)
                if "forced" in line:
                    message = f"第 {index + 1} 层已保存，质量需要手动检查"
                else:
                    message = f"第 {index + 1} 层检查通过"
                break
    if "检查通过" in simple_line:
        floor_match = re.search(r"第\s*(\d+)\s*层", simple_line)
        if floor_match:
            done = int(floor_match.group(1))
            progress = max(progress, 15 + done / max(floors, 1) * 70)
            message = simple_line.strip()[:240]
    if "Build complete" in line or simple_line.startswith("生成完成："):
        return 100, "生成完成"
    if "failed" in line.lower() or "error:" in line.lower() or "没通过" in simple_line or "出错：" in simple_line:
        message = simple_line.strip()[:240]
    return progress, message


def run_build_worker(run_id: str, run_dir: Path, output_dir: Path, cmd: list[str], floors: int) -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    update_status(
        run_dir,
        run_id=run_id,
        state="running",
        progress=2,
        message="生成进程已启动",
        command=cmd,
        out_dir=str(output_dir),
        log_path=str(log_path(run_dir)),
    )
    progress = 2.0
    log_file = log_path(run_dir)
    try:
        with log_file.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                cmd,
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                start_new_session=True,
            )
            with RUN_LOCK:
                RUN_PROCESSES[run_id] = process
            assert process.stdout is not None
            for raw_line in process.stdout:
                log.write(raw_line)
                log.flush()
                progress, message = parse_progress(raw_line, floors, progress)
                if message:
                    update_status(run_dir, progress=round(progress, 1), message=message)
            return_code = process.wait()
        with RUN_LOCK:
            RUN_PROCESSES.pop(run_id, None)
        if run_id in CANCELLED_RUNS:
            cleanup_run(run_id, run_dir)
            return
        summary_file = output_dir / "summary.json"
        project_dir = output_dir / "project"
        payload: dict[str, Any] = {
            "return_code": return_code,
            "logs": log_tail(log_file),
            "summary_path": str(summary_file) if summary_file.exists() else None,
            "project_dir": str(project_dir) if project_dir.exists() else None,
        }
        if return_code == 0:
            summary = read_json(summary_file) if summary_file.exists() else {}
            forced = any(bool(item.get("forced_accept")) for item in summary.get("floors", [])) if summary else False
            final_validation = summary.get("final_validation", {}) if isinstance(summary, dict) else {}
            completion_message = (
                "生成完成；部分楼层为最后一轮强制保存，质量可能需要手动调整"
                if forced or final_validation.get("status") == "warn"
                else "生成完成"
            )
            payload.update(
                {
                    "state": "complete",
                    "progress": 100,
                    "message": completion_message,
                    "play_url": f"/play/{run_id}/index.html",
                    "editor_url": f"/play/{run_id}/editor.html",
                    "export_url": f"/api/export?run_id={run_id}",
                }
            )
            if summary:
                payload["summary"] = summary
        else:
            payload.update(
                {
                    "state": "error",
                    "progress": max(progress, 5),
                    "message": "生成进程结束，但没有通过完整流水线。已保留当前输出目录。",
                }
            )
        update_status(run_dir, **payload)
    except Exception as exc:  # noqa: BLE001 - surface errors in UI.
        with RUN_LOCK:
            RUN_PROCESSES.pop(run_id, None)
        if run_id in CANCELLED_RUNS:
            cleanup_run(run_id, run_dir)
            return
        update_status(
            run_dir,
            state="error",
            progress=max(progress, 5),
            message=str(exc),
            logs=log_tail(log_file),
        )


def make_run_id() -> str:
    for suffix in range(1000):
        base = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        candidate = base if suffix == 0 else f"{base}-{suffix}"
        if not run_dir_for(candidate).exists():
            return candidate
    raise RuntimeError("cannot allocate run id")


def run_dir_for(run_id: str) -> Path:
    if not run_id or "/" in run_id or ".." in run_id:
        raise ValueError("invalid run_id")
    return RUNS_DIR / run_id


def cleanup_run(run_id: str, run_dir: Path) -> None:
    status_file = status_path(run_dir)
    paths: list[Path] = []
    if status_file.exists():
        try:
            status = read_json(status_file)
        except (OSError, json.JSONDecodeError):
            status = {}
        for key in ("brief_path", "idea_path"):
            value = status.get(key)
            if isinstance(value, str):
                paths.append(Path(value))
    paths.extend(
        [
            BRIEFS_DIR / f"{run_id}.tower_brief.json",
            PROMPTS_DIR / f"{run_id}.idea.txt",
        ]
    )
    for path in paths:
        try:
            resolved = path.resolve()
            allowed_roots = [BRIEFS_DIR.resolve(), PROMPTS_DIR.resolve()]
            if any(resolved == root or root in resolved.parents for root in allowed_roots):
                path.unlink(missing_ok=True)
        except OSError:
            pass
    shutil.rmtree(run_dir, ignore_errors=True)


def discover_run_process_groups(run_id: str, run_dir: Path) -> set[int]:
    try:
        run_root = str(run_dir.resolve())
        output_root = str(output_dir_for(run_dir).resolve())
    except OSError:
        run_root = str(run_dir)
        output_root = str(output_dir_for(run_dir))
    current_pid = os.getpid()
    current_pgid = os.getpgrp()
    groups: set[int] = set()
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,pgid=,command="],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return groups
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) != 3:
            continue
        try:
            pid = int(parts[0])
            pgid = int(parts[1])
        except ValueError:
            continue
        command = parts[2]
        if pid == current_pid or pgid == current_pgid:
            continue
        if run_id not in command and run_root not in command and output_root not in command:
            continue
        if not any(marker in command for marker in ("build_mota_tower.py", "codex exec", "opencode")):
            continue
        groups.add(pgid)
    return groups


def process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return False
    return True


def terminate_process_groups(groups: set[int], timeout: float = 5.0) -> None:
    if not groups:
        return
    for pgid in groups:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            continue
    deadline = time.time() + timeout
    while time.time() < deadline and any(process_group_exists(pgid) for pgid in groups):
        time.sleep(0.1)
    for pgid in groups:
        if not process_group_exists(pgid):
            continue
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            continue


def run_has_live_process(run_id: str, run_dir: Path) -> bool:
    with RUN_LOCK:
        process = RUN_PROCESSES.get(run_id)
        if process is not None and process.poll() is None:
            return True
    return bool(discover_run_process_groups(run_id, run_dir))


def recovered_completion_payload(run_id: str, output_dir: Path) -> dict[str, Any] | None:
    summary_file = output_dir / "summary.json"
    project_dir = output_dir / "project"
    if not summary_file.exists() or not project_dir.exists():
        return None
    try:
        summary = read_json(summary_file)
    except (OSError, json.JSONDecodeError):
        summary = {}
    forced = any(bool(item.get("forced_accept")) for item in summary.get("floors", [])) if summary else False
    final_validation = summary.get("final_validation", {}) if isinstance(summary, dict) else {}
    completion_message = (
        "生成完成；部分楼层为最后一轮强制保存，质量可能需要手动调整"
        if forced or final_validation.get("status") == "warn"
        else "生成完成"
    )
    payload: dict[str, Any] = {
        "return_code": 0,
        "state": "complete",
        "progress": 100,
        "message": completion_message,
        "summary_path": str(summary_file),
        "project_dir": str(project_dir),
        "play_url": f"/play/{run_id}/index.html",
        "editor_url": f"/play/{run_id}/editor.html",
        "export_url": f"/api/export?run_id={run_id}",
    }
    if summary:
        payload["summary"] = summary
    return payload


def reconcile_run_status(run_id: str, run_dir: Path, status: dict[str, Any]) -> dict[str, Any]:
    state = str(status.get("state") or "")
    if state not in {"queued", "running"}:
        return status
    with RUN_LOCK:
        process = RUN_PROCESSES.get(run_id)
        if process is not None and process.poll() is None:
            return status
    if discover_run_process_groups(run_id, run_dir):
        status["detached"] = True
        status["message"] = "检测到后台生成进程仍在运行；可点击终止生成，进度日志可能不会继续更新。"
        return status
    completion_payload = recovered_completion_payload(run_id, output_dir_for(run_dir))
    if completion_payload is not None:
        status = update_status(run_dir, run_id=run_id, **completion_payload)
        status["logs"] = log_tail(log_path(run_dir))
        return status
    status = update_status(
        run_dir,
        run_id=run_id,
        state="error",
        progress=max(float(status.get("progress") or 0), 5),
        message="生成进程已停止或无法找到；请重新开始或继续上次未完成生成。",
    )
    status["logs"] = log_tail(log_path(run_dir))
    return status


def latest_run_status() -> dict[str, Any] | None:
    if not RUNS_DIR.exists():
        return None
    candidates = sorted(
        [path for path in RUNS_DIR.iterdir() if path.is_dir()],
        key=lambda path: path.name,
        reverse=True,
    )
    for run_dir in candidates:
        run_id = run_dir.name
        try:
            status = status_payload(run_id, run_dir, reconcile_process=True)
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            continue
        return status
    return None


def stop_run(run_id: str) -> bool:
    run_dir = run_dir_for(run_id)
    with RUN_LOCK:
        CANCELLED_RUNS.add(run_id)
        process = RUN_PROCESSES.get(run_id)
    groups = discover_run_process_groups(run_id, run_dir)
    if process is not None and process.poll() is None:
        try:
            groups.add(os.getpgid(process.pid))
        except OSError:
            groups.add(process.pid)
    terminate_process_groups(groups)
    if process is not None and process.poll() is None:
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)
    with RUN_LOCK:
        RUN_PROCESSES.pop(run_id, None)
    cleanup_run(run_id, run_dir)
    return True


def health_payload() -> dict[str, Any]:
    return {
        "mota_root": str(MOTA_ROOT),
        "mota_exists": MOTA_ROOT.exists(),
        "index_exists": (MOTA_ROOT / "index.html").exists(),
        "editor_exists": (MOTA_ROOT / "editor.html").exists(),
        "python": sys.version.split()[0],
        "node_required": False,
    }


def safe_extract_zip(zip_path: Path, target: Path) -> Path:
    extract_root = target.parent / f".{target.name}-extract-{int(time.time())}"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = extract_root / member.filename
            if not member_path.resolve().is_relative_to(extract_root.resolve()):
                raise ValueError(f"unsafe zip member: {member.filename}")
        archive.extractall(extract_root)
    candidates = [path for path in extract_root.iterdir() if path.is_dir()]
    source = candidates[0] if len(candidates) == 1 else extract_root
    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(source), str(target))
    shutil.rmtree(extract_root, ignore_errors=True)
    return target


def init_mota_js() -> dict[str, Any]:
    if (MOTA_ROOT / "index.html").exists() and (MOTA_ROOT / "editor.html").exists():
        payload = health_payload()
        payload["message"] = "mota-js 已存在。"
        return payload
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    local_zip = next((REPO_ROOT / name for name in LOCAL_MOTA_ZIPS if (REPO_ROOT / name).exists()), None)
    if local_zip is None:
        local_zip = RUNS_DIR / "mota-js-download.zip"
        urlretrieve(MOTA_JS_ZIP_URL, local_zip)
    safe_extract_zip(local_zip, MOTA_ROOT)
    payload = health_payload()
    payload["message"] = f"mota-js 初始化完成：{MOTA_ROOT}"
    return payload


def safe_join(root: Path, relative: str) -> Path:
    relative = unquote(relative).lstrip("/")
    target = (root / relative).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError("unsafe path")
    return target


class MotaBuilderHandler(BaseHTTPRequestHandler):
    server_version = "MotaBuilderUI/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), format % args))

    def send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, status: int = 200) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in {"/", "/new"}:
                self.send_file(WEB_ROOT / "new_tower.html")
            elif path in {"/new_tower.css", "/new_tower.js"}:
                self.send_file(WEB_ROOT / path.lstrip("/"))
            elif path == "/api/health":
                self.send_json(health_payload())
            elif path == "/api/status":
                query = parse_qs(parsed.query)
                run_id = (query.get("run_id") or [""])[0]
                run_dir = run_dir_for(run_id)
                try:
                    status = status_payload(run_id, run_dir, reconcile_process=True)
                except FileNotFoundError:
                    self.send_json({"state": "missing", "message": "run not found"}, 404)
                    return
                self.send_json(status)
            elif path == "/api/latest-run":
                status = latest_run_status()
                if status is None:
                    self.send_json({"state": "missing", "message": "run not found"}, 404)
                else:
                    self.send_json(status)
            elif path == "/api/export":
                self.handle_export(parsed.query)
            elif path.startswith("/play/"):
                self.handle_play(path)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:  # noqa: BLE001 - send API-visible failures.
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/brief":
                payload = self.read_body_json()
                form = payload.get("form", payload)
                if not isinstance(form, dict):
                    raise ValueError("form must be a JSON object")
                brief = build_brief(form)
                self.send_json({"brief": brief})
            elif parsed.path == "/api/prompt":
                payload = self.read_body_json()
                form = payload.get("form", payload)
                if not isinstance(form, dict):
                    raise ValueError("form must be a JSON object")
                prompt = build_idea_prompt(form)
                self.send_json({"prompt": prompt})
            elif parsed.path == "/api/run":
                payload = self.read_body_json()
                form = payload.get("form", payload)
                if not isinstance(form, dict):
                    raise ValueError("form must be a JSON object")
                normalized = normalize_form(form)
                if normalized["resumeExisting"]:
                    run_id, run_dir, existing_brief = find_latest_resumable_run()
                    input_path = output_dir_for(run_dir) / "tower_brief.json"
                    input_mode = "brief"
                    floor_count = int(existing_brief.get("floor_count") or normalized["floors"])
                    idea_path = None
                    command_form = build_resume_command_form(run_dir, normalized)
                else:
                    idea = build_idea_prompt(normalized)
                    run_id = make_run_id()
                    run_dir = run_dir_for(run_id)
                    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
                    idea_path = PROMPTS_DIR / f"{run_id}.idea.txt"
                    idea_path.write_text(idea + "\n", encoding="utf-8")
                    input_path = idea_path
                    input_mode = "idea"
                    floor_count = int(normalized["floors"])
                    command_form = normalized
                run_dir.mkdir(parents=True, exist_ok=True)
                request_payload = {
                    "form": normalized,
                    "command_form": command_form,
                    "idea_path": str(idea_path) if idea_path is not None else None,
                    "input_path": str(input_path),
                    "input_mode": input_mode,
                }
                if normalized["resumeExisting"]:
                    write_json(run_dir / "last_resume_request.json", request_payload)
                else:
                    write_json(run_dir / "request.json", request_payload)
                output_dir = output_dir_for(run_dir)
                cmd = build_command(output_dir, input_path, command_form, input_mode)
                write_json(
                    status_path(run_dir),
                    {
                        "run_id": run_id,
                        "state": "queued",
                        "progress": 0,
                        "message": "继续上次未完成生成" if normalized["resumeExisting"] else "排队中",
                        "out_dir": str(output_dir),
                        "idea_path": str(idea_path) if idea_path is not None else None,
                        "input_path": str(input_path),
                        "input_mode": input_mode,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    },
                )
                worker = threading.Thread(
                    target=run_build_worker,
                    args=(run_id, run_dir, output_dir, cmd, floor_count),
                    daemon=True,
                )
                worker.start()
                self.send_json(
                    {
                        "run_id": run_id,
                        "status_url": f"/api/status?run_id={run_id}",
                        "out_dir": str(output_dir),
                        "idea_path": str(idea_path) if idea_path is not None else None,
                        "input_path": str(input_path),
                        "input_mode": input_mode,
                    },
                    202,
                )
            elif parsed.path == "/api/stop":
                payload = self.read_body_json()
                run_id = str(payload.get("run_id") or "")
                stop_run(run_id)
                self.send_json({"state": "stopped", "message": "已终止生成并删除本次产物。"})
            elif parsed.path == "/api/init":
                self.send_json(init_mota_js())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:  # noqa: BLE001 - send API-visible failures.
            self.send_json({"error": str(exc)}, 400)

    def handle_export(self, query_string: str) -> None:
        query = parse_qs(query_string)
        run_id = (query.get("run_id") or [""])[0]
        run_dir = run_dir_for(run_id)
        project_dir = project_dir_for(run_dir)
        if not project_dir.exists():
            self.send_json({"error": "project is not available yet"}, 404)
            return
        zip_path = run_dir / "project.zip"
        if not zip_path.exists() or zip_path.stat().st_mtime < project_dir.stat().st_mtime:
            shutil.make_archive(str(zip_path.with_suffix("")), "zip", project_dir)
        body = zip_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="mota-project-{run_id}.zip"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_play(self, request_path: str) -> None:
        parts = request_path.split("/", 3)
        if len(parts) < 3:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        run_id = parts[2]
        relative = parts[3] if len(parts) == 4 else "index.html"
        if relative in {"", "/"}:
            relative = "index.html"
        run_dir = run_dir_for(run_id)
        if relative.startswith("project/"):
            target = safe_join(project_dir_for(run_dir), relative[len("project/") :])
        else:
            target = safe_join(MOTA_ROOT, relative)
        self.send_file(target)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local Mota Builder web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), MotaBuilderHandler)
    print(f"Mota Builder UI: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mota Builder UI.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

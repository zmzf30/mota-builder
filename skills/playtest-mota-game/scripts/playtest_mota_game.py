#!/usr/bin/env python3
"""Browser playtest helper for generated mota-js projects.

The script keeps side effects isolated: when a generated project directory is
provided, it copies the mota-js web root to a temporary directory, replaces its
project/ folder, starts server.py there, and playtests localhost 1055/1056.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.request
from pathlib import Path
from typing import Any


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def prepare_web_root(mota_root: Path, project_dir: Path | None) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if project_dir is None:
        return mota_root, None

    tmp = tempfile.TemporaryDirectory(prefix="mota-playtest-")
    web_root = Path(tmp.name) / "mota-js"

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {".git", "node_modules", "build", "_saves"}
            or name.endswith(".log")
        }

    shutil.copytree(mota_root, web_root, ignore=ignore)
    target_project = web_root / "project"
    if target_project.exists():
        shutil.rmtree(target_project)
    shutil.copytree(project_dir, target_project)
    return web_root, tmp


def start_server_if_needed(web_root: Path, allow_existing: bool) -> subprocess.Popen[str] | None:
    if allow_existing and (http_ok("http://127.0.0.1:1055/") or http_ok("http://127.0.0.1:1056/")):
        return None
    server_py = web_root / "server.py"
    if not server_py.exists():
        return None
    process = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=web_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 12
    while time.time() < deadline:
        if http_ok("http://127.0.0.1:1055/") or http_ok("http://127.0.0.1:1056/"):
            return process
        if process.poll() is not None:
            return process
        time.sleep(0.25)
    return process


PLAYWRIGHT_JS = r"""
const { chromium } = require('playwright');

const urls = process.env.MOTA_PLAYTEST_URLS.split(',');
const maxSteps = Number(process.env.MOTA_PLAYTEST_MAX_STEPS || 160);
const routeLimit = Number(process.env.MOTA_PLAYTEST_ROUTES || 4);
const perActionDelayMs = Number(process.env.MOTA_PLAYTEST_DELAY_MS || 35);

const routeProfiles = [
  { name: 'direct', dirs: [[0,-1,'ArrowUp'], [1,0,'ArrowRight'], [-1,0,'ArrowLeft'], [0,1,'ArrowDown']] },
  { name: 'left-biased', dirs: [[-1,0,'ArrowLeft'], [0,-1,'ArrowUp'], [0,1,'ArrowDown'], [1,0,'ArrowRight']] },
  { name: 'right-biased', dirs: [[1,0,'ArrowRight'], [0,-1,'ArrowUp'], [0,1,'ArrowDown'], [-1,0,'ArrowLeft']] },
  { name: 'lower-detour', dirs: [[0,1,'ArrowDown'], [-1,0,'ArrowLeft'], [1,0,'ArrowRight'], [0,-1,'ArrowUp']] },
].slice(0, routeLimit);

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function safeClone(value) {
  return JSON.parse(JSON.stringify(value ?? null));
}

async function chooseUrl(page) {
  let lastError = null;
  for (const url of urls) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 10000 });
      await page.waitForTimeout(1200);
      const title = await page.title();
      if (title || await page.locator('text=开始游戏').count()) return url;
    } catch (error) {
      lastError = String(error);
    }
  }
  throw new Error(`No playable URL from ${urls.join(', ')}. Last error: ${lastError}`);
}

async function clearAndStart(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.evaluate(() => {
    try { localStorage.clear(); } catch {}
    try { sessionStorage.clear(); } catch {}
  });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);

  for (const label of ['取消', '跳过', '确定']) {
    const loc = page.getByText(label, { exact: true });
    if (await loc.count()) {
      try { await loc.first().click({ timeout: 1200, force: true }); } catch {}
      await page.waitForTimeout(300);
      if (label === '取消') break;
    }
  }

  const start = page.getByText('开始游戏', { exact: true });
  if (await start.count()) {
    const clicked = await page.evaluate(() => {
      const el = document.getElementById('playGame');
      if (el) {
        el.click();
        return true;
      }
      return false;
    });
    if (!clicked) await start.first().click({ timeout: 5000, force: true });
  } else {
    await page.keyboard.press('Enter');
  }
  await page.waitForTimeout(800);

  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Enter');
    await page.waitForTimeout(120);
  }
}

async function runtimeState(page) {
  return await page.evaluate(() => {
    const c = window.core;
    if (!c || !c.status) return { available: false };
    const hero = c.status.hero || {};
    return {
      available: true,
      floorId: c.status.floorId,
      hero: {
        hp: hero.hp,
        atk: hero.atk,
        def: hero.def,
        mdef: hero.mdef,
        loc: hero.loc,
        items: hero.items,
      },
      gameOver: !!c.status.gameOver,
      eventId: c.status.event && c.status.event.id,
    };
  });
}

function tileId(blocksInfo, code) {
  if (code === 0) return 'none';
  const entry = blocksInfo[String(code)] || blocksInfo[code] || {};
  return entry.id || 'unknown';
}

function tileCls(blocksInfo, code) {
  if (code === 0) return 'terrains';
  const entry = blocksInfo[String(code)] || blocksInfo[code] || {};
  return entry.cls || 'unknown';
}

function isWall(blocksInfo, code) {
  if (code === 0) return false;
  const entry = blocksInfo[String(code)] || blocksInfo[code] || {};
  if (entry.id === 'yellowWall' || entry.id === 'whiteWall' || entry.id === 'blueWall') return true;
  if (entry.cls === 'autotile') return true;
  return entry.canBreak === true && !entry.trigger;
}

function isCostTile(blocksInfo, code) {
  const entry = blocksInfo[String(code)] || blocksInfo[code] || {};
  return entry.cls === 'enemys' || entry.cls === 'enemy48' || entry.trigger === 'openDoor';
}

function findTiles(floor, blocksInfo, id) {
  const found = [];
  const map = floor.map || [];
  for (let y = 0; y < map.length; y++) {
    for (let x = 0; x < (map[y] || []).length; x++) {
      if (tileId(blocksInfo, map[y][x]) === id) found.push([x, y]);
    }
  }
  return found;
}

function floorAnalysis(floorId, floor, blocksInfo) {
  const map = floor.map || [];
  const height = map.length;
  const width = height ? map[0].length : 0;
  const down = findTiles(floor, blocksInfo, 'downFloor')[0] || null;
  const up = findTiles(floor, blocksInfo, 'upFloor')[0] || null;
  let walls = 0, enemies = 0, doors = 0, items = 0, openJunctions = 0;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const code = map[y][x];
      const entry = blocksInfo[String(code)] || blocksInfo[code] || {};
      if (isWall(blocksInfo, code)) walls++;
      if (entry.cls === 'enemys' || entry.cls === 'enemy48') enemies++;
      if (entry.trigger === 'openDoor') doors++;
      if (entry.cls === 'items') items++;
      if (!isWall(blocksInfo, code) && code === 0) {
        let degree = 0;
        for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
          const nx = x + dx, ny = y + dy;
          if (nx >= 0 && ny >= 0 && nx < width && ny < height && !isWall(blocksInfo, map[ny][nx])) degree++;
        }
        if (degree >= 3) openJunctions++;
      }
    }
  }
  return {
    floorId, width, height, down, up,
    wallRatio: Number((walls / Math.max(width * height, 1)).toFixed(3)),
    enemies, doors, items, openJunctions,
  };
}

async function allFloorAnalysis(page) {
  return await page.evaluate((helpersSource) => {
    const analyze = eval(helpersSource);
    const c = window.core;
    if (!c) return [];
    return analyze(c);
  }, `((core) => {
    const tileId = ${tileId.toString()};
    const tileCls = ${tileCls.toString()};
    const isWall = ${isWall.toString()};
    const isCostTile = ${isCostTile.toString()};
    const findTiles = ${findTiles.toString()};
    const floorAnalysis = ${floorAnalysis.toString()};
    const blocksInfo = core.maps && core.maps.blocksInfo || {};
    const ids = core.floorIds || Object.keys(core.floors || {});
    return ids.map(id => floorAnalysis(id, core.floors[id], blocksInfo));
  })`);
}

async function planPath(page, profileName, dirs) {
  return await page.evaluate(({ profileName, dirs }) => {
    const c = window.core;
    const blocksInfo = c.maps && c.maps.blocksInfo || {};
    const floorId = c.status.floorId;
    const floor = (c.status.maps && c.status.maps[floorId]) || c.floors[floorId];
    const map = floor.map || [];
    const height = map.length;
    const width = height ? map[0].length : 0;
    const hero = c.status.hero || {};
    const start = [hero.loc.x, hero.loc.y];
    function tid(code) {
      if (code === 0) return 'none';
      const entry = blocksInfo[String(code)] || blocksInfo[code] || {};
      return entry.id || 'unknown';
    }
    function wall(code) {
      if (code === 0) return false;
      const entry = blocksInfo[String(code)] || blocksInfo[code] || {};
      if (entry.id === 'yellowWall' || entry.id === 'whiteWall' || entry.id === 'blueWall') return true;
      if (entry.cls === 'autotile') return true;
      return entry.canBreak === true && !entry.trigger;
    }
    let goal = null;
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      if (tid(map[y][x]) === 'upFloor') goal = [x, y];
    }
    if (!goal) return { profileName, floorId, path: [], keys: [], reason: 'no upFloor' };
    const queue = [{ x: start[0], y: start[1], path: [], keys: [] }];
    const seen = new Set([`${start[0]},${start[1]}`]);
    for (let qi = 0; qi < queue.length; qi++) {
      const cur = queue[qi];
      if (cur.x === goal[0] && cur.y === goal[1]) return { profileName, floorId, path: cur.path, keys: cur.keys, goal };
      for (const [dx, dy, key] of dirs) {
        const nx = cur.x + dx, ny = cur.y + dy;
        const sk = `${nx},${ny}`;
        if (nx < 0 || ny < 0 || nx >= width || ny >= height || seen.has(sk)) continue;
        if (wall(map[ny][nx])) continue;
        seen.add(sk);
        queue.push({ x: nx, y: ny, path: cur.path.concat([[nx, ny]]), keys: cur.keys.concat([key]) });
      }
    }
    return { profileName, floorId, path: [], keys: [], goal, reason: 'no path ignoring combat/keys' };
  }, { profileName, dirs });
}

async function tryRoute(page, url, profile) {
  await clearAndStart(page, url);
  const before = await runtimeState(page);
  const floorsVisited = [];
  const plans = [];
  let steps = 0;
  let reachedWin = false;
  let died = false;

  for (let segment = 0; segment < 12 && steps < maxSteps; segment++) {
    const state = await runtimeState(page);
    if (!state.available) break;
    if (!floorsVisited.includes(state.floorId)) floorsVisited.push(state.floorId);
    if (state.gameOver || (state.hero && state.hero.hp <= 0)) {
      died = true;
      break;
    }
    const plan = await planPath(page, profile.name, profile.dirs);
    plans.push({ floorId: plan.floorId, plannedSteps: plan.keys.length, reason: plan.reason || null });
    if (!plan.keys.length) break;
    for (const key of plan.keys) {
      await page.keyboard.press(key);
      steps++;
      await sleep(perActionDelayMs);
      if (steps >= maxSteps) break;
    }
    for (let i = 0; i < 4; i++) {
      await page.keyboard.press('Enter');
      await sleep(80);
    }
    const after = await runtimeState(page);
    if (after.gameOver) {
      died = true;
      break;
    }
    const bodyText = await page.locator('body').innerText().catch(() => '');
    if (/通关|胜利|恭喜/.test(bodyText)) {
      reachedWin = true;
      break;
    }
    if (after.floorId === state.floorId && plan.keys.length === 0) break;
  }

  return {
    name: profile.name,
    before,
    after: await runtimeState(page),
    floorsVisited,
    steps,
    reachedWin,
    died,
    plans,
  };
}

(async () => {
  const launchOptions = { headless: true };
  if (process.env.MOTA_PLAYTEST_CHROME) launchOptions.executablePath = process.env.MOTA_PLAYTEST_CHROME;
  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const consoleEntries = [];
  page.on('console', msg => {
    if (['error', 'warning'].includes(msg.type())) {
      consoleEntries.push({ type: msg.type(), text: msg.text() });
    }
  });
  page.on('pageerror', err => consoleEntries.push({ type: 'pageerror', text: String(err) }));

  let urlUsed = null;
  const issues = [];
  try {
    urlUsed = await chooseUrl(page);
    await clearAndStart(page, urlUsed);
    const analyses = await allFloorAnalysis(page);
    for (const floor of analyses) {
      if (floor.openJunctions > 6) issues.push(`${floor.floorId}: open layout has ${floor.openJunctions} high-degree junctions`);
      if (floor.enemies <= 2) issues.push(`${floor.floorId}: low battle pressure (${floor.enemies} enemies)`);
      if (floor.doors <= 0) issues.push(`${floor.floorId}: no door pressure`);
      if (!floor.down || !floor.up) issues.push(`${floor.floorId}: missing stair endpoint`);
    }

    const attempts = [];
    for (const profile of routeProfiles) {
      attempts.push(await tryRoute(page, urlUsed, profile));
    }
    const uniqueVisited = new Set(attempts.map(a => a.floorsVisited.join('>') + ':' + a.steps));
    if (attempts.length >= 2 && uniqueVisited.size <= 1) {
      issues.push('route attempts collapsed to the same observed route; route variety may be weak');
    }
    const easyWins = attempts.filter(a => a.reachedWin && a.steps < 25);
    if (easyWins.length) {
      issues.push(`possible too-easy completion: ${easyWins.map(a => a.name).join(', ')} reached win in under 25 key steps`);
    }

    const status = issues.length ? 'warn' : 'pass';
    console.log(JSON.stringify({
      status,
      url_used: urlUsed,
      summary: status === 'pass' ? 'Browser playtest completed without obvious route-balance warnings.' : 'Browser playtest completed with warnings.',
      issues,
      console_entries: consoleEntries.slice(0, 20),
      floor_analysis: analyses,
      route_attempts: attempts,
    }));
  } catch (error) {
    console.log(JSON.stringify({
      status: 'error',
      url_used: urlUsed,
      summary: 'Browser playtest failed before completion.',
      issues: [String(error && error.stack || error)],
      console_entries: consoleEntries.slice(0, 20),
      floor_analysis: [],
      route_attempts: [],
    }));
  } finally {
    await browser.close();
  }
})();
"""


def run_playwright(args: argparse.Namespace, urls: list[str]) -> dict[str, Any]:
    if shutil.which("node") is None:
        return {"status": "skipped", "summary": "Node.js is not available.", "issues": ["node not found"]}
    if shutil.which("npm") is None:
        return {"status": "skipped", "summary": "npm is not available.", "issues": ["npm not found"]}

    node_tmp = tempfile.TemporaryDirectory(prefix="mota-playtest-node-")
    node_dir = Path(node_tmp.name)
    script_path = node_dir / "playtest.js"
    script_path.write_text(PLAYWRIGHT_JS, encoding="utf-8")
    env = os.environ.copy()
    env["MOTA_PLAYTEST_URLS"] = ",".join(urls)
    env["MOTA_PLAYTEST_MAX_STEPS"] = str(args.max_steps)
    env["MOTA_PLAYTEST_ROUTES"] = str(args.routes)
    env["MOTA_PLAYTEST_DELAY_MS"] = str(args.delay_ms)
    chrome = find_chrome_executable()
    if chrome:
        env["MOTA_PLAYTEST_CHROME"] = str(chrome)
    try:
        install = subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund", "--silent", "playwright"],
            cwd=node_dir,
            text=True,
            capture_output=True,
            timeout=min(args.timeout, 90),
            env=env,
        )
        if install.returncode != 0:
            return {
                "status": "skipped",
                "summary": "Could not install Playwright for browser playtest.",
                "issues": [install.stderr[-2000:] or install.stdout[-2000:] or f"exit {install.returncode}"],
            }
        result = subprocess.run(
            ["node", str(script_path)],
            cwd=node_dir,
            text=True,
            capture_output=True,
            timeout=args.timeout,
            env=env,
        )
    finally:
        node_tmp.cleanup()

    if result.returncode != 0:
        return {
            "status": "error",
            "summary": "Playwright command failed.",
            "issues": [result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"],
        }
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                value.setdefault("stderr", result.stderr[-2000:])
                return value
        except json.JSONDecodeError:
            continue
    return {
        "status": "error",
        "summary": "Playwright did not emit JSON.",
        "issues": [result.stdout[-2000:], result.stderr[-2000:]],
    }


def find_chrome_executable() -> Path | None:
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for name in ("google-chrome", "chromium", "chromium-browser", "msedge"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Playtest a local/generated mota-js game in a browser.")
    parser.add_argument("--mota-root", type=Path, default=Path("mota-js"), help="Path to a full mota-js web root.")
    parser.add_argument("--project-dir", type=Path, help="Generated project directory to test in an isolated web root.")
    parser.add_argument("--out", type=Path, help="Write JSON report to this path.")
    parser.add_argument("--routes", type=int, default=4, help="Number of route profiles to try.")
    parser.add_argument("--max-steps", type=int, default=160, help="Maximum keyboard steps per route attempt.")
    parser.add_argument("--delay-ms", type=int, default=35, help="Delay after each arrow-key press.")
    parser.add_argument("--timeout", type=int, default=120, help="Overall Playwright command timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    mota_root = args.mota_root.resolve()
    project_dir = args.project_dir.resolve() if args.project_dir else None
    report: dict[str, Any]
    server: subprocess.Popen[str] | None = None
    temp_root: tempfile.TemporaryDirectory[str] | None = None
    try:
        web_root, temp_root = prepare_web_root(mota_root, project_dir)
        urls = ["http://127.0.0.1:1055/", "http://127.0.0.1:1056/"]
        if project_dir and any(http_ok(url) for url in urls):
            report = {
                "status": "skipped",
                "summary": "1055/1056 already served another process; skipped to avoid playtesting the wrong project.",
                "issues": ["Stop the existing local mota-js server or run without --project-dir to test that server."],
            }
            if args.out:
                write_json(args.out, report)
            else:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        server = start_server_if_needed(web_root, allow_existing=project_dir is None)
        if not any(http_ok(url) for url in urls):
            report = {
                "status": "skipped",
                "summary": "No local mota-js server responded on 1055 or 1056.",
                "issues": ["Could not access http://127.0.0.1:1055/ or http://127.0.0.1:1056/."],
            }
        else:
            report = run_playwright(args, urls)
        report.setdefault("mota_root", str(mota_root))
        if project_dir:
            report.setdefault("project_dir", str(project_dir))
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
        if temp_root is not None:
            temp_root.cleanup()

    if args.out:
        write_json(args.out, report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") in {"pass", "warn", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

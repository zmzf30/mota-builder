---
name: playtest-mota-game
description: Browser playtest workflow for generated mota-js towers. Use when Codex needs to open a local mota-js game at http://127.0.0.1:1055/ or fallback http://127.0.0.1:1056/, skip intro/story prompts, explore routes with keyboard arrow controls, and report whether layout, route difficulty, and route balance feel reasonable after floor generation and review.
---

# Playtest Mota Game

## Role

Run a lightweight browser playtest after a generated floor has passed normal generator and reviewer checks.

This skill is intentionally a final quality signal, not a map editor. It should identify route balance, overly easy routes, dead-feeling layouts, and obvious runtime issues while keeping the generator/reviewer flow unchanged.

## Quick Start

Prefer the bundled script:

```bash
python3 skills/playtest-mota-game/scripts/playtest_mota_game.py \
  --mota-root mota-js \
  --project-dir build/mota-tower/project \
  --out build/mota-tower/playtests/MT0.playtest.json
```

The script will:

1. Prepare an isolated runnable mota-js web root when `--project-dir` is provided.
2. Visit `http://127.0.0.1:1055/`, falling back to `http://127.0.0.1:1056/`.
3. Dismiss the dynamic-map-editor prompt when present.
4. Click `开始游戏`.
5. Press confirm keys several times to skip opening story text.
6. Analyze floor topology from `core.floors`.
7. Try several route styles with keyboard arrow keys.
8. Write a JSON report with issues and route attempts.

## Review Expectations

Judge the playtest as a route-quality report:

- A route that reaches the current temporary win is acceptable, but it should not be trivially direct with little combat, door, or resource pressure.
- Multiple route attempts should feel meaningfully different. If all attempts collapse to the same path, report weak route variety.
- Dead routes and deaths are acceptable during playtest if they reflect real route choice pressure rather than broken topology.
- Report route dominance when one route appears shorter, safer, and better rewarded than the alternatives.
- Report runtime issues separately from design issues.

## Pipeline Use

When invoked from `scripts/build_mota_tower.py`, treat the playtest as non-destructive:

- Do not edit `mota-js/project` directly.
- Do not modify generated floor JSON.
- Prefer writing reports under `build/mota-tower/playtests/`.
- Keep failures non-blocking unless the caller explicitly asks for a fail policy.

## Manual Fallback

If browser automation is unavailable, still produce a JSON report from static layout analysis when possible. Mark the report `status: "skipped"` or `status: "warn"` and include the reason.

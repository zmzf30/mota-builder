---
name: build-mota-tower
description: Agentic entry point for running the classic mota-js tower build pipeline from a natural-language user request. Use when the user asks to build, generate, plan, run, or start a traditional Magic Tower / mota tower using the code orchestrator. This skill chooses parameters and execution mode, then invokes scripts/build_mota_tower.py to create a generated project under build/. It does not manually design floors, review floors, or edit the source mota-js project.
---

# Build Mota Tower

## Role

Act as the thin agentic entry point for the tower build pipeline.

Convert the user's natural-language request into parameters for `scripts/build_mota_tower.py`, then run the script. The script performs the actual code orchestration, calls headless Codex agents for brief generation, staged per-floor generation, staged review, and final browser playtest, then writes a generated `project/` directory under the output directory.

## Boundary

- Do not manually call `design-traditional-mota-tower`, `topology-mota-floor`, `economy-mota-floor`, `monster-special-mota-floor`, or `review-mota-floor`.
- Do not design floor content in this entry skill.
- Do not review floor content in this entry skill.
- Do not directly edit source `mota-js` project files. The script writes generated output under `build/`.
- Only determine script parameters, run mode, and whether the user must clarify missing intent.

## Execution Modes

- Use `--brief-only` when the user is still describing an idea, asking to start with global confirmation, or has not explicitly approved full generation.
- Use full generation with `--yes` when the user clearly asks to generate/build/run the whole pipeline or confirms the brief. Phrases like "我想直接一步生成一个……的塔" explicitly mean full generation, not `--brief-only`.
- Use `--brief-file <path>` when the user points to an existing confirmed `tower_brief.json`.
- Use `--floors <n>` when the user states a floor count outside the free-text idea.
- Use `--floor-size <9|11|13>` when the user states a supported map size outside the free-text idea. Default is 11x11.
- Use `--clean` only for a fresh run under the repository `build/` directory.
- Use `--keep-prompts` when debugging, tuning prompt architecture, or the user asks to inspect prompts.
- Use `--parallel-floors` when the user explicitly asks to generate floors concurrently. This pre-splits whole-tower tracked-resource limits into per-floor contracts, then generates and reviews floors concurrently before final ordered merge validation.
- Use `--floor-concurrency <1-4>` with `--parallel-floors` when the user requests a worker count. Never set it above 4.

## Common Commands

Brief confirmation from an inline idea:

```bash
python3 scripts/build_mota_tower.py --idea-text "<user idea>" --brief-only
```

Full noninteractive generation from an inline idea:

```bash
python3 scripts/build_mota_tower.py --idea-text "<user idea>" --yes
```

Full generation from an existing brief:

```bash
python3 scripts/build_mota_tower.py --brief-file build/mota-tower/tower_brief.json --yes
```

Debuggable fresh generation:

```bash
python3 scripts/build_mota_tower.py --idea-text "<user idea>" --yes --clean --keep-prompts
```

Parallel floor generation with the maximum supported concurrency:

```bash
python3 scripts/build_mota_tower.py --idea-text "<user idea>" --yes --parallel-floors --floor-concurrency 4
```

## Parameter Selection

Prefer defaults unless the user gives a reason to change them.

- `--out-dir`: Use a custom output directory only if the user requests one.
- `--max-attempts`: Raise above `2` only for a harder design or if the user asks for more retries.
- `--parallel-floors`: Use only when the user accepts the tradeoff. It is faster but each floor must fit a preassigned budget contract instead of reacting to the actual previous accepted floor.
- `--floor-concurrency`: Defaults to 4 for `--parallel-floors`; lower it if the user wants fewer simultaneous Codex calls. The script rejects values above 4.
- Per-floor generation is always staged: topology -> economy -> monster-special, followed by staged review and structured repair routing.
- Browser playtest runs after each accepted floor by default using `playtest-mota-game`. Use `--skip-playtest` only when browser automation is unavailable or the user explicitly wants faster non-browser generation.
- `--playtest-policy`: Defaults to `warn`, so playtest findings are reported but do not block generation. Use `fail` only when the user explicitly wants browser playtest issues to fail the pipeline.
- `--model`: Defaults to `gpt-5.5` for all internal Codex calls. Override only if the user requests a specific model.
- `--profile`: Set only if the user requests a Codex profile.
- `--config`: Defaults include `model_reasoning_effort="xhigh"` and `service_tier="priority"` for fast high-reasoning internal calls. Pass additional explicit overrides only when needed.
- `--codex-arg`: Pass through advanced raw Codex exec arguments only when necessary.
- `--timeout`: Set for long full-tower runs or when the user asks for a time limit.
- `--sandbox`: Keep `read-only` for planning. Use a broader sandbox only if later pipeline stages intentionally edit files.
- `--floor-prefix` and `--floor-number-offset`: Set only if the user wants non-default floor IDs.
- `--floor-size`: Set only when the user explicitly asks for 9x9 or 13x13, or explicitly confirms 11x11.

## Reporting

After running the script, report:

- Whether it stopped at brief confirmation, needs more user input, or completed all floor reviews and wrote the generated project.
- The path to `tower_brief.json` or `summary.json`.
- In parallel mode, the path to `floor_contracts.json`.
- The generated `project/` path when complete.
- Browser playtest reports under `build/mota-tower/playtests/`, including warnings about route variety, overly easy routes, runtime errors, or skipped browser automation.
- Any questions printed by the script.
- Any failed floor and its review summary if the script fails.

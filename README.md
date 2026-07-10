# Mota Builder

基于 `mota-js`、Python 和 AI Agent 终端（必须安装并配置Agent Cli环境，默认使用并建议使用 Codex CLI，推荐不低于 GPT-5.5 xhigh 能力的模型；同时也支持通过 `--agent-backend opencode` 使用 OpenCode）的 HTML5 魔塔制作工作区，并在样板工程之外补充了一套面向传统魔塔的 AI 造塔流水线。

mota-js 是 HTML5 魔塔样板，需要您clone https://github.com/ckcz123/mota-js 并放在本仓库下，用于运行、编辑和作为生成流水线的模板；该目录体积较大且包含工程素材，已在根 `.gitignore` 中忽略，不提交到 Git。`skills/` 和 `scripts/build_mota_tower.py` 负责把自然语言需求拆成全塔设计、楼层拓扑、经济资源、怪物压力、审查修复和浏览器试玩等阶段，最终在 `build/` 下写出生成后的 `project/`。

## 马上上手
1、克隆本仓库
```text
git clone https://github.com/zmzf30/mota-builder.git
```

2、在本仓库目录下 
```text
git clone https://github.com/ckcz123/mota-js.git
```

3、启动本地 Web UI：

```bash
python3 scripts/mota_builder_app.py
```

默认打开 `http://127.0.0.1:8765/`；如果该端口已被另一个 Mota Builder 占用，新进程会自动尝试 `8766`、`8767` 等后续端口，请以终端打印的实际地址为准。不同端口实例可以同时创建和管理各自的生成任务。页面中可以确认规模、填写基础参数、开始整塔生成；高级选项里可以查看完整提示词，也可以继续本实例上次未完成的生成。生成中可终止并清理本次产物，生成后可直接试玩、打开编辑器或导出 `project.zip`。这个 UI 不需要 Node.js。

UI 可选择“传统塔”或“红海塔”，默认传统塔。传统塔使用寒云谷、溯、CCW 的同风格 few-shot；红海塔使用红蓝的记忆、星月神话、dist、剑阁、出塞的同风格 few-shot。风格只控制地图结构和资源/怪物放置方式，不用于推断数值难度。

Web UI 仅建议基于 `mota-js` 样板生成新塔，不建议直接修改已有塔；暂不自动生成剧情、机关、脚本、事件、升级、商店、加点、新图块或非标准通行/阻挡图块。

也可以打开 AI 终端（如 Codex 或 OpenCode），进入在本仓库目录，直接输入（目前不支持剧情、自定义脚本、特殊图块等，每层速度都较慢，一般建议生成10层左右或以内，否则速度极慢；）：

```text
我想直接一步生成一个 6 层、13x13、无剧情、高数值压力、传统钥匙门博弈的塔。
```

更好的提示词：
```text
我想直接一步生成一个 6 层、13x13、无剧情、高数值压力、传统钥匙门博弈的魔塔。参数设定：初始生命1000、攻击10、防御10、金币0。初始钥匙：黄钥匙1、蓝钥匙0、红钥匙0。宝石：红宝石ATK+1、蓝宝石DEF+1。药水：红药水HP+50、蓝药水HP+100、黄药水HP+200、绿药水HP+500。整塔门总量约黄门30、蓝门15、红门5；钥匙总量约黄钥匙12、蓝钥匙3、红钥匙2。破墙镐3、炸弹3、中心对称飞行器1。怪物能力限制在白名单内（先攻、魔攻、坚固、领域、阻击）。每层需要至少3条分支路线、明显的路线选择压力、门钥匙博弈和战斗压力。
```

AI 终端会代为调用本仓库的生成脚本，默认使用 Codex 后端，生成结果写入 `build/mota-tower/`，不会直接覆盖 `mota-js/project/`。如果要用 OpenCode，在提示词末尾追加：

```text
使用 --agent-backend opencode。
```

生成完成后重点查看：

- `build/mota-tower/summary.json`
- `build/mota-tower/project/`

需要使用生成内容时，将生成产物替换到 `mota-js/project/` 下的对应文件即可。

## 适用场景

- 直接基于 `mota-js` 样板，制作或调试 HTML5 魔塔。
- 用自然语言/脚本生成一座传统魔塔的全塔方案和楼层文件。
- 需要在生成时，自动对局部地图、怪物数据、全局数值等做合理性校验/修改。
- 对生成结果做静态审查和轻量浏览器试玩。

## 目录结构

```text
.
├── mota-js/                    # 本地 HTML5 魔塔样板工程，已被 Git 忽略
│   ├── project/                # 当前游戏项目数据
│   │   ├── data.js             # 全局配置、初始勇士、楼层列表、商店等
│   │   ├── enemys.js           # 怪物属性和特殊能力
│   │   ├── floors/             # 楼层地图文件
│   │   ├── maps.js             # 地图数字码到图块/怪物/道具的映射
│   │   └── ...
│   ├── editor.html             # 可视化编辑器入口
│   ├── index.html              # 游戏入口
│   ├── server.py               # Python 本地服务，默认从 1055 端口开始
│   └── server.js               # Node.js 本地服务，默认从 3000 端口开始
├── scripts/
│   ├── build_mota_tower.py     # 传统魔塔生成流水线入口
│   └── mota_few_shot.py        # 真实参考项目提取、路线分析与样例检索
├── references/few-shot/        # 仓库内置、可复现的精选参考楼层语料
├── skills/                     # Codex 技能定义和试玩脚本
│   ├── build-mota-tower/       # 造塔流水线入口技能
│   ├── topology-mota-floor/    # 楼层拓扑生成
│   ├── economy-mota-floor/     # 门钥匙、道具、资源经济生成
│   ├── monster-special-mota-floor/
│   ├── review-mota-enemy-table/ # 怪物表分层强度与同层角色审查
│   ├── review-mota-floor/      # 楼层审查
│   └── playtest-mota-game/     # 浏览器试玩辅助
├── build/                      # 生成结果和中间产物
└── *.zip                       # 本地样板或工程备份包，已被 Git 忽略
```

## 环境要求

运行或编辑游戏本体：

- 本地存在 `mota-js/` 样板工程；新克隆仓库后需要自行放入或解压到该路径。

运行 AI 造塔流水线：

- Python 3
- 已配置可用的 `codex` 命令行工具
- 可选：已配置可用的 `opencode` 命令行工具，用于 `--agent-backend opencode`
- 可选：Node.js 和 npm，仅用于开发者手动运行 Playwright 自动试玩脚本；本地 Web UI 和生成主流程不需要 Node.js。
- 可访问本机浏览器环境；试玩会访问 `http://127.0.0.1:1055/`，必要时回退到 `1056`
- 默认使用仓库内 `references/few-shot/corpus.json`，不依赖本机外部目录；只有重建或临时覆盖语料时才需要 `~/Documents/例子` 等原始参考项目目录。每个阶段会固定选择一个 generator/reviewer 共享锚点，再分别分配生成专用样例和 reviewer holdout；重试不会重新抽样。
- 最低资源建议：至少 4 核 CPU、16GB 内存，以及楼层数 x 3,000,000 的可用 token 额度。
- 推荐资源：8 核以上 CPU、32GB 以上内存，以及楼层数 x 8,000,000 的可用 token 额度。


## 运行当前魔塔工程

```bash
cd mota-js
python3 -m pip install flask
python3 server.py
```

服务启动后会打印实际端口。默认地址通常是：

- 游戏：`http://127.0.0.1:1055/`
- 编辑器：`http://127.0.0.1:1055/editor.html`

也可以使用 Node.js 服务：

```bash
cd mota-js
node server.js
```

## 深入实践（脚本生成，适用于开发者或非新人用户）

### 两步生成之细化魔塔指标

建议先只生成全塔 brief，确认楼层数、地图尺寸、初始数值、门钥匙和资源预算是否符合预期：

```bash
python3 scripts/build_mota_tower.py \
  --idea-text "做一座 4 层、13x13、偏传统钥匙门博弈的魔塔，强调分路线和蓝门决策" \
  --brief-only \
  --out-dir build/mota-tower-demo
```

输出文件：

- `build/mota-tower-demo/tower_brief.json`

如果 brief 里 `status` 是 `needs_input`，按脚本打印的问题补充需求后重新运行。

### 两步生成之从已确认 brief 生成楼层

```bash
python3 scripts/build_mota_tower.py \
  --brief-file build/mota-tower-demo/tower_brief.json \
  --yes \
  --out-dir build/mota-tower-demo
```

生成成功后重点查看：

- `build/mota-tower-demo/summary.json`
- `build/mota-tower-demo/project/`
- `build/mota-tower-demo/playtests/`

`project/` 是可运行的生成结果。流水线默认不会直接覆盖 `mota-js/project/`。需要使用生成内容时，将生成产物替换到 `mota-js/project/` 下的对应文件即可。

### 一步式生成

```bash
python3 scripts/build_mota_tower.py \
  --idea-text "做一座 6 层、13x13、无剧情、高数值压力、传统钥匙门博弈的魔塔。参数设定：初始生命1000、攻击10、防御10、金币0。初始钥匙：黄钥匙1、蓝钥匙0、红钥匙0。宝石：红宝石ATK+1、蓝宝石DEF+1。药水：红药水HP+50、蓝药水HP+100、黄药水HP+200、绿药水HP+500。整塔门总量约黄门30、蓝门15、红门5；钥匙总量约黄钥匙12、蓝钥匙3、红钥匙2。破墙镐3、炸弹3、中心对称飞行器1。怪物能力限制在白名单内（先攻、魔攻、坚固、领域、阻击）。每层需要至少3条分支路线、明显的路线选择压力、门钥匙博弈和战斗压力。" \
  --yes \
  --clean \
  --out-dir build/mota-tower
```

也可以在 AI 终端中使用更明确的完整提示词并做更多的事情：

```text
请在当前仓库中调用 scripts/build_mota_tower.py，一步生成一座 6 层、13x13、低剧情、高数值压力、传统钥匙门博弈的魔塔。使用默认 Codex 后端，不要直接覆盖 mota-js/project，输出到 build/mota-tower。
```

如果要用 OpenCode，在提示词末尾追加：

```text
使用 --agent-backend opencode。
```

常用参数：

- `--floors <n>`：指定楼层数。
- `--floor-size`：指定正方形地图尺寸（建议13）。
- `--tower-style traditional|red_sea`：选择传统塔或红海塔，默认传统塔；few-shot 不会跨风格回退。
- `--brief-only`：只生成全塔设计草案。
- `--brief-file <path>`：从已有 `tower_brief.json` 继续。
- `--resume-existing`：复用输出目录中已有的楼层审查结果继续生成。
- `--parallel-floors --floor-concurrency 4`：并发生成楼层，速度更快；每层资源预算优先读取 `floor_progression_plan[].resource_budget`，只有规划缺失、格式错误或合计不等于整塔预算时才记录错误并回退整数均分。传统塔战斗审查按初始 HP，加上此前楼层平均可获得的红/蓝宝石攻防来估算当前层勇士能力。
- `--agent-backend codex|opencode`：选择内部 LLM 调用后端；默认 `codex`。
- `--max-attempts <n>`：每层最大尝试次数；默认 Codex 为 `4`，OpenCode 为 `6`。
- `--model <model>`：指定后端模型。默认 Codex 会传 `--model gpt-5.5`；OpenCode 只有显式设置时才会传 `--model`，通常写成 `provider/model`。
- `--config <key=value>`：额外传给 `codex exec` 的配置；Codex 默认还会传 `model_reasoning_effort="xhigh"` 和 `service_tier="priority"`。
- `--codex-arg <arg>`：额外传给 `codex exec` 的原始参数，可重复。
- `--opencode-arg <arg>`：额外传给 `opencode run` 的原始参数，可重复。使用 OpenCode 时不会传 Codex 专用的 `model_reasoning_effort` 或 `service_tier`。
- `--timeout <seconds>`：单次 agent 调用超时时间，默认 `1800` 秒（30 分钟）。
- `--max-wall-similarity <0-1>`：相邻楼层墙体相似度上限，默认 `0.9`。
- `--skip-playtest`：跳过浏览器试玩。
- `--keep-prompts`：保留每个阶段发给 agent 的 prompt，方便调试。
- `--no-generation-cache`：关闭 brief、怪物表和已接受楼层的 hash 缓存复用。
- `--few-shot-root <path>`：临时从真实参考项目根目录重新提取；只索引其下带 `project/` 的文件夹，并覆盖本次运行的内置语料。
- `--few-shot-corpus <path>`：指定预提取语料 JSON；默认使用仓库内 `references/few-shot/corpus.json`。
- `--few-shot-count <1-5>`：每个 generator 或 reviewer 注入的真实参考楼层数，默认 `3`；默认组成是 1 个共享锚点加 2 个各自专用样例。
- `--no-few-shot`：显式关闭真实参考楼层输入。
- `--self-test`：运行脚本内置本地测试，不调用外部 agent。

OpenCode 示例：

```bash
python3 scripts/build_mota_tower.py \
  --agent-backend opencode \
  --model deepseek/deepseek-chat \
  --idea-text "做一座 4 层、13x13、偏传统钥匙门博弈的魔塔" \
  --brief-only \
  --out-dir build/mota-tower-opencode
```

Codex 后端使用 `codex exec --output-schema` 强制结构化输出；OpenCode 后端会把 JSON schema 写入 prompt 并解析最终输出，因此结构化稳定性取决于所选 OpenCode provider/model。

## 浏览器试玩生成结果

可以单独对某个生成项目运行试玩报告：

```bash
python3 skills/playtest-mota-game/scripts/playtest_mota_game.py \
  --mota-root mota-js \
  --project-dir build/mota-tower/project \
  --out build/mota-tower/playtests/manual.playtest.json
```

试玩脚本会临时复制 `mota-js` Web 根目录，替换其中的 `project/`，启动本地服务，并用键盘路线尝试检查：

- 是否能正常进入游戏。
- 是否存在明显运行时错误。
- 路线是否过于单一或过于直接。
- 战斗、门钥匙、资源压力是否有基本区分。

试玩报告是质量信号，不会自动修改楼层。

## 设计和生成约束

当前流水线偏向传统数值魔塔，而不是剧情或复杂脚本塔：

- 地图尺寸支持`13x13`。
- 默认地面只使用图块码 `0`，墙只使用图块码 `1`。
- 传统塔默认墙比例 `0.35-0.45`、2-4 条主要路线、6-20 个有效决策点、18-28 个怪物；红海塔默认墙比例 `0.45-0.55`、10-40 个有效决策点、22-33 个怪物。两种风格默认每层最多 9 种怪物。传统塔仍以 2-6 个特殊压力位置、平均每层 0.5-2 个工具、70%-90% 重要资源保护率和 0%-10% 钥匙/资源安全余量为目标。用户或已确认 brief 的显式设置优先。
- WebUI 默认整塔资源为红宝石、蓝宝石、红血瓶各 `6 × 层数`，蓝血瓶 `1 × 层数`。
- 不论选择哪种风格，开始生成前都会强制把初始怪物手册 `book` 设置为 `1`。
- 生成阶段会分为怪物数据设计与专用审查、拓扑、经济、怪物特殊能力、审查和修复。
- 仓库内置语料包含精选正式楼层的原始地图、项目内图块语义、压缩路线图、候选路线、资源可达顺序和实际使用的怪物数据；按楼层位置和阶段检索真实样例后注入 prompt。传统塔布局 generator/reviewer 只从寒云谷主塔 MT2/3/4/7/8/11/12 与溯主塔 MT2/3/5/6/7/8/9 中选择，并在 prompt 投影中把指定的特殊资源、装备和红门/红钥匙归一为红蓝宝石或蓝门/蓝钥匙；怪物表 few-shot 仍使用完整同风格语料。重建语料时会读取 `maps.js`、`enemys.js`、`data.js` 并排除 `sample*` 楼层。
- 参考项目的数字图块码只在其自身项目中有效；生成 Agent 必须通过随样例提供的图块字典理解语义，不能直接复制参考图块码、脚本或事件。
- 全塔 brief 会生成 `floor_progression_plan`，把参考塔的非均匀节奏转成每层路线角色、门钥匙弧线、资源可达阶段、战斗阈值、工具兑现和跨层携带意图。
- 每层要求存在多条候选路线、门钥匙压力、战斗压力和可计算的资源取舍。
- 怪物数值和特殊属性会由怪物数据 Agent 按本次塔重新设计，只复用现有怪物 id 和素材槽位。
- 怪物表 reviewer 会根据全塔资源投影每层勇士属性，按相对战损、原始强度递进和肉盾/高攻/均衡/阈值/特殊角色编排楼层怪物池；结果写入 `hero_projection.json`、`enemy_floor_plan.json`、`enemy_floor_analysis.json` 和 `enemy_design.review.json`。
- 怪物特殊能力默认限制在先攻、魔攻、坚固、领域、阻击等白名单内。
- Web UI 可配置初始跳跃靴，以及全塔宝石、血瓶和跳跃靴数量；这些数量会进入全塔资源预算校验。
- Web UI 高级选项可调整墙比例、每层怪物种类上限、每怪特殊能力上限、是否禁止相邻怪物、楼层怪物重叠率和领域/阻击伤害具体数值范围；这些是生成和校验目标，不保证大模型输出完全遵循。
- 达到最大尝试次数的最后一轮会跳过 review 并保存最新结果，生成可继续试玩和手动调整的产物。
- 流水线会压缩阶段 prompt 上下文，并把参考语料指纹纳入输入 hash；参考项目发生变化后不会复用旧的 brief、怪物表或楼层缓存。
- 不依赖随机、隐藏脚本、新素材、复杂 UI、插件机制或重剧情事件。

这些约束主要写在 `skills/*/SKILL.md` 和 `scripts/build_mota_tower.py` 中。修改约束时建议先调整技能说明，再运行 `--self-test` 和小规模生成验证。

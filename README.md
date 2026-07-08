# Mota Builder

基于 `mota-js`， python 和codex（目前仅支持codex cli，建议使用不低于GPT 5.5 xhigh能力的模型）的 HTML5 魔塔制作工作区，并在样板工程之外补充了一套面向传统魔塔的 AI 造塔流水线。

`mota-js/` 是本地 HTML5 魔塔样板工程目录，建议您将样板放在本仓库下，用于运行、编辑和作为生成流水线的模板；该目录体积较大且包含工程素材，已在根 `.gitignore` 中忽略，不提交到 Git。`skills/` 和 `scripts/build_mota_tower.py` 负责把自然语言需求拆成全塔设计、楼层拓扑、经济资源、怪物压力、审查修复和浏览器试玩等阶段，最终在 `build/` 下写出生成后的 `project/`。

## 适用场景

- 直接打开 `mota-js` 样板，手工制作或调试 HTML5 魔塔。
- 用自然语言生成一座传统魔塔的全塔方案和楼层文件。
- 对已有楼层进行局部地图、怪物数据、全局数值等定向修改。
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
│   └── build_mota_tower.py     # 传统魔塔生成流水线入口
├── skills/                     # Codex 技能定义和试玩脚本
│   ├── build-mota-tower/       # 造塔流水线入口技能
│   ├── topology-mota-floor/    # 楼层拓扑生成
│   ├── economy-mota-floor/     # 门钥匙、道具、资源经济生成
│   ├── monster-special-mota-floor/
│   ├── review-mota-floor/      # 楼层审查
│   └── playtest-mota-game/     # 浏览器试玩辅助
├── build/                      # 生成结果和中间产物
└── *.zip                       # 本地样板或工程备份包，已被 Git 忽略
```

## 环境要求

运行或编辑游戏本体：

- Python 3
- Flask：`python3 -m pip install flask`
- 或 Node.js：用于 `mota-js/server.js`
- 本地存在 `mota-js/` 样板工程；新克隆仓库后需要自行放入或解压到该路径。

运行 AI 造塔流水线：

- Python 3
- 已配置可用的 `codex` 命令行工具
- Node.js 和 npm，用于浏览器试玩阶段自动安装并运行 Playwright
- 可访问本机浏览器环境；试玩会访问 `http://127.0.0.1:1055/`，必要时回退到 `1056`

## 快速开始

### 运行当前魔塔工程

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

Node.js 版本默认从 `3000` 端口开始，并在控制台打印游戏和编辑器地址。

### 生成全塔设计草案

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

### 从已确认 brief 生成楼层

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

`project/` 是可运行的生成结果。流水线默认不会直接覆盖 `mota-js/project/`。

### 一步式生成

```bash
python3 scripts/build_mota_tower.py \
  --idea-text "做一座 6 层、11x11、低剧情、高数值压力的传统魔塔" \
  --yes \
  --clean \
  --out-dir build/mota-tower
```

常用参数：

- `--floors <n>`：指定楼层数。
- `--floor-size 9|11|13`：指定正方形地图尺寸。
- `--brief-only`：只生成全塔设计草案。
- `--brief-file <path>`：从已有 `tower_brief.json` 继续。
- `--resume-existing`：复用输出目录中已有的楼层审查结果继续生成。
- `--parallel-floors --floor-concurrency 4`：并发生成楼层，速度更快，但每层会先被分配固定资源预算。
- `--skip-playtest`：跳过浏览器试玩。
- `--keep-prompts`：保留每个阶段发给 Codex 的 prompt，方便调试。
- `--self-test`：运行脚本内置本地测试，不调用 Codex。

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

- 地图尺寸支持 `9x9`、`11x11`、`13x13`。
- 默认地面只使用图块码 `0`，墙只使用图块码 `1`。
- 生成阶段会分为拓扑、经济、怪物特殊能力、审查和修复。
- 每层要求存在多条候选路线、门钥匙压力、战斗压力和可计算的资源取舍。
- 怪物特殊能力默认限制在先攻、魔攻、坚固、领域、阻击等白名单内。
- 不依赖随机、隐藏脚本、新素材、复杂 UI、插件机制或重剧情事件。

这些约束主要写在 `skills/*/SKILL.md` 和 `scripts/build_mota_tower.py` 中。修改约束时建议先调整技能说明，再运行 `--self-test` 和小规模生成验证。

## 修改已有项目

手工修改时，优先改 `mota-js/project/` 下的数据文件：

- 改全局配置、初始属性、楼层顺序：`mota-js/project/data.js`
- 改怪物属性、金币、经验、特殊能力：`mota-js/project/enemys.js`
- 改单层地图点位、楼梯、门、钥匙、怪物摆放：`mota-js/project/floors/*.js`
- 查图块数字码：`mota-js/project/maps.js`

生成结果在 `build/<name>/project/` 中。确认要采纳生成结果前，建议先比较它和 `mota-js/project/` 的差异，再决定是否复制覆盖。

## 验证

运行流水线本地测试：

```bash
python3 scripts/build_mota_tower.py --self-test
```

运行游戏服务后，也可以直接打开编辑器和游戏页面做人工验证。

## 许可证和来源

`mota-js/` 为 HTML5 魔塔样板工程，相关说明和许可见：

- `mota-js/README.md`
- `mota-js/LICENSE.md`

本仓库新增的生成脚本、技能说明和构造产物围绕该样板工程工作。发布或分发成品前，请同时确认样板工程素材、音频、工具和新增内容的授权边界。

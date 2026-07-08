---
name: 中心对称飞行器实现方案
overview: 为求解器添加单中心对称飞行器支持（一开始即拥有，最多使用一次），包括状态扩展、飞行逻辑、剪枝策略修正、P4/策略2兼容性修改，并估算复杂度。
todos:
  - id: fly-types
    content: "types.js: DynamicEntity.kind 加 centerFlyItem, PathStep.after 加 centerFly; FloorData 加 flightBlockSet"
    status: completed
  - id: fly-adapter
    content: "adapter.js: 识别 centerFly 地图图块(50), 构建 flightBlockSet(ground/stairs 位置), enableCenterFly 开关"
    status: completed
  - id: fly-pruning
    content: "pruning.js: 新增 isWalkReachable, 修正 findUnreachableMask/computeValidDoors 支持飞行, absorbReachableItems 扩展"
    status: completed
  - id: fly-solver
    content: "solver.js: 状态加 centerFly, stateSignature 扩展, 4方向后追加飞行分支 + 策略F + 剪枝"
    status: completed
  - id: fly-cli
    content: "cli.js: 新增 --enable-center-fly 开关, 路径输出加 cfly="
    status: completed
  - id: fly-tests
    content: 新增中心对称飞行器测试用例
    status: completed
isProject: false
---

# 单中心对称飞行器实现方案（经源码审查修正版）

## 一、mota-js 飞行机制精确定义

### canUseItemEffect（items.js L393）

```javascript
var toX = core.bigmap.width - 1 - core.getHeroLoc('x');
var toY = core.bigmap.height - 1 - core.getHeroLoc('y');
var id = core.getBlockId(toX, toY);   // 检查事件层
return id == null;                      // 只有完全无 block 才能飞
```

### getBlockId 的语义（maps.js L1911-1924）

```javascript
maps.prototype.getBlock = function (x, y, floorId, showDisable) {
    var blockObjs = this.getMapBlocksObj(floorId);
    var block = blockObjs[x + "," + y];
    if (block && !block.disable) return block;  // disable=被移除的
    return null;
}
maps.prototype.getBlockId = function (x, y) {
    var block = core.getBlock(x, y);
    return block == null ? null : block.event.id;
}
```

**关键发现**：`getBlockId` 对**所有非零地图图块**返回非 null，包括：

- 怪物、门、道具 → 已在 dynamics 中追踪 ✓
- **ground(300)、upFloor(87)、downFloor(88)** → adapter 视为空地，不在 dynamics 中 ✗
- 被 removeBlock 移除的（disable=true）→ 返回 null ✓

### bigmap.width（maps.js L540-541）

```javascript
core.bigmap.width = core.floors[floorId].width;   // 就是楼层宽度
core.bigmap.height = core.floors[floorId].height;
```

### 地图图块 50 = centerFly 道具（maps.js L49）

```javascript
"50": {"cls":"items","id":"centerFly"}
```

## 二、求解器中的飞行有效条件（5 项全部满足）

```
1. centerFly > 0
2. 目标 (symX, symY) = (floor.width-1-x, floor.height-1-y) ≠ (x, y)
3. baseGrid[symY][symX] !== 'wall'
4. 目标位置无未消耗的动态实体
   （dynamicIndexByPos 中有但 bit 已在 mask → 已被移除 → 不阻止飞行）
5. 目标位置不在 flightBlockSet 中
   （ground/stairs 等非零图块被 adapter 跳过，但在 mota 中是 block）
```

**条件 5 是源码审查发现的修正**：adapter 的 `EMPTY_IDS`/`STAIR_IDS` 处理将 ground(300)、upFloor(87)、downFloor(88) 视为可通行空地，不入 baseGrid 也不入 dynamics。但在 mota-js 中它们是 block，`getBlockId` 返回非 null → 阻止飞行。

## 三、改动清单

### 3.1 [src/types.js](mota-optimal-solver/src/types.js)

- `DynamicEntity.kind` 枚举加 `'centerFlyItem'`
- `PathStep.after` 加 `centerFly: number`
- `FloorData` 加 `flightBlockSet: Set<string>`（ground/stairs 坐标）

### 3.2 [src/adapter.js](mota-optimal-solver/src/adapter.js)

**新增常量**：

```javascript
const CENTER_FLY_IDS = new Set(['centerFly']);
```

**buildSimplifiedLevel / buildMultiFloorLevel 改动**：

1. 构建 `flightBlockSet`：当处理到 `EMPTY_IDS` 或 `STAIR_IDS` 匹配的图块时，将坐标加入 `flightBlockSet`

```javascript
if (EMPTY_IDS.has(id) || STAIR_IDS.has(id)) {
  if (options.enableCenterFly) {
    flightBlockSet.add(coordKey(x, y));
  }
  continue;
}
```

1. 识别 centerFly 道具：当 `enableCenterFly && CENTER_FLY_IDS.has(id)` 时创建 `kind: 'centerFlyItem'` 动态实体
2. FloorData 返回值加 `flightBlockSet`

### 3.3 [src/pruning.js](mota-optimal-solver/src/pruning.js)

**新增函数**：

```javascript
function isWalkReachable(floor, dynamics, mask, sx, sy, tx, ty) {
  // BFS from (sx,sy)，不穿越未消耗的 monster/door/breakableWall
  // 到达 (tx,ty) → true
}
```

**修正 findUnreachableMask**：增加 `enableCenterFly` 参数

```javascript
function findUnreachableMask(ml, enableCenterFly) {
  // 标准 BFS（门/怪可穿越）→ visited
  if (enableCenterFly) {
    // 对 visited 中的每个位置 (fid, x, y)：
    //   计算对称点 (sx, sy)
    //   如果不是 wall 且不在 flightBlockSet → 从 (sx,sy) 继续 BFS
    // 重复直到无新增
  }
  // 不在 visited 中的实体 → 不可达
}
```

**修正 computeValidDoors**：`isBossReachableWithDoors` 增加飞行模拟

```javascript
function isBossReachableWithDoors(ml, openDoorIndices, enableCenterFly) {
  // BFS 同时追踪 flyUsed 状态
  // 队列元素: { floorId, x, y, flyUsed: boolean }
  // 对每个可达位置：如果 !flyUsed，计算对称点
  //   如果对称点可达 → 入队（flyUsed=true）
}
```

**修正 collectFreeItems / absorbReachableItems**：支持 centerFlyItem 类型

### 3.4 [src/solver.js](mota-optimal-solver/src/solver.js)

**状态扩展**：

```javascript
const startState = {
  ...,
  centerFly: enableCenterFly ? 1 : 0   // 一开始就有
};
```

**stateSignature**：加入 `|${state.centerFly}|`

**飞行分支**（在 4 方向循环之后）：

```javascript
if (current.centerFly > 0) {
  const symX = curFloor.width - 1 - current.x;
  const symY = curFloor.height - 1 - current.y;

  if (symX !== current.x || symY !== current.y) {
    if (curFloor.baseGrid[symY][symX] !== 'wall'
        && !(curFloor.flightBlockSet && curFloor.flightBlockSet.has(coordKey(symX, symY)))) {

      const targetIdx = curFloor.dynamicIndexByPos.get(coordKey(symX, symY));
      const targetBlocked = targetIdx != null && (current.mask & ml.dynamics[targetIdx].bit) === 0n;

      if (!targetBlocked
          && !isWalkReachable(curFloor, ml.dynamics, current.mask, current.x, current.y, symX, symY)) {

        // 构建飞行后状态（centerFly -= 1）
        // 策略 F: absorbReachableItems 吸收目标区域道具
        // 正常 push 到 records/queue
      }
    }
  }
}
```

**动态实体处理**：monster 分支之后加 centerFlyItem 分支：

```javascript
} else if (dynamic.kind === 'centerFlyItem') {
  centerFly += 1;
  mask |= dynamic.bit;
  action = 'getCenterFly';
  detail = { id: dynamic.id, deltaCenterFly: 1 };
}
```

### 3.5 [src/cli.js](mota-optimal-solver/src/cli.js)

- 新增 `--enable-center-fly` 开关
- 传递给 adapter 和 solver
- 路径输出加 `cfly=${step.after.centerFly}`

## 四、复杂度估算

### 状态空间增量


| 因素                          | 增量       |
| --------------------------- | -------- |
| centerFly 维度 (0→1)          | 2x       |
| 每状态额外飞行分支（仅 cfly>0）         | 分支因子 +1  |
| `isWalkReachable` 剪枝（只飞新区域） | ÷ 绝大多数飞行 |
| 策略 F 吸收目标区域道具               | 减少后续排列   |


### 4 层塔中位数估算

```
无飞行器（已有剪枝）:   10^5 - 10^7 状态
+1 飞行器:              10^5 - 10^8 状态（2x-5x）
运行时间:               0.1s - 10s
内存:                   50MB - 500MB
```

### 增量可控的原因

1. 飞行只用 1 次 → centerFly=0 后退化为无飞行搜索
2. `isWalkReachable` 极强 → 绝大多数位置的对称点在同一可达区域
3. absorbReachableItems 飞行后立即收集 → 减少后续状态排列
4. 搜索实质分为"飞行前"和"飞行后"两个子问题，规模各约为原问题的一半


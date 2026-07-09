const form = document.getElementById("towerForm");
const floorsInput = document.getElementById("floors");
const redPotionInput = form.elements.redPotion;
const detailPanel = document.getElementById("detailPanel");
const confirmScaleButton = document.getElementById("confirmScale");
const runButton = document.getElementById("runButton");
const stopButton = document.getElementById("stopButton");
const viewPromptButton = document.getElementById("viewPromptButton");
const promptBox = document.getElementById("promptBox");
const initButton = document.getElementById("initButton");
const envStatus = document.getElementById("envStatus");
const errorBox = document.getElementById("errorBox");
const warningBox = document.getElementById("warningBox");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const logBox = document.getElementById("logBox");
const resultActions = document.getElementById("resultActions");
const playLink = document.getElementById("playLink");
const editorLink = document.getElementById("editorLink");
const exportLink = document.getElementById("exportLink");
const floorConcurrencyInput = document.getElementById("floorConcurrency");
const floorConcurrencyField = document.getElementById("floorConcurrencyField");
const resumeExistingInput = document.getElementById("resumeExisting");
const resumeConcurrencyHint = document.getElementById("resumeConcurrencyHint");
const agentBackendInput = form.elements.agentBackend;
const maxAttemptsInput = form.elements.maxAttempts;

let pollTimer = null;
let currentRunId = null;
const touchedResources = new Set();
const touchedSpecialDamageValues = new Set();
let maxAttemptsTouched = false;

const agentMaxAttemptDefaults = {
  codex: 4,
  opencode: 6,
};

const resourceDefaults = (floors) => ({
  yellowDoors: floors * 4,
  blueDoors: floors * 2,
  yellowKeys: floors * 2,
  blueKeys: floors,
  pickaxes: floors,
  bombs: floors,
  centerFly: floors,
  jumpShoes: 0,
  redGems: floors * 5,
  blueGems: floors * 5,
  greenGems: 0,
  redPotions: floors * 5,
  bluePotions: floors * 2,
  yellowPotions: 0,
  greenPotions: 0,
});

const stageLabels = {
  topology: "地图结构",
  economy: "资源和路线",
  monster: "怪物和战斗",
  integration: "整体",
};

const floorLabel = (rawIndex) => {
  const index = Number(rawIndex);
  return Number.isInteger(index) ? `第 ${index + 1} 层` : `第 ${rawIndex} 层`;
};

const beginnerReviewReason = (summary) => {
  const text = String(summary || "").trim();
  const lower = text.toLowerCase();
  const reasons = [];
  const add = (reason) => {
    if (!reasons.includes(reason)) reasons.push(reason);
  };

  if (lower.includes("local") && lower.includes("passed")) add("基础规则已经通过");
  if (lower.includes("broken-wall") && lower.includes("decorative")) {
    add("还有一些破墙岔路只是装饰，没有形成奖励、路线选择、道具价值或战斗压力");
  }
  if (lower.includes("local topology review failed")) add("地图结构还不合适");
  if (lower.includes("local economy review failed")) add("资源、钥匙门或路线取舍还不合适");
  if (lower.includes("local monster review failed")) add("怪物和战斗压力还不合适");
  if (lower.includes("local integration review failed")) add("整层地图还没有达到可保存标准");
  if (lower.includes("entrance") && lower.includes("exit") && lower.includes("reachable")) {
    add("入口到出口的路线不够通顺");
  }
  if (lower.includes("downfloor")) add("缺少入口楼梯");
  if (lower.includes("upfloor")) add("缺少出口楼梯");
  if (lower.includes("key/door pressure")) add("钥匙和门的安排不够好");
  if (
    (lower.includes("protected resources") || lower.includes("protected reward")) &&
    !(lower.includes("broken-wall") && lower.includes("decorative"))
  ) {
    add("奖励或工具没有被路线、门或怪物保护起来");
  }
  if (lower.includes("enemy type count")) add("这一层怪物种类太多");
  if (lower.includes("at least") && lower.includes("enemies")) add("这一层怪物数量太少");
  if (lower.includes("at most") && lower.includes("enemies")) add("这一层怪物数量太多");
  if (lower.includes("orthogonal adjacency")) add("有些怪物挨得太近");
  if (lower.includes("outside current floor policy") || lower.includes("outside whitelist")) {
    add("使用了当前楼层不允许的怪物");
  }
  if (lower.includes("exceeds whole-tower limit")) add("某类资源超过了整座塔的总量限制");
  if (lower.includes("adjacent wall mask similarity")) add("这一层墙体和相邻楼层太像");
  if (lower.includes("wall ratio")) add("墙的数量不在设置范围内");
  if (lower.includes("gem count progression") || (lower.includes("potion") && lower.includes("progression"))) {
    add("宝石或血瓶的跨层增长不符合设置");
  }
  if (lower.includes("entry-to-gem route is too easy")) add("到宝石的路线太容易，缺少取舍");
  if (lower.includes("large direct resource region")) add("有一大片奖励拿得太直接");
  if (lower.includes("zone/repulse damage")) add("领域或阻击伤害不在设置范围内");
  if (!reasons.length) add("地图还不够好玩，系统正在自动调整");
  return `原因：${reasons.join("；")}。`;
};

const beginnerLogLine = (line) => {
  const original = String(line ?? "");
  const trimmed = original.trim();
  if (!trimmed) return original;

  const integrationMatch = trimmed.match(
    /^MT(\d+) integration review failed on attempt (\d+);\s*repair will restart at ([^:]+):\s*(.*)$/i,
  );
  if (integrationMatch) {
    const [, floor, attempt, repairStage, summary] = integrationMatch;
    const repairLabel = stageLabels[repairStage] || repairStage;
    return `${floorLabel(floor)}第 ${attempt} 次检查没通过，正在从${repairLabel}重新调整。${beginnerReviewReason(summary)}`;
  }

  const stageMatch = trimmed.match(/^MT(\d+) (\w+) review failed on attempt (\d+):\s*(.*)$/i);
  if (stageMatch) {
    const [, floor, stage, attempt, summary] = stageMatch;
    const stageLabel = stageLabels[stage] || stage;
    return `${floorLabel(floor)}第 ${attempt} 次${stageLabel}检查没通过，正在自动重试。${beginnerReviewReason(summary)}`;
  }

  const forcedMatch = trimmed.match(/^MT(\d+) forced accepted.*review skipped/i);
  if (forcedMatch) return `${floorLabel(forcedMatch[1])}已保存，但质量需要生成结束后手动看一下。`;
  const generatedForcedMatch = trimmed.match(/^MT(\d+) generated with forced acceptance/i);
  if (generatedForcedMatch) return `${floorLabel(generatedForcedMatch[1])}已保存，但建议生成结束后手动微调。`;
  const passedMatch = trimmed.match(/^MT(\d+) passed review/i);
  if (passedMatch) return `${floorLabel(passedMatch[1])}检查通过。`;
  const parallelMatch = trimmed.match(/^Parallel floor generation enabled with (\d+) worker/i);
  if (parallelMatch) return `已开始同时生成 ${parallelMatch[1]} 个楼层。`;
  const enemyMatch = trimmed.match(/^Enemy data agent designed (\d+) monster slot/i);
  if (enemyMatch) return `已设计 ${enemyMatch[1]} 个怪物数据。`;
  if (trimmed.startsWith("Build complete:")) return `生成完成：${trimmed.split(":").slice(1).join(":").trim()}`;
  if (trimmed.startsWith("Generated project:")) return `可游玩项目已生成：${trimmed.split(":").slice(1).join(":").trim()}`;
  if (trimmed.toLowerCase().startsWith("error:")) return `出错：${trimmed.split(":").slice(1).join(":").trim()}`;
  const savedCnMatch = trimmed.match(/^MT(\d+)\s+已保存/);
  if (savedCnMatch) return `${floorLabel(savedCnMatch[1])}已保存，质量需要手动检查。`;
  const passedCnMatch = trimmed.match(/^MT(\d+)\s+已通过审查/);
  if (passedCnMatch) return `${floorLabel(passedCnMatch[1])}检查通过。`;
  return original;
};

const showError = (message) => {
  errorBox.textContent = message;
  errorBox.hidden = false;
};

const clearError = () => {
  errorBox.hidden = true;
  errorBox.textContent = "";
};

const showWarnings = (warnings) => {
  const items = Array.isArray(warnings) ? warnings.filter(Boolean) : [];
  if (!items.length) {
    warningBox.hidden = true;
    warningBox.textContent = "";
    return;
  }
  warningBox.textContent = `警告：${items.join(" ")}`;
  warningBox.hidden = false;
};

const clearWarnings = () => showWarnings([]);

const intValue = (data, key, label, min, max, errors) => {
  const value = Number(data[key]);
  if (!Number.isInteger(value)) {
    errors.push(`${label}必须是整数`);
    return value;
  }
  if (value < min) errors.push(`${label}不能小于 ${min}`);
  if (max !== null && value > max) errors.push(`${label}不能大于 ${max}`);
  return value;
};

const floatValue = (data, key, label, min, max, errors) => {
  const value = Number(data[key]);
  if (!Number.isFinite(value)) {
    errors.push(`${label}必须是数字`);
    return value;
  }
  if (value < min) errors.push(`${label}不能小于 ${min}`);
  if (max !== null && value > max) errors.push(`${label}不能大于 ${max}`);
  return value;
};

const validateFormData = (data) => {
  const errors = [];
  const floors = intValue(data, "floors", "楼层数", 1, 20, errors);
  const floorSize = intValue(data, "floorSize", "地图尺寸", 13, 13, errors);
  if (floorSize !== 13) errors.push("地图尺寸固定为 13x13");

  [
    ["hp", "HP", 1],
    ["atk", "ATK", 0],
    ["defense", "DEF", 0],
    ["initialPickaxe", "初始破墙镐", 0],
    ["initialCenterFly", "初始中心对称飞行器", 0],
    ["initialBomb", "初始炸弹", 0],
    ["initialJumpShoes", "初始跳跃靴", 0],
    ["initialBook", "初始怪物手册", 0],
    ["initialYellowKey", "初始黄钥匙", 0],
    ["initialBlueKey", "初始蓝钥匙", 0],
    ["yellowDoors", "黄门", 0],
    ["blueDoors", "蓝门", 0],
    ["yellowKeys", "黄钥匙", 0],
    ["blueKeys", "蓝钥匙", 0],
    ["pickaxes", "破墙镐", 0],
    ["bombs", "炸弹", 0],
    ["centerFly", "中心对称飞行器", 0],
    ["jumpShoes", "跳跃靴", 0],
    ["redGems", "红宝石数量", 0],
    ["blueGems", "蓝宝石数量", 0],
    ["greenGems", "绿宝石数量", 0],
    ["redPotions", "红血瓶数量", 0],
    ["bluePotions", "蓝血瓶数量", 0],
    ["yellowPotions", "黄血瓶数量", 0],
    ["greenPotions", "绿血瓶数量", 0],
    ["redGem", "红宝石 ATK", 0],
    ["blueGem", "蓝宝石 DEF", 0],
    ["greenGem", "绿宝石 MDEF", 0],
    ["redPotion", "红血瓶 HP", 0],
    ["bluePotion", "蓝血瓶 HP", 0],
    ["yellowPotion", "黄血瓶 HP", 0],
    ["greenPotion", "绿血瓶 HP", 0],
  ].forEach(([key, label, min]) => intValue(data, key, label, min, null, errors));

  intValue(data, "maxAttempts", "最大尝试次数", 1, 10, errors);
  const concurrency = intValue(data, "floorConcurrency", "并发数", 1, 4, errors);
  const enemyMin = intValue(data, "enemyMin", "怪物下限", 1, 60, errors);
  const enemyMax = intValue(data, "enemyMax", "怪物上限", 1, 60, errors);
  floatValue(data, "maxWallSimilarity", "相似度上限", 0.1, 1, errors);
  const wallRatioMin = floatValue(data, "wallRatioMin", "墙比例下限", 0.1, 0.9, errors);
  const wallRatioMax = floatValue(data, "wallRatioMax", "墙比例上限", 0.1, 0.9, errors);
  intValue(data, "monsterTypesPerFloor", "每层怪物种类上限", 1, 30, errors);
  intValue(data, "maxSpecialsPerMonster", "每怪特殊能力上限", 1, 3, errors);
  floatValue(data, "floorOverlapRatio", "楼层怪物重叠率", 0, 1, errors);
  const specialDamageValueMin = floatValue(data, "specialDamageValueMin", "领域/阻击伤害下限", 0, null, errors);
  const specialDamageValueMax = floatValue(data, "specialDamageValueMax", "领域/阻击伤害上限", 0, null, errors);
  const gemFloorDeltaMin = floatValue(data, "gemFloorDeltaMin", "宝石增长下限", 0, 10, errors);
  const gemFloorDeltaMax = floatValue(data, "gemFloorDeltaMax", "宝石增长上限", 0, 10, errors);
  const potionFloorDeltaMin = floatValue(data, "potionFloorDeltaMin", "药水增长下限", 0, 10, errors);
  const potionFloorDeltaMax = floatValue(data, "potionFloorDeltaMax", "药水增长上限", 0, 10, errors);
  floatValue(data, "highValuePocketThreshold", "高价值口袋阈值", 0, 20, errors);
  intValue(data, "enemyDesignCount", "怪物表重写数", 0, 200, errors);
  const timeout = intValue(data, "timeoutMinutes", "超时分钟", 10, 120, errors);
  if (![10, 20, 30, 60, 90, 120].includes(timeout)) {
    errors.push("超时分钟只能选择 10、20、30、60、90、120");
  }
  if (Number.isInteger(concurrency) && Number.isInteger(floors) && concurrency > floors) {
    errors.push("并发数不能高于楼层数");
  }
  if (Number.isInteger(enemyMin) && Number.isInteger(enemyMax) && enemyMin > enemyMax) {
    errors.push("怪物下限不能大于上限");
  }
  if (Number.isFinite(wallRatioMin) && Number.isFinite(wallRatioMax) && wallRatioMin > wallRatioMax) {
    errors.push("墙比例下限不能大于上限");
  }
  if (
    Number.isFinite(specialDamageValueMin) &&
    Number.isFinite(specialDamageValueMax) &&
    specialDamageValueMin > specialDamageValueMax
  ) {
    errors.push("领域/阻击伤害下限不能大于上限");
  }
  if (Number.isFinite(gemFloorDeltaMin) && Number.isFinite(gemFloorDeltaMax) && gemFloorDeltaMin > gemFloorDeltaMax) {
    errors.push("宝石增长下限不能大于上限");
  }
  if (Number.isFinite(potionFloorDeltaMin) && Number.isFinite(potionFloorDeltaMax) && potionFloorDeltaMin > potionFloorDeltaMax) {
    errors.push("药水增长下限不能大于上限");
  }
  if (!data.allowedSpecials.length) {
    errors.push("至少选择一个怪物能力");
  }
  if (errors.length) {
    throw new Error(errors.join("；"));
  }
};

const postJson = async (url, payload) => {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.message || `HTTP ${response.status}`);
  }
  return data;
};

const collectForm = () => {
  const data = Object.fromEntries(new FormData(form).entries());
  if (!("floorConcurrency" in data) && floorConcurrencyInput) {
    data.floorConcurrency = floorConcurrencyInput.value;
  }
  for (const [key, value] of Object.entries(data)) {
    if (value !== "" && !Number.isNaN(Number(value))) {
      data[key] = Number(value);
    }
  }
  data.allowedSpecials = [...form.querySelectorAll("input[name='special']:checked")].map((item) =>
    Number(item.value),
  );
  data.resumeExisting = document.getElementById("resumeExisting")?.checked === true;
  data.noAdjacentEnemies = document.getElementById("noAdjacentEnemies")?.checked !== false;
  validateFormData(data);
  const redPotionBase = Math.max(Number(data.redPotion) || 0, 1);
  data.specialDamageMin = Number(data.specialDamageValueMin) / redPotionBase;
  data.specialDamageMax = Number(data.specialDamageValueMax) / redPotionBase;
  return data;
};

const applyResourceDefaults = () => {
  const floors = Math.max(1, Number(floorsInput.value) || 4);
  const defaults = resourceDefaults(floors);
  for (const [name, value] of Object.entries(defaults)) {
    const input = form.elements[name];
    if (input && !touchedResources.has(name)) {
      input.value = value;
    }
  }
};

const applySpecialDamageDefaults = () => {
  if (touchedSpecialDamageValues.size) return;
  const redPotion = Math.max(0, Number(redPotionInput?.value) || 100);
  const minInput = form.elements.specialDamageValueMin;
  const maxInput = form.elements.specialDamageValueMax;
  if (minInput) minInput.value = Math.round(redPotion * 0.5);
  if (maxInput) maxInput.value = Math.round(redPotion);
};

const syncResumeControls = () => {
  const isResume = resumeExistingInput?.checked === true;
  if (floorConcurrencyInput) {
    floorConcurrencyInput.disabled = isResume;
  }
  floorConcurrencyField?.classList.toggle("is-disabled", isResume);
  if (resumeConcurrencyHint) {
    resumeConcurrencyHint.hidden = !isResume;
  }
};

const syncAgentDefaults = () => {
  if (!agentBackendInput || !maxAttemptsInput || maxAttemptsTouched) return;
  const backend = String(agentBackendInput.value || "codex");
  maxAttemptsInput.value = agentMaxAttemptDefaults[backend] || agentMaxAttemptDefaults.codex;
};

const setProgress = (value, message) => {
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  progressBar.style.width = `${pct}%`;
  progressText.textContent = `${pct.toFixed(0)}% · ${message || "运行中"}`;
};

const isActiveState = (state) => state === "queued" || state === "running";

const hasResultLinks = (status) => Boolean(status.play_url && status.editor_url && status.export_url);

const renderResultActions = (status) => {
  if (!hasResultLinks(status)) {
    resultActions.hidden = true;
    return;
  }
  playLink.href = status.play_url;
  editorLink.href = status.editor_url;
  exportLink.href = status.export_url;
  resultActions.hidden = false;
};

const startPolling = (runId) => {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    pollStatus(runId).catch((error) => showError(error.message));
  }, 1800);
};

const renderStatus = (status) => {
  setProgress(status.progress || 0, beginnerLogLine(status.message || status.state || "运行中"));
  logBox.textContent = (status.logs || []).map(beginnerLogLine).join("\n");
  showWarnings(status.warnings);
  if (status.state === "complete") {
    renderResultActions(status);
    runButton.disabled = false;
    stopButton.hidden = true;
    currentRunId = null;
    if (pollTimer) clearInterval(pollTimer);
  } else if (status.state === "error") {
    renderResultActions(status);
    runButton.disabled = false;
    stopButton.hidden = true;
    currentRunId = null;
    if (hasResultLinks(status)) {
      clearError();
    } else {
      showError(status.message || "生成失败");
    }
    if (pollTimer) clearInterval(pollTimer);
  }
};

const pollStatus = async (runId) => {
  const response = await fetch(`/api/status?run_id=${encodeURIComponent(runId)}`);
  const status = await response.json();
  if (!response.ok) {
    throw new Error(status.error || status.message || `HTTP ${response.status}`);
  }
  renderStatus(status);
};

const startRun = async () => {
  clearError();
  clearWarnings();
  try {
    const payload = collectForm();
    resultActions.hidden = true;
    logBox.textContent = "";
    setProgress(0, "准备中");
    runButton.disabled = true;
    stopButton.hidden = false;
    const data = await postJson("/api/run", { form: payload });
    currentRunId = data.run_id;
    setProgress(0, "排队中");
    startPolling(data.run_id);
    await pollStatus(data.run_id);
  } catch (error) {
    runButton.disabled = false;
    stopButton.hidden = true;
    currentRunId = null;
    showError(error.message);
  }
};

const viewFullPrompt = async () => {
  clearError();
  try {
    const payload = collectForm();
    const data = await postJson("/api/prompt", { form: payload });
    const prefix = payload.resumeExisting
      ? "继续上次未完成生成会复用上次输出目录中的 tower_brief.json，不会使用当前基础/高级配置生成新的 brief；系统只会用原始请求补齐旧 brief 缺失的资源和初始工具字段，继续模式会按楼层顺序修复，不使用并发数。\n\n当前表单对应的新建提示词如下：\n\n"
      : "";
    promptBox.textContent = `${prefix}${data.prompt}`;
    promptBox.hidden = false;
  } catch (error) {
    showError(error.message);
  }
};

const stopRun = async () => {
  if (!currentRunId) return;
  clearError();
  const runId = currentRunId;
  stopButton.disabled = true;
  try {
    await postJson("/api/stop", { run_id: runId });
    if (pollTimer) clearInterval(pollTimer);
    currentRunId = null;
    resultActions.hidden = true;
    clearWarnings();
    setProgress(0, "已终止并删除本次产物");
    logBox.textContent = "";
    runButton.disabled = false;
    stopButton.hidden = true;
    stopButton.disabled = false;
  } catch (error) {
    stopButton.disabled = false;
    showError(error.message);
  }
};

const restoreLatestRun = async () => {
  try {
    const response = await fetch("/api/latest-run");
    if (response.status === 404) return;
    const status = await response.json();
    if (!response.ok) throw new Error(status.error || status.message || `HTTP ${response.status}`);
    if (isActiveState(status.state)) {
      currentRunId = status.run_id;
      runButton.disabled = true;
      stopButton.hidden = false;
      startPolling(status.run_id);
    }
    renderStatus(status);
  } catch (error) {
    showError(error.message);
  }
};

const loadHealth = async () => {
  try {
    const response = await fetch("/api/health");
    const health = await response.json();
    if (!response.ok) throw new Error(health.error || `HTTP ${response.status}`);
    if (health.mota_exists && health.index_exists && health.editor_exists) {
      envStatus.textContent = `mota-js 就绪 · ${health.mota_root}`;
      initButton.disabled = true;
    } else {
      envStatus.textContent = "mota-js 未就绪";
      initButton.disabled = false;
    }
  } catch (error) {
    envStatus.textContent = "环境检测失败";
    showError(error.message);
  }
};

const initMota = async () => {
  clearError();
  initButton.disabled = true;
  envStatus.textContent = "初始化中";
  try {
    const data = await postJson("/api/init", {});
    envStatus.textContent = data.message || "mota-js 就绪";
    await loadHealth();
  } catch (error) {
    initButton.disabled = false;
    showError(error.message);
    await loadHealth();
  }
};

confirmScaleButton.addEventListener("click", () => {
  detailPanel.setAttribute("aria-disabled", "false");
  applyResourceDefaults();
  detailPanel.scrollIntoView({ behavior: "smooth", block: "start" });
});

floorsInput.addEventListener("input", () => {
  applyResourceDefaults();
});

redPotionInput?.addEventListener("input", () => {
  applySpecialDamageDefaults();
});

maxAttemptsInput?.addEventListener("input", () => {
  maxAttemptsTouched = true;
});

agentBackendInput?.addEventListener("change", syncAgentDefaults);

resumeExistingInput?.addEventListener("change", syncResumeControls);

form.querySelectorAll(".resource-input").forEach((input) => {
  input.addEventListener("input", () => touchedResources.add(input.name));
});

form.querySelectorAll("input[name='specialDamageValueMin'], input[name='specialDamageValueMax']").forEach((input) => {
  input.addEventListener("input", () => touchedSpecialDamageValues.add(input.name));
});

runButton.addEventListener("click", startRun);
stopButton.addEventListener("click", stopRun);
viewPromptButton.addEventListener("click", viewFullPrompt);
initButton.addEventListener("click", initMota);

applyResourceDefaults();
applySpecialDamageDefaults();
syncAgentDefaults();
syncResumeControls();
loadHealth().then(restoreLatestRun);

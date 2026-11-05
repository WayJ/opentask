# E49 Design：Formula Display v2 — color scale + icon sets · CLI 1.33.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E49  
基线：`sprint/E48-S1` @ `e84fd12`（全文 `e84fd12bee48f6ea9b9f32a13d4d98cc94df100c`；design `88ea4e8`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E49-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E50**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E49-S1`。开放问题 Q1–Q6 均按建议默认关闭。建议路径  
`docs/superpowers/specs/2026-11-05-e49-formula-display-color-scale-icon-sets-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E48 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 thin → Formula query surfaces v2（含 Display **离散 tint** 条件格式）→ WS Activity Feed → SLA first-response + pause timeline。

E48 附录与 E42–E47 附录仍把下一刀标为（不绑定）：

1. **专用 webhook** `issue.cycle_changed` / `issue.estimate_changed`（± `project_changed` / `sla_paused`）— **偏薄**；timeline + `issue.updated.changed[]` 已覆盖大半  
2. **SLA 营业日历 / 时区 / 节假日 / 策略优先级**（完整运维面）— 易爆；E48 刚交 first-response，宜拆薄或再沉淀  
3. **Formula 色阶（连续 color scale）/ 图标集条件格式** — E46 离散 tint 的自然加厚；列表/看板「看得见」闭环  
4. Activity Feed 加厚（反应/订阅/推送）— E47 刚交薄 FE；宜沉淀  
5. Formula 物化 emit — **明确永不**

代码实证 @ `e84fd12`：

| 面 | 现状 |
|----|------|
| Display `conditionalFormats[]` | E46：≤10；`when{field,op,value}` + `style.rowTint` 枚举 tint；客户端先匹配先生效；**无**连续色阶 / 图标集 |
| Formula | E43 等值 + E46 range/sort；E40 D2/D7 **永不 emit** |
| Webhook | E44 包：assignee/label/CF/sla_breached；**无**专用 cycle/estimate/project/sla_paused 事件名 |
| SLA | E42–E45–E48：time_in_status + first_response + pause + breach→automation；**无**营业时/节假日/策略优先级 |
| Activity | E47 JSON 游标薄 FE；pause 动作已可自然出现 |
| CLI | **1.32.0**；下一刀 **1.33.0** |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Formula Display v2**：在 E46 离散 tint 之上加 **连续 color scale**（number/date）+ **图标集**（枚举 icon）；扩展 Display prefs JSON；List/Board 渲染；CLI **1.33.0**；守 no-emit | **中厚且连贯**；闭合多轮附录 #3；对齐 Linear/表格「色阶/图标看数」；不碰 SLA 运维面 / 薄 webhook 重命名 |
| B | 专用 `cycle_changed`/`estimate_changed`/`project_changed`/`sla_paused` webhook（± 订阅事件过滤 UI） | 单事件名 **过薄**；若捆「订阅过滤 + FE」可抬到中厚，但集成面 ROI 低于 Display 闭环 |
| C | SLA business hours **thin**（WS timezone + 周内营业时段；**无**节假日表 / 策略优先级矩阵） | 中厚运维；但 E48 刚交 SLA metric，次日再加 deadline 语义易溢 |
| D | Activity Feed 加厚（反应/订阅/推送） | E47 宜沉淀；产品化 UI 重 |
| E | Formula emit / 物化写路径 | 打破 E40 D7；**永不本轮** |

**拍板：A（Formula Display v2 — color scale + icon sets）。**  
专用 cycle/estimate webhook、SLA business-hours thin 列入附录供 E50+。

自检：色阶/图标 schema、与 E46 tint 并存、客户端求值边界、权限、FE/CLI **1.33.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| 专用 cycle/estimate webhook | 薄；E41 timeline + `changed[]` 已覆盖；可挂 E50 小刀或与订阅过滤捆 |
| SLA 营业日历 / 优先级完整面 | 运维+测试爆炸；与「中厚可控」冲突；若选须收成 business-hours thin |
| Activity Feed 加厚 | E47 刚交；宜沉淀 |
| Formula 物化 emit | 打破 E40 D7；**永不本轮** |

## 1. 目标

成功标准：用户可在 Issue Display 上配置 **连续色阶**（对 number/date 字段——含 formula 结果与 stored CF）与 **图标集**（枚举 icon 按规则映射）；与 E46 离散 `rowTint` 规则 **并存**（tint 先匹配先生效）；List/Board 客户端求值渲染；跨租户隔离；非法 schema 被 normalize 丢弃或 400（对齐 E46）；CLI **1.33.0**；**不**引入 formula emit / 营业日历 / 新 webhook 事件名 / 进程内 cron。

### A · Color scale（Display JSON + FE）

- 独立数组 `colorScales[]`（**Q1a**）  
- 每条：`id` / `field`（`cf:<key>` 或内建 number/date 字段白名单）/ `domain: { min, max }`（**Q2a** 仅手动；无 auto）/ `palette`（固定枚举 **Q3a**：`blue_red` / `green_red` / `mono` 等 3–5 套）/ `target: cell|row`  
- 仅 number/date（formula_result_type 或 stored type）；其它类型忽略  
- 客户端线性插值 → 背景色；**E46 tint 先匹配先生效；未命中再应用 scale**（**Q4a**）  
- cap：≤5 scales（与 E46 ≤10 rules 分开计）

### B · Icon sets（Display JSON + FE）

- 独立数组 `iconSets[]`：`id` / `field` / `rules[]`（`op`+`value`→`icon` 枚举）  
- 图标枚举固定（**Q5a**）：`arrow_up` / `arrow_down` / `arrow_flat` / `flag` / `dot_red` / `dot_yellow` / `dot_green` / `check` / `warn`；**禁止**任意 URL/自定义 SVG 上传  
- 渲染于 cell 前缀或独立列指示；不影响 sort/filter  
- cap：≤5 sets；每 set rules ≤8

### C · BE

- `display_prefs` normalize/validate 接纳新键；超限/非法丢弃或 400（对齐 E46）  
- **无 migration**（**Q6a**；JSON prefs）  
- **不**因 Display 读写触发 automation/webhook；formula **no-emit** spy 守住

### D · FE

- Display Options：色阶 / 图标集编辑器（字段选择、min/max、palette、icon 映射）  
- List + Board：cell/row 应用；与现 `resolveRowTint` 共存（tint > scale）  
- vitest：normalize、优先级、渲染 helper

### E · CLI **1.33.0**

- 若已有 display prefs CLI：读写示例含 colorScales/iconSets；否则 version bump + help 指向 API/FE；钉 pyproject/`__init__`/setup/`VERSION`  
- 历史 version 断言 → **1.33.0**

## 2. 安全 / 租户 / 威胁模型

- Display prefs 仍按 workspace + user/view 现网隔离；跨租户 404  
- 字段白名单防任意路径注入；palette/icon 枚举防 XSS（无用户 HTML/URL）  
- 客户端求值；服务端只校验形状；读路径 **no-emit**  
- 无进程内 cron / Redis；无营业时注入

## 3. 非目标

- Formula 物化 emit（E40 D2/D7）  
- 完整 spreadsheet 规则引擎 / 跨列公式 / 自由 CSS  
- 自定义上传图标 / 任意 hex（Q3a 固定枚举）  
- domain `auto`（当前页 min/max）  
- 专用 `issue.cycle_changed` / `estimate_changed` / `sla_paused` webhook  
- SLA 营业日历 / 节假日 / 策略优先级  
- Activity Feed 反应/订阅/推送加厚  
- Redis / 进程内 cron；远程 push / 开 PR / 自开 E50

## 4. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 可保存合法 `colorScales[]` / `iconSets[]`；超限/非法被拒或 normalize 掉；与 E46 tint 并存 |
| B | number/date（含 formula）按手动 domain 插值着色；非 number/date 忽略 |
| C | icon 枚举按规则显示；未知 icon 丢弃 |
| D | List/Board 可见；tint 命中优先于 scale |
| E | 跨租户隔离；读 Display **无** emit / 无 webhook/automation |
| F | FE 编辑器 + vitest 绿；build ok |
| G | CLI **1.33.0** + version 断言 |
| 门禁 | BE 定向+全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E50 |

## 5. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = **Formula Display v2（color scale + icon sets）**（方案 A）；**无**日历大战 / 薄 webhook 单包 |
| D2 | 独立 `colorScales[]` / `iconSets[]`（Q1a）；与 E46 `conditionalFormats` 并存 |
| D3 | domain 仅手动 min/max（Q2a）；固定 palette 枚举（Q3a）；tint > scale（Q4a） |
| D4 | 图标小枚举 Q5a；禁止自定义 URL/SVG |
| D5 | **无 migration**（Q6a；JSON display prefs） |
| D6 | 仅 number/date；客户端求值 |
| D7 | CLI = **1.33.0** |
| D8 | 守 E40 D2/D7：本 Epic **永不** formula emit；非目标见 §3；不 push；不自开 E50 |

## 6. 测试要点

- BE：normalize 边界；超限；非法 field/palette/icon  
- FE：插值、优先级、Board/List helper；vitest  
- CLI：1.33.0 pins  
- spy：Display 读/写路径无 formula emit；无额外 webhook

## 7. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE normalize + 单测（TDD）  
3. FE helpers + Display 面板（TDD）  
4. List/Board 接线  
5. CLI 1.33.0  
6. 门禁 + acceptance tip  

## 8. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | 色阶/图标用独立数组，还是塞进 `conditionalFormats[].style`？ | **Q1a** 独立 `colorScales[]` + `iconSets[]` |
| Q2 | domain：手动 min/max，还是支持 `auto`？ | **Q2a** 仅手动 min/max |
| Q3 | palette：仅固定枚举，还是受限 hex？ | **Q3a** 固定枚举（`blue_red` / `green_red` / `mono` 等） |
| Q4 | 与 E46 tint 优先级？ | **Q4a** tint 先匹配先生效；未命中再 scale |
| Q5 | 图标词汇表范围？ | **Q5a** `arrow_up/down/flat` / `flag` / `dot_red/yellow/green` / `check` / `warn` |
| Q6 | 是否本轮加 alembic migration？ | **Q6a 否** |

---

## 附录 · 本轮未选但仍高 ROI（供 E50+ / runners-up）

1. **专用 webhook pack** `issue.cycle_changed` / `issue.estimate_changed`（+ 可选 `project_changed` / `sla_paused`）— 默认偏薄；若改选建议捆「订阅事件过滤 FE」抬到中厚。  
2. **SLA business hours thin**：WS `timezone` + 周内营业时段窗口重算 `deadline_at`；**明确砍**节假日表 / 策略优先级矩阵 — 中厚运维，E48 沉淀后再开。  
3. Activity Feed 加厚（反应、订阅、推送）— E47 沉淀后再开。  
4. Formula 物化 emit — **明确永不**（除非单独立项重审 E40 D7）。

## CLI 版本

**1.33.0**

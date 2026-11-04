# E48 Design：SLA first-response metric + pause timeline · CLI 1.32.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E48  
基线：`sprint/E47-S1` @ `c963793`（全文 `c9637936e8372a35c46cbf0ae848f50e16671708`；design `5ab2400`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E48-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E49**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E48-S1`。开放问题 Q1–Q6 均按建议默认关闭。建议路径  
`docs/superpowers/specs/2026-11-05-e48-sla-first-response-pause-timeline-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E47 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 thin（pause + breach→automation）→ Formula query surfaces v2 → WS Activity Feed v1。  
E47 附录与 E42–E46 附录反复把下一刀标为：

1. **SLA first-response metric + pause timeline**（`sla_paused`/`sla_resumed`）— **不含**营业日历 / 策略优先级大战；E45 已沉淀两轮（E46 Formula、E47 Feed）  
2. **专用 webhook** `issue.cycle_changed` / `issue.estimate_changed`（+ 可选 `project_changed`）— 薄；timeline + `issue.updated.changed[]` 已覆盖大半  
3. SLA 营业日历 / 时区 / 节假日 / 策略优先级（完整运维面）— 易爆设置 UI  
4. Formula 色阶（连续 color scale）/ 图标集条件格式 — UI 抛光  
5. Formula 物化 emit — **明确永不**

代码实证 @ `c963793`：

| 面 | 现状 |
|----|------|
| SLA policy | `metric` 仅 `time_in_status`（`SLA_METRICS` 单元素）；`pause_statuses` / 时钟 `paused` / `elapsed_before_pause_minutes` / `segment_started_at` 已落地（E45） |
| SLA clock | `running\|paused\|met\|breached\|cancelled`；`run_due` 只扫 `running`；breach → Inbox + webhook + automation |
| Timeline | E41 已有 `cycle_changed` / `estimate_changed` / `custom_field_changed` 等；**无** `sla_paused` / `sla_resumed`（E45 Q4b 刻意砍） |
| Activity Feed | E47 已可读跨 Issue timeline；新增 pause 动作会自然出现在 Feed / CSV |
| Webhook | E44 包：assignee/label/CF/sla_breached；**无**专用 cycle/estimate 事件名 |
| Formula | E40 D2/D7 **永不 emit** — 本轮继续守 |
| CLI | **1.31.0**；下一刀 **1.32.0** |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **SLA first-response + pause timeline**：策略可配 `metric=first_response`；首响事件停表/标 met；pause/resume 写 `sla_paused`/`sla_resumed` timeline；FE/CLI **1.32.0**；**无**营业日历 / 优先级矩阵 | **中厚且连贯**；闭合多轮附录 #1；对齐 Linear/支持台「首响 SLA」；pause 审计补齐 E45 缺口；不碰运维日历面 |
| B | 专用 `cycle_changed`/`estimate_changed` webhook（± pause timeline） | **偏薄**；事件名可由 timeline + `changed[]` 覆盖；单独不够撑 Epic |
| C | 完整营业日历 / 时区 / 节假日 / 策略优先级 | 运维+测试面大；单 sprint 必溢 |
| D | Formula 色阶 / 图标集 | UI-only；ROI 低于 SLA 产品闭环 |
| E | Formula emit / 物化写路径 | 打破 E40 D7；**永不本轮** |

**拍板：A（SLA first-response metric + pause timeline · 无日历大战）。**  
专用 cycle/estimate webhook、营业日历、Formula 色阶列入附录供 E49+。

自检：metric 语义边界、首响定义、pause timeline 与 no-spam、与 E45 时钟/E47 feed 并存、CLI **1.32.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| 专用 `cycle_changed` / `estimate_changed` webhook | 薄；E41 timeline + `issue.updated.changed[]` 已覆盖；可挂 E49 小刀 |
| SLA 营业日历 / 策略优先级 | 运维矩阵 + FE 设置爆炸；刻意与 first-response **拆开** |
| Formula 色阶 / 图标集 | UI 抛光；非中厚产品闭环 |
| Formula 物化 emit | 打破 E40 D7；**永不本轮** |
| Activity Feed 加厚（反应/订阅/推送） | E47 刚交薄 FE；宜沉淀 |

## 1. 目标

成功标准：WS 可配置 **first_response** SLA 策略（与既有 `time_in_status` 并存）；Issue 进入策略 start 条件后启动首响时钟；**非创建者首条 comment** 发生时时钟 **met**（未逾则 met，逾则仍可由 `run_due` breach）；pause/resume 状态迁移写入 **`sla_paused` / `sla_resumed` timeline**（对两种 metric 的 pause 路径均生效）；详情徽标区分 first-response；跨租户隔离；FE 设置 + 徽标 + timeline 文案；CLI **1.32.0**；**不**引入营业日历 / 策略优先级 UI / formula emit / 进程内 cron；**不**因 pause timeline 单独 fire webhook/automation。

### A · Metric：`first_response`（BE）

- `SLA_METRICS` += `"first_response"`（保留 `"time_in_status"`）  
- 策略 CRUD：`metric` 可设为 `first_response`；校验仍限枚举  
- **时钟复用** `issue_sla_clocks`（同表；按 `policy.metric` 分流行为）— **无新表**  
- 启动：Issue 状态进入 `start_statuses` 且无活跃钟 → 建 `running`（同 E42/E45）；`target_minutes` / pause / stop 优先级 **stop > pause > start** 不变（**Q4a**）  
- **停表（met）触发 = 首响（Q1a + Q2b）**：Issue 上出现 **非创建者** 的首条 **comment**（`TimelineAction.COMMENTED` / create_comment 路径），评论作者 ≠ issue.creator；**assignee 分配不算首响**  
- 首响发生时：若 clock `running|paused` → `met` + `stopped_at=now`；**不**再跑 breach；payload 记 `responseKind=comment` / `actorId`  
- `run_due`：与 time_in_status 相同——仅 `running AND deadline_at<=now` → breach + Inbox + webhook + `fire_automations(issue.sla_breached)`（事件名复用；payload 增 `metric`）  
- **paused 永不 tick breach**（E45 不变）  
- 策略删除/禁用 → 活跃钟 `cancelled`（同现网）  
- 同一 Issue 上允许 `time_in_status` + `first_response` 两策略并存（**Q5a**；每 policy 独立钟）

### B · Pause timeline（BE）

- `TimelineAction` += `SLA_PAUSED = "sla_paused"` / `SLA_RESUMED = "sla_resumed"`（字符串枚举；**无** DB migration）  
- 在 `SlaService.sync_clocks` 的 pause / resume 分支（同事务）：  
  - running→paused → append timeline `sla_paused`（payload：`policyId` / `policyName` / `metric` / `elapsedBeforePauseMinutes` / `fromStatus`/`toStatus`）  
  - paused→running → append `sla_resumed`（payload：`remainingMinutes` / `newDeadlineAt` / …）  
- **对两种 metric 均写**  
- stop/met/breach/cancel **不**额外写 pause 类 timeline  
- Activity Feed / E41 CSV / 单 Issue timeline **自动可见**（E47 已共享 query）  
- **不**因 pause timeline 单独 `fire_webhooks` / `fire_automations`（**Q3a**）

### C · FE

- `/settings/sla`：metric 下拉增加「首次响应」；帮助文案：非创建者首条评论算首响；指派不算  
- Issue 详情 SLA 徽标：`first_response` 文案区分（如「首响 SLA」）；`paused` 仍琥珀色  
- Issue timeline / Activity 文案 map：`sla_paused` / `sla_resumed`  
- Automations：`issue.sla_breached` 帮助注明含 first_response 违约  
- vitest：metric 选项；timeline 文案；徽标分支

### D · CLI **1.32.0**

- `sla policy create|update`：`--metric first_response|time_in_status`（或 json-body）  
- `sla issue` 输出含 `metric`  
- help 示例 1–2 行（首响策略）  
- version → **1.32.0**；pyproject / `__init__` / setup / `VERSION` 全钉；历史 version 断言同步

### E · 数据模型摘要

- **无 migration（Q6a）**：`metric` 已是 String(32)；timeline `action_type` 已是枚举字符串；首响语义写死为 Q1a+Q2b（无策略级布尔列）  
- **不改**：formula emit；HMAC；营业日历表；策略优先级列；webhook 事件集

## 2. 安全 / 租户 / 威胁模型

- 一切 query/tick/timeline 带 `workspace_id`；跨租户 404  
- 策略写：owner；run-due：member+（对齐 E42/E45）  
- 首响判定只用本 WS Issue/comment；防把其它租户评论算入；creator 自评不算  
- pause timeline 与 clock 同事务  
- 读路径（Feed/CSV）仍 **no-emit**；pause **写** timeline 但不 fire webhook/automation（Q3a）  
- 无进程内 cron / Redis；无营业时注入

## 3. 非目标

- 营业时间 / 时区矩阵 / 节假日日历 / 策略优先级 / IssueType·项目覆盖  
- resolution / 多阶段 metric 矩阵（仅 first_response 一刀）  
- assignee 算首响 / 策略级可配触发器  
- 专用 `issue.cycle_changed` / `estimate_changed` / `sla_paused` webhook  
- Formula 色阶 / 图标集；Formula 物化 emit（E40 D2/D7）  
- Activity Feed 反应/订阅/推送加厚  
- Redis / 进程内 cron；远程 push / 开 PR / 自开 E49

## 4. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 可创建 `metric=first_response` 策略；非法 metric → 400；与 `time_in_status` 策略可并存 |
| B | Issue 进入 start → 首响钟 running；非创建者首评 → met + stopped_at；创建者自评不算；未响且超时 → run_due breach（Inbox+webhook+automation），payload 含 metric |
| C | pause 路径：running→paused / paused→running 写 `sla_paused`/`sla_resumed`；Activity/单 Issue timeline 可见；time_in_status 与 first_response 均覆盖 |
| D | paused 钟不被 run_due breach；stop 优先于 pause（E45 回归） |
| E | 跨租户隔离；viewer 可读徽标/timeline；策略写权限不变 |
| F | FE metric 选项 + 文案 + 徽标；vitest 绿 |
| G | CLI **1.32.0** + metric 参数/输出 + version 断言 |
| H | spy：读 Feed **无** emit；pause timeline **无** fire_webhooks/fire_automations |
| 门禁 | BE 定向+全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E49 |

## 5. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = **SLA first-response metric + pause timeline**（方案 A）；**无**营业日历 / 优先级大战 |
| D2 | `SLA_METRICS` += `first_response`；复用 `issue_sla_clocks`；行为按 `policy.metric` 分流 |
| D3 | 首响 = **非创建者首条 comment**（Q1a）；**assignee 不算**（Q2b） |
| D4 | Pause/resume → timeline `sla_paused`/`sla_resumed`；对所有 metric；**不**单独 webhook/automation（Q3a） |
| D5 | breach 事件名仍 `issue.sla_breached`；payload 增 `metric` |
| D6 | 沿用同一套 start/stop/pause 状态集（Q4a）；双 metric 并存允许（Q5a） |
| D7 | **无 migration**（Q6a） |
| D8 | CLI = **1.32.0** |
| D9 | 守 E40 D2/D7：本 Epic **永不** formula emit；非目标见 §3；不 push；不自开 E49 |

## 6. 测试要点

- BE：first_response 启停/met；超时 breach；与 time_in_status 同 Issue 多策略互不踩踏（每 policy 一钟）  
- BE：creator 自评 **不**算首响；他评算；跨 WS 评论不可见；assignee 变更不算  
- BE：pause/resume timeline 条数与 payload；Activity 过滤 `actionType=sla_paused`  
- BE：E45 回归 pause 不计时 / run_due 跳过 paused  
- FE：metric 文案；timeline map；徽标  
- CLI：1.32.0；`--metric first_response`  
- spy：读路径 no-emit；pause 写路径无 webhook/automation

## 7. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. TimelineAction + sync_clocks pause/resume 写审计（TDD）  
3. first_response metric 启停/met/breach（TDD）  
4. FE 设置/徽标/文案  
5. CLI 1.32.0  
6. 门禁 + acceptance tip  

## 8. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | 首响事件定义？ | **Q1a** 非创建者首条 comment |
| Q2 | assignee 首次分配是否算首响？ | **Q2b 否**（仅 comment） |
| Q3 | `sla_paused`/`sla_resumed` 是否 fire webhook/automation？ | **Q3a 否**（仅 timeline） |
| Q4 | 是否沿用同一套 start/stop/pause 状态集？ | **Q4a 是** |
| Q5 | 同一 Issue 上双 metric 策略？ | **Q5a 允许** |
| Q6 | 是否本轮加 migration？ | **Q6a 否** |

---

## 附录 · 本轮未选但仍高 ROI（供 E49+ / runners-up）

1. **专用 webhook** `issue.cycle_changed` / `issue.estimate_changed`（+ 可选 `project_changed` / `sla_paused`）— 薄；订阅方强需求时再拆。  
2. **SLA 营业日历 / 时区 / 节假日 / 策略优先级**（完整运维面）— 与 first-response 刻意拆开。  
3. Formula 色阶（连续 color scale）/ 图标集条件格式。  
4. Activity Feed 加厚（反应、订阅、推送）— E47 沉淀后再开。  
5. Formula 物化 emit — **明确永不**（除非单独立项重审 E40 D7）。

## CLI 版本

**1.32.0**

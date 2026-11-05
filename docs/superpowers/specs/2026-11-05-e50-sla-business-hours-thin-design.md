# E50 Design：SLA business hours thin — timezone + weekday windows · CLI 1.34.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E50  
基线：`sprint/E49-S1` @ `c1085d9`（全文 `c1085d944e265281b1b3f626c26ece175b0453b9`；feature tip `9d4ebfe`；design `39b2f79`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E50-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E51**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E50-S1`。开放问题 Q1–Q6 均按建议默认关闭。建议路径  
`docs/superpowers/specs/2026-11-05-e50-sla-business-hours-thin-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E49 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 thin → Formula query surfaces v2 → WS Activity Feed → SLA first-response + pause timeline → Formula Display v2（色阶 + 图标集）。

E49 附录与 E42–E48 附录仍把下一刀标为（不绑定）：

1. **专用 webhook** `issue.cycle_changed` / `issue.estimate_changed`（± `project_changed` / `sla_paused`）— **偏薄**；timeline + `issue.updated.changed[]` 已覆盖大半；若捆「订阅事件过滤 FE」可抬到中厚  
2. **SLA business hours thin**：WS `timezone` + 周内营业时段窗口重算 `deadline_at`；**明确砍**节假日表 / 策略优先级矩阵 — **中厚运维**；E48 first-response 后已隔一轮 Display（E49）沉淀  
3. Activity Feed 加厚（反应/订阅/推送）— E47 薄 FE 后已隔 E48/E49；仍偏产品化 UI 重  
4. Formula 物化 emit — **明确永不**

代码实证 @ `c1085d9`：

| 面 | 现状 |
|----|------|
| SLA policy | `metric∈{time_in_status,first_response}`；`pause_statuses`；`target_minutes` 墙钟分钟；**无** timezone / 营业时段 |
| SLA clock | `deadline_at = now + target_minutes`（pause 时按剩余墙钟重算）；`run_due` 扫 `deadline_at <= now` |
| Workspace | **无** `timezone` 列 / 营业日历字段（仅 cycles/git hooks 等） |
| Webhook | E44 包：assignee/label/CF/sla_breached；**无**专用 cycle/estimate/project/sla_paused 事件名 |
| Activity | E47 JSON 游标薄 FE；无反应/订阅 |
| Formula Display | E46 tint + E49 colorScales/iconSets；E40 D2/D7 **永不 emit** |
| CLI | **1.33.0**；下一刀 **1.34.0** |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **SLA business hours thin**：WS IANA timezone + 周内营业窗口；`deadline_at` / `run_due` / pause 续跑按 **营业分钟** 计数；FE 薄设置；CLI **1.34.0**；**无**节假日表 / 策略优先级矩阵 / 多日历 | **中厚且连贯**；闭合 SLA 弧（E42→E45→E48→E50）；对齐 Linear/支持台「营业时 SLA」；砍掉日历大战 |
| B | 专用 webhook pack + 订阅事件过滤 FE | 中厚集成面；ROI 低于 SLA 语义闭环 |
| C | Activity Feed 加厚 | UI 重；E47 宜继续沉淀 |
| D | 完整营业日历（节假日 + 优先级矩阵） | **单 sprint 必溢** |
| E | Formula emit | 打破 E40 D7；**永不本轮** |

**拍板：A（SLA business hours thin — timezone + weekday windows）。**  
专用 webhook pack、Activity 加厚列入附录供 E51+。

自检：营业分钟语义、与 E45 pause / E48 first_response 并存、存储落点、迁移边界、FE/CLI **1.34.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| 专用 cycle/estimate webhook（± 订阅过滤 FE） | 集成抛光；语义价值低于「deadline 真按营业时走」；可挂 E51 |
| Activity Feed 加厚 | 产品化 UI Epic；E47 API 已够读 |
| 完整节假日/优先级大战 | 运维+测试爆炸；本轮刻意 thin |
| Formula 物化 emit | 打破 E40 D7；**永不本轮** |

## 1. 目标

成功标准：工作区可配置 **IANA timezone** + **周内营业时段窗口**；SLA 时钟的 `deadline_at` 与 `run_due` / pause-resume 剩余时间按 **营业分钟**（非纯墙钟）计算；关闭营业时功能时行为 **回退** 到现网墙钟语义；跨租户隔离；FE 薄设置面；CLI **1.34.0**；**不**引入节假日表 / 策略优先级矩阵 / 专用新 webhook 事件名 / formula emit / 进程内 cron。

### A · 营业时模型（BE）

- **Timezone**：IANA 名（如 `Asia/Shanghai`）；非法名 400  
- **Weekday windows**：周一…周日各 0..2 段 `{start, end}`（本地 `HH:MM`，半开 `[start,end)`）（**Q6a**）；空日 = 全日非营业；倒置/重叠 normalize 合并或 400  
- **启用开关**：`businessHoursEnabled`（默认 false → 现网墙钟）  
- 落点：**Workspace 级**（**Q1a**）；本轮 **不允许** policy 覆盖（**Q2a**）  
- 辅助纯函数：`add_business_minutes(start_utc, minutes, tz, windows) → deadline_utc`；`elapsed_business_minutes(a,b,...)`  
- pause：暂停期间 **不计** 营业分钟；resume 用剩余营业分钟重算 `deadline_at`；`elapsed_before_pause_minutes` 在 enabled 时语义为营业分钟（**Q4a**）  
- `run_due`：仍扫 `status=running AND deadline_at <= now`（deadline 已按营业时写出）  
- first_response / time_in_status **共用**同一营业时加法器  
- 配置变更后：写配置事务内批量重算该 WS `running`/`paused` 的 `deadline_at`（**Q5a**；封顶条数防炸，超额记日志）

### B · 存储 / migration（**Q3a**）

- Alembic：`workspaces.timezone`（nullable string）+ `workspaces.business_hours`（JSON：`{enabled, windows}`）  
- **禁止**节假日表新实体；**禁止**优先级矩阵列  
- SQLite/PG 双测

### C · FE

- WS 设置（或 SLA 设置旁）：timezone 选择 + 周历时段编辑（薄；可「工作日 09–18 一键」）+ enabled 开关  
- Issue SLA 徽标：可选展示「营业时」提示（非必须）  
- vitest：窗口归一化 / 非法时段

### D · CLI **1.34.0**

- `workspace` / `sla` 读写 timezone + business hours；`sla run-due` 行为说明更新  
- 钉 pyproject / `__init__` / setup / `VERSION`；历史 version 断言 → **1.34.0**

### E · 安全 / 租户

- 配置读写按 WS 成员权限（admin 写，见现网 SLA settings）  
- 跨租户 404；IANA / 窗口白名单防注入  
- 配置变更 **不** fire webhook/automation（除既有 breach 路径）；守 formula **no-emit**

## 2. 非目标

- 节假日 / 例外日表 / 国家日历包  
- 策略优先级矩阵 / policy 级营业时覆盖 / 多策略冲突 UI  
- 专用 `issue.cycle_changed` / `estimate_changed` / `project_changed` / `sla_paused` webhook  
- Activity Feed 反应/订阅/推送加厚  
- Formula 物化 emit（E40 D2/D7）  
- Redis / 进程内 cron；远程 push / 开 PR / 自开 E51

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 可保存合法 timezone + 周内窗口；非法 IANA / 倒置时段被拒 |
| B | `businessHoursEnabled=true` 时：跨夜/跨周末的 `deadline_at` 跳过非营业段；单测钉死样例 |
| C | `enabled=false`（或未配置）时行为与 E48/E45 墙钟语义一致 |
| D | pause/resume 剩余时间按营业分钟重算；paused 不 tick |
| E | first_response 与 time_in_status 共用加法器；breach payload 仍含 `metric` |
| F | 配置变更批量重算 running/paused deadline；跨租户隔离；配置写路径 **无** 额外 webhook/automation；formula no-emit spy |
| G | FE 薄设置 + vitest；build ok |
| H | CLI **1.34.0** + version 断言 |
| 门禁 | BE 定向+全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E51 |

## 4. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = **SLA business hours thin**（方案 A）；**无**节假日/优先级大战 / 薄 webhook 单包 |
| D2 | 营业分钟加法器为唯一 deadline 语义源；`run_due` 仍比 UTC `deadline_at` |
| D3 | 默认关闭 → 墙钟回退（兼容现网时钟） |
| D4 | pause 不计营业分钟；resume 重算剩余；`elapsed_before_pause_minutes` enabled 时为营业分钟（Q4a） |
| D5 | **Workspace 级** timezone + business_hours；本轮无 policy 覆盖（Q1a/Q2a） |
| D6 | **Alembic** 增 WS 列（Q3a）；配置变更批量重算（Q5a）；每日最多 2 段（Q6a） |
| D7 | CLI = **1.34.0** |
| D8 | 守 E40 D2/D7：本 Epic **永不** formula emit；非目标见 §2；不 push；不自开 E51 |

## 5. 测试要点

- 纯函数：同日窗口内、跨午休、跨周末、跨 timezone DST（若选区有 DST）、enabled=false 回退  
- pause/resume 剩余；first_response 停表仍正确  
- 配置 CRUD 权限 / 跨租户；配置变更重算  
- spy：配置写无 emit；breach 路径既有 webhook/automation 不变  
- CLI 1.34.0 pins

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. 纯函数 business-minutes + 单测（TDD）  
3. Alembic + API（TDD）；接线 create/resume/run_due + 配置变更重算  
4. FE 薄设置  
5. CLI 1.34.0  
6. 门禁 + acceptance tip

## 7. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | timezone / windows 挂在 Workspace 还是 SlaPolicy？ | **Q1a Workspace 级** |
| Q2 | policy 是否允许覆盖？ | **Q2a 本轮不允许** |
| Q3 | 是否 alembic migration？ | **Q3a 是**（WS `timezone` + `business_hours` JSON） |
| Q4 | pause 累计列语义？ | **Q4a** enabled 时复用为营业分钟；false 时墙钟 |
| Q5 | 配置变更后是否立刻重算 running deadline？ | **Q5a 是**（批量重算；封顶防炸） |
| Q6 | 每日多段还是单段？ | **Q6a 每日最多 2 段** |

---

## 附录 · 本轮未选但仍高 ROI（供 E51+ / runners-up）

1. **专用 webhook pack** `issue.cycle_changed` / `issue.estimate_changed`（+ 可选 `project_changed` / `sla_paused`）**捆订阅事件过滤 FE** — 抬到中厚集成闭环。  
2. **Activity Feed 加厚**（反应、订阅、推送）— E47 API 已够读；产品化 UI 重。  
3. 完整节假日/优先级大战、Formula emit — 本轮不推。

## CLI 版本

**1.34.0**

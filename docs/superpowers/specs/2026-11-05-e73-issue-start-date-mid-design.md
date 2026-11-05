# E73 Design：Issue start_date mid — 计划开始日 · CLI 1.57.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E73  
基线拟：`sprint/E72-S1` @ `6911e71`（全文 `6911e717ec751975b0b42b77b7b1d73311ad1ee9`；E72 design 基线 `91bea39`；E71 tip `b95da6f` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E73-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E74**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e73-issue-start-date-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E73-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E72 连续闭合 … → multi-assignee（E71）→ **Project 模板 mid（E72：`project_templates` · CLI 1.56.0）**。

E72 附录 runners-up（任务硬指引）：

1. **Activity Push** — 仍 **勿默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b advance** — **rotate off**  
5. **表单公开附件** — **prefer skip**  
6. **递归孙项进度** — **prefer skip**  
7. **Bulk/Insights 多指派** — **prefer skip**  
8. **Issue start_date** — **本轮候选**  
9. **深拷贝 duplicate project** — **prefer skip**（过厚）  
10. **模板内 Issue stubs** — **prefer skip**（刚交无 stubs 模板）

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ·due / Form→Triage / 评论附件 / childProgress / multi-assignee / project templates**。

代码实证 @ `6911e71`：

| 面 | 现状 |
|----|------|
| 截止 | `issues.due_date` 可读写；列表 `due_before`；FE 详情可编；audit 有 `due_date_changed` |
| 开始 | 仅有自动 **`started_at`**（status→`in_progress` 时写入）— **非**用户计划开始日 |
| Timeline（E8） | Issue 点/条 mainly `due_date`；roadmap 明示 **Issue start_date 后置** |
| Linear 对齐 | Linear Issue 有 Start / Due；排期条需要两端 |
| Project 模板 | E72 **刚闭**；本轮宜离开模板/Project 创建弧 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue start_date mid**：alembic 加 `issues.start_date`（与 `due_date` 同形 DateTime；**语义≠** `started_at`）；Create/Update/详情嵌入；校验 start≤due（同日允许）；列表 `start_before`/`start_after`；FE 详情「开始」旁 due；Timeline Issue 有 start+due 时画条；CLI **1.57.0**；无新 webhook 事件名 | **中厚**；补 E8 后置缺口；单 sprint 可交付 |
| B | Activity Push | 勿默认 |
| C | Customer 门户再厚 | prefer skip |
| D | Initiative 甘特 | prefer skip |
| E | Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / 模板 stubs | skip |
| F | 复用/改写 `started_at` 为可编计划日 | **语义污染**；破坏「进入进行中」自动戳 |
| G | 仅 FE 本地假字段 | **过薄**；Timeline/CLI/过滤不一致 |

**建议拍板：A（Issue start_date mid）。**  
Push / 门户 / 甘特 / Q2b / 附件 / 递归 / Bulk / duplicate / stubs 列入附录 runners-up。

自检：与 `started_at` 边界、校验、过滤、Timeline 薄改、CLI **1.57.0**、非目标与 no-emit、不重开 E63–E72 邻面已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 勿默认 |
| Customer 门户再厚 | prefer skip |
| Initiative 甘特 | prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 | skip / rotate off |
| 深拷贝 duplicate / 模板 Issue stubs | prefer skip（E72 刚交） |
| 再开 project templates / multi-assignee / childProgress / 评论附件 / Form / TZ / 假日 | 刚闭 |
| Formula children rollup / emit | E40/E43 **永不** |

### Why this Epic now（一句话）

有 due 无 **计划开始日**，Timeline/排期只能落点不能画条；E8 明示后置、E72 模板弧刚闭后轮换离开模板/指派/进度/附件/表单/TZ/门户/假日/依赖，用中厚刀补上 **`start_date` 一等字段 + 校验/过滤/详情/Timeline 薄增强 + CLI**，对齐 Linear Start/Due，且不碰 `started_at` 自动戳、不重开 Push/甘特。

---

## 1. 目标

成功标准：Issue 可读写 **`start_date`**（计划开始；**独立于** `started_at`）；Create/Update/详情返回；若与 `due_date` 皆有则 **start_date.date ≤ due_date.date**（**Q1a** 违则 400）；列表过滤 `start_before` / `start_after`（对齐 due_before 风格）；FE 详情可编；Project Timeline 在 issue 同时有 start+due 时渲染条（仅 due 仍点）；CLI **1.57.0**；**不**改 recurrence/due-reminder 主语义、**不** Activity Push、**不**改 E63–E72 邻面主表面、**不** formula emit、**不**甘特大图/门户/模板再开。

### A · 数据 / BE

- alembic：`issues.start_date` DateTime NULL + index（同 `due_date`）  
- Schema：Create/Update/Response 增 `start_date`；**不**改 `started_at` 自动写入逻辑  
- 校验（**Q1a**）：两者皆非空且 `start_date.date() > due_date.date()` → 400；清其一允许  
- 列表：`start_before` / `start_after`（YYYY-MM-DD；语义对齐既有 due 过滤）  
- 排序（**Q3a**）：可选 `sort=start_date`；默认排序不变  
- Audit（**Q4a**）：变更记 `start_date_changed`（若 E41 枚举可扩）或并入既有 field-change；**不**新 webhook 名  
- CSV（**Q2a**）：本轮 **不做** import/export 列（后置）；避免 E28/E34 再开过宽

### B · Timeline / FE

- 详情右栏：「开始」EditableField（邻 due）  
- 列表/看板：可选显示（默认可不加列；有值时可小徽章）— **Q3a** 详情必做，列表列 **可选薄**  
- `project-timeline`：`TimelineIssueLike` 增 `start_date?`；有 start+due → bar；仅 due → 点（保持 E8）  
- vitest：校验 helper + timeline bar；build ok；守 E63 `f`+`r`

### C · CLI **1.57.0**

- `issue create|update --start-date YYYY-MM-DD`  
- `issue show` 打印 Start / Due  
- `issue list --start-before/--start-after`（若 list 旗标风格允许）  
- pins → **1.57.0**（**Q6a**）

### D · 安全 / 邻面 / no-emit

- 跨租户 404 不变  
- **Q5a**：不新增 webhook 事件名；写路径沿用既有 `issue.updated`（及现有 field webhooks 若有）；**无** `issue.start_date_changed` 出站事件  
- formula **no-emit**；不把 start_date 做成 formula 字段  
- **不**改 E67 TZ 存储策略（日期形态对齐 `due_date` 既有惯例，不重开假日/TZ Epic）  
- **不**改 E39 due-reminder 触发集（start_date **不**触发到期提醒）  
- **不**改 E63–E72 主表面（project templates / multi-assignee / childProgress / 评论附件 / Form / Initiative / 假日 / 门户 仅 pins）

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户再厚、Initiative 甘特大图、Recurrence Q2b、表单公开附件、递归孙项、Bulk/Insights 多指派  
- 深拷贝 duplicate project、模板 Issue stubs、再开 project templates  
- 把 `started_at` 改成可编计划日或删除自动戳  
- start_date 驱动 due-reminder / SLA clock  
- CSV 列、formula 跨 Issue、Formula emit  
- 远程 push / 开 PR / **自开 E74**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | alembic `start_date`；CRUD 读写；与 `started_at` 独立 |
| B | start>due → 400；仅一侧有值 OK；清 start OK |
| C | `start_before`/`start_after` 过滤正确 |
| D | FE 详情可编；Timeline start+due 条；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.57.0** + create/update/show + pins |
| F | 无新 webhook 事件名；不改 E63–E72 邻面；formula no-emit；reminders 不因 start 触发 |
| 门禁 | BE 定向 start_date；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E74 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue start_date mid**（方案 A）；计划开始日一等字段；**无** Push / 甘特大图 / 门户 / 模板再开 |
| D2 | 新列 `start_date`；保留自动 `started_at` 不动 |
| D3 | 校验 start.date ≤ due.date；过滤 start_before/after |
| D4 | Timeline：双端有值画条；本轮不做 CSV |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.57.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E63–E72 邻面；不 push；不自开 E74 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | start>due？ | **Q1a** 400；备选 Q1b 自动交换（隐式危险） / Q1c 仅警告仍写入（FE 难一致） |
| Q2 | CSV？ | **Q2a** 本轮不做；备选 Q2b 加 import/export 列（偏宽，易再开 E28） |
| Q3 | 列表列 / 排序？ | **Q3a** API sort 可选；FE 列表列可选薄（详情必做）；备选 Q3b 强制列表列（UI 噪） |
| Q4 | audit 类型？ | **Q4a** 扩 `start_date_changed`（若枚举易扩）否则 generic field；备选 Q4b 完全静默（不利排障） |
| Q5 | webhook？ | **Q5a** 无新事件名，走 `issue.updated`；备选 Q5b 新 `issue.start_date_changed`（订阅分裂） |
| Q6 | CLI？ | **Q6a** `--start-date` + show + pins **1.57.0**；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic + model/schema（TDD）  
3. Service 校验 + list filters（TDD）  
4. API create/update/detail + audit 薄扩  
5. FE 详情 + timeline util（TDD）  
6. CLI 1.57.0  
7. reminders/TZ/邻面不动 spy + acceptance

---

## 7. 测试要点

- create/update 读写 `start_date`；`started_at` 仍仅 status→in_progress 自动写  
- start=2026-11-10 due=2026-11-09 → 400；同日 OK；仅 start / 仅 due OK  
- `start_before`/`start_after` 边界（含当日）  
- Timeline：双端 → bar 宽度；仅 due → 非空点逻辑不变  
- spy：无新 webhook **事件名**；due-reminder 不因纯 start 变更触发；不触 E72 templates / E71 assignees / E70 childProgress 写 / E69 attach / E68 enqueue / E67 TZ 主路径；formula no-emit  
- CLI 1.57.0 pins；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E74+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — E31 非目标。  
6. **递归孙项进度** — prefer skip。  
7. **Bulk/Insights 多指派拆分** — prefer skip。  
8. **深拷贝 duplicate project** — prefer skip。  
9. **模板内 Issue stubs** — prefer skip。  
10. **CSV start_date 列 / start 驱动提醒** — 本 Epic Q2a 后置。

（备选扫描但本轮不推：再开 project templates/multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.57.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E72-S1` @ `6911e717ec751975b0b42b77b7b1d73311ad1ee9`  
- 拟开：`sprint/E73-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e73-issue-start-date-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E74**

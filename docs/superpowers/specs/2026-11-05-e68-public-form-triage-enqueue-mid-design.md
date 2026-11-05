# E68 Design：公开表单 → Triage 入队 mid — enqueue_triage · CLI 1.52.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E68  
基线拟：`sprint/E67-S1` @ `dcf4c0c`（全文 `dcf4c0c49b97d8bd0b92cf727f5cf4910160b022`；E67 design 基线 `1fa4a85`；E66 tip `ea96ebd` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E68-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E69**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e68-public-form-triage-enqueue-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E68-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E67 连续闭合 … → Initiative 依赖（E65）→ 附件鉴权（E66）→ **Workspace 时区进 due/recurrence mid（E67：本地日历日 · CLI 1.51.0）**。

E67 附录 runners-up（不绑定）：

1. **Activity Push** — 单列易溢；**默认不重开**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence 本地午夜 advance（Q2b）** — 震存量 `next_run_at`；**prefer rotate off**（非本轮最高 ROI）

任务硬约束：轮换离开 **TZ/due · 附件 ACL · Initiative deps · 假日 · Customer · Search · Insights**；Push 勿默认；Q2b advance 非明显最高 ROI 则跳过。

代码实证 @ `dcf4c0c`：

| 面 | 现状 |
|----|------|
| Public Forms（E31） | `issue_forms` + `/f/:token` 匿名 submit → `IssueService.create_issue`（默认进工作区，**无** `triage_status`）；可选 `create_customer_request` |
| Triage（E9） | `triage_status=pending` 队列；`TriageService.enqueue` / `create_and_enqueue` / accept/decline/duplicate 齐；设计明示「公共表单 / 邮件→自动入 Triage」**后置** |
| Form 成功页 | 仅展示 `issueCode`；**无**「已入受理队列」叙事；**无** status URL 深链（后者属 Customer 门户再厚，本轮 skip） |
| TZ/due | E67 **刚闭**；advance 仍 UTC — 本轮宜离开 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | E9+E31 明示缺口「表单自动入队」仍空；可用单 bool + submit 后 `enqueue` 做成 mid；不碰刚闭弧，不默认 Push/甘特/门户/Q2b |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **公开表单 → Triage 入队 mid**：`issue_forms.enqueue_triage` bool（默认 false）；submit 创建 Issue 后若开则 `TriageService.enqueue`（`triage_status=pending`）；FE 表单设置开关 + 成功文案；CLI **1.52.0**；**无** status 深链 / Push / 甘特 / TZ advance | **中厚**；闭合 E9 后置项；复用既有 Triage API；单 sprint 可交付 |
| B | Activity Push | 易溢；**勿默认** |
| C | Customer 门户再厚（Form 成功→status URL） | prefer skip；属门户弧 |
| D | Initiative 甘特 | prefer skip |
| E | Recurrence 本地午夜 advance（Q2b） | 震存量；非最高 ROI；rotate off |
| F | 评论附件 mid | 真缺口，但贴 E66 附件弧；次优 |
| G | 仅改成功页文案、不入队 | **过薄** |

**建议拍板：A（公开表单 → Triage 入队 mid）。**  
Push / Customer 门户再厚 / 甘特 / Q2b advance / 评论附件列入附录 runners-up。

自检：默认关兼容、与 `create_customer_request` 共存、租户、FE/CLI **1.52.0**、非目标与 no-emit 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 非明显最优；勿默认 |
| Customer 门户再厚 | prefer skip；轮换离开 Customer |
| Initiative 甘特 | prefer skip |
| Q2b recurrence advance | 震存量；任务 prefer rotate off |
| 再开 TZ / 附件 ACL / 假日 / Search / Insights / Initiative 关系 | 刚闭 |
| 评论附件 | 可贴 E66；ROI 次于 Form→Triage 产品闭环 |
| 真 GitHub App / SSO / RRULE | 过厚 |

### Why this Epic now（一句话）

公开表单已能匿名建单，但 **一提交就进正式 Issue 面**——客服/值班无法先筛；E9 明示「表单→Triage」后置至今空着；E67 时区弧刚闭后轮换离开 TZ/附件/依赖/假日/门户/Search，用中厚刀补上 **表单级 `enqueue_triage` + submit 入队 + 设置/CLI**，正好把「外呼入口」接到「受理队列」，且不重开 Push、甘特、门户深链或 advance 大战。

---

## 1. 目标

成功标准：表单开启 **`enqueue_triage`** 后，公开 submit 创建的 Issue **`triage_status=pending`** 并出现在 Triage 列表；默认 **false** 行为与今日一致（直接进工作区、不入队）；可与既有 `create_customer_request` 共存；FE 设置可开关；成功页提示「已进入受理队列」；CLI **1.52.0**；**不** status URL 深链、**不** Activity Push、**不**改 E57–E67 邻面主表面、**不** formula emit、**不**改 recurrence advance。

### A · 模型（BE）

- `issue_forms` 增列 **`enqueue_triage`** `Boolean NOT NULL DEFAULT false`（**Q1a**）  
- alembic 新修订（建议 `x1a2b3c4d5e6` 一类）  
- serialize / create / patch 暴露 `enqueueTriage`

### B · Submit 路径（BE）

- `IssueFormService.submit`：`create_issue` 成功后：  
  - 若 `form.enqueue_triage`：**Q2a** 调用 `TriageService.enqueue`（或等价写 `triage_status=pending` + commit）；已 pending 则幂等  
  - 若同时 `create_customer_request`：**Q3a** 两者都做（CR 挂已建 Issue；Issue 仍 pending）  
- 公开响应可增 `triageEnqueued: bool`（薄，便于 FE 文案）  
- rate-limit / 租户 / enabled 校验不变

### C · FE

- 表单设置：开关「提交后进入 Triage」  
- 公开 `/f/:token` 成功态：若 `triageEnqueued` → 「已进入受理队列，请等待处理」；否则保持现有 issueCode 文案  
- **不做** status_token / `/r/:token` 深链（Customer 门户再厚，非本 Epic）  
- vitest：文案/标志 flatten；build ok；守 E63 `f`+`r` 路由

### D · CLI **1.52.0**

- `opentask form create|update … --enqueue-triage / --no-enqueue-triage`（**Q6a**）  
- `form show/list` 展示 `EnqueueTriage`  
- pins → **1.52.0**

### E · 安全 / 邻面 / no-emit

- 跨 WS 404 不变；公开 token 仍仅能打自己的 form  
- **Q5a**：不新增 webhook 事件名；既有 `issue.created`（若有）行为不本轮扩展；入队本身不 fire 新出站  
- formula **no-emit**  
- **不**改 E57–E67 主表面（TZ helpers / 附件 ACL / Initiative relations / 假日 / 门户 / Search / Insights 仅 pins）  
- **不**改 recurrence `advance_*`

---

## 2. 非目标

- Activity Push / 浏览器 Notification / FCM  
- Customer 门户再厚（Form 成功→status URL、公开回复线程 UI）  
- Initiative 甘特；Recurrence 本地午夜 advance（Q2b）  
- 再开 TZ/due 语义、附件 ACL、假日包、Search、Insights  
- 邮件→Triage、Slack 入站、验证码、表单附件上传（E31 仍非目标）  
- Formula emit；远程 push / 开 PR / 自开 E69

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | `enqueue_triage=true` submit → Issue `triage_status=pending`；出现在 Triage list |
| B | 默认 false → 与今日一致（不入队） |
| C | 与 `create_customer_request` 同开：CR 创建成功且 Issue 仍 pending |
| D | FE 开关 + 成功文案；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.52.0** + flag + pins |
| F | 无新 webhook；不改 E57–E67 邻面；formula no-emit；不改 advance |
| 门禁 | BE 定向（forms + triage）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E69 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **公开表单 → Triage 入队 mid**（方案 A）；bool + submit enqueue + FE/CLI；**无** Push / 甘特 / 门户深链 / Q2b advance |
| D2 | 新列 `enqueue_triage` 默认 false；兼容存量表单 |
| D3 | submit 后复用 `TriageService.enqueue`；与 CR 可并存 |
| D4 | 成功页只改文案标志；不做 `/r/:token` 深链 |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.52.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E57–E67 邻面；不 push；不自开 E69 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 存储？ | **Q1a** 列 `enqueue_triage` bool default false；备选 Q1b 塞进 `fields_json` meta（难校验/难 CLI） |
| Q2 | 入队方式？ | **Q2a** create 后 `TriageService.enqueue`；备选 Q2b create 时直接带 triage 字段（要改 IssueCreate 主路径，面更宽） |
| Q3 | 与 CR 同开？ | **Q3a** 允许并存；备选 Q3b 互斥（产品过窄） |
| Q4 | 成功页？ | **Q4a** 文案区分入队 vs 直接建单；**不**深链 status；备选 Q4b 深链 `/r/:token`（属门户再厚，拒默认） |
| Q5 | webhook？ | **Q5a** 不新增事件、入队不 fire 新出站；备选 Q5b `triage.enqueued`（易噪） |
| Q6 | CLI？ | **Q6a** `form create/update --enqueue-triage` + show 字段；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic `enqueue_triage` + model/serialize（TDD）  
3. submit → enqueue + 与 CR 并存（TDD）  
4. FE 设置开关 + 成功文案 + vitest  
5. CLI 1.52.0  
6. no-emit / 邻面不动 / f+r spy + acceptance

---

## 7. 测试要点

- 默认表单 submit：`triage_status is null`；Triage list 不含  
- `enqueue_triage=true`：pending；Triage list 含；accept 后清除  
- 与 `create_customer_request` 同开：有 `requestId` 且 pending  
- 幂等：重复 enqueue 不炸  
- 跨 token / disabled form 行为不变  
- spy：无新 webhook 事件名；不触 E67 TZ tick / E66 signed-url / E65 relations / E64 holiday / E63 status 主路径；formula no-emit；`advance_once` 未改  
- CLI 1.52.0 pins  
- FE vitest；build ok；elegant-router `f`+`r` 仍在

---

## 附录 · runners-up（供 E69+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WS / Notification / FCM）— 单列易溢；非明显最优不重开。  
2. **Customer 门户再厚 thin-mid**（Form 成功深链 status URL / 公开回复线程 UI）— 本轮刻意不做深链；多轮后再评。  
3. **Initiative 甘特/时间线精修** — E65 关系已在；有排程需求再开。  
4. **Recurrence 本地午夜 advance（Q2b）** — E67 刻意不震存量；运营要「每天本地 09:00」再开。  
5. **评论附件 mid** — 复用 E66 ACL/签名 URL；次于 Form→Triage 闭环。

（备选扫描但本轮不推：再开 TZ/附件/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / 表单验证码/附件 — 过厚或 E31 非目标。Formula emit — 永不。）

## CLI 版本

**1.52.0**

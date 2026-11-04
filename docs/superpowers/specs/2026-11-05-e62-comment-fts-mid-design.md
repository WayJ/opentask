# E62 Design：评论全文入索 mid — IssueComment → SearchBackend · CLI 1.46.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E62  
基线拟：`sprint/E61-S1` @ `9e8d281`（全文 `9e8d28163efe8d8319645afaaaca45fe8b192c80`；E61 design 基线 `36dfb75`；E60 tip `950256e` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E62-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E63**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e62-comment-fts-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E62-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E61 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ Webhook 可观测（E54）→ Insights 效能加厚（E55）→ SLA policy 日历覆盖（E56）→ Webhook 死信告警（E57）→ 国家/地区假日包（E58）→ Insights 再厚/效能日报（E59）→ Search FTS mid（E60）→ **Insights 共享报表 mid（E61：visibility personal|workspace + fork + CLI 1.45.0）**。

E61 附录 runners-up（不绑定）：

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」；**默认不重开**  
2. **假日包扩容 thin**（再加 EU/UK 或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 已隔 E59–E61 三轮；可作附录  
3. **评论全文入索 thin-mid**（`IssueComment.content` → E60 SearchBackend；仍无 Meili/Elastic）— E60 明示「隔一轮后再评」；**E61 已隔一轮 → 本轮正好** → **本草案收之**

代码实证 @ `9e8d281`：

| 面 | 现状 |
|----|------|
| Search | E60 `SearchBackend`（PostgresFTS / SQLiteFTS / ILike）；Issue title+code+description；Project；Doc；Member ILIKE；API 分组 `issues|projects|docs|members`；**不搜** `issue_comments.content`；CLI **1.45.0**（E61 pin；search 子命令仍在） |
| IssueComment | 表 `issue_comments`：`content` Text、`issue_id`、`user_id`、`parent_id`、`comment_type`；经 Issue 挂 WS；**无** `search_tsv` / FTS5 |
| Insights | E55→E59→E61 弧刚闭（多 label / 我的报表 / digest / 共享报表）；本轮宜 **轮换离开** |
| SLA 日历 | E50→E53→E56→E58 弧已闭；包扩容有价值但薄 |
| Webhook | E44→E51→E54→E57 出站弧已闭 |
| Activity | E52 watching+反应+铃铛；**无** Push / 浏览器 Notification |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | E61 明示最高 ROI 让路项回到 **评论全文入索**（隔一轮）；要求轮换离开刚闭的 Insights；Activity Push 非「明显最优」不默认；假日包扩容 / 门户·App·依赖图 次之或过厚 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **评论全文入索 mid**：在 E60 `SearchBackend` 上增 `search_comments`；Postgres `issue_comments.search_tsv`+GIN；SQLite `issue_comments_fts`+triggers；`GET /api/search` 新增分组 **`comments`**（命中带 `issueId`/`issueCode`/`snippet`/`rank`）；FE/⌘K 薄接新组；CLI **1.46.0** 打印 `comments:`；租户经 Issue.workspace_id；**无** Meili/Elastic、**无** Activity Push、**不**改 E61 Insights / E57–E58 主表面 | **中厚且轮换离开 Insights**；接 E61 #3 / E60「隔一轮」；复用方言抽象，单 sprint 可交付 |
| B | 假日包扩容 thin（EU/UK/2027） | 有价值但薄；日历弧非本轮最高 ROI；作 runners-up |
| C | Activity 实时/Push（WS 扇出 / 浏览器 Notification / FCM） | 单列易溢；非「明显最优」；**默认不重开** |
| D | 再开 Insights（共享 digest / BI / Slack Incoming） | **刚闭 E59→E61**；与 prefer rotate OFF Insights 冲突 |
| E | Customer 公开门户 / 真 GitHub App / Initiative 依赖图 / Formula emit | 过厚或排除；emit **永不** |
| F | 仅把 comment 拼进 Issue description 索引、无独立命中 | **过薄且难解释**命中来源；snippet 糊 |

**建议拍板：A（评论全文入索 mid）。**  
假日包扩容、Activity Push、（可选）下一刀门户/依赖图边缘列入附录 runners-up。

自检：方言索引、分组契约、租户 join、软删/类型过滤、FE/CLI **1.46.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity 实时/Push | 单列易溢；非「明显最优」；任务明确要求勿默认 |
| 假日包扩容 EU/UK/2027 | 有价值但薄；非最高 ROI |
| 再开 Insights | E59→E61 刚闭；明确要求轮换离开 |
| Customer 门户 / GitHub App / Initiative 依赖图 | 过厚或排除 |
| 再开 webhook / Formula emit / 重做 E52–E61 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E60 把 Issue/Project/Doc 全文基建立起来了，但讨论真相常在评论里——搜标题/描述仍漏「说过但没写进字段」的线索；E61 刚把 Insights 共享报表闭完后轮换离开，用中厚刀把 **`IssueComment.content` 接到既有 SearchBackend**，正好把「能搜实体」抬到「能搜对话」，且不重开 Push、Elasticsearch 或 Insights 大战。

---

## 1. 目标

成功标准：Workspace 成员（viewer+，对齐 E17/E60）对 `GET /api/search?q=` 在 **Postgres / SQLite** 方言下可命中 **本 WS Issue 的评论正文**；结果以新分组 **`comments`** 返回（含 `id`、`issueId`、`issueCode`、`snippet`、可选 `rank`、可选 `authorUserId`）；既有 `issues|projects|docs|members` 行为回归不变；FE `/search` + global-search 薄接新组（缺 `comments` 时兼容旧客户端）；CLI **1.46.0** 顶层 `search` 打印 `comments:`；跨租户隔离；**不**引入外部搜索引擎、**不** Activity Push、**不**改 E61 Insights / E57 webhook 告警 / E58 假日包主表面、**不** formula emit。

### A · SearchBackend + 评论索引（BE）

- 扩展 `SearchBackend`：`search_comments(workspace_id, q, limit) -> list[Hit]`  
- **Postgres**：`issue_comments.search_tsv`（generated/`to_tsvector`，对齐 E60 **simple**）+ GIN；查询 `plainto_tsquery` + `ts_rank`；**JOIN issues** 滤 `issues.workspace_id`  
- **SQLite**：`issue_comments_fts` 虚表 + INSERT/UPDATE/DELETE triggers（对齐 E60 Q3a）；JOIN issues 滤租户  
- **ILike 降级**：`IssueComment.content.ilike` + join Issue（未知方言）  
- 入索字段：`content`（截断对齐 E60 `INDEX_BODY_MAX`，建议同 16KiB）；**不**索 `meta_data` JSON  
- alembic 新修订（建议 `u7d8e9f0a1b5` 一类）；conftest 双方言 bootstrap 同步

### B · API 契约（BE）

- `GET /api/search` 响应增 **`comments: [...]`**（空 q → 各组空数组，含 comments）  
- Hit 形状建议：  
  `{ id, issueId, issueCode, snippet, rank?, authorUserId?, createdAt? }`  
- limit 仍 **1..50 每组**（与 E60 同）  
- 精确 issue_code 置顶逻辑 **仅作用于 issues 组**（评论组不做 code 置顶）  
- 权限：viewer+ 可读；跨 WS → 不泄漏他租户评论

### C · 过滤边界（BE）

- 仅索挂在 **本 WS Issue** 上的评论；Issue 软删/不可见则评论不命中（**Q2a**）  
- `comment_type`：默认仅 `COMMENT`（排除系统/自动化噪声 — **Q3a**）；备选全类型  
- 嵌套回复：父子均入索（各自一行 Hit）；深链到父 Issue（及可选 `parentId`）  
- **不**索 MissionCenter / Requirement 评论轴

### D · FE

- `/search` + ⌘K global-search：新增「评论」分组；点击深链 Issue 详情（可选 hash/query 定位评论 — **Q5a** 先深链 Issue，精确定位可后置）  
- 缺 `comments` 键时不炸（兼容）  
- vitest：flatten/分组契约；build ok

### E · CLI **1.46.0**

- 顶层 `opentask search <q> [--limit] [--json]`：人类可读输出增 `comments: N` 与行摘要（`issueCode · snippet`）  
- `--json` 透传完整分组（含 comments）  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.46.0**

### F · 安全 / 租户 / no-emit

- 跨租户：他 WS 评论永不入结果  
- formula **no-emit**；搜索路径 spy 不触发 `fire_webhooks` / automations  
- **不**改 E61 Insights / E57 alerts / E58 holiday-packs 主表面（仅 CLI version pins）  
- **不**改 E60 Issue/Project/Doc 索引语义（仅加法）

---

## 2. 非目标

- Elasticsearch / Meilisearch / 外部托管搜索  
- Activity Push / 浏览器 Notification / FCM / 真 WebSocket 扇出产品化  
- 假日包 EU/UK/2027、ICS、州包、外网拉取  
- Insights 再厚 / 共享 digest 广播 / BI / Slack Incoming  
- Customer 公开门户、真 GitHub App、Initiative 依赖图  
- Formula 物化 emit（E40 D2/D7）  
- 重索引全库运维 UI / 后台 job 产品面（alembic + triggers 即可）  
- 远程 push / 开 PR / 自开 E63

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | PG+SQLite（或至少一方言+ILike 降级测）评论正文可命中；rank/snippet 可选有 |
| B | 响应含 `comments`；issues/projects/docs/members 回归；空 q 全空 |
| C | 跨租户不泄漏；软删/不可见 Issue 下评论不命中；默认仅 COMMENT 类型（若 Q3a） |
| D | FE 新组 + 深链 Issue；缺键兼容；vitest+build |
| E | CLI **1.46.0** + `comments:` 输出 + pins |
| F | 跨租户隔离；formula no-emit spy；不改 E57–E58 / E61 主表面 |
| 门禁 | BE 定向（E62+E60 search）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E63 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **评论全文入索 mid**（方案 A）；IssueComment → SearchBackend + `comments` 分组 + CLI；**无** Push / Insights 再开 / Meili / 假日包扩容 |
| D2 | 复用 E60 `SearchBackend` 方言抽象；不引入第二套搜索引擎 |
| D3 | API **加法**：新分组 `comments`；不破坏既有四组契约 |
| D4 | 租户边界 = **JOIN issues.workspace_id**；不可见/软删 Issue 下评论不返回 |
| D5 | 默认仅索 `comment_type=COMMENT`；系统噪声类型排除 |
| D6 | CLI = **1.46.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E57/E58/E61 主表面；非目标见 §2；不 push；不自开 E63 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 评论命中如何呈现？ | **Q1a** 独立分组 `comments`（带 issueId/issueCode/snippet）；备选 Q1b 折叠进 `issues` 并标 `matchedOn: "comment"`（契约更吵、旧客户端难展示来源） |
| Q2 | 软删 / 不可见 Issue？ | **Q2a** Issue 不可检索则其评论亦不命中（join 可见集）；备选 Q2b 仍返回评论但 404 深链（差体验） |
| Q3 | 哪些 `comment_type`？ | **Q3a** 仅 `COMMENT`；备选 Q3b 全部类型（易噪） |
| Q4 | 超长评论入索？ | **Q4a** 截断对齐 E60 `INDEX_BODY_MAX`（16KiB）+ snippet ≤120；备选 Q4b 全量 |
| Q5 | FE 深链精度？ | **Q5a** 本轮深链 Issue 详情即可；评论锚点/高亮后置；备选 Q5b 本轮强制 `?commentId=` 滚动（FE 面更大） |
| Q6 | CLI 输出？ | **Q6a** 人类可读增 `comments:` 组 + 行 `issueCode · snippet`；`--json` 全透传；备选 Q6b 仅 json 暴露（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic PG tsvector+GIN + SQLite FTS5+triggers（TDD）  
3. SearchBackend.search_comments + service 装配 + 租户/类型过滤（TDD）  
4. API 契约 + 跨租户 + 空 q + 回归 E60 四组（TDD）  
5. FE 分组 + 深链 + vitest  
6. CLI 1.46.0  
7. no-emit spy + acceptance

---

## 7. 测试要点

- 评论正文命中；title-only 查询不误伤（除非正文也含）  
- 跨 WS 404/空；软删 Issue 下评论不出现  
- `comment_type` 过滤（Q3a）  
- 空 q → `comments: []`；limit clamp 1..50  
- E60 issues/projects/docs/members 回归；Member 仍 ILIKE  
- spy：无 fire_webhooks；不触 E57 alert eval / E58 holiday apply / E61 share；formula no-emit  
- CLI 1.46.0 pins + comments 输出  
- FE vitest 分组 flatten；build ok

---

## 附录 · runners-up（供 E63+；若 Yuri 改选可替换本草案）

1. **假日包扩容 thin**（EU/UK 与/或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 已隔三轮；薄刀可随时插入。  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 后再评估；单列易溢；非「明显最优」不重开。  
3. **Customer 门户薄边 / Initiative 依赖图薄刀** — Roadmap 常排除或过厚；仅当产品入口明确升高再开。

（备选扫描但本轮不推：再开 Insights 共享 digest 广播 / BI — 刚闭 E61。Webhook / PagerDuty — 出站弧已闭。Formula emit — 永不本轮。重做 E52–E61 表面 — 无增量，不推。真 GitHub App — 过厚。）

## CLI 版本

**1.46.0**

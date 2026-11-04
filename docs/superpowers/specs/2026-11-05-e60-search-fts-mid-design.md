# E60 Design：Search FTS mid — 方言全文检索（Issue/Project/Doc）· CLI 1.44.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E60  
基线拟：`sprint/E59-S1` @ `ccc5b4f`（全文 `ccc5b4f4543625757e6e8185c2e22a68d180ae5e`；E59 design 基线 `e52ad34`；E58 tip `0494871` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E60-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E61**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e60-search-fts-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E60-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E59 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ Webhook 可观测（E54）→ Insights 效能加厚（E55）→ SLA policy 日历覆盖（E56）→ Webhook 死信告警（E57）→ 国家/地区假日包（E58）→ **Insights 再厚 / 效能日报（E59：多 label OR +「我的报表」+ 可选 digest）**。

E59 附录 runners-up（不绑定）：

1. **Search FTS mid**（Postgres `tsvector` + SQLite FTS5 或统一 trigram 降级；Issue/Project/Doc）— 现网 ILIKE 可规模化前的基建刀；方言测本需控 → **本草案收之**  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」；**默认不重开**  
3. **假日包扩容 thin**（再加 EU/UK 或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 刚交；非轮换优先

代码实证 @ `ccc5b4f`：

| 面 | 现状 |
|----|------|
| Search | E17 `GET /api/search` + FE `/search` + ⌘K 深链；`SearchService` 全员 **ILIKE**（Issue title/code；Project name；Doc title+body_md；Member username/name）；**不搜** Issue.description；**无** tsvector / FTS5 / trigram；**无** 排名字段 |
| CLI | **无**顶层 `search` 子命令（仅 issue list `--search` / requirements search 等局部）；pins **1.43.0** |
| Insights | E24→E55→E59 弧刚闭（多 label / 我的报表 / digest）；本轮宜 **轮换离开** |
| SLA 日历 | E50→E53→E56→E58 弧已闭；再开包扩容非轮换优先 |
| Webhook | E44→E51→E54→E57 出站弧已闭 |
| Activity | E52 watching+反应+铃铛；**无** Push / 浏览器 Notification；仓内 realtime≠产品闭环 |
| DB | 双方言：`USE_SQLITE` → aiosqlite；否则 asyncpg Postgres（`config.py`） |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | 厚 Linear 主面近期已交；E59 明示最高 ROI 缺口回到 **Search FTS**；且要求轮换离开刚闭的 Insights 弧；Activity Push 非「明显最优」不默认 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Search FTS mid**：在既有 `GET /api/search` 下换引擎——Postgres **tsvector+GIN**，SQLite **FTS5**（共享 `SearchBackend` 抽象）；Issue 增搜 **description**；返回可选 `rank`/`snippet`；FE 薄用；CLI **1.44.0** 顶层 `search`；**无** Elasticsearch / Meilisearch、**无** Activity Push、**不**改 E59 Insights / E57–E58 主表面 | **中厚且轮换离开 Insights 弧**；接 E59 #1 让路项；双方言测本可控（抽象+双测）；单 sprint 可交付 |
| B | 统一 `pg_trgm` / SQLite LIKE+trigram 模拟 | 实现简单但 PG 需扩展、SQLite 无真 trigram；相关度弱于 FTS；作备选降级而非主路径 |
| C | Activity 实时/Push（WS 扇出 / 浏览器 Notification / FCM） | 单列易溢；非「明显最优」；**默认不重开** |
| D | 假日包扩容 thin（EU/UK/2027） | E58 刚交；与「轮换离开」SLA 日历弧冲突；非最高 ROI |
| E | 再开 Insights（共享报表 / BI / Slack Incoming） | **刚闭 E55→E59**；与 prefer rotate OFF Insights 冲突 |
| F | Customer 公开门户 / 真 GitHub App / Initiative 依赖图 / Formula emit | 过厚或排除；emit **永不** |
| G | 仅加 Issue.description ILIKE、无 FTS | **过薄**；不解决规模化 |

**建议拍板：A（Search FTS mid）。**  
Activity Push、假日包扩容、（可选）Insights 共享报表列入附录 runners-up。

自检：方言抽象、索引/同步、实体范围、排名/snippet、FE/CLI **1.44.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity 实时/Push | 单列易溢；非「明显最优」；任务明确要求勿默认 |
| 假日包扩容 EU/UK/2027 | E58 刚交；非轮换优先 |
| 再开 Insights | E55→E59 刚闭；明确要求轮换离开 |
| Customer 门户 / GitHub App / Initiative 依赖图 | 过厚或排除 |
| 再开 webhook / Formula emit / 重做 E52–E59 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E17 用 ILIKE 把全局 Search 立起来了，但 Issue 描述未入索、相关度靠 `updated_at`、双方言下无真全文索引——规模一上来就会慢且漏；E55→E59 刚把效能面闭完后轮换离开，用中厚刀把 **Postgres tsvector + SQLite FTS5** 接到既有 `/api/search`，正好把「能搜」抬到「能相关 / 能扩字段 / 能 CLI」，且不重开 Push、Elasticsearch 或 Insights 大战。

---

## 1. 目标

成功标准：Workspace 成员（viewer+，对齐 E17）对 `GET /api/search` 在 **Postgres** 走 **tsvector+GIN**、在 **SQLite** 走 **FTS5**（同一 API 契约）；Issue 检索覆盖 **title + issue_code(+legacy) + description**；Project / Doc 走 FTS（Member 可留 ILIKE，见 Q2）；结果可带 **rank**（及可选 snippet）；FE `/search` + global-search 薄接（不破既有分组）；CLI **1.44.0** 顶层 `search`；跨租户隔离；**不**引入外部搜索引擎、**不** Activity Push、**不**改 E59 Insights / E57 webhook 告警 / E58 假日包主表面、**不** formula emit。

### A · SearchBackend + 方言 FTS（BE）

- 新抽象（建议 `opentask/services/search/backend.py`）：  
  - `SearchBackend.search_issues|projects|docs(workspace_id, q, limit) -> list[Hit]`  
  - `Hit = {id, rank?, snippet?, …payload}`  
- **Postgres**：generated / 维护列 `search_tsv`（`to_tsvector('simple'|'english', …)` — **Q1**）+ GIN；查询 `plainto_tsquery` / `websearch_to_tsquery` + `ts_rank`  
- **SQLite**：FTS5 虚表（`issues_fts` / `projects_fts` / `docs_fts`，content= 或外部 content + triggers — **Q3**）；查询 `MATCH` + `bm25`  
- 检测 `session.bind.dialect.name`；未知方言 → **安全降级 ILIKE**（保 E17 行为）  
- 空 `q` → 空分组（对齐 E17）；`limit` 1..50

### B · 实体与字段（BE）

- **Issue**：title、issue_code、legacy_issue_code、**description**（本轮新增入索；E17 未搜 description）  
- **Project**：name、description  
- **Doc**：title、body_md（可截断入索，防超大 — **Q4**）  
- **Member**：**Q2a** 本轮仍 ILIKE（集合小、姓名分词收益低）；不建 FTS  
- KEY-N / issue_code 精确优先路径 **保留**（E17 D3）

### C · 索引同步（BE）

- alembic：PG 加 tsvector 列 + GIN；SQLite 建 FTS5 + triggers（或应用层双写 — **Q3a** 建议 DB triggers / generated）  
- 写路径：Issue/Project/Doc create/update/delete 后索引一致（trigger 优先，免漏改 service）  
- 可选一次性 backfill 命令 / migration data step（测夹具用小数据即可）  
- **不做**独立 reindex worker / 进度 UI

### D · API 契约加厚（薄）

- 保持 `GET /api/search?q=&limit=`  
- 各组 item 可增可选字段：`rank?: number`、`snippet?: string`（Doc 已有 snippet；Issue/Project 可选）  
- **不**改分组键名；**不**破 FE flatten 兼容（缺 rank 仍可渲染）

### E · FE

- `/search` + `layouts/modules/global-search`：若有 rank 则组内按 rank 再 `updated`；snippet 展示薄加  
- vitest：flatten 兼容缺省 rank；snippet 截断  
- **不做**高级查询语法 UI、筛选面板大战、搜索分析仪表盘

### F · CLI **1.44.0**

- 新顶层：`opentask search <q> [--limit] [--json]` → `GET /api/search`  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.44.0**  
- 可选：`issue find` 文档交叉引用（不强制改语义）

### G · 安全 / 租户 / no-emit

- 读权限对齐 E17（workspace member）  
- 所有查询强制 `workspace_id`；跨租户 0 命中 / 404 对齐既有  
- **不**新增 outbound webhook 事件、**不**改 fire 路径  
- formula **no-emit**；search 读路径 spy 不触发 `fire_webhooks` / automations  
- **不**改 E59 Insights / E57 alerts / E58 holiday-packs 主表面（仅 CLI version pins）

## 2. 非目标

- Elasticsearch / OpenSearch / Meilisearch / Typesense 等外部引擎  
- 向量 / 语义搜索 / embedding  
- Activity Push / FCM / 浏览器 Notification / 实时 WS 产品化  
- 再开 Insights（共享报表 / BI / Slack Incoming / 拖拽构建器）  
- 再开 SLA 日历（ICS、州包、冲突矩阵、EU/UK/2027 主表面）  
- 改 E57 webhook 告警 / E58 holiday-packs / E51 pack/HMAC / E59 reports/digest  
- Formula 物化 emit（E40 D2/D7）  
- Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动  
- Knowledge-base 独立全文、附件 OCR、评论全文（评论可列 E61+）  
- 远程 push / 开 PR / 自开 E61

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | PG 路径 tsvector 命中；SQLite 路径 FTS5 命中；未知方言 ILIKE 降级；空 q 空结果 |
| B | Issue description 可命中；title/code 回归 E17；Member 仍可用 |
| C | create/update/delete 后索引一致；alembic upgrade 绿（双测或方言 fixture） |
| D | API 分组契约不变；可选 rank/snippet 不破旧客户端 |
| E | FE 分组+键盘跳转回归；vitest；build ok |
| F | CLI **1.44.0** + `search` + pins |
| G | 跨租户隔离；formula no-emit spy；不改 E57–E59 主表面 |
| 门禁 | BE 定向（E60 search + E17 global_search）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E61 |

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **Search FTS mid**（方案 A）；方言 FTS + description 入索 + CLI search 并捆；**无** Push / 外部引擎 / Insights·SLA 再开 |
| D2 | 保持既有 `GET /api/search` 契约；引擎替换在 service 内；不新建第二套搜索 API |
| D3 | PG = **tsvector + GIN**；SQLite = **FTS5**；共享 backend 抽象；失败/未知方言 → ILIKE 降级 |
| D4 | 实体 = Issue / Project / Doc 走 FTS；Member 本轮 ILIKE；Issue **含 description** |
| D5 | 索引同步 = alembic + DB generated/triggers（优先）或等价应用层双写；无独立 reindex worker |
| D6 | CLI = **1.44.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E57/E58/E59 主表面；非目标见 §2；不 push；不自开 E61 |

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | PG 文本配置 / 查询解析？ | **Q1a** `simple` 配置（中英混合 WS 更稳，少 stemming 惊喜）+ `plainto_tsquery`；备选 Q1b `english` + `websearch_to_tsquery`（英文体验更好，中文弱） |
| Q2 | Member 是否进 FTS？ | **Q2a** 仍 ILIKE（集合小）；备选 Q2b 一并 FTS5/tsvector（收益低、测本+） |
| Q3 | SQLite FTS 同步方式？ | **Q3a** FTS5 外挂 content 表 + INSERT/UPDATE/DELETE triggers；备选 Q3b 仅应用层双写（易漏路径） |
| Q4 | Doc/Issue 超长正文？ | **Q4a** 入索截断（如 8–16KiB 字符）+ 检索 snippet ≤120；备选 Q4b 全量入索（大 doc 胀索引） |
| Q5 | 排名与排序？ | **Q5a** 组内 `rank DESC`，同分再 `updated_at DESC`；精确 issue_code 命中置顶（保 E17）；备选 Q5b 仅 updated_at（浪费 FTS） |
| Q6 | CLI 形态？ | **Q6a** 顶层 `opentask search <q> [--limit] [--json]` 打 `/api/search`；备选 Q6b 仅文档化用 `curl`（过薄，砍） |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE SearchBackend 抽象 + ILIKE 降级保绿（TDD 锚定 E17）  
3. PG tsvector + GIN alembic + Issue description（TDD）  
4. SQLite FTS5 + triggers + 双方言测（TDD）  
5. API rank/snippet 薄字段 + 回归租户隔离  
6. FE 薄接 rank/snippet  
7. CLI 1.44.0 `search`  
8. 门禁 + acceptance tip  

## 7. 测试要点

- E17 回归：空 q、code 精确、跨租户、limit cap  
- PG：description 命中；ts_rank 排序；GIN 存在（migration）  
- SQLite：FTS5 MATCH；trigger 同步；删除后不命中  
- 降级：mock 未知 dialect → ILIKE 仍可用  
- spy：无 fire_webhooks；不触 E57 alert eval / E58 holiday apply / E59 digest；formula no-emit  
- CLI 1.44.0 pins + `search` 帮助/json  
- FE vitest flatten 兼容  

---

## 附录 · runners-up（供 E61+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」不重开。  
2. **假日包扩容 thin**（再加 EU/UK 或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 刚交；非轮换优先。  
3. **Insights 共享报表 thin-mid**（personal→shared / 只读团队报表；仍砍拖拽构建器）— E59 刚交 personal；隔一轮再评估。  

（备选扫描但本轮不推：Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动、评论全文 — Roadmap 排除或过厚/可顺延。Webhook 再厚 / PagerDuty — 出站弧已闭。Formula emit — 永不本轮。重做 E52–E59 表面 — 无增量，不推。）

## CLI 版本

**1.44.0**

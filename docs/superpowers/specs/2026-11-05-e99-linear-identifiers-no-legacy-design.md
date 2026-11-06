# E99 Design：Linear Issue Identifiers — 无历史环境，删除 legacy

日期：2026-11-05（Asia/Shanghai）  
Epic：E99  
触发：Way 明示 ——「不存在历史版本的环境」「不需要考虑旧标识兼容和存量迁移」（`pt226u` / `pt227u`）  
基线：`sprint/E98-S1` @ `02af930`（全文 `02af930d60aa23bff5037ee499e8725fefabe5ef`；E98 acceptance tip；含 KEY-N 新建 harden + E98 年号回填 migration + legacy 双读保留）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟分支 `sprint/E99-S1`  
约束：**本轮仅 design 入库**；**禁止改码 / 禁止 plan·实现本轮**；**禁止 commit / push / 开 PR**；大软不自开实现，等 Yuri 下发 plan。  
入库：`docs/superpowers/specs/2026-11-05-e99-linear-identifiers-no-legacy-design.md`  
状态：**Yuri 代 Way 已拍板** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05（Asia/Shanghai）。

> 依据：
> 1. Way `pt226u` / `pt227u`：无历史环境；不要旧标识兼容；不要存量迁移。
> 2. E98 design/acceptance（Q3a/Q4a/Q6a 曾保留无限期 legacy 读 + 年号回填）——被本 Epic **显式推翻**。
> 3. tip @ `02af930` 扫描：`legacy_issue_code` 列、双解析、`keys.py` year 投影、E98 backfill rev `f9a0b1c2d3e4`、CLI/FE 双形态、E12/E60 FTS 引用。
> 4. E12 仍保留且有价值的部分：`workspaces.issue_key` + `issue_counter`、新建仅 `KEY-N`、WS 绑定策略（E98 已落地）——**不回退**。

---

## 0. Brainstorming

### 背景（E98 落地后仍多出的「历史税」）

E98 已堵死新建年号，但按当时 Q3a/Q4a 仍留下：

| 面 | tip @ `02af930` 实证 |
|----|----------------------|
| 列 | `issues.legacy_issue_code`（E12 `b8c9d0e1f2a4` 引入；可空索引） |
| 解析 | `get_issue(by_code)`：`issue_code OR legacy_issue_code`；VCS resolve 同类 OR；search/CSV ILIKE 含 legacy |
| Migration | `f9a0b1c2d3e4` E98 data backfill：年号主码 → KEY-N 并写 legacy；孤儿跳过 |
| Jira | `keys.py`：legacy `ISSUE{year}-N` ↔ `OPENTASK-{year*1e9+seq}` **与** KEY-N 高号段并存 |
| CLI | `validate_issue_code` 显式 `ISSUE\d+` 分支；help 多处 legacy 例 |
| FE | `looksLikeIssueCode` 宽正则仍匹配 `ISSUE2026-32`；vitest 断言 legacy true |
| FTS | E60 `issues_fts` 列/触发器含 `legacy_issue_code` |
| 测试 | `test_e98_backfill_migration`、`test_by_code_matches_legacy_issue_code`、Jira wire year 往返 |

Way 现判定：**产品环境无历史版本** → 上述兼容与回填均为纯复杂度，应删除，只留 `KEY-N`。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **删 legacy 语义 + drop 列**：解析/搜索/Jira codec/CLI/FE 仅 KEY-N；E98 backfill 废止（保留 rev id 作 no-op 或链上接 E99）；**新 migration drop `legacy_issue_code`** 并调整 FTS；不重写 E12/E60 历史 revision 文件 | **推荐**：满足 Way；链稳定；单 sprint 可验 |
| B | 仅停用双读，**保留**可空列与 E98 backfill 文件不动 | 半吊子；死列+死 migration 继续误导 |
| C | **改写** E12 `b8c9…` / E60 FTS revision，使全新库从不创建 legacy 列 | 破坏已 stamp 的 alembic 校验和；多 worktree/本地库风险高；Way「无历史产品」≠「可改写已应用的迁移链」 |
| D | 继续 E98 Q3a 无限期兼容 | **违背** `pt227u` |

**已选默认：A。**

自检：不重开 E97–E79 CLI 邻面；不引入 Team；不改 Requirement `需求{year}-N`；不 push；本轮不实现。

### Why this Epic now

E98 按「有存量」设计留下了双读与回填；Way 立刻澄清环境无历史 → 必须在下一 Epic 拆掉，否则 KEY-N 产品真相仍被 legacy 路径、codec、列与测试拖住。

---

## 1. 目标

1. **全产品表面只认 `KEY-N`**：`^[A-Z0-9]{2,6}-\d+$`（前缀 = Workspace.`issue_key` 规则；大小写策略与现网 KEY-N 一致）。  
2. **删除年号 legacy 双解析**：`by_code` / VCS / search / CSV 等不再读 `legacy_issue_code`，不再把 `ISSUE{year}-N` 当合法 issue code。  
3. **删除 / 废止 E98 存量回填**：不再维护「年号 → KEY-N + 写 legacy」数据 migration 行为；对应 directed 测删除或改写为「no-op / 不存在年号行」。  
4. **Jira**：只保留 **KEY-N → `OPENTASK-{numeric}`** 投影与反向解码；**删除** year×1e9 legacy 编解码。Jira 侧外部 ID 仍是数字形 `OPENTASK-…`（集成需要），但数字 **仅** 来自 KEY-N 号段，不再有「解出 ISSUE2026-N」路径。  
5. **CLI / FE 样例与校验**：主例与 doctest / help / vitest 全部 KEY-N；校验收紧到 2–6 前缀；**不再**断言 `ISSUE2026-*` 为合法 code。  
6. **DB**：在无历史产品前提下，**drop `issues.legacy_issue_code`（及索引）** 为默认；ORM/API 响应若曾暴露该字段则移除。  
7. **FTS**：去掉对 `legacy_issue_code` 的索引列/触发器依赖（随 drop 列的同 Epic migration 重建或调整，见 §3.4）。

非目标见 §5。

---

## 2. 探索事实（tip @ `02af930`）

### 2.1 必须动的代码锚点

| 锚点 | 现状 | E99 动作 |
|------|------|----------|
| `models/issue/model.py` | `legacy_issue_code` 列 | 删字段 |
| `services/issue_service.py` | `get_issue` OR legacy；list search ILIKE legacy | 仅 `issue_code` |
| `services/vcs/service.py` | OR legacy | 仅 `issue_code` |
| `services/search/{service,backend}.py` | ILIKE / FTS 含 legacy | 去掉 |
| `services/issue_csv/service.py` | ILIKE legacy | 去掉 |
| `api/issue/router.py` | docstring 提 legacy | 改 KEY-N only |
| `api/jira/keys.py` | `_ISSUE_CODE_RE` + year 编解码 | 删除；KEY-N only |
| CLI `helpers.validate_issue_code` | `ISSUE\d+` 分支 | 删；`^[A-Za-z][A-Za-z0-9]{1,5}-\d+$`（2–6） |
| CLI `core/issue.py` help | 大量 `ISSUE2026-*` / legacy 说明 | 改 KEY-N |
| FE `command-palette-entities.ts` | 无上限前缀 | 收紧 2–6；测例去 legacy true |
| Alembic `f9a0b1c2d3e4` | 年号回填 | 废止行为（§3.3） |
| 新 Alembic E99 | — | drop 列 + FTS 调整 |
| Tests | E12 legacy by_code、E98 backfill、Jira year 往返 | 删或改 KEY-N |

### 2.2 迁移链现实

```text
… → e8f9a0b1c2d3 (project_lead_members)
  → f9a0b1c2d3e4 (E98 year backfill)   # 本地 tip 头；未随 E90–E93 推远程的叙事下仍可能已 stamp 于本 WT DB
  → (E99) g0a1b2c3d4e5 drop legacy_issue_code + FTS fix   # 拟
```

E12 `b8c9d0e1f2a4` **仍会在全新库**先 `ADD legacy_issue_code` 再被 E99 drop——这是有意的：**不改写历史 revision**，用前向 migration 收敛到无列终态。

### 2.3 「无历史」不等于「库内保证零行」

实现验收以 **代码路径与 schema 终态** 为准：不再分配、不再解析、不再投影年号。若某开发库仍残留 `ISSUE{year}-N` 主码行（不应存在于 Way 所述环境），E99 **不提供**回填；可选 directed 断言「测试夹具禁止插入年号主码」，而不是 migration 改写。

---

## 3. 架构与行为

```
Create (unchanged from E98)
  resolve_workspace → FOR UPDATE counter → KEY-N only

Read / Resolve (E99)
  by_code / VCS / search → issue_code ONLY
  ISSUE{year}-N → 404 / validation false（不再命中）

Jira key (E99)
  KEY-N ⇄ OPENTASK-{KEY_N_BASE + pack(prefix)*CAP + seq}
  number < KEY_N_BASE → ValueError（不再 decode 为 ISSUE{year}-N）

Schema
  issues.issue_code UNIQUE
  （无 legacy_issue_code）
```

### 3.1 解析与搜索

- `get_issue(..., by_code=True)`：`Issue.issue_code == issue_id`（可加 `workspace_id` 收窄，逻辑保持）。  
- 所有 `or_(… legacy_issue_code …)` / ILIKE legacy：**删除**。  
- Router / OpenAPI 描述改为「by_code = issue_code（KEY-N）」。

### 3.2 Jira `keys.py`

- 保留：`KEY_PREFIX`、`_KEY_N_RE`、`KEY_N_BASE`、`KEY_N_SEQ_CAP`、radix-37 pack、`issue_code_to_key` / `key_to_issue_code` 的 KEY-N 分支。  
- 删除：`_ISSUE_CODE_RE`、`SEQ_CAPACITY` year 公式、`key_to_issue_code` 中 `number < KEY_N_BASE` 解年号分支（改为明确 `ValueError`）。  
- **保留**「Jira 外部 key 为 `OPENTASK-{数字}`」——这是集成协议的 **numeric external id**，不是 OpenTask 产品 issue id；产品 id 仅为 KEY-N。  
- 更新 `backend/README.md` / 过时 sprint 证据文案：**不强制**改历史 sprint 证据 md（§5）；只改仍当「现行文档」的 README/注释。

### 3.3 E98 backfill revision 处理（默认 Q2a）

**默认：保留 revision id `f9a0b1c2d3e4` 在链上，但将 `upgrade()`/`backfill_year_issue_codes` 改为文档化 no-op**（或 `pass` + log「superseded by E99; no stock migration」），然后 E99 新 revision `down_revision = f9a0b1c2d3e4` 执行 drop 列。

理由：

- 本 WT / 其他 agent 库可能已 `alembic_version = f9a0b1c2d3e4`；删文件会导致头断裂。  
- E98 未要求本设计去改写已推送远程的故事；本地链稳定性优先。  
- Way 要的是「不要存量迁移**行为**」，不是「物理抹掉 git 里曾经的文件名」。

备选（Q2b，不推荐默认）：直接删除 `f9a0…` 文件，E99 `down_revision = e8f9a0b1c2d3`，并要求已 stamp 环境 `alembic stamp e8f9a0b1c2d3`——仅当确认**无任何 DB** stamp 过 f9a0 时可用。

### 3.4 Drop `legacy_issue_code`（默认 Q1a：值得做）

**结论：在无历史新鲜环境，drop 列是值得的**——双读/OR/FTS/测试的长期税高于「留一列永远 NULL」。

实现约束：

1. **新** Alembic revision（勿改 E12 `b8c9…` 正文）。  
2. `DROP INDEX ix_issues_legacy_issue_code`（若在）+ `DROP COLUMN legacy_issue_code`（PG/SQLite 可移植写法与既有 migration 风格一致）。  
3. **FTS**：E60 用 SQLite FTS5 时通常需 rebuild（drop/recreate `issues_fts` + 触发器，去掉 legacy 列），并同步 PG 路径若有 `legacy` 拼进 document 的表达式（`tests/conftest.py` / search backend 镜像 DDL）。  
4. ORM 删除 mapped column；任何 schema/dict 导出字段一并删。  
5. **不**在 drop 前跑年号回填。

### 3.5 CLI / FE

| 面 | 动作 |
|----|------|
| `validate_issue_code` | 仅 KEY-N（2–6）；doctest 去掉 `ISSUE2026-123` True |
| auto-detect 测 | 年号样例改为 **False** 或不列入 code 类 |
| `issue.py` help | 例一律 `OT-1` / `WAY-42`；删除「legacy still resolves」 |
| FE regex | `^[A-Za-z][A-Za-z0-9]{1,5}-\d+$`（与 2–6 对齐） |
| vitest | `ISSUE2026-32` → **false**（前缀过长 / 非合法 key）；保留 `ABC-1` true |

### 3.6 测试策略

- **删除**：`test_e98_backfill_migration.py`（或缩成「no-op revision 可 upgrade」）；`test_by_code_matches_legacy_issue_code`；`test_missing_legacy_by_code_404`（若仅测 legacy）；Jira wire 中 year 往返断言。  
- **保留/加强**：E98 新建 KEY-N / WS 绑定 / 400；E12 KEY-N 分配与 `by_code` **主码**；Jira KEY-N ↔ OPENTASK 高号段；CLI/FE 收紧后负例。  
- 夹具禁止再 `INSERT` 年号主码充当 happy path。

---

## 4. Q1–Q6（推荐默认 = a）

### Q1 · 是否 drop `legacy_issue_code` 列

- **a（推荐）**：是。前向 migration drop 列 + 索引；ORM/FTS/搜索同步删除。无历史环境下保留死列无收益。  
- b：仅代码停用双读，列保留可空。  
- c：改写 E12 migration 使列从未存在。

**默认 Q1a**（拒 Q1c：checksum/多库风险）。

### Q2 · E98 backfill revision `f9a0b1c2d3e4`

- **a（推荐）**：保留 revision id；`upgrade` 改为 no-op；删除/改写 backfill 单测；E99 接在其后 drop 列。  
- b：删除该文件；E99 接 `e8f9a0b1c2d3` + stamp 说明。  
- c：保留完整回填行为（违背 Way）。

**默认 Q2a。**

### Q3 · Jira codec

- **a（推荐）**：删除 year legacy 编解码；仅 KEY-N ↔ `OPENTASK-{n}`；`< KEY_N_BASE` → ValueError。  
- b：编码拒年号，解码仍接受旧数字（半兼容）。  
- c：连 `OPENTASK-{n}` 也改成非数字（破坏 Orca 探测约定）——否决。

**默认 Q3a**（保留数字 external id，仅服务 KEY-N）。

### Q4 · CLI/FE 校验收紧

- **a（推荐）**：前缀 2–6；`ISSUE2026-N` 不再视为合法 code。  
- b：只改文案，正则仍放行长前缀/`ISSUE\d+`。  
- c：允许任意长 Linear 式前缀（与 WS `issue_key` 2–6 不一致）。

**默认 Q4a。**

### Q5 · 历史 revision / 文档

- **a（推荐）**：不改写 E12/E60 已应用 revision 文件；现行 README/代码注释改 KEY-N；历史 sprint 证据 md 不动。  
- b：全库 rg 改写所有历史证据 md。  
- c：改写 E12/E60 migration 正文。

**默认 Q5a。**

### Q6 · Requirement 年号 `需求{year}-N`

- **a（推荐）**：本 Epic **不动**（与 E98 非目标一致）；若 Way 要清，另开 Epic。  
- b：本 Epic 一并改 Requirement。  
- c：文档宣称 Issue+Requirement 同时清，但只改 Issue。

**默认 Q6a。**

**拍板结果：Yuri 代 Way 于 2026-11-05 确认 Q1a–Q6a 全收；可按此编写 plan 并实施。**

---

## 5. 非目标

- 重写 E12 / E60 历史 Alembic 文件使「从未有过 legacy 列」  
- 任何年号 → KEY-N **数据回填** / 孤儿绑定  
- Linear Team 模型  
- Requirement `需求{year}-N`  
- 重开 E97–E79 邻面；Activity Push / 门户 / 甘特 / Initiative health / bulk project_id / watching  
- 改 Jira 前缀名 `OPENTASK` 或改为非数字 key（破坏集成）  
- formula emit；停 7377/9527  
- 本设计阶段改业务码 / push / 开 PR（design-only commit 除外）

---

## 6. 验收标准（acceptance 草案）

1. **Schema**：upgrade 至 E99 head 后，`issues` **无** `legacy_issue_code` 列；ORM 无该属性。  
2. **解析**：`GET /api/issues/ISSUE2026-1?by_code=true`（夹具不插入年号行）→ 404；KEY-N by_code → 200。  
3. **搜索 / FTS / CSV / VCS resolve**：源码与 DDL **无** `legacy_issue_code` 引用。  
4. **Jira**：`issue_code_to_key("OT-1")` 往返成立；`issue_code_to_key("ISSUE2026-3")` / `key_to_issue_code("OPENTASK-2026000000003")` → ValueError；无 year 公式分支。  
5. **E98 backfill**：`f9a0…` 若保留则为 no-op；`test_e98_backfill_migration` 删除或仅验 no-op；**无**改写年号行的生产代码路径。  
6. **CLI/FE**：`validate_issue_code` / `looksLikeIssueCode` 对 `ISSUE2026-32` 为 false；主 help/演示无 legacy 教法。  
7. **回归**：E98 新建 KEY-N / WS 绑定 / 400 行为保持；BE/CLI/FE 门禁绿（允许已知 `test_user_search` flake）；WT 干净；`f`+`r` 守。  
8. **文档**：本 design + 后续 plan + acceptance；superpowers 链完整。

---

## 7. 精确清理范围（给实现 / 回执用）

### 7.1 删除或废止

- 双解析 OR / ILIKE / FTS 对 `legacy_issue_code` 的依赖  
- `keys.py` legacy year 编解码与相关测例  
- E98 backfill **行为** + `test_e98_backfill_migration.py`（或改 no-op）  
- E12 `test_by_code_matches_legacy_issue_code` 等 legacy happy path  
- CLI/FE 文案与「legacy still resolves」断言  

### 7.2 新增

- Alembic：drop `legacy_issue_code` + FTS 重建/去列  
- （可选）负例测：年号 code / 旧 OPENTASK year 数字 → 拒绝  

### 7.3 明确不动

- E98 WS 绑定 / `_generate_issue_code` 必填 WS / 禁止年号**分配**  
- `issue_key` / `issue_counter` / KEY-N 分配锁  
- Requirement 年号；Team；邻面 Epic；历史 sprint 证据 md  

---

## 8. 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| 本地 DB 已 stamp `f9a0` 且删 revision 文件 → alembic 断裂 | 中 | **Q2a** 保留 id、改 no-op |
| SQLite FTS5 drop 列需 rebuild，遗漏触发器 → 写入失败 | 中 | 与 E60 同构的 drop/recreate；conftest DDL 同步；directed search 测 |
| 某处动态 SQL / 原始 SQL 仍 SELECT legacy | 中 | rg 门禁；全量 BE |
| Orca/Jira 若环境仍存旧 `OPENTASK-2026…` 外键 | 低（Way：无历史） | Q3a 直接 ValueError；不提供兼容 |
| FE 宽正则曾把长前缀当 code，收紧后 ⌘K 行为变化 | 低 | 与 WS key 2–6 对齐；测例锁定 |
| 误改 E12/E60 历史 revision checksum | 高若做错 | Q5a 禁止；只加前向 E99 |
| 与「未 push 的 E94–E98 长链」交织 | 低 | E99 基线钉死 `02af930`；不混入无关 CLI |

---

## 9. 实现约束（拍板后给大软）

| 项 | 约束 |
|----|------|
| 流程 | design 确认 → plan → TDD → verify → acceptance |
| 分支 | `sprint/E99-S1`（自 E98 tip `02af930`） |
| 本轮 | **仅本 design 文件**；作者不改业务码、不 commit、不 push |
| 门禁 | BE full + identifiers/Jira/search directed；CLI/FE 相关；守 `f`+`r` |
| 安全 | 测试假码；无跨租户猜 WS（保持 E98）；不复活年号分配 |
| 本地 | only；等 Yuri 下发 plan |

---

## 附录 · runners-up / 否决

1. **留列停读（Q1b）** — 死 schema，拒。  
2. **改写 E12/E60（Q1c/Q5c）** — alembic 校验和与多 WT，拒。  
3. **保留 year 解码（Q3b）** — 半兼容违背「不要旧标识」，拒。  
4. **改非数字 Jira key（Q3c）** — 破坏 Orca 约定，拒。  
5. **本 Epic 清 Requirement 年号（Q6b）** — 扩 scope，拒。  
6. **继续 E98 回填（Q2c）** — 违背 `pt227u`，拒。

## 基线 / 路径

- Baseline tip：`02af930d60aa23bff5037ee499e8725fefabe5ef`（`sprint/E98-S1`）  
- 拟分支：`sprint/E99-S1`  
- 设计：`docs/superpowers/specs/2026-11-05-e99-linear-identifiers-no-legacy-design.md`  
- 拟 plan：`docs/superpowers/plans/2026-11-05-e99-linear-identifiers-no-legacy-plan.md`  
- 拟 acceptance：`docs/superpowers/acceptances/2026-11-05-e99-linear-identifiers-no-legacy-acceptance.md`  
- **设计阶段未改码、未 push**；design-only commit 后进入 plan 与实现

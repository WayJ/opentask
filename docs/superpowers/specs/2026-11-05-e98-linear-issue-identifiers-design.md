# E98 Design：Linear-style Issue Identifiers harden（堵死 ISSUE{year}-N 新建）

日期：2026-11-05（Asia/Shanghai）  
Epic：E98  
触发：Way 明示 ——「ISSUE 的 ID 要参考 Linear 的设计，不要再沿用 ISSUE+年份+id」（`pt217u`）  
基线：`sprint/E97-S1` @ `f8d5232`（全文 `f8d5232e1f761ce384e57fc79e0e649b1fcf4f26`；E97 acceptance tip；起草扫描 @ `1f2e255`，E97 为 CLI-only 事实仍成立）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E98-S1`  
约束：**本地提交 design only**；**禁止改码 / 禁止 plan·实现本轮**；**禁止 push / 开 PR**；**不开 E99**；大软不自开实现，等 Yuri 下发 plan。  
入库：`docs/superpowers/specs/2026-11-05-e98-linear-issue-identifiers-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

> 注：`docs/product/PROJECT.md` 在本 tip **不存在**。本设计依据：
> 1. Way `pt217u` 产品硬约束（Linear 式标识，禁年号前缀）；
> 2. E12 design/plan（`2026-11-04-e12-invites-issue-key-de-pge-design.md` + S1 plan）已落地的 `Workspace.issue_key` / `issue_counter` / `legacy_issue_code` / 双解析；
> 3. tip @ `1f2e255` 代码扫描（分配器、Jira、Tasks contract、POST `/api/issues`、CLI/FE 样例；基线 `f8d5232` = E97 CLI-only，分配器事实不变）；
> 4. Linear 对齐心智：`TEAM-123` / `ENG-42` 工作区（或团队）作用域单调序号，**不是** `ISSUE2026-32`。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E12 已交付 Linear 式主路径：

| 能力 | 现状（tip 实证） |
|------|------------------|
| 分配 | `IssueService._generate_issue_code(workspace_id)`：有 WS → `SELECT … FOR UPDATE` 行锁 `workspaces` → `issue_counter += 1` → `f"{ws.issue_key}-{ws.issue_counter}"` |
| 列 | `workspaces.issue_key`（2–6 `[A-Z0-9]`，UQ）+ `issue_counter`；`issues.issue_code` UNIQUE；`issues.legacy_issue_code` 可空索引 |
| 解析 | `get_issue(..., by_code=True)`：`issue_code` **或** `legacy_issue_code`；可选 `workspace_id` 租户收窄 |
| FE | `looksLikeIssueCode` 已匹配 `KEY-N` 与 legacy `ISSUE{year}-N` |
| CLI | `validate_issue_code` / auto-detect 已双读 KEY-N + legacy |

**但仍有三条创建入口在无 `workspace_id` 时落入年号回退**（分配器 docstring 明示「无 workspace_id：保留历史 ISSUE{year}-N」）：

1. **`POST /api/issues`** —— `get_optional_workspace_context`；缺 `X-Workspace-Id` 时 `workspace_id=None` → 年号码 + 孤儿行。  
2. **Jira `POST /rest/api/2/issue`** —— `service.create_issue(..., dept_id=None)` **未传** `workspace_id` → 年号码。  
3. **Tasks contract `POST /api/tasks`** —— 同样未传 `workspace_id` → 年号码；`ContractIssueService.create_issue` 仅在撞唯一索引时重试（注释仍写「当年最大序号 + 1」）。

Way 的要求不是「再发明一套 Team 模型」，而是：**产品上不再产生 `ISSUE+年份+id`**；标识对齐 Linear `KEY-N`。E12 主路径已对齐，本 Epic 是 **harden / 堵洞**，不是重做 S1。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Harden E12**：删除/禁用 `_generate_issue_code` 年号回退；所有创建路径必须落到可解析的 Workspace；Jira/Tasks 在「可可靠推导」时绑当前用户默认/唯一成员 WS，否则 **确定性 400**（可行动错误）；保留 legacy **读/解析** 无限期；仅回填仍以 `ISSUE{year}-N` 为 **当前** `issue_code` 的行；清理 API/CLI/FE 样例 | **薄→中**：复用 E12 列与锁；单 sprint 可验；满足 Way；不引入 Team 表 |
| B | 新建 Linear **Team** 模型 + per-team key/counter，Issue 改挂 Team | 过厚；与现有 Workspace=租户 模型冲突；E12 已选 WS 作用域 |
| C | 强制所有写路径 `require_workspace_context`，Jira/Tasks 无头一律 400，不做默认 WS 绑定 | 过硬；易打断既有 Jira/Orca 集成（常无 WS header） |
| D | 仅改文档「请带 X-Workspace-Id」，保留年号回退 | **违背 Way**；洞仍在 |
| E | 全局把 `ISSUE` 当 key 前缀（`ISSUE-1`） | 与历史 `ISSUE2026-N` 混淆；非 Linear 心智 |

**已拍板：A（Harden existing E12）。**  
B/C/D/E 列入附录 runners-up / 否决理由。

自检：不重开 E97 VCS CLI / E96 access-token / E95 project-repos / …；**不**引入 Team 表；**不**物理删 PGE/Requirement；**不**默认废弃 legacy 读；**不开 E99**；formula no-emit；守 E63 `f`+`r`。

### Why this Epic now（一句话）

Way 明示禁年号 ID 时，主路径已是 `KEY-N`，但 Jira / Tasks contract / 无头 `POST /api/issues` 仍可写出 `ISSUE2026-N`——必须在下一 Epic 堵死新建，并保留旧链解析，避免「产品嘴上 Linear、API 仍年号」。

---

## 1. 目标

1. **新建 Issue 的 `issue_code` 永远是 `KEY-N`**（`^[A-Z0-9]{2,6}-\d+$`，前缀 = 目标 Workspace.`issue_key`），**永不**再分配 `ISSUE{year}-N`。  
2. **堵死三条已知洞**：无 WS 的 `POST /api/issues`、Jira `create_issue`、Tasks `POST /api/tasks`（及任何仍调用 `_generate_issue_code(None)` 的同胞路径，含 collection/batch 若可无 WS）。  
3. **绑定策略（安全）**：有显式 Workspace（header / body / 已解析上下文）→ 用之；否则若能**可靠**推导「当前用户的默认/唯一可写 Workspace」→ 绑之并落库 `workspace_id`；否则 **400**，错误文案可行动（如何传 `X-Workspace-Id` / 先建 WS / 指定 project 所属 WS），**禁止**年号回退，**禁止**静默挂到「库内最早 Workspace」一类跨租户猜测（既有 `_resolve_fallback_workspace_id` 用于标签等旁路时，本 Epic **不得**拿它给新 Issue 分配码）。  
4. **读兼容**：`legacy_issue_code` + `issue_code` 双解析、`by_code`、CLI auto-detect、Jira key 双向对 **已存在** 的 legacy 码 **无限期保留**，除非另开 deprecation Epic。  
5. **回填**：仅处理「当前 `issue_code` 仍匹配 `^ISSUE\d{4}-\d+$`」的行；写入 `legacy_issue_code`（若空）并改写为所属 WS 的下一 `KEY-N`；**不得**覆盖已是 KEY-N 且 `legacy_issue_code` 另有用途的行；无 `workspace_id` 的孤儿年号行：能可靠挂到创建者默认 WS 则挂+改码，否则记数/报告并 **跳过改码**（不删数据）。  
6. **样例清理**：OpenAPI / router docstring / CLI help·doctest / FE 注释·测试夹具中「教人新建/演示」的 `ISSUE2026-*` 改为 `KEY-N`；保留「legacy 仍可解析」的双读测试。  
7. **并发**：保留/加强行锁路径测试（双并发 create 同 WS → 两枚连续 N，无重复）；无 WS 路径在 harden 后应变为 400 或绑定后走同一锁，**不再**依赖 `issue_code` 唯一索引重试年号算法。

非目标见 §5。

---

## 2. 探索事实（起草扫描 tip @ `1f2e255`；基线 `f8d5232`）

### 2.1 分配器

```text
services/issue_service.py::_generate_issue_code
  if workspace_id:
      SELECT Workspace … WITH FOR UPDATE
      counter += 1; flush; return f"{issue_key}-{counter}"
  else:
      prefix = f"ISSUE{year}-"
      scan LIKE prefix%; return prefix+(max+1)   # ← 必须删除/改为 raise
```

`create_issue(..., workspace_id=None)` 直接把 `None` 写入行并调用上述回退。

### 2.2 入口

| 入口 | 传 WS？ | 后果 |
|------|---------|------|
| `POST /api/issues` + `X-Workspace-Id` | 是 | KEY-N ✓ |
| `POST /api/issues` 无头 | 否 | 年号 ✗ |
| `POST /api/issues` + `template_id` 无头 | 已 400「使用模板需要 X-Workspace-Id」 | 可对齐扩展 |
| Jira `POST /rest/api/2/issue` | 否 | 年号 ✗ |
| Tasks `POST /api/tasks` | 否 | 年号 ✗ |
| `duplicate_issue` / 多数 WS 路由 | `require_workspace_context` | KEY-N ✓ |
| `issue_collection_service.parse_and_create_issues` | 每条可带 `workspace_id` | 缺则年号 ✗ |

### 2.3 解析 / 兼容（应保留）

- `get_issue(by_code=True)`：`issue_code ==` OR `legacy_issue_code ==`  
- Jira `keys.py`：legacy `ISSUE{year}-N` ↔ `OPENTASK-{year*1e9+seq}`；KEY-N ↔ 高号段投影（已存在）  
- CLI：`^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$`  
- FE：`looksLikeIssueCode` 已双形态  

### 2.4 「默认 Workspace」可可靠推导的定义（本 Epic）

**可靠**（可自动绑定）当且仅当下列之一成立（实现计划写清优先级）：

1. 请求显式携带 Workspace 上下文（`X-Workspace-Id` / 已认证 Jira/Tasks 扩展头若已有 / body 字段若本 Epic 增补且文档化）；或  
2. 当前用户作为 **owner** 恰好有 **一个** 个人默认 Workspace（注册时 `create_for_owner` 创建的那类），且用户对该 WS 为可写角色（owner/member）；或  
3. 当前用户作为 member/owner 的可写 Workspace **恰好一个**。

**不可靠**（必须 400，禁止猜测）：

- 多个可写 WS 且无显式头；  
- 零可写 WS；  
- 使用「库内最早 Workspace / 全局 Default」跨用户回退（既有 `_resolve_fallback_workspace_id`）给 **新 Issue 编号**。

错误示例（文案可微调，语义固定）：

```text
400 workspace_required: Issue identifiers are KEY-N scoped to a workspace.
Provide X-Workspace-Id, or ensure the caller has exactly one writable workspace.
Year-prefixed ISSUE{year}-N allocation is removed.
```

### 2.5 与 Linear 的对齐边界

- Linear：**Team** key + 序号。  
- OpenTask E12：**Workspace** `issue_key` + 序号（产品已选）。  
- 本 Epic **不**引入 Team；若未来要 Team，另开 Epic，且不得复活年号。

---

## 3. 架构与行为

```
Create Issue (any surface)
  │
  ├─ resolve_workspace(explicit | sole-writable | owner-default)
  │     ├─ ok → workspace_id
  │     └─ ambiguous/missing → HTTP 400 (actionable)  // never ISSUE{year}
  │
  └─ _generate_issue_code(workspace_id)   // workspace_id REQUIRED
        SELECT ws FOR UPDATE → counter+1 → "{issue_key}-{n}"

Read / Resolve
  issue_code | legacy_issue_code | Jira key codecs | CLI/FE dual regex
  (indefinite; no silent drop)
```

### 3.1 `_generate_issue_code`

- 签名改为 `workspace_id: str`（非 Optional），或 Optional 但 `None` → `ValueError`（路由转 400）。  
- **删除** year/LIKE 扫描分支。  
- 保持 `WITH FOR UPDATE` + flush；计数器语义不变。

### 3.2 `POST /api/issues`

- 无显式 WS 时走 §2.4 解析；成功则视同带上下文创建。  
- 推荐默认（Q5a）：**先**尝试可靠默认绑定，失败再 400——比「一律强制 header」更不打断单 WS 用户/脚本。  
- `template_id` 路径已要求 WS：保持；绑定成功后的隐式 WS 亦满足。

### 3.3 Jira / Tasks

- `create_issue` / `create_task`：在调用 service 前解析 `workspace_id`（§2.4）；传入 `create_issue(..., workspace_id=…)`。  
- 响应中的 `key` / `metadata.issue_code` 必须为 KEY-N。  
- Jira **读**路径：继续接受 legacy 数字投影与 KEY-N 投影；`key_to_issue_code` 对旧号段仍可解出 `ISSUE{year}-N` 以便查 `legacy_issue_code` / 旧 `issue_code`（若回填后仅存 legacy，解析层已覆盖）。  
- **禁止**新创建再走 year 投影的「正向分配」（只读解码可留）。

### 3.4 回填 migration

数据 migration（Alembic data step 或 follow-up revision；实现计划定 `down_revision`）：

1. 选出 `issue_code ~ '^ISSUE[0-9]{4}-[0-9]+$'` 的行。  
2. 若已有非空 `legacy_issue_code` 且与 `issue_code` 不同 → **跳过改码**（避免踩无关 legacy 链）；仅当 `legacy_issue_code IS NULL` 或等于当前年号码时可设 `legacy_issue_code = issue_code`。  
3. 有 `workspace_id`：按 WS 分组，`ORDER BY created_at, id`，从该 WS 当前 `issue_counter` 之后分配新 N，或紧凑重编号（**推荐 Q4a：紧跟现 counter 递增分配，不重排已是 KEY-N 的旧单**，避免打乱已公开 KEY）。  
4. 无 `workspace_id`：尝试创建者唯一/默认可写 WS；成功则挂上再改码；否则 skip + 计数日志。  
5. 更新 `workspaces.issue_counter = max(counter, max N assigned)`。  
6. 幂等：再跑不改已是 KEY-N 的行。

### 3.5 样例 / 文档 / 测试夹具

| 面 | 动作 |
|----|------|
| `api/issue/router.py` docstring 例 | `ISSUE2026-32` → `OT-32` + 注明 legacy 仍可用 |
| `openapi*.json` | 重生或手工改 example（若生成物入库） |
| CLI help / doctest | 主例改 `OT-1` / `WAY-42`；保留至少一个 legacy 解析测例 |
| FE | 演示字符串改 KEY-N；`looksLikeIssueCode('ISSUE2026-32')` **保留**为 true 的兼容断言 |
| `CodingWorker.md` | 主路径强调 KEY-N；legacy 列为兼容 |
| 单元测 | 新增：无 WS 且多 WS 用户 → 400；单 WS → KEY-N；并发双 create → 两码唯一且前缀=issue_key |

---

## 4. Q1–Q6（推荐默认 = a）

### Q1 · 建模策略

- **a（推荐）**：Harden E12 Workspace `issue_key`+counter；不引入 Team。  
- b：新建 Team 模型做 key 作用域。  
- c：仅文档，保留年号回退。

**默认 Q1a。**

### Q2 · Jira / Tasks 无显式 WS 时

- **a（推荐）**：可靠推导（§2.4）则绑定；否则确定性 400；**永不**年号。  
- b：一律 400（不做默认绑定）。  
- c：绑库内最早/全局 Default WS（跨租户猜测）。

**默认 Q2a**（拒 Q2c）。

### Q3 · Legacy 读/解析寿命

- **a（推荐）**：无限期保留双解析与 Jira legacy 解码，直至另开 deprecation Epic。  
- b：本 Epic 起标 Deprecated header，N 个版本后删除。  
- c：本 Epic 直接删除 legacy 列与解码。

**默认 Q3a。**

### Q4 · 回填范围

- **a（推荐）**：只改写当前 `issue_code` 仍为 `ISSUE{year}-N` 的行；先写入/保留 `legacy_issue_code`；不碰已是 KEY-N 的行；不覆盖无关 legacy。  
- b：全量按 created_at 重排所有 Issue 为紧凑 KEY-1…N（破坏已公开 KEY）。  
- c：不回填，只堵新建（库内旧年号码继续当主码展示）。

**默认 Q4a**（Q4c 违背「不要再沿用」的展示真相；Q4b 过险）。

### Q5 · `POST /api/issues` 无头

- **a（推荐）**：与 Q2a 同策略（可靠默认绑定，否则 400）。  
- b：改为 `require_workspace_context`（无头一律 400）。  
- c：保持年号回退。

**默认 Q5a。**

### Q6 · 样例清理范围

- **a（推荐）**：API docstring / OpenAPI examples / CLI 主 help / FE 演示与新建文档 → KEY-N；**保留** legacy 双读测试与兼容说明。  
- b：只改 BE，CLI/FE 样例不动。  
- c：连兼容测试里的 legacy 字符串也删光。

**默认 Q6a。**

**已拍板：Q1a–Q6a 全收**（Yuri 代 Way · 2026-11-05 Asia/Shanghai；本文件为 design-only 入库）。

---

## 5. 非目标（本 Epic 不做）

- Linear **Team** 实体、多 Team 每 Issue、Team↔Project 矩阵  
- 废弃/删除 `legacy_issue_code` 或拒绝解析 `ISSUE{year}-N`  
- 重排已是 KEY-N 的公开编号  
- 改 Requirement `需求{year}-N`（另弧；本 Epic 只动 Issue）  
- SSO / 强制 SMTP / 物理删 PGE  
- 重开 E97 VCS CLI、E96 access-token、E95 project-repos、E94–E79 邻面  
- Activity Push / 门户 / 甘特 / Initiative health / bulk `project_id` / `project list --watching`  
- formula emit  
- **E99**（本设计明确 **No E99**；实现齐套后 STOP）  
- push / 开 PR（本地 only，直至 Yuri 另令）

---

## 6. 验收标准（acceptance 草案）

1. **新建**：经 `POST /api/issues`（有头 / 单 WS 无头）、Jira create、Tasks create 产生的 `issue_code` **匹配** `^[A-Z0-9]{2,6}-\d+$` 且前缀等于目标 WS.`issue_key`；库内 **零** 新行 `issue_code ~ '^ISSUE[0-9]{4}-'`（测后断言）。  
2. **拒绝年号**：强制 `_generate_issue_code(None)`（单测直接调）→ ValueError；多 WS 用户无头 create → 400，body 含可行动指引。  
3. **并发**：同 WS 两并行 create → 两枚不同 N，无唯一索引重试风暴依赖年号算法；行锁路径有 directed 测。  
4. **Legacy 读**：回填后 `GET …/{legacy}?by_code=true`、CLI `issue show ISSUE2026-…`、Jira get-by-old-key **仍 200**（夹具预置 legacy）。  
5. **回填安全**：已是 `WAY-7` 且 `legacy_issue_code='OLD-OTHER'` 的行 **不变**；仅年号主码行改写并写 legacy。  
6. **样例**：抽查 OpenAPI/router/CLI 主例不再教用户「创建 ISSUE2026-*」；兼容测仍在。  
7. **门禁**：BE full + directed；CLI full（若触 helpers）；FE vitest + build；WT 干净；`f`+`r` 守；不自开 E99。  
8. **文档三件套**：design（本文件）+ plan + acceptance；superpowers design/plan/TDD/verify/acceptance = ok。

---

## 7. 实现约束（拍板后给大软）

| 项 | 约束 |
|----|------|
| 流程 | design 已确认 → plan → TDD → verify → acceptance |
| 分支 | `sprint/E98-S1`（自 E97 acceptance tip `f8d5232`） |
| 本轮 | **仅 design 入库**；作者 **不**改业务码、**不**写 plan/实现 |
| 门禁 | BE full + issue-key/concurrency directed；相关 CLI/FE；守 `f`+`r` |
| 安全 | 测试只用假码；migration 可在空库/夹具库跑；不做跨租户 Default 猜测编号 |
| 本地 | only；不 push；**不开 E99** |

---

## 附录 · runners-up / 否决

1. **Team 模型（Scheme B）** — 过厚；与 E12 Workspace 作用域重复；Way 未要求。  
2. **一律强制 header、无默认绑定（Q2b/Q5b）** — 可后置收紧；本轮优先少打断单 WS 集成。  
3. **跨租户最早 WS 回退（Q2c）** — 安全否决。  
4. **本 Epic 删除 legacy（Q3c）** — 断链；否决。  
5. **全量重编号（Q4b）** — 破坏已共享 KEY；否决。  
6. **只堵新建不回填（Q4c）** — 列表仍展示年号主码，弱于 Way 意图。  
7. **Requirement 年号** — 另弧。  
8. **再开 E97–E79 CLI 邻面 / Push / 甘特 / 门户** — 勿默认。  
9. **E99** — 本包 **No E99**。

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E97-S1` @ `f8d5232e1f761ce384e57fc79e0e649b1fcf4f26`（起草扫描 @ `1f2e2556d448618cce6b5703da05dd1963b68ecd`）  
- 分支：`sprint/E98-S1`  
- 设计：`docs/superpowers/specs/2026-11-05-e98-linear-issue-identifiers-design.md`  
- 拟 plan：`docs/superpowers/plans/2026-11-05-e98-linear-issue-identifiers-plan.md`  
- 拟 acceptance：`docs/superpowers/acceptances/2026-11-05-e98-linear-issue-identifiers-acceptance.md`  
- **本地 only**；design 已拍板入库；不 push / 不开 PR；**未改码**；**大软不自开 plan/E99**；等 Yuri 下发 plan/TDD

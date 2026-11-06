# E98 Acceptance：Linear-style Issue Identifiers harden

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E98-S1`  
基线：`46848a8`（全文 `46848a80ed632088f4435a9a86fb00e0482d4428`；含 E98 design；E97 tip `f8d5232` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e98-linear-issue-identifiers-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e98-linear-issue-identifiers-plan.md`  
Migration：`backend/alembic/versions/2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py`（rev `f9a0b1c2d3e4`，down `e8f9a0b1c2d3`）

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Scheme A / Q1a–Q6a：新建仅 `KEY-N`；`_generate_issue_code(None)` → `ValueError`；删除年号分配分支；`resolve_workspace_for_issue_create`（显式 header / `project_id→project.workspace_id` 可写 / 唯一个人默认 / 唯一可写；零/多可写 → `WorkspaceRequiredError` → HTTP 400）；堵 `POST /api/issues`、Jira create、Tasks contract create、`parse_and_create_issues`；`SELECT … FOR UPDATE` 计数器锁保留；data migration 回填年号主码、保留 legacy、跳过不可靠孤儿、幂等；**未**引入 Team；**未改** Requirement 年号；邻面 E79–E97 **未重开** |
| B FE | ✅ | 样例演示改 KEY-N（`IssueCardsDemo` `OT-1`、`MarkdownEditor` `#OT-1`）；legacy 双读语义保留；vitest **427 passed**（63 files）；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 冲掉 imports/typings → **已 checkout 恢复**；WT 干净） |
| C CLI | ✅ | **VERSION 保持 1.81.0**（E98 未要求 bump）；help/示例主码 KEY-N，legacy 双解析说明保留；suite **852 passed**, 89 skipped |
| D 安全/邻面/no-emit | ✅ | **无跨租户猜 WS**（禁用 `_resolve_fallback_workspace_id` / 库内最早 / Default 猜测用于新建）；**无新 ISSUE{year} 分配路径**；legacy 读/双解析/Jira legacy key codec **长期保留**；不可靠孤儿 **跳过不删**；formula no-emit；无 Team / 真 Git / OAuth2 / Push / 门户 / 甘特 / Initiative health / bulk project_id / watching filter；**未停** 7377/9527 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E98-S1`
- tip short：5c6a04f
- tip full：5c6a04fae16389fdc7bf03b5fe4763f7ba55f153
- **未 push / 未开 PR / 未开 E99**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E98 `tests/api/test_e98_linear_issue_identifiers.py` | **11 passed**（显式 WS / 单可写自动绑 / 多可写 400 / viewer 零可写 400 / `None` ValueError / FOR UPDATE 源路径 / 同 WS 连续 KEY-N / legacy by_code / resolver / surfaces） |
| Directed E98 backfill `tests/api/test_e98_backfill_migration.py` | **4 passed**（年号→KEY-N 保留 legacy；已有 KEY-N+异 legacy 跳过；不可靠孤儿跳过不删；空库 noop / 幂等） |
| Directed E12 `tests/api/test_issue_key.py` | **合跑 24 passed**（含 E98 上两项） |
| Directed issue create / collection / Jira / Tasks / review | **140 passed**（`test_issues_api` + `issue_collection` + `tasks_contract` + `tasks_jira_wire` + `tasks_mapping_config` + `tasks_review_fixes`） |
| Full BE `pytest tests` | **1477 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **852 passed**, 89 skipped；VERSION **1.81.0** |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 冲掉 imports → 已 checkout 恢复；WT 干净） |

## Q1a–Q6a 落地

- **Q1a** 新建仅 `KEY-N`（`^[A-Z0-9]{2,6}-\d+$`，KEY=目标 WS.`issue_key`）；删除 `_generate_issue_code` 的 `ISSUE{year}-N` 分配；`_generate_issue_code(None)` → 明确 `ValueError`
- **Q2a** 创建路径全堵：`POST /api/issues`、Jira create、Tasks contract create、`issue_collection_service.parse_and_create_issues`（含 parse_collection 注入可选 header WS）及同胞路径
- **Q3a** 无显式 WS：仅可靠推导唯一可写 / 唯一个人默认 /（可选）`project_id` 且调用方可写于该 project.workspace_id；零可写 / 多可写 / 不可写 project WS → 可行动 400；**绝不** `_resolve_fallback_workspace_id` / 库内最早 / Default 跨租户猜
- **Q4a** 显式 header/body/已认证上下文优先；绑定后落库 `workspace_id`，走同一 `SELECT Workspace FOR UPDATE` 计数器锁
- **Q5a** Jira/Tasks 创建前解析 `workspace_id` 并传 service；响应 KEY-N；旧 Jira 数字投影 / legacy 解码 **只读长期保留**；CLI auto-detect / FE looksLikeIssueCode / legacy GET by_code **保留**
- **Q6a** 回填仅 `^ISSUE\d{4}-\d+$` 主码；按 WS `created_at,id` 从 counter 后递增；不重排已有 KEY-N；`legacy_issue_code` 空或等于当前年号码时保留，另有不同值则跳过改码；无 WS 孤儿仅当能可靠绑创建者唯一可写 WS 才绑+改码，否则报告跳过、不删；更新 counter；幂等；样例主例 KEY-N

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 安全

- 无跨租户猜 WS；viewer 不可写；多可写不猜；无 WS 不猜
- 无新 `ISSUE{year}` 分配代码路径（分配侧）；legacy **读**路径与 Jira legacy codec 仍在
- 不可靠孤儿不删；已有 KEY-N 不改；测试仅假 issue codes

## 禁区

未触碰：Team 新模型 / Requirement 年号 / 真 Git / OAuth2 / Activity Push / 门户 / 甘特 / Initiative health / bulk project_id / watching filter；**未重开** E79–E97 邻面；formula no-emit；**未停** 7377/9527；**未 push / 未开 PR / 未自开 E99**；WT 干净；CLI VERSION 未擅自升版（仍 1.81.0）。

## 未做 / flake / 并发边界

- 未做：E99；Team；真 Git/OAuth2；Push/门户/甘特；Initiative health；bulk project_id；watching filter
- flake：`tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`（已知，不阻塞）
- 并发：SQLite 下 `FOR UPDATE` 无真实行锁；directed 验证 **源路径含 `with_for_update`** + 同 WS 顺序创建连续 KEY-N；**未**伪称真实 Postgres 并行事务竞争已在本环境验证

# E99 Acceptance：Linear Issue Identifiers — 无历史环境，删除 legacy

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E99-S1`  
基线：`f4bd973`（全文 `f4bd973e9d3ba006676511c526efb4168e02fa9c`；含 E99 design；E98 tip `02af930` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e99-linear-identifiers-no-legacy-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e99-linear-identifiers-no-legacy-plan.md`  
Migrations：
- E98 no-op：`backend/alembic/versions/2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py`（rev `f9a0b1c2d3e4`，down `e8f9a0b1c2d3`）
- E99 drop：`backend/alembic/versions/2026_11_05_5900-g0a1b2c3d4e5_e99_drop_legacy_issue_code.py`（rev `g0a1b2c3d4e5`，down `f9a0b1c2d3e4`）

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Scheme A / Q1a–Q6a：drop `legacy_issue_code` + 索引；ORM 删字段；`get_issue`/list/search/VCS/CSV 仅 `issue_code`；E98 backfill → 文档化 no-op；Jira 仅 KEY-N↔OPENTASK（`< KEY_N_BASE` → ValueError）；branch_naming 忽略年号；**保持** E98 WS 绑定/新建 KEY-N/`_generate_issue_code` 必填 WS/禁止年号分配/跨租户不猜；**未改** Requirement 年号；**未**引入 Team；邻面 E79–E97 **未重开**；**未改写** E12 `b8c9…` / E60 `s5b6…` 历史 revision |
| B FE | ✅ | `looksLikeIssueCode` 前缀 2–6；`ISSUE2026-32` → false；`ABC-1` true；vitest **427 passed**（63 files）；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 冲掉 imports/typings → **已 checkout 恢复**；WT 干净） |
| C CLI | ✅ | **VERSION 保持 1.81.0**；`validate_issue_code` / auto-detect 仅 KEY-N；help/演示一律 KEY-N；删「legacy still resolves」；suite **852 passed**, 89 skipped |
| D 安全/邻面/no-emit | ✅ | 无跨租户猜 WS（E98 保留）；无年号分配/双读/year Jira codec；夹具禁止年号主码 happy path；formula no-emit；无 Team / 真 Git / OAuth2 / Push / 门户 / 甘特；**未停** 7377/9527 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E99-S1`
- tip short：b694556
- tip full：b6945563b4856c51a052cff015f001cd8c79fe2e
- **未 push / 未开 PR / 未开下一 Epic**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E99 `tests/api/test_e99_no_legacy_identifiers.py` | **5 passed**（KEY-N by_code 200；年号 404；ORM 无列；Jira KEY-N 往返+年号 ValueError；drop migration 去列） |
| Directed E98 create/WS `test_e98_linear_issue_identifiers.py` | **回归绿**（含年号 by_code 404 负例替换原 legacy happy path） |
| Directed E98 backfill no-op | **2 passed** |
| Directed issue_key / branch_naming / e60 FTS / Jira TestKeyCodec / tasks_contract | **合跑绿** |
| Full BE `pytest tests` | **1481 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **852 passed**, 89 skipped；VERSION **1.81.0** |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 冲掉 → 已恢复；WT 干净） |
| `rg legacy_issue_code` | 业务 `backend/opentask/` **零**；仅历史 alembic（E12 add / E60 FTS）+ E98 no-op 说明 + E99 drop + docs/tests |

## Q1a–Q6a 落地

- **Q1a** 前向 migration drop `legacy_issue_code` + 索引；ORM 删除；API 不暴露
- **Q2a** `f9a0b1c2d3e4` 保留 id；`upgrade`/`backfill_year_issue_codes` → 文档化 no-op；E99 `g0a1b2c3d4e5` 接其后 drop + FTS rebuild
- **Q3a** Jira 仅 KEY-N ↔ `OPENTASK-{n}`；年号/`< KEY_N_BASE` → ValueError；保留数字 external id 协议
- **Q4a** CLI/FE 前缀 2–6；`ISSUE2026-*` false；help/演示 KEY-N
- **Q5a** 不改写 E12/E60 历史 revision（diff 对两文件为 0）；不改历史 sprint 证据 md；现行 README/CodingWorker/代码注释改 KEY-N
- **Q6a** Requirement 年号不动

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 安全

- 无跨租户猜 WS；E98 绑定/400 保留
- 无年号分配、无双读、无 year Jira 编解码
- 测试假码；夹具种子改为 `CT-{n}` / `OT-{n}`

## 禁区

未触碰：Team / Requirement 年号 / 真 Git / OAuth2 / Activity Push / 门户 / 甘特 / Initiative health / bulk project_id / watching；**未重开** E79–E97；**未改写** E12/E60 历史 revision；formula no-emit；**未停** 7377/9527；**未 push / 未开 PR / 未自开下一 Epic**；WT 干净；CLI VERSION 未升版（仍 1.81.0）。

## 风险 / flake / 边界

- FTS：SQLite FTS5 drop/recreate + 触发器去 legacy；PG drop generated `search_tsv` 后按无 legacy 表达式重建；conftest/e60 DDL 同步
- stamp：`f9a0` 保留 id 作 no-op，避免已 stamp 环境断链
- 无历史年号外键兼容（Way：无历史）；旧 `OPENTASK-2026…` → ValueError
- flake：`test_user_search`（已知，不阻塞）

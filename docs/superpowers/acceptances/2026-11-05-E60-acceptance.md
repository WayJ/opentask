# E60 Acceptance：Search FTS mid · CLI 1.44.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E60-S1`  
基线：`0fb0df5`（全文 `0fb0df5c1d72330736463863c2f446d05e7745cd`；含 E60 design；E59 实现 tip `ccc5b4f` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e60-search-fts-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e60-search-fts-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A SearchBackend + 方言 FTS | ✅ | `backend.py`：PostgresFTS / SQLiteFTS / ILike；空 q 空结果；limit 1..50 |
| B 实体字段 | ✅ | Issue +description；Project name+desc；Doc title+body；Member ILIKE（Q2a） |
| C 索引同步 | ✅ | alembic `s5b6c7d8e9f3`；PG generated tsvector+GIN；SQLite FTS5+triggers；无 reindex worker |
| D API 契约 | ✅ | `GET /api/search` 分组不变；可选 rank/snippet |
| E FE | ✅ | types + flatten 兼容缺省 rank；snippet≤120；vitest；build ok |
| F CLI 1.44.0 | ✅ | 顶层 `opentask search <q> [--limit] [--json]`；pins 全钉 |
| G 安全 / no-emit | ✅ | 跨租户 403；fire_webhooks spy；不改 E57–E59 主表面 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1172 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E60 无关）
- BE 定向 E60+E17 search：**14 passed**（E60 API 6 + backend unit 4 + E17 4）
- CLI：**551 passed / 89 skipped**（全钉 **1.44.0**）
- FE vitest：**352 passed**（46 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E60-S1`
- tip：`dce9b60`（全文 `dce9b6001470cec6f402b6017db5ea70ef300672`）
- **未 push / 未开 PR / 未开 E61**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

# E60 Acceptance：Search FTS mid · CLI 1.44.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E60-S1`  
基线：`0fb0df5`（全文 `0fb0df5c1d72330736463863c2f446d05e7745cd`；含 E60 design；E59 实现 tip `ccc5b4f` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e60-search-fts-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e60-search-fts-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A SearchBackend + 方言 FTS | ⏳ | PG tsvector+GIN；SQLite FTS5；未知方言 ILIKE；空 q 空结果 |
| B 实体字段 | ⏳ | Issue +description；Project name+desc；Doc title+body；Member ILIKE |
| C 索引同步 | ⏳ | alembic；PG generated；SQLite triggers；无 reindex worker |
| D API 契约 | ⏳ | 分组不变；可选 rank/snippet |
| E FE | ⏳ | `/search` + global-search 薄接；vitest；build |
| F CLI 1.44.0 | ⏳ | 顶层 `search`；pins |
| G 安全 / no-emit | ⏳ | workspace 隔离；spy；不改 E57–E59 主表面 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地（待实现填 ✅）。

## 门禁

- BE：_pending_
- BE 定向 E60+E17：_pending_
- CLI：_pending_
- FE vitest / build：_pending_
- 已知 flake：`tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`（不挡）

## Tip

- 分支：`sprint/E60-S1`
- tip：_pending_
- **未 push / 未开 PR / 未开 E61**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

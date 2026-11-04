# E62 Acceptance：评论全文入索 mid · CLI 1.46.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E62-S1`  
基线：`6fdeba8`（全文 `6fdeba8bcdcaf82890cb823bc772ce3d5b777e19`；含 E62 design；E61 实现 tip `9e8d281` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e62-comment-fts-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e62-comment-fts-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A SearchBackend.search_comments + PG/SQLite/ILike + alembic | ✅ | alembic `u7d8e9f0a1b5`；conftest PG bootstrap；三后端 + SQLite FTS5 trigger 单测 |
| B API `comments` 组 + empty q + E60 四组回归 | ✅ | Hit={id,issueId,issueCode,snippet,rank?,authorUserId?,createdAt?}；limit 1..50；code boost 仍仅 issues |
| C COMMENT only；软删 Issue 下不命中；嵌套各 Hit | ✅ | SYSTEM 排除；parent+reply 各 Hit；无 MC/Req |
| D FE 评论组 + 深链 Issue；缺键兼容；vitest；build | ✅ | flatten + /search；Q5a Issue detail |
| E CLI 1.46.0 + comments 输出 + pins | ✅ | `issueCode · snippet`；全钉 1.46.0 |
| F 跨租户；no-emit；不改 E57–E58/E61 主表面 | ✅ | 403；fire_webhooks spy；仅 CLI version pins |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1191 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E62 无关）
- BE 定向 E62+E60 search：**19 passed**（E62 API 8 + E60 API 6 + backend unit 5）
- CLI：**555 passed / 89 skipped**（全钉 **1.46.0**）
- FE vitest：**357 passed**（46 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E62-S1`
- tip：`TIP_PLACEHOLDER`（全文 `FULL_PLACEHOLDER`）
- **未 push / 未开 PR / 未开 E63**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

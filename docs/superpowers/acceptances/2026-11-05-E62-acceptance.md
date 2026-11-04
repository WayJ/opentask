# E62 Acceptance：评论全文入索 mid · CLI 1.46.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E62-S1`  
基线：`6fdeba8`（全文 `6fdeba8bcdcaf82890cb823bc772ce3d5b777e19`；含 E62 design；E61 实现 tip `9e8d281` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e62-comment-fts-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e62-comment-fts-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A SearchBackend.search_comments + PG/SQLite/ILike + alembic | ⬜ | |
| B API `comments` 组 + empty q + E60 四组回归 | ⬜ | |
| C COMMENT only；软删 Issue 下不命中；嵌套各 Hit | ⬜ | |
| D FE 评论组 + 深链 Issue；缺键兼容；vitest；build | ⬜ | |
| E CLI 1.46.0 + comments 输出 + pins | ⬜ | |
| F 跨租户；no-emit；不改 E57–E58/E61 主表面 | ⬜ | |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**TBD**
- BE 定向 E62+E60：**TBD**
- CLI：**TBD**（全钉 **1.46.0**）
- FE vitest：**TBD**；`pnpm run build`：**TBD**

## Tip

- 分支：`sprint/E62-S1`
- tip：`TBD`
- **未 push / 未开 PR / 未开 E63**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

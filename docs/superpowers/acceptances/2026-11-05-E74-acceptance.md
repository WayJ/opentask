# E74 Acceptance：评论线程 mid — nested replies · CLI 1.58.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E74-S1`  
基线：`52e0b1d`（全文 `52e0b1dc22e3ad671604d1e6add13520b7305502`；含 E74 design；E73 实现 tip `9d76ea2` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e74-comment-threading-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e74-comment-threading-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | validate parent 同 Issue / 未软删 / 深度=1；扁平 GET；软删父隐藏子；notify ∪ 父作者；无 alembic |
| B FE | ⏳ | buildCommentTree + 回复 UX；vitest；build；f+r |
| C CLI 1.58.0 | ⏳ | `--parent-id` + list Parent；全钉 1.58.0 |
| D 邻面/no-emit | ⏳ | 无新 webhook 名；formula no-emit；不重开 E63–E73 / E69 附件主表面 |
| E 租户隔离 | ⏳ | 既有成员校验不变 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：_pending_
- CLI：_pending_
- FE：_pending_

## Tip

- 分支：`sprint/E74-S1`
- tip：_pending_
- **未 push / 未开 PR / 未开 E75**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E75

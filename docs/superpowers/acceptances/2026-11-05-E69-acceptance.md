# E69 Acceptance：评论附件 mid — issue_comment Documents · ACL 复用 · CLI 1.53.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E69-S1`  
基线：`a5d1a91`（全文 `a5d1a91e09884fe6c78b57aeb512be30a9e04a69`；含 E69 design；E68 实现 tip `35f1e0a` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e69-comment-attachments-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e69-comment-attachments-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A storage `entity_type=issue_comment` | ✅ | Q1a 复用 documents；错绑 issue/comment → 404 |
| B nested CRUD + E66 ACL | ✅ | Q2a `require_attachment_read` 扩 issue_comment；download/preview/signed-url 复用 |
| C list embed + FE | ✅ | Q4a 评论 list 嵌 attachments 摘要（cap 20）；CommentsCard + detail Activity；vitest flatten；elegant-router `f`+`r` 守 E63（build 误删已还原） |
| D CLI 1.53.0 | ✅ | Q6a `issue comment attachment list\|upload\|download`；全钉 **1.53.0** |
| E 安全 / no-emit / 邻面不动 | ✅ | Q5a 无新 webhook 事件名（spy）；Q3a 硬删级联 Document+MinIO、软删保留文件；不改 E57–E68 邻面主表面；formula 未触；不暴露公开 `/r`/`/f` |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1252 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E69 无关）
- BE 定向 comment-attachments + E66 ACL：**9 + 10 passed**
- CLI：**575 passed / 89 skipped**（全钉 **1.53.0**）
- FE vitest：**374 passed**（51 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E69-S1`
- tip：`5e11bf9`（全文 `5e11bf9135de8b2e1d7e9d28b3849092207f91d4`）
- **未 push / 未开 PR / 未开 E70**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E70

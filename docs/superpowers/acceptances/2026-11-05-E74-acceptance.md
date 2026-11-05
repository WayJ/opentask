# E74 Acceptance：评论线程 mid — nested replies · CLI 1.58.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E74-S1`  
基线：`52e0b1d`（全文 `52e0b1dc22e3ad671604d1e6add13520b7305502`；含 E74 design；E73 实现 tip `9d76ea2` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e74-comment-threading-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e74-comment-threading-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | `validate_comment_parent`（同 Issue / 未软删 / 深度=1 仅回根）；`add_comment` 校验；扁平 GET 含 `parent_id`；Q3a 软删父级联软删子 + list 防御过滤；Q4a `notify_comment` ∪ 父评作者；Q5a 仍 `comment.created`（无新事件名）；**无 alembic**；router 透传 HTTPException 400 |
| B FE | ✅ | `buildCommentTree` + vitest；详情树缩进 +「回复」+ `replyToId`→`addComment(..., parentId)`；CommentsCard 同款；复用 AttachmentList/IssueReactions（不改 E69/E27 契约）；build ok；elegant-router 误删 `f`+`r` 类型/imports 已还原；`routes/index.ts` 仍含 `/f/:token`+`/r/:token` |
| C CLI 1.58.0 | ✅ | Q6a `issue comment add --parent-id`；list 显示 `Parent:`；json 含 `parent_id`；全钉 **1.58.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION`；历史 epic 版本断言级联至 1.58.0 |
| D 安全/邻面/no-emit | ✅ | Q5a 无新 webhook 事件名；formula no-emit（本轮未触 formula attrs）；不改 E63–E73 邻面主表面（仅 CLI 版本钉）；不重开 E69 附件 ACL/上传主表面；无 Activity Push / 无门户 / 无甘特 |
| E 租户隔离 | ✅ | 既有成员校验 / workspace 隔离路径不变 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1317 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E74 无关）
- BE 定向 E74 unit+API：**14 passed**
- CLI：**592 passed / 89 skipped**（全钉 **1.58.0**，含 `VERSION` 文件）
- FE vitest：**396 passed**（55 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E74-S1`
- tip：（全文 ）
- **未 push / 未开 PR / 未开 E75**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E75

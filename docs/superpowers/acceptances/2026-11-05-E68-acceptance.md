# E68 Acceptance：公开表单 → Triage 入队 mid — enqueue_triage · CLI 1.52.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E68-S1`  
基线：`6e3d1a6`（全文 `6e3d1a6a311c436559aad90bc860e356fa266d78`；含 E68 design；E67 实现 tip `dcf4c0c` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e68-public-form-triage-enqueue-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e68-public-form-triage-enqueue-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A enqueue_triage 列 + serialize | ✅ | Q1a Boolean NOT NULL DEFAULT false；alembic `x1a2b3c4d5e6`；CRUD `enqueueTriage` |
| B submit → TriageService.enqueue | ✅ | Q2a create 后 enqueue（幂等）；Q3a 与 CR 并存；响应 `triageEnqueued` |
| C FE 开关 + 成功文案 | ✅ | Q4a 文案区分、无 `/r` 深链；vitest `formSubmitSuccessCopy`；elegant-router `f`+`r` 守 E63（build 误删已还原） |
| D CLI 1.52.0 | ✅ | Q6a `form create/update --enqueue-triage`；list 列 EnqueueTriage；全钉 **1.52.0** |
| E 安全 / no-emit / 邻面不动 | ✅ | Q5a 无新 triage.* webhook（spy）；不改 E57–E67 邻面主表面；formula 未触；不改 recurrence advance |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1243 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E68 无关）
- BE 定向 forms+triage+E68：**20 passed**（e68 6 + issue_forms + triage）
- CLI：**572 passed / 89 skipped**（全钉 **1.52.0**）
- FE vitest：**372 passed**（51 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E68-S1`
- tip：`cff130f`（全文 `cff130f8da227dbaa756116b62c10cd629d50d2b`）
- **未 push / 未开 PR / 未开 E69**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E69

# E70 Acceptance：子问题进度汇总 mid — childProgress · CLI 1.54.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E70-S1`  
基线：`076f0f6`（全文 `076f0f6a5fb01c888b9297fa71377a7fec6818af`；含 E70 design；E69 实现 tip `08e327f` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e70-subissue-progress-rollup-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e70-subissue-progress-rollup-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 语义 total/done/open/percent | ✅ | Q1a done=resolved\|closed\|rejected；Q2a 仅直接子；Q3a 0 子 percent=null；软删不计；孙项不计 |
| B API 详情默认 + 列表 include | ✅ | Q4a 列表无 include 无 key；`?include=childProgress` 批量聚合；children 根同构；无 alembic |
| C FE 进度条/徽章 | ✅ | 详情子问题区 NProgress+分数；列表/看板有 payload 时徽章；vitest format；elegant-router `f`+`r` 守 E63（build 误删已还原） |
| D CLI 1.54.0 | ✅ | Q6a `issue show` 打印 ChildProgress；`issue list --include`；全钉 **1.54.0** |
| E 安全 / no-emit / 邻面不动 | ✅ | Q5a 读路径无新 webhook fire（spy）；formula 未触；不改 E57–E69 邻面主表面；不做 formula children rollup |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1265 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E70 无关）
- BE 定向 childProgress API + helper：**8 + 5 = 13 passed**
- CLI：**578 passed / 89 skipped**（全钉 **1.54.0**）
- FE vitest：**376 passed**（52 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E70-S1`
- tip：`"8895805"`（全文 `"8895805f3fb2762d6c2c6e82c28382be4702408b"`）
- **未 push / 未开 PR / 未开 E71**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E71

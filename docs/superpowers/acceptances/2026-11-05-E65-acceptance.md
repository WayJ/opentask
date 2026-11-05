# E65 Acceptance：Initiative 依赖图 mid — blocks/blocked_by/relates_to · CLI 1.49.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E65-S1`  
基线：`c3c0b25`（全文 `c3c0b25424732a5aaa7959f5c39939f693d17331`；含 E65 design；E64 实现 tip `ab746df` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e65-initiative-dependency-graph-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e65-initiative-dependency-graph-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A `initiative_relations` model + alembic `w9f0a1b2c3d7` | ✅ | 独立表；Q1a types；unique (src,tgt,type)；indexes；勿混 issue_relations |
| B API CRUD + 环检 + counts | ✅ | GET/POST/DELETE；Q2a 字面存储+双向展开；自环 400；跨 WS 404；viewer 写 403；Q4a blocks 环检 depth32；详情默认 counts；列表 `?include=relationCounts` |
| C FE 依赖折叠 + vitest + build | ✅ | 详情「依赖」折叠增删；列表徽章；无甘特/力导向；vitest `initiativeRelations.test.ts`；build ok（elegant-router 误删 f/r 已还原，守 E63） |
| D CLI 1.49.0 + relations | ✅ | `initiative relations list` + `relation add/remove`；全钉 **1.49.0** |
| E 安全 / no-emit / 邻面不动 | ✅ | Q5a 无新 webhook 事件/无 fire spy；不改 E57–E64 邻面主表面；formula 路径未触 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1216 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E65 无关）
- BE 定向 E65+E10：**22 passed**
- CLI：**564 passed / 89 skipped**（全钉 **1.49.0**）
- FE vitest：**364 passed**（49 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E65-S1`
- tip：`e1da754`（全文 `e1da754d70bd1722b5df9a8864447bd00a4be4f8`）
- **未 push / 未开 PR / 未开 E66**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E66

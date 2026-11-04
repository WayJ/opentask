# E65 Acceptance：Initiative 依赖图 mid — blocks/blocked_by/relates_to · CLI 1.49.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E65-S1`  
基线：`c3c0b25`（全文 `c3c0b25424732a5aaa7959f5c39939f693d17331`；含 E65 design；E64 实现 tip `ab746df` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e65-initiative-dependency-graph-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e65-initiative-dependency-graph-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A `initiative_relations` model + alembic `w9f0a1b2c3d7` | ⏳ | |
| B API CRUD + 环检 + counts | ⏳ | |
| C FE 依赖折叠 + vitest + build | ⏳ | |
| D CLI 1.49.0 + relations | ⏳ | |
| E 安全 / no-emit / 邻面不动 | ⏳ | |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：⏳
- BE 定向 E65+E10：⏳
- CLI：⏳（全钉 **1.49.0**）
- FE vitest：⏳；`pnpm run build`：⏳

## Tip

- 分支：`sprint/E65-S1`
- tip：⏳
- **未 push / 未开 PR / 未开 E66**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E66

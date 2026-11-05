# E68 Acceptance：公开表单 → Triage 入队 mid — enqueue_triage · CLI 1.52.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E68-S1`  
基线：`6e3d1a6`（全文 `6e3d1a6a311c436559aad90bc860e356fa266d78`；含 E68 design；E67 实现 tip `dcf4c0c` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e68-public-form-triage-enqueue-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e68-public-form-triage-enqueue-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A enqueue_triage 列 + serialize | ⏳ | Q1a DEFAULT false |
| B submit → TriageService.enqueue | ⏳ | Q2a/Q3a；triageEnqueued |
| C FE 开关 + 成功文案 | ⏳ | Q4a 无 status 深链；守 f+r |
| D CLI 1.52.0 | ⏳ | Q6a --enqueue-triage |
| E 安全 / no-emit / 邻面不动 | ⏳ | Q5a 无新 webhook；不改 E57–E67 主表面；不改 advance |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：_pending_
- BE 定向 E68：_pending_
- CLI：_pending_（全钉 **1.52.0**）
- FE vitest：_pending_；`pnpm run build`：_pending_

## Tip

- 分支：`sprint/E68-S1`
- tip：_pending_
- **未 push / 未开 PR / 未开 E69**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E69

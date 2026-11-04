# E63 Acceptance：Customer Request 公开状态门户 mid · CLI 1.47.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E63-S1`  
基线：`ea2119c`（全文 `ea2119c6242ef47ef11217b5a6e8ccde8be1fa71`；含 E63 design；E62 实现 tip `0a5706b` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e63-customer-request-public-status-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e63-customer-request-public-status-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A status_token 列 + enable/rotate/revoke + alembic | ⏳ | |
| B 公开 GET 脱敏 + rate-limit + 404 | ⏳ | |
| C 公开 replies Q3a/Q4a/Q5a + 内部可见 | ⏳ | |
| D FE `/r/:token` + 详情管理；vitest；build | ⏳ | |
| E CLI 1.47.0 + status-link / public-status + pins | ⏳ | |
| F 跨租户；no-emit；不改 E57–E58/E60–E62/E61 主表面 | ⏳ | |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：（收口补）
- CLI：（收口补）
- FE vitest：（收口补）；`pnpm run build`：（收口补）

## Tip

- 分支：`sprint/E63-S1`
- tip：（收口补）
- **未 push / 未开 PR / 未开 E64**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`（收口确认）

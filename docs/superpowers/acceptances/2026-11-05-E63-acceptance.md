# E63 Acceptance：Customer Request 公开状态门户 mid · CLI 1.47.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E63-S1`  
基线：`ea2119c`（全文 `ea2119c6242ef47ef11217b5a6e8ccde8be1fa71`；含 E63 design；E62 实现 tip `0a5706b` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e63-customer-request-public-status-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e63-customer-request-public-status-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A status_token 列 + enable/rotate/revoke + alembic | ✅ | alembic `v8e9f0a1b2c6`；conftest additive bootstrap；writer+；跨租户 404 |
| B 公开 GET 脱敏 + rate-limit + 404 | ✅ | `/api/public/customer-requests/{token}`；Q1a linkedIssueCodes；`OPENTASK_PUBLIC_REQUEST_RATE_LIMIT` |
| C 公开 replies Q3a/Q4a/Q5a + 内部可见 | ✅ | 首 Issue→COMMENT+`comment.created`；无 Issue→`customer_request_public_replies`；无 Inbox notify |
| D FE `/r/:token` + 详情管理；vitest；build | ✅ | blank layout；enable/rotate/revoke/copy + 公开回复开关 |
| E CLI 1.47.0 + status-link / public-status + pins | ✅ | 全钉 **1.47.0** |
| F 跨租户；no-emit；不改 E57–E58/E60–E62/E61 主表面 | ✅ | 公开 GET 不 fire_webhooks；邻面 diff 空；仅 CLI version pins |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1198 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E63 无关）
- BE 定向 E63+E22/E31：**18 passed**
- CLI：**559 passed / 89 skipped**（全钉 **1.47.0**）
- FE vitest：**359 passed**（47 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E63-S1`
- tip：`3b4a239`（全文 `3b4a2396d710612b999781362d435061ba6e4dcd`）
- code tip：`6ca0e2f`（全文 `6ca0e2f044725e81d08824c95326c48dc35c73d5`）
- **未 push / 未开 PR / 未开 E64**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

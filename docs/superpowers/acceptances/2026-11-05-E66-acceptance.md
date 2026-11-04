# E66 Acceptance：Issue 附件鉴权 mid — ACL · 签名 URL · CLI 1.50.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E66-S1`  
基线：`0e93813`（全文 `0e93813d08d1f7994366bced65fbf0e5b9a828a6`；含 E66 design；E65 实现 tip `8202d69` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e66-issue-attachment-acl-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e66-issue-attachment-acl-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A download/preview + issue-scoped ACL | ✅ | Q1a 会话+WS 成员；无会话 401；非成员 404；成员 200；去「公共」叙事 |
| B 签名 URL mint/verify | ✅ | Q2a/Q3a TTL 默认 900 / 硬顶 3600；`POST …/signed-url` + `GET /signed/{token}`；无状态 HMAC；篡改/过期拒 |
| C FE signed-url 预览 | ✅ | Q4a AttachmentList 预览走 signed-url；显式下载走鉴权 blob；vitest `attachmentUrls.test.ts`；build ok |
| D CLI 1.50.0 + attachment | ✅ | Q6a `issue attachment download` + `signed-url`；全钉 **1.50.0** |
| E 安全 / no-emit / 邻面不动 | ✅ | Q5a 下载/签发不 fire_webhooks spy；不改 E57–E65 邻面主表面；formula 路径未触 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1226 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E66 无关）
- BE 定向 E66+attachments：**12 passed**
- CLI：**566 passed / 89 skipped**（全钉 **1.50.0**）
- FE vitest：**368 passed**（50 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E66-S1`
- tip：`3a85dda`（全文 `3a85dda7a42353ae87e30e8ba8d005286864110a`）
- **未 push / 未开 PR / 未开 E67**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E67

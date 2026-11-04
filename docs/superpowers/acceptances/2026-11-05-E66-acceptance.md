# E66 Acceptance：Issue 附件鉴权 mid — ACL · 签名 URL · CLI 1.50.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E66-S1`  
基线：`0e93813`（全文 `0e93813d08d1f7994366bced65fbf0e5b9a828a6`；含 E66 design；E65 实现 tip `8202d69` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e66-issue-attachment-acl-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e66-issue-attachment-acl-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A download/preview + issue-scoped ACL | ⏳ | Q1a 会话+WS 成员；401/404/200；去「公共」叙事 |
| B 签名 URL mint/verify | ⏳ | Q2a/Q3a TTL 900/3600；无状态 HMAC |
| C FE signed-url 预览 | ⏳ | Q4a；vitest+build |
| D CLI 1.50.0 + attachment | ⏳ | Q6a download + signed-url |
| E 安全 / no-emit / 邻面不动 | ⏳ | Q5a 无新 webhook；不改 E57–E65 主表面 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：_pending_
- CLI：_pending_
- FE：_pending_

## Tip

- 分支：`sprint/E66-S1`
- tip：_pending_
- **未 push / 未开 PR / 未开 E67**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E67

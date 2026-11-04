# E29 Acceptance：Outbound Webhooks

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E29-S1`  
基线：`64c5371`

## 状态
✅ 本地齐套（未 push）

## tip
`f6c20e6` (`f6c20e69271413ac0af3e04516bfb72cdacfb7da`)

## 测试数
- BE pytest：890 passed / 1 flake（`test_user_search` 隔离复跑确认）/ 24 skipped；本 Epic `tests/api/test_webhooks.py` **4P**
- CLI pytest：442 passed / 89 skipped（含 E29 3P）；version **1.13.0**
- FE vitest：245 passed（+3 webhooks helpers）；`pnpm run build` 成功

## 范围核对
- [x] A workspace_webhooks CRUD + test + 权限/租户（写=owner；读=owner|member）
- [x] B 投递 HMAC + 重试 + delivery log；事件 issue.created/updated/status_changed/comment.created
- [x] C FE `/settings/webhooks`
- [x] D CLI `webhook list|create|update|delete|test`；**1.13.0**
- [x] 未 push / 未开 PR / 未自开 E30

## ADR 摘要
- D1：`/api/webhooks` 与入站 `/api/webhook`、`/api/webhooks/github` 并存
- D2：写=owner；读=owner|member；viewer 403
- D3：secret 仅创建响应返回；此后 secretHint
- D4–D10：events 枚举、envelope、签名、重试、best-effort fire、status_changed 另发 updated、test 强制投递
- D11–D13：FE / CLI / 非目标

## 缺口
- Slack OAuth、邮件、Zapier、入站新通道、队列/cron：明确非目标
- `test_user_search` 偶发失败与 E29 无关（既往 Epic 同款 flake）

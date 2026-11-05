# E30 Acceptance：Email Notifications

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E30-S1`  
基线：`3595778`

## 状态
✅ 本地齐套（未 push）

## tip
`c037f5b` (`c037f5b4dcd241d89916d6f9729387d7b9de6ed6`)

## 测试数
- BE pytest：897 passed / 1 flake（`test_user_search`，与既往 Epic 同款）/ 24 skipped；本 Epic `tests/api/test_email_notifications.py` **7P**
- CLI pytest：446 passed / 89 skipped（含 E30 4P）；version **1.14.0**
- FE vitest：248 passed（notif-prefs +3 helpers）；`pnpm run build` 成功

## 范围核对
- [x] A `email_enabled` + SMTP 配置 + `email_configured` 暴露于 prefs API
- [x] B Inbox create 后 best-effort 发信（mock transport）；失败不回滚
- [x] C FE `/settings/notifications` 邮件总开关；未配置 SMTP 禁用+提示
- [x] D CLI `notif prefs` 支持 `email_enabled`；`notif email-test`；**1.14.0**
- [x] 未 push / 未开 PR / 未自开 E31

## ADR 摘要
- D1：`email_enabled` 通道开关，不进 PREF_KEYS；默认 false（opt-in）
- D2：`email_configured` = SMTP_HOST ∧ SMTP_FROM
- D3：收件地址 = username 含 `@`（user 表无 email 列）
- D4–D6：create after-flush + to_thread；MemoryEmailTransport 可注入；纯文本+可选 FRONTEND_BASE_URL 深链
- D7：`POST /api/inbox/email-test`
- D8–D10：FE / CLI / 非目标

## 缺口
- digest/cron、HTML 模板、Slack、字段级偏好、SendGrid SDK：明确非目标
- `test_user_search` 偶发失败与 E30 无关

# E30 设计：Email Notifications（出站邮件）

日期：2026-11-04（Asia/Shanghai）  
Epic：E30  
基线：`sprint/E29-S1` @ `3595778`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E30-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E31**。

## 1. 目标

在 E27 Inbox 偏好之上补 **邮件通道**：偏好允许时把同类事件发到用户邮箱。

### A · Prefs + SMTP
- `notification_preferences.email_enabled`（bool，默认 **false**）— 通道总开关，**非**类型键
- SMTP 配置：`SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM`（可选 `SMTP_TLS`、`FRONTEND_BASE_URL`）
- 未配置（缺 HOST 或 FROM）→ 邮件 no-op；`GET /api/inbox/preferences` 暴露 `email_configured: bool`
- `GET/PUT /api/inbox/preferences` 含 `email_enabled`；原类型开关语义不变

### B · 发送
- Inbox `create` 成功后：对应类型 pref 已开（create 已尊重）+ `email_enabled` + 用户有可投递地址 + SMTP 已配置 → best-effort 发信
- 纯文本主题/正文：事件 title、body、issue 摘要、可选深链
- 单测 mock transport；失败只打 log，不回滚 Inbox

### C · FE
- `/settings/notifications`：邮件总开关；未配置 SMTP 时禁用并提示

### D · CLI **1.14.0**
- `notif prefs get|set` 支持 `email_enabled`
- `notif email-test`（向当前用户发测试信；未配置 → 清晰错误）

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | `email_enabled` 是**通道开关**，不进 `PREF_KEYS` / `TYPE_TO_PREF_KEY`；默认 **false**（opt-in） |
| D2 | `email_configured` = `bool(SMTP_HOST and SMTP_FROM)`；PORT 默认 587；USER/PASSWORD 可空（开放中继） |
| D3 | user 表无 email 列（既有约束）；**收件地址** = `username` 若含 `@`，否则视为无邮箱 → 跳过发送 |
| D4 | 发送挂在 `NotificationService.create` flush 成功之后；`asyncio.to_thread` + try/except；异常只 log |
| D5 | Transport 可注入：默认 `SmtpEmailTransport`（smtplib）；测试用 `MemoryEmailTransport` |
| D6 | 正文纯文本；深链若配置 `FRONTEND_BASE_URL` 则附 `/issue/{id}` 或资源路径 |
| D7 | `POST /api/inbox/email-test`：强制 `X-Workspace-Id`；未配置 → 400；无邮箱 → 400；成功返回 `{sent:true,to}` |
| D8 | FE：邮件开关独立卡片区；`!email_configured` 时 Switch disabled + Alert |
| D9 | CLI 1.14.0；`prefs set --key email_enabled --on|--off`；`notif email-test` |
| D10 | 非目标：digest/cron、HTML 模板、Slack、字段级偏好、SendGrid SDK、远程 push；不自开 E31 |

## 3. 非目标

digest/cron、HTML 精美模板、Slack、按字段级偏好、外部 ESP SDK、远程 push、E31。

## 4. 验收摘要

- prefs 含 `email_enabled` + `email_configured`；create 后按条件发信；email-test；FE 开关；CLI 1.14.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**

# E30 Plan：Email Notifications

日期：2026-11-04  
基线 tip：`3595778` · 分支 `sprint/E30-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** 出站邮件通道（SMTP）+ prefs `email_enabled` + FE 开关 + CLI 1.14.0。

**Architecture:** 扩展 `NotificationPreference`；`services/email`（config + transport + send）；`NotificationService.create` after-flush best-effort；`POST /api/inbox/email-test`；FE 设置页；CLI `notif` 扩展。

**Tech Stack:** FastAPI + SQLAlchemy + smtplib；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E31；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE
- [x] migration `email_enabled`
- [x] config SMTP + email service
- [x] prefs serialize/upsert + create 挂钩
- [x] `POST /api/inbox/email-test`
- [x] pytest

### Task 3 — FE
- [x] notif-prefs 类型扩展；设置页邮件开关
- [x] vitest helpers

### Task 4 — CLI 1.14.0
- [x] prefs 支持 email_enabled；`notif email-test`；version bump；测

### Task 5 — 门禁
- [x] BE/CLI/FE；acceptance tip；STOP

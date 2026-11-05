# E27 Plan：Notification preferences + 评论 Reactions

日期：2026-11-04  
基线 tip：`9bf8464` · 分支 `sprint/E27-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** 人均每 WS 通知偏好 + Inbox 写入尊重偏好 + 评论 Reactions + FE 设置页 + CLI 1.11.0。

**Architecture:** `NotificationPreference` 模型；`NotificationService` 偏好 CRUD + create 闸门；`CommentReaction` + IssueService 方法；`/api/inbox/preferences`；评论 reactions 路由；FE `/settings/notifications`；CLI `notif prefs`。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E28；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE 偏好
- [x] 模型 + 迁移 `notification_preferences`
- [x] service：get/upsert + create 闸门 + automation_comment 类型
- [x] `GET/PUT /api/inbox/preferences`
- [x] pytest

### Task 3 — BE 评论 Reactions
- [x] 模型 + 迁移 `comment_reactions`
- [x] service + API GET/POST/DELETE
- [x] 评论列表带 reactions；跨租户测

### Task 4 — FE
- [x] API client + `/settings/notifications`
- [x] Issue 详情评论区 Reactions
- [x] 基本 vitest

### Task 5 — CLI 1.11.0
- [x] `notif prefs get|set`；version bump；测

### Task 6 — 门禁
- [x] BE/CLI/FE；acceptance tip；STOP

# E54 Acceptance：Webhook 投递可观测 mid-thick · CLI 1.38.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E54-S1`  
基线：`7dc7f56`（全文 `7dc7f56c738aa34db3f6b40fc115aa0aee3ef679`）  
**tip：** `4e82871`（全文 `4e82871fd8c29150450f9d2cd916a98d964044f2`）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A Stats API window 24h\|7d\|30d | ✅ | `GET /api/webhooks/stats` + `/{id}/stats`；默认 7d；非法 400；跨租户 404；Q1a/Q5a |
| A successRate 分母含 pending_retry | ✅ | Q2a；`latency_ms` 列已有 → p50/p95 一并输出 |
| B Dead-letter 列表仅 dead | ✅ | `GET /api/webhooks/dead-letter`；webhook/event 过滤；cursor |
| B 单条/批量 retry | ✅ | 复用 E44 `retry_delivery`；bulk cap 50；超 cap 400；Q3a |
| B 无 dismiss | ✅ | Q4a |
| C FE 顶栏 + 死信箱 + vitest | ✅ | `settings/webhooks` 时间窗卡 + 死信抽屉；保留 E44/E51 详情 |
| D CLI 1.38.0 | ✅ | `webhook stats` / `dead-letter list\|retry`；Q6a；pins 全 1.38.0 |
| E 安全 / no-emit / 不扩 pack | ✅ | Owner 写 bulk；reader 读；WEBHOOK_EVENTS 仍 14；formula/read no-emit spy；不改 E52/E53 |

## ADR 确认
- D1 Epic=Webhook 投递可观测 mid-thick · D2 扫既有 DeliveryLog · D3 死信箱=WS 级 dead + E44 replay · D4 FE=`settings/webhooks` · D5 CLI **1.38.0** · D6 no-emit / 不 push / 不自开 E55

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1117 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E54+E44+E51+webhooks+unit stats **31P** |
| CLI | **530 passed**, 89 skipped；`test_e54_webhook_observability` **5P**；pins 全 **1.38.0**（VERSION / `__init__` / `opentask_cli` / setup / pyproject + 历史断言） |
| FE | vitest **338 passed**（46 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- dismiss/归档；告警引擎；邮件/Slack 失败日报；Grafana
- 扩 E51 pack；改 HMAC；Redis/Celery/cron
- Activity Push；SLA policy 日历；Formula emit；push/PR/E55

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E55**

# E57 Acceptance：Webhook 死信告警 mid-thick · CLI 1.41.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E57-S1`  
基线：`5752cb4`（全文 `5752cb442a0054ad46baa1cc0f0cf1bb735de812`）  
**tip：** `d9a4afc`（全文 `d9a4afced34c42f1ff89d311c6ef41d99033a984`）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 告警设置 JSON + 覆盖 | ✅ | Q1a WS+hook field-level overlay；Q2a enabled=false opt-in；Q3a window dead + optional consecutive |
| B 评估/投递/去重/autoDisable | ✅ | Q4a post-dead sync-eval + `POST /run-alert-eval`；Q5a WS owners；Q6a windowHours bucket ledger；autoDisable + `paused_reason` |
| C alembic + pref | ✅ | `p2e3f4a5b6c0`：WS/hook JSON + `paused_reason` + `webhook_alert_deliveries`；pref `webhook_delivery_alert` |
| D FE 折叠+停用标签 | ✅ | settings/webhooks 死信告警折叠；per-hook overlay；「已自动停用」+ 一键启用；vitest merge/mute |
| E CLI 1.41.0 | ✅ | `webhook alerts show\|set\|mute\|unmute`；`webhook run-alert-eval`；pins 全 1.41.0；保留 dead-letter/stats |
| F 安全/no-emit | ✅ | owner write / member+ read；alert 路径不 `fire_webhooks`；不改 E51/HMAC/E55/E56；formula no-emit |

## ADR 确认
- D1–D7 见 design；开放问题 **Q1a–Q6a** 全关（未重开）

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1144 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`）；E57+prefs 定向 25P |
| CLI | **542 passed / 89 skipped**；version pins **1.41.0** |
| FE | **vitest 347 passed**（46 files）；**build OK** |

## Gaps / 非目标（未做）
- Activity Push / 国家日历包 / Insights 再厚 / PagerDuty / Slack on-call
- Formula emit；改 E51 pack / HMAC；改 E55 Insights / E56 SLA 主表面
- **无 push / 无 PR / 不自开 E58**

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**

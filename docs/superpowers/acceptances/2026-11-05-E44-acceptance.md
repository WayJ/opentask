# E44 Acceptance：Webhook event pack + delivery reliability v1

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E44-S1`  
基线：`2984a54`  
tip：`fbb1514`

## 范围（已交付）
- **A** `WEBHOOK_EVENTS` += `issue.assignee_changed` / `issue.label_added` / `issue.label_removed`；`update_issue` 指派双发 updated+专用；TagService 加/删/replace 只发专用 label 事件（不发假 updated）
- **B** Alembic `k7f8a9b0c1d5` 扩 `webhook_delivery_logs`：`delivery_id` / `payload_json` / `status` / `next_attempt_at` / `max_attempts`；一逻辑投递一行；失败存 payload；成功可清空；backoff `[1,5,25,120]`；`WEBHOOK_DELIVERY_MAX_ATTEMPTS=5`
- **C** `POST /api/webhooks/run-due-deliveries`（member+）；`POST …/deliveries/{id}/retry`（owner；无 payload → 400 `delivery_not_replayable`；跨 WS 404）；GET serialize 含 status/nextAttemptAt/deliveryId/replayable；tick cap 100
- **D** FE 事件多选 +3（经办人变更/添加标签/移除标签）；投递抽屉：状态列、失败/死信筛选、重试按钮、dead 高亮；vitest
- **E** CLI **1.28.0**：`webhook deliveries|retry|run-due`；EVENTS +3；全仓 version 断言同步
- **F** 模型/写路径/门禁齐套

## ADR（落地）
- D1 方案 A：event pack + delivery reliability  
- D2/D3 专用 `issue.*`；指派双发；标签只发专用  
- D4 失败才持久化 payload；成功可清空  
- D5 同步短重试保留；其后 pending_retry + 外部 run-due  
- D6 max attempts **5**；超限 dead  
- D7 replay=owner；run-due=member+  
- D8 CLI **1.28.0**  
- D9 不 push；不自开 E45；formula 永不 emit

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1013 passed**, 1 failed（已知 flake `test_user_search` / `TestMetadata::test_user_search`）, 24 skipped |
| BE 定向 | E44+E29+E41+E42：**37 passed** |
| CLI | **496 passed**, 89 skipped |
| FE vitest | **295 passed**（44 files） |
| FE build | **ok**（vite prod） |
| E44 专测 | BE `test_e44_webhook_events_delivery` 9P；CLI `test_e44_*` 4P |

## Gaps / 非目标（刻意不做）
- Redis / Celery / 进程内 cron；HMAC 改版；入站 webhook
- `issue.cycle_changed` / `estimate_changed` 专用事件；SLA v2；Formula range；全局 feed
- push / PR / E45

## superpowers
`design/plan/TDD/verify/acceptance = ok`

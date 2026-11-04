# E41 Acceptance：Issue audit & outbound signals

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E41-S1`  
基线 design：`bf86c23`  
tip：_(见本 commit)_  
状态：**PASS（本地齐套；未 push）**

## 交付 A–D

| 面 | 内容 |
|----|------|
| A | `TimelineAction` +4（`custom_field_changed`/`cycle_changed`/`estimate_changed`/`project_changed`）；Alembic `h4c5d6e7f8a2`；CF upsert 同事务按 `changes[]` 写 timeline；`update_issue` 写 cycle/estimate/project；formula 不写 |
| B | `GET /api/issues/{id}/timeline/export.csv` + `GET /api/issues/timeline/export.csv`；列 schema 见 design；默认 limit 5000、硬顶 10000；截断头 `X-OpenTask-Truncated: true`；跨租户 404 |
| C | FE `formatTimelineAction` 四类中文文案；详情「导出 CSV」；webhook 多选含 `issue.custom_field_changed`（label：自定义字段变更） |
| D | CLI **1.25.0**：`issue timeline` / `timeline-export` / `timeline-export-workspace`；`WEBHOOK_EVENTS`/`EVENTS` += `issue.custom_field_changed`；emit 每字段一条 `fire_webhooks`；全仓 version 断言同步 |

## ADR（落地）
- D1 方案 A：Activity 加厚 + export + CF webhook
- D2 四类 timeline actions
- D3 PG enum ADD VALUE + Python/FE 同步
- D4 CF timeline/webhook 基于 E36 `changes[]`；每字段一条
- D5 事件名 `issue.custom_field_changed`
- D6 formula 不写 timeline、不发 webhook
- D7 单 Issue + WS CSV；硬顶 10000；`X-OpenTask-Truncated`
- D8 timeline 与 status 等 **同事务**
- D9 CLI 1.25.0
- D10 非目标见 design §7；不 push；不自开 E42

## 门禁

| 面 | 结果 |
|----|------|
| BE 定向 `test_e41_issue_audit_outbound.py` | **8 passed** |
| BE 全量 | **977 passed** / 24 skipped / **1 failed**（已知 flake `test_tasks_jira_wire::TestMetadata::test_user_search`；与 E41 无关；单跑复测 **PASSED**） |
| CLI 全量 | **484 passed** / 89 skipped |
| FE vitest | **285 passed**（43 files） |
| FE build | **ok**（vite prod） |

## 约束确认
- 未 push / 未开 PR / 未自开 E42 · STOP 待命

`superpowers: design/plan/TDD/verify/acceptance = ok`

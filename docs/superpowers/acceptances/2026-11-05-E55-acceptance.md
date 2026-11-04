# E55 Acceptance：Insights 效能加厚 mid-thick · CLI 1.39.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E55-S1`  
基线：`6e2c8d3`（全文 `6e2c8d34c18b02d527babf9f872878831571351b`）  
**tip：** `4f68688`（全文 `4f686887dcb40cdb0daddc20a507390f065c7bce`）— 收口后再钉最终 tip

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A Summary 切片 projectId/labelId/cycle | ✅ | Q1a `labelId`→Tag；Q5a 单 label；Q2a 收窄 cycleSnapshot；跨租户/未知 404；无过滤 ≡ E24 |
| B estimateVelocity 14d | ✅ | Q3a；Σ coalesce(estimate_points,0) by `coalesce(closed_at, resolved_at)` 日桶 |
| C export.csv | ✅ | Q4a `GET /api/insights/export.csv`；扁平行 status/priority/assignee/estimate_velocity；同过滤对账 |
| D FE 过滤+速度+导出+vitest | ✅ | `/insights` Project/Label/Cycle + 速度卡 + 导出 CSV；vitest normalize/empty velocity |
| E CLI 1.39.0 | ✅ | `insights summary` 筛 + `insights export` stdout/-o（Q6a）；pins 全 1.39.0 |
| F 安全 / no-emit / 不改 E52–E54 | ✅ | viewer+；读路径 spy 无 fire_webhooks；无新 webhook 事件；不改 Activity/SLA/webhook 主表面 |

## ADR 确认
- D1 Epic=Insights 效能加厚 mid-thick · D2 挂既有 summary · D3 估点速度 14d 日桶 · D4 CSV 只读端点 · D5 FE=`/insights` · D6 CLI **1.39.0** · D7 no-emit / 不 push / 不自开 E56

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1124 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E55+E24 insights **13P** |
| CLI | **533 passed**, 89 skipped；`test_e55_insights_thicken` **3P**；pins 全 **1.39.0**（VERSION / `__init__` / `opentask_cli` / setup / pyproject + 历史断言） |
| FE | vitest **341 passed**（46 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- 报表构建器 / 多 label AND-OR / Slack-email digest
- Activity Push；SLA policy 日历；Webhook 死信告警
- Formula emit；push/PR/E56

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E56**

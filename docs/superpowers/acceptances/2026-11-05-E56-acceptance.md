# E56 Acceptance：SLA policy 日历覆盖 thin · CLI 1.40.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E56-S1`  
基线：`137f734`（全文 `137f7346730fefe110fa38014f5d5b85d42e7400`）  
**tip：** `31f61be`（全文 `31f61beff15cf83486f89da73f54e54ee6223f4e`）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 覆盖模型 calendar JSON | ✅ | Q1a 可选字段继承；Q2a WS 总闸关闭→墙钟；exceptions=E53 / windows=E50；非法/重复 date→400；跨租户 404 |
| B 时钟路径 effective calendar | ✅ | create/pause/resume/recompute/run-due 透传 policy；Q3a WS 变更全量重算；policy 日历变更仅本 policy；cap 500；disabled 跳过对齐 E42 |
| C alembic calendar 列 | ✅ | Q4a `sla_policies.calendar` JSON nullable（rev `o1d2e3f4a5b9`）；null≡全继承；SQLite/PG 友好 |
| D FE 日历覆盖+清除+vitest | ✅ | settings/sla 折叠「日历覆盖」；空=继承；「清除覆盖」；vitest merge/empty≡WS |
| E CLI 1.40.0 | ✅ | `--calendar-json` / `--clear-calendar`；show 含 `calendar`+`effectiveCalendar`（Q5a/Q6a）；pins 全 1.40.0 |
| F 安全 / no-emit / 不改 E52/E54/E55 | ✅ | owner 写；spy 无额外 fire_webhooks/automations；无新 webhook 事件；不改 Activity/webhook/Insights 主表面 |

## ADR 确认
- D1 Epic=SLA policy 日历覆盖 thin · D2 `SlaPolicy.calendar` JSON · D3 effective calendar 时钟 · D4 policy 变更重算本 policy / WS 见 Q3a · D5 FE=既有 SLA 表单 · D6 CLI **1.40.0** · D7 no-emit / 不 push / 不自开 E57

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1135 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E56+E53+E50+E48/E45 **45P** |
| CLI | **536 passed**, 89 skipped；`test_e56_sla_policy_calendar` **3P**；pins 全 **1.40.0**（VERSION / `__init__` / `opentask_cli` / setup / pyproject + 历史断言） |
| FE | vitest **343 passed**（46 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- 国家日历包 / 冲突矩阵 / Activity Push / 死信告警 / Insights 再厚
- Formula emit；push/PR/E57
- FE 不做月历拖拽 / ICS / 冲突可视化（设计非目标）

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E57**

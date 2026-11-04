# E53 Acceptance：SLA 节假日/例外日 thin · CLI 1.37.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E53-S1`  
基线：`5fbb63e`（全文 `5fbb63e2469794c161027134729765a704087528`）  
**tip：** （全文 ）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 例外模型 closed\|forced_open | ✅ | `{date, kind, windows?}`；非法 date/kind/重复 → 400；Q1a |
| B forced_open 默认窗 Q2a | ✅ | Mon 窗非空取其副本；否则 09:00–18:00 |
| C Workspace 级 / 无 policy 覆盖 | ✅ | Q3a/Q4a；挂 `business_hours` |
| D JSON exceptions cap 366 | ✅ | Q5a；无新表 / 无 migration |
| E 加法器 + enabled=false 惰性 | ✅ | `resolve_day_segments` → add/elapsed；enabled=false 墙钟 |
| F pause/resume/first_response/重算 | ✅ | compute_* 透传 exceptions；配置变更 cap 500 |
| G FE 薄例外列表 + vitest | ✅ | normalizeExceptions / closed skip；settings/sla CRUD + 空态 |
| H CLI 1.37.0 exceptions | ✅ | `sla business-hours exceptions list\|add\|remove`；show 含 exceptions；Q6a |
| I 安全 / no-emit / 不扩 E51/E52 | ✅ | 跨租户 404；配置写无额外 webhook/automation；不改 Activity/webhook pack |

## ADR 确认
- D1 Epic=SLA 节假日/例外日 thin · D2 挂既有营业分钟加法器 · D3 WS 级无 policy 覆盖 · D4 closed/forced_open · D5 JSON `exceptions` · D6 CLI **1.37.0** · D7 no-emit / 不 push / 不自开 E54

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1106 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E53+E50 **32P**；E48+E45+E42 **36P** |
| CLI | **525 passed**, 89 skipped；`test_e53_sla_exceptions` **4P**；pins 全 **1.37.0**（VERSION / `__init__` / `opentask_cli` / setup / pyproject + 历史断言） |
| FE | vitest **333 passed**（46 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- 国家日历包自动导入；policy 级例外覆盖 / 优先级矩阵；ICS/Outlook 同步
- Activity Push / FCM / 实时 WS；Webhook 成功率仪表 / 死信箱；Formula emit
- 重做 E51 webhook pack / E52 Activity；完整月历拖拽；push/PR/E54
- 进程内 cron / Redis

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E54**

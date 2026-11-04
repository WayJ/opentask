# E51 Acceptance：专用 webhook pack + 订阅事件过滤 FE · CLI 1.35.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E51-S1`  
基线：`38bd9c6`  
**tip：** `dd0d98a`（全文 `dd0d98ac29f54f7f7fe057475e94ae83a33a9f57`）— 收口 commit 后以 HEAD 为准

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A WEBHOOK_EVENTS +5 | ✅ | `cycle_changed` / `estimate_changed` / `project_changed` / `sla_paused` / `sla_resumed`（Q1a） |
| B 写路径 fire + 并存 updated | ✅ | `issue_service` cycle/estimate/project；`SlaService` pause/resume；Q2a 不替代 `issue.updated` |
| C 未订阅不投 | ✅ | dispatch 按 `events_json`；非法事件名 400 |
| D FE 勾选/标签/预设/投递过滤 | ✅ | 「集成常用」+清除（Q3a）；投递日志按 `eventType` 过滤；vitest |
| E CLI 1.35.0 + `webhook events` | ✅ | pyproject+`__init__`+setup+`VERSION`+`opentask_cli.VERSION` 全钉；Q6a |
| F no-emit / 无回放 / 无 Activity | ✅ | Q5a；钩子 CRUD 无业务 emit；E48 回归改为「有 webhook、无 automation」 |

## ADR 确认
- D1 Epic=专用 webhook pack + 订阅过滤 FE · D2 并存 updated · D3 事件名对齐 timeline · D4 FE 薄预设+过滤 · D5 HMAC/重试沿用无回放 · D6 CLI **1.35.0** · D7 no-emit / 不 push / 不自开 E52

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1082 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E51+E44+E48+E41 **32P** |
| CLI | **518 passed**, 89 skipped；`test_e51_webhook_pack` **5P**；pins 全 **1.35.0** |
| FE | vitest **326 passed**（46 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- 节假日/policy 覆盖；Activity 加厚；Formula emit；历史回放；订阅中心/多渠道路由；Redis/cron；push/PR/E52
- pause/resume **仍不** fire automation（仅 webhook）
- FE 投递事件过滤为单选下拉（薄）；无按钩子成功率仪表

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E52**

# E50 Acceptance：SLA business hours thin · CLI 1.34.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E50-S1`  
基线：`a77e2cf`  
**tip：** _(本 commit 后补 SHA)_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 纯函数 | ✅ | `add_business_minutes` / `elapsed_business_minutes`；normalize windows（≤2/日、倒置拒、重叠合并）；IANA `validate_timezone`；unit 10P |
| B 存储/API | ✅ | alembic `m9b0c1d2e3f7`：`workspaces.timezone` + `business_hours` JSON；PATCH 校验；无 policy 覆盖（Q2a） |
| C SLA 接线 | ✅ | create/pause/resume 走营业分钟加法器；enabled=false 墙钟回退；`recompute_deadlines_for_workspace`（cap 500） |
| D pause 语义 | ✅ | Q4a elapsed=营业分钟 when enabled；paused 不 tick；resume 重算 |
| E first_response | ✅ | 共用加法器；breach payload 含 `metric` |
| F FE | ✅ | SLA 设置页营业时段卡片 + timezone/预设/周历；vitest `businessHours` |
| G CLI 1.34.0 | ✅ | pyproject + `__init__` + setup + `VERSION` + `opentask_cli.VERSION` 全钉；`workspace update` / `sla business-hours show\|set`；历史断言同步 |
| H no-emit | ✅ | 配置写路径 spy：`fire_webhooks` / `fire_automations` 未调用 |

## ADR 确认
- D1 Epic=business hours thin · D2 加法器唯一 deadline 源 · D3 默认关→墙钟 · D4 pause 不计 · D5 WS 级无 policy 覆盖 · D6 Alembic+重算+≤2段 · D7 CLI **1.34.0** · D8 no-emit / 不 push / 不自开 E51

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1075 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E50+E48+E45 **38P**（unit E50 **10P** + api E50 **8P**） |
| CLI | **513 passed**, 89 skipped；`test_e50_sla_business_hours` **4P**；pins 全 **1.34.0** |
| FE | vitest **321 passed**（46 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- 节假日/例外日/国家日历包；策略优先级矩阵 / policy 级覆盖；专用 cycle/estimate/project/sla_paused webhook；Activity 加厚；Formula emit；Redis/cron；push/PR/E51
- FE 周历编辑为逗号分隔薄输入（非可视化时间轴）；DST 覆盖依赖 zoneinfo，单测以 Asia/Shanghai 钉样例
- 配置变更重算以「当前 now + 剩余」重写 paused/running deadline（paused 预览若立即 resume 的 deadline）

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E51**

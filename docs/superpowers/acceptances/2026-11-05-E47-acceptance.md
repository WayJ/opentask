# E47 Acceptance：WS Activity Feed v1 — JSON 游标 · 薄 FE · CLI 1.31.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E47-S1`  
基线：`5ab2400`  
**tip：** _(收口填写)_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A JSON Activity API | ⏳ | `GET /api/issues/activity`；cursor；clamp 200；过滤 |
| B FE `/activity` + Dashboard 链 | ⏳ | 顶栏；过滤；加载更多；RecentActivity 语义不变 |
| C CLI 1.31.0 | ⏳ | `activity list`；四文件版本钉 |
| D 无 migration | ⏳ | ADR D7 |
| E no-emit spy | ⏳ | 读路径无 webhook/automation/timeline append |

## ADR 确认
- D1 Feed v1 · D2 只读 timeline · D3 cursor + clamp · D4 path · D5 薄 FE · D6 CLI 1.31.0 · D7 无 migration · D8 no-emit · D9 非目标

## 门禁
| 面 | 结果 |
|----|------|
| BE | _(待填)_ |
| CLI | _(待填)_ |
| FE | _(待填)_ |

## Gaps / 非目标（未做）
- SLA 日历 / first-response / pause timeline；cycle/estimate 专用 webhook；Linear Updates；formula emit；Redis/cron；**无 push / 无 PR / 不自开 E48**

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`（收口勾）
- **STOP**

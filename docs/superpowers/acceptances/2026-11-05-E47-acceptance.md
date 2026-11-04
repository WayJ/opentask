# E47 Acceptance：WS Activity Feed v1 — JSON 游标 · 薄 FE · CLI 1.31.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E47-S1`  
基线：`5ab2400`  
**tip：** （全文 ；若滞后以 HEAD 为准）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A JSON Activity API | ✅ | `GET /api/issues/activity`；since/until/actionType/actorId/issueId/cursor/limit；默认 50 / **clamp 200**；`items`+`nextCursor`；共享 `query_timeline_entries` 与 E41 CSV |
| B FE `/activity` + Dashboard 链 | ✅ | 顶栏 ActivityNav；过滤（actionType / 24h·7d / actor）；加载更多；行跳 Issue；Dashboard「查看全部活动」→`/activity`；**RecentActivity 语义不变**；vitest `activityFeed` |
| C CLI 1.31.0 | ✅ | 顶级 `activity list`；pyproject + `__init__` + setup + `VERSION` 全钉 **1.31.0**；历史 version 断言同步；保留 `issue timeline` / `timeline-export` |
| D 无 migration | ✅ | 无 alembic / 无新表 / 无索引 migration（ADR D7 / Q6a） |
| E no-emit spy | ✅ | 读路径 spy：`fire_webhooks` / `fire_automations` 未调用 |

## ADR 确认
- D1 Feed v1 · D2 只读 `issue_timeline` · D3 cursor `(created_at,id)` + clamp · D4 path Q1a · D5 薄 FE Q3a/Q4a · D6 CLI **1.31.0** · D7 无 migration · D8 no-emit · D9 非目标 / 不 push / 不自开 E48

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1045 passed**, 24 skipped；1 fail `test_user_search` = **已知 flake**，solo 复跑绿；E47 `test_e47_*` **9P**；E41 定向 **8P** |
| CLI | **503 passed**, 89 skipped；`test_e47_activity` **2P** |
| FE | vitest **307 passed**（45 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- SLA 营业日历 / first-response / pause timeline；cycle/estimate 专用 webhook；Linear Updates（反应/订阅/推送）；formula emit；Redis/cron；**无 push / 无 PR / 不自开 E48**

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**

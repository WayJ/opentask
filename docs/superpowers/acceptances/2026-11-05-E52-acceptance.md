# E52 Acceptance：Activity Feed 加厚 v2 · CLI 1.36.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E52-S1`  
基线：`abb96db`  
**tip：** `1896ed0`（全文 `1896ed0becd27ed8a822cb4089cccac1ab6c86b5`）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A watching 过滤 | ✅ | `GET /api/issues/activity?watching=true` 对齐 E19；join `issue_watchers`（Q1a） |
| B 空 watcher / 跨租户 | ✅ | 无 watch → `items=[]`；他 WS 不泄漏 |
| C 反应摘要 + FE chips | ✅ | Q2a issue 为主；`payload.comment_id` → comment；复用 E27；无 entry 反应表；评论写路径 flush 以填 comment_id |
| D unread-count + mark-read + 铃铛 | ✅ | Q3a `activity_read_cursors`；`GET unread-count` / `POST mark-read`；ActivityNav 角标；Q4a 默认全量；铃铛 `?watching=1`；Q5a 无 Push |
| E FE 仅关注开关 + vitest/build | ✅ | 空态区分；query 序列化 vitest |
| F CLI 1.36.0 + `--watching` + `unread` | ✅ | 五处钉版 + 历史断言；Q6a |
| G 读路径 no-emit / formula | ✅ | list/unread/mark-read spy；不扩 E51 pack |

## ADR 确认
- D1 Epic=Activity Feed 加厚 v2 · D2 watching←issue_watchers · D3 复用 E27 反应 · D4 薄铃铛非 Push · D5 小 migration · D6 CLI **1.36.0** · D7 no-emit / 不 push / 不自开 E53

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1092 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E52+E47+watchers+reactions **30P** |
| CLI | **521 passed**, 89 skipped；`test_e52_activity_thicken` **3P**；pins 全 **1.36.0** |
| FE | vitest **330 passed**（46 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- 节假日；webhook 仪表；Formula emit；Push/FCM/实时 WS；富媒体；entry 反应表；push/PR/E53
- 浏览器 Notification；进程内 cron / Redis

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E53**

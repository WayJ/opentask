# E19 Acceptance：Home / My Issues · Due→Inbox · Watchers

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E19-S1`  
基线：`46d562b`

## ADR
Due soon = **Home/list 查询**（`due_soon=true`：今日起 3 日内且未关闭）；**不**造 cron Inbox。  
事件型 Inbox 仅覆盖 **due_date 被改**（type=`due_date_changed`）。

## 交付
| 项 | 状态 |
|----|------|
| A Home 四区 + list `scope` 深链 | ✅ |
| A API `me` / watching / due_before / due_soon | ✅ |
| B due_date → timeline + Inbox（assignee+watchers，跳过 actor） | ✅ |
| C 详情 Watchers 列表 + 取消自己；API username/name | ✅ |
| D CLI `--mine/--watching/--due-soon` · v1.4.0 | ✅ |
| design/plan/acceptance | ✅ |
| **不 push** | ✅ |

## 测试
- BE `tests/api/test_e19_home_filters_due.py`：5 passed（整包全量另记）
- CLI `tests/test_e19_issue_list_filters.py`：2 passed

## Gaps
- Due soon 不主动 Inbox 提醒（ADR）
- Watchers 不支持管理他人
- Issue list 仍先拉多页再前端 tab 滤；scope 滤参已下推 API

## Tip
`sprint/E19-S1` @ `45279ab`

- BE pytest: **837 passed**, 24 skipped
- CLI pytest: **416 passed**, 89 skipped
- FE vitest (router): **8 passed**
- **未 push**；STOP，不自开 E20

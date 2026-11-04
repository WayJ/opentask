# E27 Acceptance：Notification preferences + 评论 Reactions

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E27-S1`  
基线：`9bf8464`

## 状态
✅ 本地齐套（未 push）

## tip
`b2206fb` (`b2206fbac7e5342658b110ddbc8a8ebda6041c63`)

## 测试数
- BE pytest：883 passed / 1 flake（`test_user_search` 隔离复跑确认）/ 24 skipped；本 Epic `tests/api/test_notif_prefs_reactions.py` **7P**
- CLI pytest：436 passed / 89 skipped（含 E27 3P）；version **1.11.0**
- FE vitest：240 passed（+2 notif-prefs helpers）；`npm run build` 成功

## 范围核对
- [x] A 通知偏好 GET/PUT + Inbox create 尊重偏好 + 跨用户/跨租户
- [x] B FE `/settings/notifications` 开关即时保存
- [x] C 评论 Reactions API + 详情评论区；Issue 级不重做
- [x] D CLI `notif prefs get|set`；**1.11.0**
- [x] 未 push / 未开 PR / 未自开 E28

## ADR 摘要
- D1：偏好键 ↔ Inbox type 映射（含 automation_comment）
- D2：无行=全开懒默认；GET 不建行；PUT upsert
- D3：未知 type fail-open
- D4：system/automation 评论 → automation_comment；mention 仍 mentioned
- D5：独立表 comment_reactions
- D6：评论列表附带 reactions；另有独立 CRUD
- D7：FE `/settings/notifications`；评论区复用 IssueReactions
- D8：CLI `notif prefs`；1.11.0
- D9：非目标 + 不 push + 不自开 E28

## 缺口
- 邮件/Slack 外发、digest、字段级偏好：明确非目标
- `test_user_search` 偶发失败与 E27 无关（既往 Epic 同款 flake）

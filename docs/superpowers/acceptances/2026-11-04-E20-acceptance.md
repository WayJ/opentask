# E20 Acceptance

状态：齐套  
分支：`sprint/E20-S1`  
基线：`f78d5ff`

## Checklist
- [x] A Bulk：X 选中、Esc 清空、底栏五项（status/assignee/priority/cycle/labels）、跨租户 403
- [x] B Relations：列表/看板 `blocks_count`/`blocked_by_count` 徽章 + 详情 CRUD
- [x] C Mentions/IssueReference vitest 绿（无 skip）；Markdown `@user` / `KEY-N` 链接
- [x] D CLI 1.5.0 `issue bulk-update`
- [x] BE pytest 全绿；CLI 绿；相关 vitest 绿
- [x] **未 push**

## Tip / 测试数
- tip：收口 commit 后填写
- BE：`843 passed, 24 skipped`
- CLI：`418 passed, 89 skipped`
- FE（相关）：selection/hotkeys/mentions/issue index — 33 passed / 10 skipped（SmartSearch/Template/Reactions 仍 skip）

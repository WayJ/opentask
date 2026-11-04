# E21 Acceptance

状态：齐套  
分支：sprint/E21-S1  
基线：db9c87b  
tip：46b0dbad43a5ee549dbc99d03f029e6fb0d67c9d

## Checklist
- [x] A SmartSearch → list API/filters（assignee:@me / is: / label: / priority: / type: / cycle: / project: / KEY-N）；URL `q` 深链；清空恢复；无 skip
- [x] B Templates：WS API 优先 + 静态 ISSUE_TEMPLATES fallback；Alt+C → pickTemplate；无 skip
- [x] C Reactions Issue 级接既有 `/reactions`；无 skip；评论反应 ADR 不做
- [x] D 选中序 `setIssueOrder/getIssueOrder`；无 window `__opentaskIssueOrder`；list+board
- [x] E CLI **1.6.0** `issue list --cycle`
- [x] BE/CLI/相关 vitest 绿；未 push

## 测试数
- BE：843 passed, 24 skipped
- CLI：420 passed, 89 skipped
- FE：229 passed（全量；三类 skip 已去掉）

## ADR 摘要
D1–D10 见 design；label 客户端过滤；Reactions 仅 Issue 级；CLI 加 `--cycle`。

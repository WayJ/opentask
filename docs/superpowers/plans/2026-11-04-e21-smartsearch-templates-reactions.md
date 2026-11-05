# E21 Plan：SmartSearch · Templates · Reactions · Order · CLI

日期：2026-11-04  
基线 tip：`db9c87b` · 分支 `sprint/E21-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** SmartSearch 真正驱动 Issue 列表；模板/Reactions 测绿；选中序正规化；CLI 1.6.0。

**Architecture:** 强化 `issueSearchParser` → list filters/API；URL `q` 深链；selection composable 持有 order；Reactions/Templates 修测与薄打磨。

**Tech Stack:** Vue3 + Naive + vitest；FastAPI（不改契约除非必要）；Click CLI。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E22；中文 docs；DESIGN/主题令牌不动。

---

### Task 1 — Docs
- [ ] design + plan（本文件）入库
- [ ] acceptance 骨架；收口补 tip/测试数

### Task 2 — Parser + 单测（TDD）
- [ ] 扩展 `parseSearchString`：`assignee:@me`/`me`、`cycle:`、KEY-N、`label:` 累积
- [ ] 导出 `parsedQueryToFilters`（可选）映射到 list 形状
- [ ] vitest：覆盖上述语法

### Task 3 — List 接线 + URL 深链
- [ ] `handleSmartSearch`：写 `filters.assignee_id/status/type/priority/project_id/cycle_id/search/labels`；**勿**把 assignee 拼进 search
- [ ] `loadIssues` 传 `status`（及既有字段）
- [ ] 客户端 `label:` 过滤；同步 `route.query.q`；mount 读 `q` 应用；`clearFilters` 清 scope 外的 smart 态

### Task 4 — 选中序 composable
- [ ] `setIssueOrder`/`getIssueOrder`/`reset`；热键改用；list+board 注册；删 `__opentaskIssueOrder`
- [ ] 单测

### Task 5 — Templates 打磨 + 测
- [ ] Alt+C → create?pickTemplate=1（hotkeys + resolveIssueHotkeyAction）
- [ ] 复活 TemplateSelector vitest（mock NSpin/NGrid + fetch）

### Task 6 — Reactions 测
- [ ] 复活 IssueReactions vitest；确认详情已接 API（ADR D8）

### Task 7 — SmartSearch 组件测
- [ ] 去掉 skip；固定 pinia 变量；mock 齐全；断言 emit search

### Task 8 — CLI 1.6.0
- [ ] `--cycle` → `cycle_id`；version bump；测 + README 一行

### Task 9 — 门禁
- [ ] BE pytest；CLI pytest；FE 相关 vitest；acceptance tip；回执；STOP

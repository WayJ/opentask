# E24 设计：Insights（Linear 式只读效能，lite）

日期：2026-11-04（Asia/Shanghai）  
Epic：E24  
基线：`sprint/E23-S1` @ `89242cf`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E24-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E25**。

## 1. 目标

提供 Workspace 级只读效能摘要，对齐 Linear Insights 的 lite 子集：状态/优先级/负责人负荷、当前 Cycle 快照、近 14 日创建 vs 完成。

### A · API（只读聚合）
`GET /api/insights/summary`（强制 `X-Workspace-Id`；viewer+）：
- **statusCounts**：本 WS 未删除 Issue 按 status
- **priorityCounts**：按 priority
- **assigneeCounts**：开放 Issue 按 assignee（含 unassigned）；`assigneeLimit` 默认 10（top N + unassigned 始终保留）
- **cycleSnapshot**（query `cycleId` 可选；默认当前 active cycle）：issue 总数、completed 数、`estimatePointsSum`（无则 0）
- **createdVsCompleted**：近 14 日每日 created / completed 计数（按日 bucket）

跨租户负例；SQL `GROUP BY` / `SUM` / `COUNT` 聚合，禁止 N+1 拉全表。

### B · 前端 `/insights`
- 侧栏 Workspace 区「Insights」入口
- 卡片 + Naive Progress/表格：状态、优先级、负责人、近 14 日创建 vs 完成
- Cycle 下拉切换 snapshot；空状态；loading；viewer 可见
- **不新引**重型 BI 库（echarts 已存在但本期不用，避免复杂依赖）

### C · Home
- Home 嵌一行「本周完成 / 开放数」链到 Insights（薄）

### D · CLI
- `opentask insights summary [--cycle ID]`；version **1.8.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | **新建** `/api/insights` 只读面；**不复用**既有 `models/datainsight`（会话/执行引擎遗留，非 Linear Insights） |
| D2 | `DONE_STATUSES = {resolved, closed}`（与 Cycle capacity 一致）；「开放」= 未删除且 status ∉ DONE |
| D3 | completed 日桶：`func.date(coalesce(closed_at, resolved_at))`；仅统计时间戳落在窗口内的完成事件 |
| D4 | 默认 Cycle = 本 WS 唯一/首个 `status=active`；无 active → `cycleSnapshot=null`；显式 `cycleId` 跨租户 → 404 |
| D5 | `assigneeCounts`：按 count DESC；`unassigned`（assignee_id IS NULL）始终单独计入结果；具名 assignee 取 top N；附带 `assigneeName`（User.name/username） |
| D6 | 响应 camelCase：`statusCounts` / `priorityCounts` / `assigneeCounts` / `cycleSnapshot` / `createdVsCompleted` |
| D7 | Home 做薄条「本周完成 / 开放」；本周完成 = createdVsCompleted 近 7 日 completed 之和（或单独从 summary 再算）；开放 = statusCounts 中非 DONE 之和 |
| D8 | FE 用 Naive Progress + 表格，**不**新引 BI；路由 `layout.base$view.insights` |
| D9 | CLI **1.8.0** + `insights summary [--cycle]` |
| D10 | 不做自定义报表/CSV/Slack/自定义字段/自动化/Redis WS/远程 push；不自开 E25 |

## 3. 非目标

自定义报表构建器、导出 CSV 大屏、Slack、自定义字段、自动化、Redis 多进程 WS、远程 push、E25。

## 4. 验收摘要

- summary 聚合正确 + 缺头/非成员/跨租户负例
- `/insights` 可看；侧栏入口；Cycle 切换；Home 薄链
- CLI 1.8.0 `insights summary`
- BE/CLI pytest 绿；FE 相关测/构建不恶化；本地 tip；**不 push**

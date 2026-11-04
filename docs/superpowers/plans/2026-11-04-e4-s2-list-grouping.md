# E4-S2 实施计划 — 列表分组泳道

## 目标

Issue 列表（及可选看板旁控件）按属性分组泳道：`none` | `status` | `assignee` | `priority` | `type`。客户端分组；`display_json.group_by` 与 Saved Views 联动。本地 `sprint/E4-S2`，不推远程。

## 实现要点

1. **纯函数** `frontend/src/utils/groupIssuesBy.ts`
   - 输入：issues + GroupByKey
   - 输出：有序 `IssueGroupBucket[]`：`{ key, label, issues }`
   - assignee 空 → key=`__unassigned__`，label=`未分配`
   - status/priority/type 用 constants 文案；未知值回退原值

2. **UI** `IssueListGrouped.vue`
   - Naive `NCollapse` 可折叠；标题 = label + count
   - 每泳道内嵌 `NDataTable`（columns 由父组件传入）
   - DESIGN.md / `--color-*` 令牌；无新色板
   - **展示-only**：无跨泳道拖拽 mutation（看板 status 拖拽保持 IssueBoard 既有行为）

3. **列表页** `index.vue`
   - `groupBy` ref + 工具栏 NSelect
   - `groupBy !== 'none'` → 渲染 IssueListGrouped(filteredIssues)；隐藏分页
   - 保存视图：`display: { view_mode, group_by }`
   - 应用视图：恢复 `group_by`
   - 有 `activeSavedViewId` 时变更分组 → PATCH `display`

4. **后端**：无需新 group_by list API；沿用 S1 display JSON。可选加一条 pytest 断言 display.group_by 往返（若已有 create 覆盖则可复用）。

## 非目标

S3 `parent_issue_id`、⌘K、共享视图、跨泳道改字段、远程 push。

---
epic: E4
status: active
date: 2026-11-04
---

# OpenTask Linear 进阶：Saved Views · 列表分组 · 一等公民子 Issue

产品参考 Linear；在 E3（开放注册 / Workspace / 双视图 / Inbox）之上补齐「个人收藏视图 + Issue 列表按属性泳道分组 + 一等公民父子子 Issue」。本 Epic 为整包一个 Roadmap。⌘K / Cycles / Labels 打磨明确排除。

## Deliverables

| deliverable | note |
|---|---|
| 个人 Saved Views（可收藏/保存筛选与排序） | 新表 `issue_saved_views`；`owner_user_id` 个人作用域；`filter_json` / `sort_json` / 可选 `display_json`；不复用 `IssueCollection` |
| Issue 列表按属性分组泳道 | 按 assignee / priority / type 等属性分组呈现（S2）；对齐 Linear group-by 手感 |
| 一等公民子 Issue | `parent_issue_id` 父子嵌套（S3）；非 `IssueRelation` 语义；列表可嵌套展示 |

## Definition of Done

- [ ] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed，合并证据写入各 sprint 台账
- [ ] `cd backend && uv run pytest tests/ -v` 全绿（含 Saved Views 隔离 / 分组 / 子 Issue 用例）
- [ ] `cd frontend && npm run lint && npm run build` 通过（0 errors）
- [x] Saved Views：用户可保存/列出/应用/收藏/删除个人视图；跨用户不可见
- [x] 列表分组：可按属性泳道呈现且与筛选一致（S2）
- [ ] 子 Issue：可建父子、列表嵌套、父级约束正确（S3）
- [ ] DESIGN.md / Naive UI / soybean 令牌被前端改动遵守；无 ⌘K / 工作区共享视图交付

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | closed | **个人 Saved Views**：模型 + API + Issue 列表工具栏保存/应用/收藏。evidence: `docs/superpowers/sprints/2026-11-04-E4-S1-plan.md` / `docs/superpowers/acceptances/2026-11-04-E4-S1-acceptance.md` |
| S2 | closed | Issue 列表分组泳道（客户端 none/status/assignee/priority/type；display.group_by）。evidence: `docs/superpowers/sprints/2026-11-04-E4-S2-plan.md` / `docs/superpowers/acceptances/2026-11-04-E4-S2-acceptance.md` |
| S3 | active | 一等公民子 Issue：`parent_issue_id` + 嵌套列表；非 IssueRelation。worktree `/workspace/opentask-worktrees/E4-S3`；分支 `sprint/E4-S3`（基 E4-S2 tip `1e79a91`）。 |

推荐顺序理由：Saved Views 先固化筛选/排序配置契约，S2 分组与 S3 嵌套可挂在同一列表呈现层；个人作用域不阻塞后续共享视图另开 Epic。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | Saved Views 归属 = **仅个人**（`owner_user_id`）；MVP 不做工作区共享 | Way 拍板；贴近 Linear Custom Views 个人默认 | 2026-11-04 | 本文档；Yuri 转达 |
| D2 | 新建 `issue_saved_views` 表；**不**复用 `IssueCollection` | Collection 是 issue_id 袋子；Views 是筛选/排序配置 | 2026-11-04 | 设计 spec |
| D3 | `filter_json` 对齐 `ParsedQuery` / `IssueQueryParams`（status/type/priority/project_id/assignee_id/search 等） | 复用现有 Issue 筛选与智能搜索 | 2026-11-04 | schema + 前端 parser |
| D4 | API 前缀 `/api/saved-views`；强制 `X-Workspace-Id` + 成员校验；列表恒过滤 `owner_user_id=current` | 与 E3 租户头一致；防跨用户泄漏 | 2026-11-04 | S1 计划 |
| D5 | S2 groupBy：优先客户端分组或查询参数；可写入 `display_json.group_by` | 不阻塞 S1；呈现层可后补服务端聚合 | 2026-11-04 | 本文档 |
| D6 | S3 用 `parent_issue_id` FK，不用 `IssueRelation` 表达父子 | 一等公民嵌套；Relation 保留阻塞/相关等语义 | 2026-11-04 | 本文档 |
| D7 | 排除 ⌘K、Cycles、Labels 打磨、邮件/IM、工作区共享视图、远程推送 | Way 拍板本批范围 | 2026-11-04 | 指派纪要 |

## Exclusions

- ⌘K / 命令面板
- Cycles
- Labels 打磨
- 邮件 / IM 外发
- 工作区共享 Saved Views（另开 Epic）
- 远程 push / PR（本批仅本地 worktree）
- mission-center 前端复活、计费、SSO 大改、Orca/Jira 变更

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `IssueCollection` | leave | 继续作 issue_id 集合；Saved Views 另表 | 2026-11-04 |
| Issue 列表 `filters` + `IssueSmartSearch` | reuse | 保存/应用视图读写同一套筛选状态 | 2026-11-04 |
| `IssueRelation` | leave | S3 父子不走 Relation | 2026-11-04 |
| Inbox / Workspace 模式 | reuse | API 信封、`require_workspace_context`、pytest 注册样板 | 2026-11-04 |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q1 | Saved Views 是否工作区共享？ | closed | MVP 仅个人（D1） |
| Q2 | 拆法？ | closed | 一 Epic E4，三 Sprint S1→S2→S3 |
| Q3 | S2 groupBy 服务端还是客户端？ | closed | 客户端对 filteredIssues 分桶（E4-S2 D1） |

## Cross-cutting

| concern | owning epic | note |
|---|---|---|
| 个人视图隔离 | E4 | 每个 Saved Views API 用例须含跨用户负例 |
| 租户隔离 | E3/E4 | 强制 X-Workspace-Id + require_member |
| DESIGN.md 视觉令牌 | E4 | Naive / soybean / design-system.css |
| 门禁 | E4 | AGENTS.md；PG `opentask-pg-test` |

## Overall Acceptance Scenarios

| id | scenario | how to verify | expected |
|---|---|---|---|
| R1 | 用户可保存并应用个人视图 | POST saved-view → GET list → 前端应用 filters | 筛选恢复一致 |
| R2 | 跨用户不可见 | 用户 A 创建；用户 B list | 空或不含 A 的 id |
| R3 | 列表分组泳道（S2） | 选择 groupBy=priority | 按优先级分栏 |
| R4 | 子 Issue 嵌套（S3） | 创建 parent+child | 列表可见父子关系 |

```supervibe-acceptance-plan
{
  "schema": 1,
  "scope": "epic",
  "scenarios": [
    {
      "id": "R1",
      "goal": "保存并应用个人 Saved View",
      "steps": ["设置筛选", "POST /api/saved-views", "GET list", "应用 filter_json"],
      "expected": "筛选与排序恢复",
      "required": true,
      "modality": "api",
      "environment": "real"
    },
    {
      "id": "R2",
      "goal": "跨用户隔离",
      "steps": ["A 创建视图", "B GET /api/saved-views"],
      "expected": "B 看不到 A 的视图",
      "required": true,
      "modality": "api",
      "environment": "real"
    },
    {
      "id": "R3",
      "goal": "列表分组泳道（S2）",
      "steps": ["开启 groupBy"],
      "expected": "按属性分栏呈现",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R4",
      "goal": "一等公民子 Issue（S3）",
      "steps": ["创建 parent_issue_id 子项", "列表"],
      "expected": "嵌套可见",
      "required": true,
      "modality": "api",
      "environment": "real"
    }
  ]
}
```

## 进度注记

- 2026-11-04（UTC+8）：E4 启动；Way 拍板个人 Views + 三 Sprint；分支 `sprint/E4-S1`（基 E3-S3 tip `61d2f40`）；worktree `/workspace/opentask-worktrees/E4-S1`；不推远程。
- 2026-11-04（UTC+8）：E4-S1 closed；acceptance `docs/superpowers/acceptances/2026-11-04-E4-S1-acceptance.md`；分支 `sprint/E4-S1` 未推远程。下一步 S2（列表分组泳道）。
- 2026-11-04（UTC+8）：E4-S2 started；分支 `sprint/E4-S2`（基 E4-S1 tip `cf748eb`）；worktree `/workspace/opentask-worktrees/E4-S2`；客户端 groupBy；不推远程。
- 2026-11-04（UTC+8）：E4-S2 closed；acceptance `docs/superpowers/acceptances/2026-11-04-E4-S2-acceptance.md`；分支 `sprint/E4-S2` 未推远程。下一步 S3（一等公民子 Issue）。
- 2026-11-04（UTC+8）：E4-S3 started；分支 `sprint/E4-S3`（基 E4-S2 tip `1e79a91`）；worktree `/workspace/opentask-worktrees/E4-S3`；`parent_issue_id` 一等公民；不推远程。

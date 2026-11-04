---
epic: E6
status: active
date: 2026-11-04
---

# OpenTask Linear 进阶：Cycles（厚）· 冲刺 · 归属 · Rollover · 容量

产品参考 Linear Cycles；在 E5（⌘K / 热键 / 实体跳转）之上补齐「Workspace 级时间盒 Cycle + Issue 归属 + 列表/看板/⌘K 筛选跳转 + 结束 rollover + 容量粗算 + 设置/空状态」。本 Epic 为整包一个 Roadmap。Labels / 共享 Views / Initiatives / 精修 velocity / Slack 明确排除。

北星：[OpenTask · Linear 对齐完整 PRD](https://cursor.com/canvas/store-adddb90c-33cd-496c-a6c4-08755560f586/656f4217-cbf0-48a3-9edb-168b4a36cbee) §E6。

## Deliverables

| deliverable | note |
|---|---|
| Cycle 模型（Workspace 作用域） | 新表 `cycles`：`starts_at` / `ends_at`、状态 `upcoming` / `active` / `completed`；**非** Linear Team 日历；挂 `workspace_id` |
| Issue.cycle_id | 可空 FK；列表 / 看板 / `IssueQueryParams` 可按 Cycle 过滤；详情可指派 Cycle |
| 结束 Cycle + Rollover | 未完成 Issue 可配置滚入下一 Cycle（默认滚入）；完成态 Issue 留在原 Cycle |
| 容量提示 | 近 N 个已完成 Cycle 的完成数均值粗估；无历史则回退成员数；可选 `estimate_points` 钩子（保留 `estimated_hours`） |
| 设置页 + 空状态 | Cycles 关闭时设置引导；无 upcoming 时一键生成下一 Cycle |
| ⌘K 扩展 | Palette 增加 Cycles 分组：跳转 / 应用「按 Cycle 筛选」 |

## Definition of Done

- [ ] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；合并证据本地台账（merged-commit 仍 null / 未推远程）
- [ ] `cd backend && uv run pytest tests/ -v` 全绿（含 Cycle CRUD / 跨租户负例 / rollover / capacity）
- [ ] `cd frontend && npm run lint && npm run build` 通过（0 errors）
- [ ] 可创建/列出/编辑 Cycle；Issue 可挂 Cycle；列表与看板可按 Cycle 筛选
- [ ] 结束 active Cycle：未完成按策略 rollover；容量提示可见
- [ ] Cycles 关闭 / 无 upcoming 空状态有引导；一键生成 upcoming 可用
- [ ] ⌘K 可搜/跳 Cycle 或应用 Cycle 筛选
- [ ] DESIGN.md / Naive UI / soybean 令牌被前端改动遵守；无多 Team 日历 / Slack / 精修 velocity 图 / Initiatives

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | active | **Cycle CRUD API + Alembic + Workspace Cycles 设置列表 UI**（启用开关、列表、创建 upcoming）。plan: `docs/superpowers/sprints/2026-11-04-E6-S1-plan.md` |
| S2 | planned | **Issue.cycle_id** + 列表/看板筛选 + 指派 Cycle + ⌘K Cycles 分组跳转/筛选。可选 `estimate_points` 字段最小钩子 |
| S3 | planned | **complete/rollover** + 容量提示 + 空状态打磨 + 全量门禁 + Epic local-complete |

推荐顺序理由：先固化 Workspace 级 Cycle 真相源与设置壳（S1），再挂 Issue 归属与呈现/⌘K（S2），最后做结束态自动化与容量（S3）——rollover 依赖「下一 Cycle」存在与 `cycle_id` 可写。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | Cycles **Workspace 作用域**；不做 Linear Team 多日历 | OpenTask 无 Team 模型；PRD 默认 | 2026-11-04 | PRD open Q；Yuri/Way |
| D2 | 新建 `cycles` 表；**不**复用 Jira sprint / agent_task sprint 字符串 | Jira JQL `sprint` 恒空集仅为兼容短路；产品 Cycle ≠ Jira | 2026-11-04 | `api/jira/jql.py` |
| D3 | `Issue.cycle_id` 可空 FK → `cycles.id` ON DELETE SET NULL | 对齐 project_id 模式；删 Cycle 不级联删 Issue | 2026-11-04 | 设计 spec |
| D4 | 状态机：`upcoming` → `active` → `completed`；同时至多一个 `active` / workspace | Linear 手感；简化容量与「当前冲刺」 | 2026-11-04 | 设计 spec |
| D5 | Rollover 策略存 Workspace：`into_next`（默认）/ `leave_unassigned`；完成判定 = status ∈ {resolved, closed} | PRD AC；拒绝/其它状态按未完成处理 | 2026-11-04 | PRD §E6 |
| D6 | 容量 hint：近 N（默认 3）completed Cycle 的「完成 Issue 数」均值；无历史 → `member_count`；有 `estimate_points` 时优先点均值 | PRD；不做精修 velocity 图 | 2026-11-04 | PRD |
| D7 | Workspace 开关：`workspaces.cycles_enabled`（bool，默认 false）+ `cycle_duration_days`（默认 14）+ rollover/lookback 列 | 空状态「未启用」可引导；S1 设置页写入 | 2026-11-04 | 设计 spec |
| D8 | 可选 `issues.estimate_points` Numeric/Int 可空；**保留** `estimated_hours`；容量无点时回退计数 | PRD Estimates 横切；不强制迁移工时 | 2026-11-04 | PRD |
| D9 | API 前缀 `/api/cycles`；强制 `X-Workspace-Id` + `require_member`；写操作 member+；viewer 只读 | 与 E3/E4 租户一致 | 2026-11-04 | 设计 spec |
| D10 | 排除多 Team 日历、Slack、精修 velocity、Initiatives、远程推送、改 Jira sprint 语义 | Way/PRD | 2026-11-04 | 指派纪要 |
| D11 | 整 Epic 一次回执；Sprint 中间不逐个找 Yuri/Way 验收 | 与 E5 汇报节奏一致 | 2026-11-04 | Yuri |

### 方案比选（锁定 D1/D2）

| 方案 | 描述 | 结论 |
|---|---|---|
| **A（选定）** | Workspace 级 `cycles` 新表 + `Issue.cycle_id` | **锁定** |
| B | 仿 Team：每「研发组」独立 Cycle 日历 | 拒绝：无 Team；复杂 |
| C | 复用 Jira sprint 字段 / agent meta `sprint` 字符串 | 拒绝：非一等公民；JQL 空集 |

## Exclusions

- 多 Team / 多日历对齐
- Slack / 邮件订阅与投递
- 精修 velocity 图表（允许 MVP 数字/进度条）
- Initiatives（E10）
- Labels / 共享 Views / Display options（E7）
- 改写 Jira `sprint` JQL 使其映射 OpenTask Cycles（可另议；本 Epic 保持空集短路）
- 远程 push / PR（本批仅本地 worktree）
- mission-center 前端复活、计费、SSO 大改

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `cycles` 表 | **create** | S1 Alembic；head 后接 `e1f2a3b4c5d6` | 2026-11-04 |
| `issues.cycle_id` | **add** | S2 migration（可与 S1 同迁或拆迁；推荐 S1 建表、S2 加 FK 以便 S1 可独立验 CRUD） | 2026-11-04 |
| `issues.estimate_points` | **add optional** | S2 最小钩子 | 2026-11-04 |
| `workspaces.cycles_*` 列 | **add** | S1：enabled / duration / rollover / lookback | 2026-11-04 |
| `IssueQueryParams` + list FE `filters` | **extend** | S2 加 `cycle_id` | 2026-11-04 |
| ⌘K `PaletteItemKind` / `setEntitySources` | **extend** | S2 加 `cycle` kind + sources | 2026-11-04 |
| Jira JQL `sprint` 空集 | **leave** | 不在本 Epic 接通 | 2026-11-04 |
| `estimated_hours` | **keep** | 与 points 并存 | 2026-11-04 |
| Saved Views `filter_json` | **compat** | S2+ 允许存 `cycle_id`；不强制迁移旧视图 | 2026-11-04 |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q1 | Cycle 挂 Workspace 还是 Team？ | closed | Workspace（D1） |
| Q2 | 故事点？ | closed | 可选 `estimate_points`；工时保留（D8） |
| Q3 | S1 是否已写 `cycle_id` 列？ | closed | **S1 只建 `cycles` + workspace 设置**；`cycle_id` 放 S2（便于 S1 验收纯 CRUD） |
| Q4 | 「完成」定义？ | closed | `resolved` \| `closed`（D5） |

无阻塞 Open Questions。

## Cross-cutting

| concern | owning epic | note |
|---|---|---|
| 租户隔离 | E3/E6 | 凡 Cycle API 强制 X-Workspace-Id；跨区负例必测 |
| 角色 | E6 | viewer 只读；member 可写 Cycle/指派；owner 可改 `cycles_enabled` 等设置 |
| DESIGN.md | E6 | Naive / soybean；设置页与列表筛选控件一致 |
| 门禁 | E6 | AGENTS.md；PG `opentask-pg-test`；本地不推远程 |
| 汇报节奏 | E6 | **整 Epic 一次回执** |
| Jira 兼容 | E2 leave | sprint 子句仍空集 |

## Overall Acceptance Scenarios

| id | scenario | how to verify | expected |
|---|---|---|---|
| R1 | 启用 Cycles 并创建 upcoming | 设置页开开关 → 创建 Cycle | 列表可见；跨 workspace 不可见 |
| R2 | Issue 挂 Cycle | PATCH/指派 UI | `cycle_id` 持久化；详情可见 |
| R3 | 列表/看板按 Cycle 筛选 | 选 Cycle 过滤 | 仅该 Cycle Issue |
| R4 | ⌘K 跳转/筛选 Cycle | 面板搜 Cycle | 进设置或列表带 `cycle_id` |
| R5 | 结束 Cycle rollover | complete active | 未完成进下一；完成留原 Cycle |
| R6 | 容量提示 | 有/无历史 | 显示均值或成员数回退 |
| R7 | 空状态 | 关闭 Cycles / 无 upcoming | 引导文案；一键生成可用 |
| R8 | 跨租户负例 | 他区 Cycle id | 404/403 |

```supervibe-acceptance-plan
{
  "schema": 1,
  "scope": "epic",
  "scenarios": [
    {
      "id": "R1",
      "goal": "启用并创建 Workspace Cycle",
      "steps": ["打开 Cycles 设置", "启用", "创建 upcoming Cycle"],
      "expected": "本工作区可见；他区不可见",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R2",
      "goal": "Issue 归属 Cycle",
      "steps": ["指派 Issue 到 Cycle", "刷新详情"],
      "expected": "cycle_id 保持",
      "required": true,
      "modality": "api",
      "environment": "real"
    },
    {
      "id": "R3",
      "goal": "列表/看板 Cycle 筛选",
      "steps": ["选择 Cycle 过滤"],
      "expected": "仅显示该 Cycle Issue",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R4",
      "goal": "⌘K Cycle 跳转或筛选",
      "steps": ["⌘K 搜 Cycle 名", "Enter"],
      "expected": "导航或列表筛选生效",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R5",
      "goal": "结束 Cycle 默认 rollover",
      "steps": ["complete active；存在下一 upcoming"],
      "expected": "未完成滚入下一；resolved/closed 留原 Cycle",
      "required": true,
      "modality": "api",
      "environment": "real"
    },
    {
      "id": "R6",
      "goal": "容量提示",
      "steps": ["查看 active/upcoming 容量区"],
      "expected": "有历史显示均值；无历史显示成员数回退",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R7",
      "goal": "空状态引导",
      "steps": ["cycles_enabled=false；或无 upcoming"],
      "expected": "设置引导；一键生成 upcoming",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R8",
      "goal": "跨租户隔离",
      "steps": ["用 B 区 token 读 A 区 cycle"],
      "expected": "403/404",
      "required": true,
      "modality": "api",
      "environment": "real"
    }
  ]
}
```

## 进度注记

- 2026-11-04（UTC+8）：E6 Phase 1 启动（仅文档）。基线 `sprint/E5-S3` @ `da13c86`；分支 `sprint/E6-S1`；worktree `/workspace/opentask-worktrees/E6-S1`。按 PRD 加厚范围写 roadmap/design/S1 stub；**无产品实现、不推远程**。

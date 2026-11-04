---
epic: E7
status: active
date: 2026-11-04
---

# OpenTask Linear 进阶：Labels 打磨 · 共享 Views · Display · 看板泳道（厚）

产品参考 Linear Labels / Shared Views / Display options / Board swimlanes。在 E6（Cycles）之上补齐「标签分组与颜色 + L 热键打标 + 列表/看板按 label 分组 + workspace-shared Saved Views + Display 字段显隐 + Board 行维泳道」。本 Epic 为整包一个 Roadmap。退休标签复杂治理、计费 Insights、强制唯一工作区默认布局、E8+ 明确排除。

北星：[OpenTask · Linear 对齐完整 PRD](https://cursor.com/canvas/store-adddb90c-33cd-496c-a6c4-08755560f586/656f4217-cbf0-48a3-9edb-168b4a36cbee) §E7。

基线 tip：`sprint/E6-S3` @ `7dd7c55`；worktree `/workspace/opentask-worktrees/E7-S1` · 分支 `sprint/E7-S1`。本地不推远程。

## Deliverables

| deliverable | note |
|---|---|
| Labels 打磨 | 工作区作用域标签：颜色、分组；CRUD API；详情/列表可见；与既有 `issue_tags` / Jira labels 契约兼容 |
| groupBy label | 列表 `GroupByKey` 增加 `label`；Saved View `display.group_by` 可存；无标签桶 `__unlabelled__` |
| 热键 L + ⌘K | 焦点 Issue 上 `L` 开标签 picker（复用 E5 `useIssueFocus` / picker host）；⌘K 可搜/应用标签动作 |
| Shared Saved Views | `issue_saved_views` 可标 workspace-shared；member+ 可建；全员可见；个人 vs 共享列表隔离；不可改他人个人视图；编辑者 = 创建者 + owner；member 可 Save As |
| Display options | 卡片/行字段显隐写入 `display_json`；个人默认 vs View 默认可区分；不强制唯一工作区默认布局 |
| Board swimlanes | 行维 `assignee` / `priority` / `type` / `label` / `none` + 列维 status；`hide_empty_lanes` 可选 |

## Definition of Done

- [ ] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；合并证据本地台账（merged-commit 仍 null / 未推远程）
- [ ] `cd backend && uv run pytest tests/ -v` 全绿（含标签 CRUD / 跨租户负例 / 共享 View 权限 / display·swimlane 序列化）
- [ ] `cd frontend && npm run lint && npm run build` 通过（0 errors）
- [ ] 可为工作区建标签（色/组）；Issue 可加减标签；列表可按 label 分组；焦点 Issue 上 L 打标
- [ ] 可创建/列出共享 Saved View；viewer 只读；member 改他人个人视图 → 404；共享视图仅 creator+owner 可写，member Save As
- [ ] Display 字段显隐可存；个人默认与应用 View 的 display 可区分；看板可开泳道并隐藏空泳道
- [ ] DESIGN.md / Naive UI / soybean 令牌被前端改动遵守；无退休治理 / Insights / 强制唯一默认布局
- [ ] 整 Epic 一次回执 Yuri/Way（路径、分支 tip、门禁、acceptance）

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | closed | **Labels 打磨** done @ `a1b59bb`：workspace tags/groups + API + Issue 打标 + groupBy label + L / ⌘K。acceptance: `docs/superpowers/acceptances/2026-11-04-E7-S1-acceptance.md` |
| S2 | closed | **Shared Saved Views** done @ `8ca308a`：`is_shared` + personal/shared isolation + ACL + Save As + FE sections。acceptance: `docs/superpowers/acceptances/2026-11-04-E7-S2-acceptance.md` |
| S3 | planned | **Display options + Board swimlanes** + 个人 display 默认 + Epic 全量门禁 / local-complete。plan: `docs/superpowers/sprints/2026-11-04-E7-S3-plan.md` |

推荐顺序理由：先把标签真相源与 L/groupBy 打通（S1，依赖最薄且解锁筛选语义），再放开共享 View 与权限面（S2，复用已可存 `group_by: label` 的 display），最后打磨呈现层 Display + 看板行维泳道（S3，依赖 display_json 契约稳定）。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | 标签 **Workspace 作用域**；`tags.workspace_id` + unique `(workspace_id, name)` | 租户隔离；现状全局 `uq_tags_name` 不安全 | 2026-11-04 | 探索；PRD 租户表 |
| D2 | 扩展既有 `tags` / `issue_tags`；**不**另起 labels 表 | Jira/tasks `sync_issue_labels` 已绑 Tag；最小破坏 | 2026-11-04 | `api/tasks/service.py` |
| D3 | `color` String + `group_id`（可空 FK → `tag_groups`） | PRD「分组/颜色」；组可空 = 未分组 | 2026-11-04 | PRD §E7 |
| D4 | 新建轻量表 `tag_groups(workspace_id, name, …)`；不做复杂层级 | 够用；非目标退休治理 | 2026-11-04 | YAGNI |
| D5 | Shared View：布尔 `is_shared`（false=个人）；保留 `owner_user_id`=创建者 | PRD；比 visibility enum 更简 | 2026-11-04 | PRD open Q |
| D6 | 共享 View 写权限：创建者 **或** workspace owner；member 只读共享并可 **Save As** 成自己的个人视图 | PRD 默认决议 | 2026-11-04 | PRD |
| D7 | 列表他人个人视图：恒不可见（list 不返回）；直链 GET → 404（不泄漏） | 与 E4 get_mine 一致 | 2026-11-04 | E4 design |
| D8 | `display_json` 扩展：`fields` / `swimlane_by` / `hide_empty_lanes`；保留 `view_mode` / `group_by` | 向后兼容旧 View | 2026-11-04 | 探索 |
| D9 | 个人 Display 默认：表 `issue_display_prefs(workspace_id, user_id, display_json)` 唯一；应用 View 时 View.display 覆盖会话，不改 prefs，除非显式「设为个人默认」 | 可区分个人 vs View 默认；无强制工作区唯一布局 | 2026-11-04 | PRD AC |
| D10 | Board 列维固定 status；行维 = swimlane；跨泳道拖拽改字段 **不做**（与 E4 列表 groupBy 同边界） | 降低复杂度 | 2026-11-04 | E4 先例 |
| D11 | 热键 L 扩展 `resolveIssueHotkeyAction` + picker kind `labels`；输入态/面板开忽略 | E5 扩展点 | 2026-11-04 | `issue-hotkeys.ts` |
| D12 | `/api/tags` 新建 router；Issue `GET …/tags` 取消空壳；强制 `X-Workspace-Id` | FE `tagApi` 已预留路径 | 2026-11-04 | 探索 |
| D13 | 整 Epic 一次回执；Sprint 中间不逐个找 Yuri/Way 验收 | 与 E5/E6 节奏一致 | 2026-11-04 | Yuri |
| D14 | 排除：标签退休治理、Insights、强制唯一工作区默认、远程 push、E8 Favorites/Timeline | PRD / 指派 | 2026-11-04 | 指派 |

### 方案比选（锁定 D1 / D5 / D9）

| 主题 | A（选定） | B（拒绝） | C（拒绝） |
|---|---|---|---|
| 标签租户 | Workspace 列 + 复合唯一 | 保持全局 name | 每 Issue 自由字符串无 Tag 表 |
| 共享标记 | `is_shared` bool | 新表 `shared_views` 复制 | visibility 三态含 team |
| 个人默认 | `issue_display_prefs` 表 | 仅 localStorage | 强制写入某条「默认 View」 |

## Exclusions

- 标签退休 / 合并 / 归档复杂治理与审计流
- 计费级 Insights / 报表
- 工作区级强制唯一默认布局（允许「Set as personal default」即可）
- 跨泳道拖拽改 assignee/priority/label（展示-only 泳道）
- 侧栏 Favorites（E8）、Timeline / 里程碑（E8）、Triage（E9）
- 远程 push / PR（本批仅本地 worktree）
- mission-center 前端复活、计费、SSO 大改

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `tags` 表 | **extend** | 加 `workspace_id` / `color` / `group_id`；改唯一约束 | 2026-11-04 |
| `tag_groups` | **create** | S1 Alembic；head 后接 `a1b2c3d4e5f7` | 2026-11-04 |
| `issue_tags` | **keep** | 关联表不动；权限经 Issue/Tag 工作区校验 | 2026-11-04 |
| `/api/tags` | **create** | 现无 router；FE `tagApi` 复活 | 2026-11-04 |
| Issue `GET/POST/DELETE …/tags` | **fix** | GET 取消空列表 stub | 2026-11-04 |
| `issue_saved_views.is_shared` | **add** | S2 | 2026-11-04 |
| SavedViewService list/get | **extend** | S2：list_accessible / 写权限分支 | 2026-11-04 |
| `issue_display_prefs` | **create** | S3 | 2026-11-04 |
| `GroupByKey` / `groupIssuesBy` | **extend** | S1 加 `label` | 2026-11-04 |
| `IssueBoard.vue` | **extend** | S3 泳道矩阵；S1 可不改板 | 2026-11-04 |
| `issue-hotkeys` / picker host | **extend** | S1 加 `L` / `labels` | 2026-11-04 |
| Jira `sync_issue_labels` | **compat** | 创建 Tag 时写入当前 workspace_id | 2026-11-04 |
| `display_json` 旧键 | **compat** | 缺省 fields/swimlane = 现状硬编码行为 | 2026-11-04 |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q1 | 共享 View 谁可编辑？ | closed | 创建者 + owner；member Save As（D6） |
| Q2 | 标签全局还是工作区？ | closed | 工作区（D1） |
| Q3 | 多标签 Issue 在 groupBy label 出现几次？ | closed | **每个标签一桶各出现一次**；无标签进 `__unlabelled__`（Linear 常见手感） |
| Q4 | S1 是否已加 `is_shared`？ | closed | **否** — S1 专注 Labels；共享归 S2 |
| Q5 | 存量无 workspace 的 Tag 如何回填？ | closed | 若 Tag 仅挂单一 Issue.workspace → 写入该 WS；多 WS 或无 Issue → 挂「最早关联 Issue 的 WS」或 Default Workspace；冲突名加后缀 `-migrated`（实现计划写清） |

## Next

1. Design spec：`docs/superpowers/specs/2026-11-04-e7-labels-shared-views-display-design.md`
2. S1 sprint stub（本批）：`docs/superpowers/sprints/2026-11-04-E7-S1-plan.md`
3. **本 Phase 不写产品实现**；实现阶段再写 `docs/superpowers/plans/2026-11-04-e7-s1-*.md` 并 TDD
4. S1→S2→S3 本地收口后整包回执，再按 PRD 自动接 E8

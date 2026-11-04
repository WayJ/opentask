---
epic: E11
status: active
date: 2026-11-04
---

# OpenTask Linear 进阶：Git / PR 集成（厚）

产品参考 Linear「Copy git branch name」+ Issue 上挂 PR + 可选自动推进状态。在 **E10 local-complete**（Initiatives + Docs）之上交付：**分支名约定**、**PR↔Issue 关联**、**可选状态钩子**、**CLI/Agent 同契约**。本 Epic 为整包一个 Roadmap；本地可测优先，**不依赖**能推远程或真实 GitHub OAuth 才能验收。

**Yuri 收紧范围（2026-11-04）——仅此四条为主 AC：**

1. **分支名约定**（Linear-like：含 KEY-N / `issue_code`）
2. **PR 关联**到 Issue
3. **可选状态钩子**（PR open/merge → Issue status，可开关）
4. **CLI/Agent 同契约**（同一 HTTP API/约定，不另起一套）

北星：[OpenTask · Linear 对齐完整 PRD](https://cursor.com/canvas/store-adddb90c-33cd-496c-a6c4-08755560f586/656f4217-cbf0-48a3-9edb-168b4a36cbee) §E11（「分支名约定；PR 关联；可选状态钩子；CLI/Agent 同契约」）。

基线 tip：`sprint/E10-S3` @ `55ed5b7`；worktree `/workspace/opentask-worktrees/E11-S1` · 分支 `sprint/E11-S1`。本地不推远程。Phase 1 **仅** explore + roadmap + design + S1 stub；**不**产品实现。

## Deliverables

| deliverable | note |
|---|---|
| **分支名约定** | 自 `issue_code`（KEY-N，E12 已交）生成 Linear-like 建议名；解析分支名 → Issue；Issue 详情可复制；CLI/Agent 同端点 |
| **PR↔Issue 关联** | 一等公民链接（branch / PR URL / provider status）；挂 **Issue**，不挂 Requirement/PGE；列表于 Issue 详情 |
| **可选状态钩子** | Workspace 开关：PR `open`→`in_progress`；`merged`→`resolved`（可配置目标态）；默认关；可本地 webhook fixture 测 |
| **CLI/Agent 同契约** | opentask-cli + CodingWorker/Agent 只调同一 `/api/issues/.../vcs-*`（或等价）与 webhook 契约；无平行私有协议 |
| **打磨** | 空状态；ACL；DESIGN.md / Naive；Epic local-complete |

## PRD / Yuri ACs

- [ ] 分支名约定；含 KEY-N / issue_code（Linear-like）
- [ ] PR 关联到 Issue
- [ ] 可选状态钩子（PR open/merge → issue status，可开关）
- [ ] CLI/Agent 同契约（同一 API/约定）

## Definition of Done

- [ ] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；merged-commit 仍 null / 未推远程
- [ ] `cd backend && pytest` 全绿（含分支 suggest/parse、VCS link ACL/跨租户、webhook fixture、状态钩子开关负例）
- [ ] FE eslint touched 0 errors；Issue 详情可复制分支名、见关联 PR；工作区设置可见钩子开关
- [ ] CLI/Agent：至少一条命令或文档路径证明走同一 API（无第二套 schema）
- [ ] **无** RequirementRepo / PGE 作主路径；**无** 强制真实 GitHub App OAuth 才能绿测
- [ ] 整 Epic 一次回执 Yuri/Way

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | **planned** | 分支名约定：suggest/parse API + `issue_vcs_links`（至少 branch 类型）+ Issue FE「复制分支名」+ CLI 同端点 |
| S2 | **planned** | PR 关联 CRUD + GitHub-compatible webhook ingest（可 mock）更新 link 状态 + Issue 详情 PR 面板 |
| S3 | **planned** | 可选状态钩子（WS 开关）+ 打磨 + CLI/Agent 契约验收 + Epic local-complete |

推荐顺序理由：分支约定是 Linear 日常最高频且不依赖 webhook（S1）；PR 关联与状态字段建立在同一 link 模型上，webhook 可本地 fixture（S2）；状态钩子是可选副作用，需开关与负例，放 S3 与整包验收同频。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | **Yuri 四 AC 即 Epic 边界**；不做完整 GitHub App 产品、不做多 provider 深度、不复活 PGE | steering 2026-11-04 | 2026-11-04 | 指派 |
| D2 | 新表 **`issue_vcs_links`** 挂 **Issue**；**不**复用 `requirement_repos.pr_url`（PGE 轴） | E12 de-PGE；探索见 design | 2026-11-04 | inventory |
| D3 | 分支模式默认：`{type?}/{issue_code}-{slug}` 或 Linear 简式 `{issue_code}-{slug}`；slug 自 title 清洗；**必须含完整 issue_code** | Linear copy-branch；KEY-N 已在 E12 | 2026-11-04 | Linear；E12 |
| D4 | 验收优先 **API + 签名可选的 webhook fixture**；live OAuth/GitHub App **非** DoD | 「本地可测优先」 | 2026-11-04 | 指派 |
| D5 | 状态钩子默认 **关闭**；开启后 PR open→`in_progress`，merged→`resolved`（closed 仅当目标已 resolved 可再关另议） | 可选；不惊喜改状态 | 2026-11-04 | Yuri |
| D6 | CLI/Agent **只**消费公开 HTTP API（与 FE 同）；CodingWorker 文档指向同一契约 | 「不另起一套」 | 2026-11-04 | Yuri |
| D7 | Alembic `down_revision = c3d4e5f6a7b8`（E10 entity_documents tip） | E10-S3 tip | 2026-11-04 | alembic |
| D8 | 排除：真实 GitHub App 安装 UX、GitLab 深度、自动开 PR 到远程、RequirementRepo 迁移、远程 push | 指派 / 本地优先 | 2026-11-04 | 指派 |

## Out of scope

- 完整 GitHub/GitLab App 安装与 OAuth 产品化（可后置；E11 用 mockable webhook + 手动/API 关联）
- 自动在远程创建真实 PR（`git_create_pr` 占位可保留；非本 Epic DoD）
- 复用 / 迁移 `requirement_repos` 作主路径
- 多 repo 智能选仓、commit status checks UI、CODEOWNERS
- 计费；SSO；远程 push

## Explore gaps（Phase 1）

| gap | note |
|---|---|
| **无** `issue_vcs_links` / Issue↔PR 一等模型 | 绿田；S1 新建 |
| `repo_configs` 已有（Project 挂仓 URL + main_branch） | 可作「默认仓」展示；非 PR 实体 |
| `requirement_repos` 有 `branch`/`pr_url`/`merge_status` | **PGE 轴**；E11 **不**作主入口；可作字段参考 |
| `repositories` + `git_create_pr` | PR 创建 **占位未实现**；clone/status 有；不阻塞 link 模型 |
| KB webhook `/api/webhook` | 仅知识库 sync；非 Issue/PR |
| E12 `Workspace.issue_key` + `issue_code` KEY-N | 分支名输入已就绪 |
| IssueStatus | open / in_progress / feedback / resolved / closed / rejected |
| MergeStatus（requirement 枚举） | open / merged / closed / draft — 可镜像到 VCS link status |
| opentask-cli | 有 Issue 命令；**无** branch/PR 子命令 — S1/S3 接同一 API |
| CodingWorker | 已去 PGE 默认；需补 VCS 契约说明（S3） |

## Changelog

| date | note |
|---|---|
| 2026-11-04 | Phase 1：roadmap + design + S1 stub；基线 E10-S3 `55ed5b7`；Yuri 四 AC 写入；无产品 impl / 无 push |

## Sprint status

- [ ] E11-S1 分支名约定 + link 骨架
- [ ] E11-S2 PR 关联 + webhook ingest
- [ ] E11-S3 可选状态钩子 + Epic DoD

## Epic status

- [ ] E11 Phase 1 docs（本提交）
- [ ] E11 **local-complete**（待 S1–S3）

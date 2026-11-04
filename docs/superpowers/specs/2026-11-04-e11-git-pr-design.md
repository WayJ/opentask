# E11 设计：Git / PR 集成（分支 · PR 关联 · 可选状态钩子 · CLI/Agent 同契约）

日期：2026-11-04  
Epic：E11  
状态：draft（Phase 1；无产品 impl）  
基线：`sprint/E10-S3` @ `55ed5b7`；worktree `/workspace/opentask-worktrees/E11-S1`（分支 `sprint/E11-S1`）  
北星：OpenTask Linear PRD §E11  
Alembic head：`c3d4e5f6a7b8`（`entity_documents`）

## 0. 硬约束（Yuri 2026-11-04）

> E11 收紧为四条；厚 Epic；本地可测；不推远程。

1. **分支名约定**（Linear-like：含 KEY-N / `issue_code`）
2. **PR 关联**到 Issue
3. **可选状态钩子**（PR open/merge → Issue status，**可开关**）
4. **CLI/Agent 同契约**（同一 API/约定，**不另起一套**）

补充：

- **勿**把 `requirement_repos` / PGE 当作主路径
- **勿**把「必须连上真实 GitHub OAuth / 能 push 远程」写成验收前提——优先 mockable / fixture / 手动 API
- Phase 1 **只** docs；实现仍按 S1→S3 做完整 Epic，不提前停 Epic

## 1. 目标与非目标

### 1.1 目标（按 Sprint）

1. **S1** 分支名 suggest/parse；`issue_vcs_links` 表（至少 `kind=branch`）；Issue FE「复制分支名」；CLI 调同一 API  
2. **S2** PR 关联（`kind=pull_request`）CRUD；GitHub-compatible webhook ingest（可无签名或测试密钥）更新 status；Issue 详情 PR 列表  
3. **S3** Workspace 开关控制状态钩子；open→`in_progress`、merged→`resolved`；打磨 + CodingWorker/CLI 契约说明 + Epic local-complete  

### 1.2 非目标

- GitHub App 安装向导 / 多 org 绑定产品化  
- 在远程真实 `create_pull_request`（现有 `git_create_pr` 占位可保留）  
- GitLab/Gitea 深度（provider 字段预留即可）  
- Requirement/PGE 仓库关联迁移  
- Commit status / checks UI、自动选仓策略精修  
- 远程 git push 本仓库  

## 2. 探索事实（Phase 1 inventory）

### 2.1 已有、可借

| 资产 | 路径 | 与 E11 关系 |
|---|---|---|
| `Workspace.issue_key` + Issue.`issue_code`（KEY-N） | E12 | **分支名必含**的标识 |
| `repo_configs` | Project 挂仓 `url` + `main_branch` | 展示「默认仓」；非 PR 实体 |
| `repositories` / `repository_branches` | `models/repo/` | 本地 clone/status；`git_create_pr` **占位失败** |
| KB webhook | `api/knowledge/webhooks.py` | 仅 KB sync；模式可参考，**不复用路由语义** |
| `MergeStatus` | requirement enums | open/merged/closed/draft — 可镜像 |
| opentask-cli Issue 命令 | `agent-harness/opentask-cli` | S1/S3 加薄封装，走 HTTP |

### 2.2 不可作主路径

| 资产 | 原因 |
|---|---|
| `requirement_repos.branch/pr_url/merge_status` | PGE/Requirement 轴；E12 主路径已去 PGE |
| KB `create_pull_request` | 知识库文档 PR，非 Issue OS |

### 2.3 缺口

- 无 Issue↔branch/PR 一等表  
- 无分支名 suggest/parse  
- 无 Issue 详情 VCS 面板  
- 无 GitHub PR webhook → Issue  
- 无「PR 事件 → Issue status」开关  
- CLI/Agent 无 VCS 子契约文档  

## 3. 方案对比与推荐

| 方案 | 做法 | 利 | 弊 |
|---|---|---|---|
| **A. 推荐** | 新 `issue_vcs_links` + 纯 API/手动关联 + **mockable GitHub webhook** + WS 钩子开关 | 本地 pytest 全覆盖；对齐 Linear 手感；不绑 OAuth | 真 GitHub 需后置装 App |
| B | 只做 FE 深链外链、无表 | 快 | 无 ACL/状态/钩子；CLI 契约空 |
| C | 复用 `requirement_repos` | 少表 | 复活 PGE 轴；违反 Yuri/E12 |
| D | 强制 GitHub App + live OAuth 才验收 | 「真集成」 | 违反「本地可测优先」；本环境难绿 |

**推荐 A。** 实现期 S1–S3 按 A 落地；真 GitHub App 另 Epic 或 E11 后补丁，不挡 DoD。

## 4. 架构总览

```
Workspace
  + git_status_hooks_enabled: bool = false     [S3]
  + git_hook_on_pr_open: IssueStatus = in_progress
  + git_hook_on_pr_merged: IssueStatus = resolved
  └── Issue (issue_code = KEY-N)
        └── IssueVcsLink[]                     [S1+]
              kind: branch | pull_request
              branch_name / pr_url / provider / external_id
              status: open | draft | merged | closed | unknown
              repo_config_id? (optional FK)

HTTP（FE = CLI = Agent）:
  GET  /api/issues/{id}/vcs/branch-name        → { branchName, issueCode, ... }
  POST /api/issues/{id}/vcs/links              → create branch|PR link
  GET  /api/issues/{id}/vcs/links
  PATCH/DELETE /api/issues/{id}/vcs/links/{linkId}
  POST /api/webhooks/github/pull-request       → ingest (fixture-friendly)  [S2]

禁止主路径：
  requirement_repos 作为 Issue Git UI/API
```

## 5. 数据模型

### 5.1 `issue_vcs_links`（S1 建表；S2 用满 PR 字段）

| 列 | 说明 |
|---|---|
| id | uuid PK |
| workspace_id | FK workspaces CASCADE（冗余便于 ACL） |
| issue_id | FK issues CASCADE |
| kind | `branch` \| `pull_request` |
| branch_name | str(255) nullable；PR 也可填 head ref |
| pr_url | str(500) nullable |
| provider | `github` \| `gitlab` \| `gitea` \| `manual` \| `custom`；默认 `manual` |
| external_id | str(100) nullable；如 GitHub PR number / node_id |
| status | `open` \| `draft` \| `merged` \| `closed` \| `unknown`；默认 `unknown` |
| repo_config_id | optional int FK `repo_configs.id` SET NULL |
| title | optional str（PR 标题缓存） |
| created_by | optional |
| created_at / updated_at | 审计 |

约束建议：

- Index `(issue_id, kind)`  
- 部分唯一：同 Issue 下相同 `pr_url` 不重复（应用层或 uq）  
- 跨 WS：创建时校验 issue.workspace_id == X-Workspace-Id  

### 5.2 Workspace 钩子设置（S3）

| 列 | 默认 |
|---|---|
| `git_status_hooks_enabled` | `false` |
| `git_hook_on_pr_open` | `in_progress` |
| `git_hook_on_pr_merged` | `resolved` |

仅 owner（或现有 workspace settings 写角色）可改；viewer 只读。

## 6. 分支名约定（S1）

对齐 Linear「Copy git branch name」精神：

**默认模板（锁定）：**

```text
{issue_code}-{slug}
```

例：`WAY-42-fix-login-redirect`

规则：

1. `issue_code` **原样**（已是 `KEY-N` 或遗留 `ISSUE2026-N`）；大小写保持库内值  
2. `slug`：title → NFKC → 小写 → 非 `[a-z0-9]+` 换成 `-` → 压缩连字符 → trim → 最长 40  
3. 空 title → 仅 `{issue_code}`  
4. **Parse**：分支名中用正则提取 **第一个** 匹配 `issue_code` 形态的片段（优先 KEY-N，其次 legacy），在当前 WS 解析 Issue；找不到 → 404/空  
5. API 响应 camelCase：`branchName`, `issueCode`, `slug`  
6. FE：Issue 详情按钮「复制分支名」；⌘K 可选后置（S3 打磨可不做）  
7. **不**在 S1 强制本地 `git checkout -b`（无沙箱仓也可测）

可选前缀（**不做默认**，设置可后置）：`feature/`、`bugfix/` — E11 默认不加 type 前缀，避免与 Linear 简式不一致；若加，必须仍含完整 issue_code。

## 7. PR 关联（S2）

### 7.1 手动 / API

- `POST .../vcs/links` body：`{ kind: "pull_request", prUrl, branchName?, provider?, externalId?, status? }`  
- 成员+ 可写；viewer 只读  
- 列表按 `updated_at` desc  
- FE：Issue 详情「关联的 PR」卡片：外链、状态徽章、解除关联  

### 7.2 Webhook ingest（GitHub-compatible，可 mock）

- `POST /api/webhooks/github/pull-request`  
- Body 兼容 GitHub `pull_request` event 子集：`action`, `pull_request.html_url`, `pull_request.number`, `pull_request.state`, `pull_request.merged`, `pull_request.head.ref`, `pull_request.title`, `repository.html_url`（字段可扁平测试夹具）  
- 鉴权：`X-Hub-Signature-256` **可选**；测试环境允许共享 `WEBHOOK_GITHUB_SECRET` 为空时跳过验签（文档标明危险，仅 local/dev）  
- 匹配策略（顺序）：  
  1. `head.ref` parse → issue_code → Issue  
  2. 否则已有 link 的 `external_id` / `pr_url`  
- Upsert `issue_vcs_links`：status 映射 `open|draft|closed`；`merged=true` → `merged`  
- **不**要求仓库已在 `repo_configs`（有则尝试填 FK）

## 8. 可选状态钩子（S3）

当且仅当 `workspace.git_status_hooks_enabled`：

| 事件 | 默认目标 IssueStatus | 条件 |
|---|---|---|
| PR → open/draft（新开或 reopen） | `in_progress` | 当前 status ∈ {`open`} 才自动推进（已 in_progress/feedback 不降级不扰） |
| PR → merged | `resolved` | 当前非 `closed`/`rejected` 时可设为配置目标 |
| PR → closed（未合并） | **不**自动改 Issue（避免误关） | — |

实现要点：

- 钩子跑在 webhook upsert **之后**同一请求事务或紧随服务调用  
- 写 Issue timeline `status_changed` + 既有通知通道（若有）  
- 单元测试：开关关 → 状态不变；开关开 + open Issue + PR open → in_progress；merged → resolved  
- FE：Workspace 设置页 Toggle「从 PR 自动更新 Issue 状态」  

## 9. CLI / Agent 同契约（贯穿 S1–S3）

| 调用方 | 用法 |
|---|---|
| FE | `service/api` → 上表 HTTP |
| opentask-cli | 薄封装：`opentask issue branch-name <code>`、`opentask issue link-pr <code> <url>` 等，**只** HTTP |
| CodingWorker / Agent | `CodingWorker.md` / harness 文档写明同一路径；**禁止**私有 RPC 或直写 DB |

契约验收（S3）：

- 至少 1 个 CLI 测试或文档 + API 测试证明同一 payload 形状（camelCase 与现有 Issue API 一致）  
- Agent 文档含「关联 PR / 取分支名」示例，指向 `/api/issues/...`  

## 10. 权限与多租户

- 所有业务 API：`X-Workspace-Id` + `require_member`（写）/ viewer 可读  
- Webhook：无用户 JWT；靠 secret（可选）+ 解析出的 Issue 必须存在；跨 WS 不可能（issue 自带 workspace）  
- 跨租户负例：A 的 token + B 的 issue id → 404；webhook 伪造 URL 不能改写他仓 Issue  

## 11. 测试策略（本地可测）

| 层 | 内容 |
|---|---|
| pytest | suggest/parse；link CRUD ACL；webhook fixture JSON → upsert；钩子开关矩阵；跨 WS |
| FE | 复制按钮（可单测 util）；PR 列表渲染（可选 vitest） |
| CLI | mock httpx → 同路径 |
| **不要求** | 真 GitHub token、真 push、真 create PR |

## 12. Alembic

- S1 revision 建议 id：`d4e5f6a7b8c9`  
- `down_revision = c3d4e5f6a7b8`  
- S3 可同迁移加 workspace 三列，或独立 `e5f6a7b8c9d0`（实现时择一，roadmap 不阻断）

## 13. Sprint 切分（厚）

### S1 — 分支名约定 + link 骨架

- 迁移 `issue_vcs_links`  
- `GET .../vcs/branch-name`；可选 `POST .../vcs/links` kind=branch  
- FE 复制分支名  
- CLI `branch-name`  
- 测试：slug、KEY-N、legacy code、ACL  

### S2 — PR 关联 + webhook

- links CRUD 补齐 PR  
- webhook ingest + fixture tests  
- Issue 详情 PR 面板  
- 不做状态钩子  

### S3 — 可选钩子 + 打磨 + Epic

- WS 设置列 + Toggle UI  
- 钩子逻辑 + 负例  
- CodingWorker/CLI 契约收口  
- acceptance + roadmap DoD  
- **无 push**  

## 14. 风险

| 风险 | 缓解 |
|---|---|
| 真 GitHub 用户期望 App | 文档标明 E11=契约+本地 ingest；App 后置 |
| 分支 parse 误匹配 | 优先完整 issue_code；WS 作用域查询 |
| 钩子误改状态 | 默认关；仅 open→in_progress；closed 未合并不改 |
| 与 requirement_repos 并存混淆 | UI/API 零入口指向 RequirementRepo |

## 15. Self-review

- [x] 无 TBD 阻塞实现（App 明确后置）  
- [x] 四 AC 均有章节与 Sprint 归属  
- [x] 不与 E12 KEY-N / E10 / de-PGE 矛盾  
- [x] 本地可测写清；无强制远程  

## 16. 开放默认（不必再问）

| 问题 | 默认 |
|---|---|
| 分支模板？ | `{issue_code}-{slug}` |
| 钩子默认开？ | **关** |
| merged → 哪态？ | `resolved` |
| 未合并 close？ | 不改 Issue |
| 主路径用 requirement_repos？ | **否** |

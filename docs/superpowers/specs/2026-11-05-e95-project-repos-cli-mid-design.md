# E95 Design：Project Repos CLI mid · CLI 1.79.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E95  
基线拟：`sprint/E94-S1` @ `315d459`（全文 `315d459deec59242802530cd46c9226889e2b2c6`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E95-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**大软不自开 E96**。  
入库：`docs/superpowers/specs/2026-11-05-e95-project-repos-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

> 注：`docs/product/PROJECT.md` 在本 tip **不存在**；本设计依据 Linear 对齐 PRD canvas、E90–E94 design/acceptance runners-up，以及 @ `315d459` 代码扫描。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E94 连续闭合 … → Display Prefs CLI mid（E93 · 1.77.0）→ Issue Reactions CLI mid（E94：`issue reaction` + `issue comment-reaction` · 1.78.0）。

E94 附录 runners-up（硬排除）+ tip 扫描 @ `315d459`：

1. **Activity Push** — 仍 **勿默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b** — **rotate off**  
5. **表单公开附件** — **prefer skip**  
6. **递归孙项进度** — **prefer skip**  
7. **Bulk/Insights 多指派** — **prefer skip**  
8. **深拷贝 duplicate project** — **prefer skip**  
9. **模板内 Issue stubs** — **prefer skip**  
10. **CSV start_date / start reminders** — **后置**  
11. **depth≥2 threading** — **后置**  
12. **评论版本史 / 编辑加厚** — **另弧**（简单 `comment update` CLI 可 runners-up，非本轮主推）  
13. **G-then-X** — **另弧**  
14. **复制附件/子树 / Issue merge** — **过厚**  
15. **Timed purge / `archived_at` dual-track** — **后置 / skip**  
16. **Project 私有 ACL** — **另大弧**  
17. **bulk_update `project_id` + integrity** — **明示跳过**（需 BE schema；触 E80）  
18. **`project list --watching` BE 过滤** — **明示跳过**（需 BE Query）  
19. **Initiative health 独立 CLI** — **明示跳过**（tip 无对称 `/health` 路由）  
20. **再开 E79–E94 邻面** — **刚闭，勿默认**  
21. **（扫描 · 本轮主推）Project Repos CLI** — BE `GET/POST /api/projects/{id}/repos` + `GET/PUT/DELETE …/repos/{repo_id}` **齐**（`TestRepoConfigCRUD`）；FE `fetchProjectRepos` / `createRepoConfig` / `updateRepoConfig` / `deleteRepoConfig` **齐**；api_client / `opentask project` **零** repo 子组——agent 无法脚本「给 Project 挂/改/卸 Git 仓库配置」——实证为 Reactions 闭合后剩余最清晰的 **BE/FE 齐、CLI 洞** mid（复用既有路由；无新表；单 sprint；弱对齐 Linear Project↔Repo，并为 E11 Git/PR 脚本面铺垫，**不做** clone/commit/PR 真 Git 操作）

代码实证 @ `315d459`：

| 面 | 现状 |
|----|------|
| BE Project repos | `GET/POST /api/projects/{project_id}/repos`；`GET/PUT/DELETE /api/projects/{project_id}/repos/{repo_id}`；body create `{name,url,main_branch,project_id}`；update 可选 `{name,url,main_branch}`；挂在 `project_router` → 全局 `authenticate` |
| FE | `project.ts` 四 helpers + 项目详情仓库表 **齐** |
| CLI | **无** `project repo …`；api_client **零** project-repo helpers |
| 邻面 | Issue VCS links（`issue link-branch/link-pr/vcs-links`）已有——挂 **Issue**；本洞是挂 **Project** 的 RepoConfig |
| 明示跳过 | bulk `project_id` / `project list --watching` / Initiative health / Push / 门户 / 甘特 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Project Repos CLI mid**：CLI **1.79.0** 新子组 `project repo list\|show\|add\|update\|remove`；api_client 五 helpers → 复用既有 GET/POST/PUT/DELETE；**无**新表/webhook/路由；FE 已齐 → 零产品 FE；human 薄表 id/name/url/main_branch | **薄→中薄**；闭合「BE/FE 齐、CLI 洞」；单 sprint；agent 价值清晰（脚本 Project↔Git 配置）；不触明示跳过面 |
| B | 仅 `activity mark-read` CLI | 过薄；个人水位，agent 价值偏弱 |
| C | `issue comment update` CLI | 真洞但「评论编辑加厚」曾标另弧；半截于版本史 |
| D | `form regenerate-token` 薄补 | 过薄；api_client 已有 helper、CLI 仅缺命令 |
| E | bulk_update `project_id` + integrity | 明示跳过；触 BE + E80 |
| F | `project list --watching` BE 过滤 | 明示跳过；需 BE Query |
| G | Initiative health / 甘特 / Activity Push / 门户 / … | 明示跳过 / prefer skip |
| H | 再开 reactions / display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Project Repos CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.79.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成 Initiative health / bulk project_id / watching filter / 真 Git clone·PR；**不**做 `requirement-repos`（PGE/遗留关联）。

### Why this Epic now（一句话）

E86–E94 连续闭合「BE/FE 齐、CLI 洞」关联/reorder/看板/Saved View/Display/Reactions 后，**Project RepoConfig** BE/FE（项目详情仓库表）早已齐而 CLI **完全空洞**——agent 无法脚本「挂/改/卸 Project 的 Git 仓库配置」；用薄刀一次闭合该洞，为后续 Git/PR 脚本面留接口，且 **不动** 刚闭邻面与明示跳过项。

---

## 1. 目标

成功标准：member+（既有会话鉴权）可用 CLI **1.79.0** 做 Project **repo list / show / add / update / remove**；api_client 有对应 helpers；复用既有 `/api/projects/{id}/repos` CRUD；语义对齐既有 BE（`name`/`url` 必填于 create；`main_branch` 默认 `main`；update 部分字段；delete 成功消息）；**不**改 E79–E94 邻面主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E96；**不做** `/api/repositories/*` 真 Git 操作、**不做** `requirement-repos`。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `GET /api/projects/{project_id}/repos` → `data: RepoConfig[]`  
  - `POST /api/projects/{project_id}/repos` body `{ "name", "url", "main_branch"?, "project_id" }` → `data: RepoConfig`  
  - `GET /api/projects/{project_id}/repos/{repo_id}` → `data: RepoConfig`  
  - `PUT /api/projects/{project_id}/repos/{repo_id}` body 可选 `{ "name"?, "url"?, "main_branch"? }`  
  - `DELETE /api/projects/{project_id}/repos/{repo_id}`  
- 鉴权：沿用 `project_router` 挂载级 `authenticate`；非法/缺资源既有错误语义不变  
- **不**本轮改 RepoConfig 模型 / FE 组件 / workspace ACL 加厚；**不**做 requirement-repos；**不**做 `/api/repositories` git clone/commit/pr  
- **不**改 board-move / initiative-projects / reactions / display-prefs / saved-views / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`project.ts` helpers + 项目详情仓库 UI 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.79.0**

- **Q2a** 命令形状（挂既有 `project` 下子组，与 `milestone`/`health`/`lead`/`member` 同构）：  
  - `opentask project repo list PROJECT [--json]`  
  - `opentask project repo show PROJECT REPO_ID [--json]`  
  - `opentask project repo add PROJECT --name NAME --url URL [--main-branch BRANCH] [--json]`  
  - `opentask project repo update PROJECT REPO_ID [--name NAME] [--url URL] [--main-branch BRANCH] [--json]`  
  - `opentask project repo remove PROJECT REPO_ID [--json]`（别名 `rm` 可选）  
  - 备选 Q2b 顶层 `repo` 组（不选——缺 project 上下文）  
  - 备选 Q2c 仅 list+add（不选——半截，缺 update/remove）  
- **Q3a** 语义对齐 BE：api_client  
  - `list_project_repos(project_id)` → **GET** `/api/projects/{id}/repos`  
  - `get_project_repo(project_id, repo_id)` → **GET** `…/repos/{repo_id}`  
  - `create_project_repo(project_id, *, name, url, main_branch="main")` → **POST** + body（含 `project_id` 以对齐既有 schema/测试）  
  - `update_project_repo(project_id, repo_id, **fields)` → **PUT** + 仅提供字段  
  - `delete_project_repo(project_id, repo_id)` → **DELETE**  
  - 失败透传 BE 401/403/404/422/…  
- **Q4a** human：`list`/`show` 薄表 id / name / url / main_branch；`add`/`update`/`remove` 成功薄回显；**不**改 `project show` 默认嵌入大块（可选后薄刀一行 Repos 摘要，本轮不做）  
- **Q5a** pins → **1.79.0**；历史 epic 断言级联  
- **不**改 `issue reaction|comment-reaction|link-branch|link-pr|vcs-links` / `display-prefs` / `view …` / `issue board-move` / initiative projects / CF / favorite-reorder / tag-group / label / project health / cycle / watchers / milestone / lead

### D · 安全 / 邻面 / no-emit

- 无新 alembic / webhook / formula emit  
- 不触 bulk `project_id`、watching filter、Initiative health  
- 不引入 token/密码写入 RepoConfig（本轮仅 name/url/main_branch；凭证面另弧）  
- 本地 only；不 push；不自开 E96

---

## 2. 数据 / 权限约束

| 项 | 约束 |
|----|------|
| 资源 | `RepoConfig`：`id:int`，`project_id:str`，`name:str`，`url:str`，`main_branch:str`（默认 `main`），`created_at`/`updated_at` |
| Create | `name`+`url` 必填；`main_branch` 缺省 `main`；body 带 `project_id`（与 path 一致，对齐既有测试） |
| Update | 全字段可选；至少提供一个变更字段（CLI 本地校验） |
| Delete | 按 `repo_id`；成功即删（既有语义） |
| Auth | 会话 Bearer；`project_router` 级 `authenticate`；本轮 **不**加厚 workspace/member ACL |
| 跨面 | **不**写 `requirement-repos`；**不**调用 `/api/repositories/{id}/git/*` |

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE project repos CRUD 行为不变；CLI 透传 |
| B | CLI **1.79.0** `project repo list\|show\|add\|update\|remove` 绿；缺必填本地失败；失败透传 |
| C | api_client 五 helpers 接线绿；pins 级联 1.79.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E79–E94 邻面主语义；无新 webhook/表/alembic；formula no-emit；无 initiative `/health`；无 bulk `project_id`；无 `project list --watching` BE |
| 门禁 | BE 定向（既有 `TestRepoConfigCRUD` 可回归 + e95 spy）；CLI 定向 e95；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E96 |

---

## 4. ADR（Yuri 已确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Project Repos CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用既有 project repos CRUD |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.79.0**；`project repo list\|show\|add\|update\|remove` |
| D5 | 语义 = 既有 BE；human 薄表 id/name/url/main_branch |
| D6 | 守 E40 D2/D7；不改 E63–E94 邻面主语义；不 push；不自开 E96；**不做** Initiative health/甘特/Push/门户 / bulk project_id / watching filter / requirement-repos / 真 Git ops |

---

## 5. 开放问题（Yuri 已一键全收建议默认）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有五端点；备选 Q1b 另开 `/api/cli/project-repos/...`（不选） |
| Q2 | CLI 命令挂载？ | **Q2a** `project repo list\|show\|add\|update\|remove`；备选 Q2b 顶层 `repo`（不选）；备选 Q2c 仅 list+add（不选——半截） |
| Q3 | create body 是否带 `project_id`？ | **Q3a** 是（对齐既有 schema/测试，path 已有 id）；备选 Q3b 仅 path（不选——与现测不一致） |
| Q4 | human 输出深度？ | **Q4a** list/show 薄表 + `--json` 全量；**不**改 `project show` 默认；备选 Q4b show 嵌入 Repos 列（后薄刀） |
| Q5 | VERSION？ | **Q5a** pins **1.79.0**；备选 Q5b 不动版本（不选） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE；备选 Q6b 改 FE（不选） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（已拍板）+ plan  
2. CLI api_client：五 project-repo helpers → GET/POST/PUT/DELETE（TDD）  
3. CLI 1.79.0：`project repo` 子组；注册到 `project_cli`  
4. pins 级联 1.79.0  
5. BE spy：无新路由/alembic；repos markers；邻面 marker（含 E94 reactions / E93 display-prefs …）；formula no-emit；**无**新 initiative `/health`；**无** bulk `project_id`  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `project repo list`：空 → []；有配置 → id/name/url/main_branch  
- `add --name --url` 后再 list/show 可见；`update` 改字段可见；`remove` 后再 list 消失  
- 缺 `--name`/`--url` → CLI 侧失败（不打 BE）  
- `update` 无任何变更 flag → CLI 侧失败  
- api_client helpers：正确 method + path；POST body 含 name/url/main_branch/project_id；PUT 仅提供字段  
- CLI pins 1.79.0；命令 json/human  
- spy：未改 reactions / display-prefs / view write / board-move / initiative projects / CF reorder / favorite reorder / tag-group / label set/multi / project health / cycle / project-watchers / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic；无 requirement-repos CLI；无 `/api/repositories/*/git/*`  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E96+；若改选可替换本设计）

1. **Activity Push** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件 / 递归孙项 / Bulk 多指派 / 深拷贝 / 模板 stubs** — prefer skip。  
6. **CSV start_date / depth≥2 / 评论版本史 / G-then-X / 复制附件 / Issue merge / purge / archived_at** — 后置或另弧。  
7. **Project 私有 ACL** — 另大弧。  
8. **bulk_update project_id + integrity** — 明示跳过本轮。  
9. **读路径 orphan milestone lazy-heal（Q4b）** — 后置。  
10. **`project list --watching` BE 过滤** — 明示跳过本轮。  
11. **Initiative health 独立 CLI / 自动健康 AI** — 明示跳过 / 另弧。  
12. **再开 E79–E94 邻面** — 刚闭。  
13. **Activity mark-read CLI** — BE/FE 齐、CLI 洞但过薄（个人水位）。  
14. **Issue comment update CLI** — 真洞；「编辑加厚」另弧，可后薄刀。  
15. **`form regenerate-token` CLI 命令** — api_client 已有；过薄。  
16. **Issue VCS unlink CLI** — api_client 已有 `delete_issue_vcs_link`；可后薄刀。  
17. **`/api/repositories` 真 Git clone/commit/PR** — 过厚；属 E11 深弧，非本 mid。  
18. **`requirement-repos` CLI** — PGE/遗留关联；勿默认。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.79.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E94-S1` @ `315d459deec59242802530cd46c9226889e2b2c6`  
- 分支：`sprint/E95-S1`  
- 入库设计：`docs/superpowers/specs/2026-11-05-e95-project-repos-cli-mid-design.md`  
- 拟 plan：`docs/superpowers/plans/2026-11-05-e95-project-repos-cli-mid-plan.md`  
- 拟 acceptance：`docs/superpowers/acceptances/2026-11-05-e95-project-repos-cli-mid-acceptance.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E96**

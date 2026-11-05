# E96 Design：Access Token CLI mid · CLI 1.80.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E96  
基线拟：`sprint/E95-S1` @ `2809068`（全文 `2809068aec94b62ad444eb1fe57612745b9b8ab1`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E96-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**大软不自开 E97**。  
入库：`docs/superpowers/specs/2026-11-05-e96-access-token-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

> 注：`docs/product/PROJECT.md` 在本 tip **不存在**。本设计依据：
> 1. E90–E95 design/acceptance 附录 runners-up（硬排除 + 扫描洞）；
> 2. tip @ `2809068` 代码扫描（BE/FE/CLI 对照）；
> 3. 仓库内 roadmap：`docs/superpowers/roadmaps/2026-10-31-opentask-orca-integration.md`（D9 复用 `access_token` / API Key Bearer）、`docs/superpowers/roadmaps/2026-10-31-opentask-public-release.md`（API Key 凭据面）、`docs/superpowers/roadmaps/2026-11-04-opentask-git-pr.md`（CLI/Agent 同契约；已闭 E11 VCS 主弧）；
> 4. 记忆中的 Linear 对齐 PRD canvas（`canvas_id` `656f4217-cbf0-48a3-9edb-168b4a36cbee`）——本轮**未重新打开 canvas 全文**；E95 同口径以 runners-up + 代码扫描为主。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E95 连续闭合 … → Issue Reactions CLI mid（E94 · 1.78.0）→ Project Repos CLI mid（E95 · 1.79.0）。

E95 附录 runners-up（硬排除）+ tip 扫描 @ `2809068`：

1. **Activity Push** — 仍 **勿默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b** — **rotate off**  
5. **表单公开附件 / 递归孙项 / Bulk 多指派 / 深拷贝 / 模板 stubs** — **prefer skip**  
6. **CSV start_date / depth≥2 / 评论版本史 / G-then-X / 复制附件 / Issue merge / purge / archived_at** — **后置或另弧**  
7. **Project 私有 ACL** — **另大弧**  
8. **bulk_update `project_id` + integrity** — **明示跳过**  
9. **读路径 orphan milestone lazy-heal（Q4b）** — **后置**  
10. **`project list --watching` BE 过滤** — **明示跳过**  
11. **Initiative health 独立 CLI / 自动健康 AI** — **明示跳过 / 另弧**  
12. **再开 E79–E95 邻面** — **刚闭，勿默认**  
13. **Activity mark-read CLI** — BE/FE 齐、CLI 洞但 **过薄**（个人水位）  
14. **Issue comment update CLI** — 真洞；「编辑加厚」另弧，可后薄刀  
15. **`form regenerate-token` CLI 命令** — api_client 已有；**过薄**  
16. **Issue VCS unlink CLI** — api_client 已有 `delete_issue_vcs_link`；**可后薄刀**（E95 已标；本 tip CLI 已有 `link-branch`/`link-pr`/`vcs-links`，仅缺 unlink/update）  
17. **`/api/repositories` 真 Git clone/commit/PR** — **过厚**；E11 深弧  
18. **`requirement-repos` CLI** — PGE/遗留；**勿默认**  
19. **（扫描 · 本轮主推）Access Token CLI** — BE `GET/POST /api/access-tokens` + `DELETE /api/access-tokens/{id}` **齐**（`AccessTokenService`：`vk_` 前缀、默认 365d、创建仅一次返回原文）；FE Profile「Access Tokens」页 + `accessTokenApi` + store **齐**；CLI **仅** `config set-access-token`（粘贴既有明文）——**无** list/create/revoke 管理命令、api_client **零** `/api/access-tokens` helpers——agent 无法脚本「签发 / 枚举 / 吊销」个人 API Key（`vk_…`），必须回 Web UI；实证为 Project Repos 闭合后剩余最清晰的 **BE/FE 齐、CLI 洞** mid（复用既有路由；无新表；单 sprint；对齐 Orca/合约鉴权与 Linear 式 personal API key 心智；**不**做 OAuth2 client CRUD / SSO）

代码实证 @ `2809068`：

| 面 | 现状 |
|----|------|
| BE Access Tokens | `POST /api/access-tokens` body `{name, description?}` → 含一次性 `token`；`GET /api/access-tokens` → 列表（无原文，含 `token_prefix`/`expires_at`/`last_used_at`）；`DELETE /api/access-tokens/{token_id}`；`authenticate`；`TOKEN_PREFIX=vk_`；`DEFAULT_EXPIRE_DAYS=365` |
| FE | `frontend/src/service/api/access-token.ts` + `views/profile/access-tokens/index.vue` + store **齐**（创建弹窗展示一次明文） |
| CLI | `config set-access-token <token>` **仅粘贴**；**无** `access-token list\|create\|revoke`；api_client **零** manage helpers |
| 邻面 | Issue VCS（E11/E95 邻）已有 link/list；OAuth2 provider 另弧（`oauth_access_tokens` ≠ 本表 `access_tokens`） |
| 明示跳过 | Push / 门户 / 甘特 / Initiative health / bulk `project_id` / `project list --watching` |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Access Token CLI mid**：CLI **1.80.0** 新顶层组 `access-token list\|create\|revoke`（`rm` 别名）；api_client 三 helpers → 复用既有 GET/POST/DELETE；create 人类/JSON **仅此一次**打印原文；可选 `--save` 写入本地 `config.access_token`（**不**默认覆盖）；**无**新表/webhook/路由；FE 已齐 → 零产品 FE | **薄→中薄**；闭合「BE/FE 齐、CLI 洞」；单 sprint；agent 价值清晰（脚本签发/吊销 API Key，闭环 `config set-access-token`）；不触明示跳过面 |
| B | Issue VCS unlink + update（+ 可选 `issue vcs` 重组） | 真洞但 E95 已标 unlink 为薄刀；list/link-branch/link-pr 已有；面偏补丁；可 runners-up |
| C | `issue comment update` CLI | 真洞；「评论编辑加厚」另弧；半截于版本史 |
| D | `activity mark-read` / `form regenerate-token` | 过薄 |
| E | bulk_update `project_id` + integrity / `project list --watching` | 明示跳过；需 BE |
| F | Initiative health / 甘特 / Activity Push / 门户 / Q2b / … | 明示跳过 / prefer skip |
| G | 再开 project-repos / reactions / display-prefs / view write / board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |
| H | OAuth2 client CRUD / SSO / 真 GitHub App | 过厚或另弧 |

**建议拍板：A（Access Token CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E95 project-repos / E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.80.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成 Initiative health / bulk project_id / watching filter / OAuth2 / 真 Git；**不**改 `config set-access-token` 既有语义（可文档交叉引用）。

### Why this Epic now（一句话）

E86–E95 连续闭合「BE/FE 齐、CLI 洞」关联/reorder/看板/Saved View/Display/Reactions/Project Repos 后，**个人 Access Token（`vk_` API Key）** BE/FE（Profile 页）早已齐而 CLI **只有粘贴、没有签发/枚举/吊销**——agent 无法脚本完成「创建 →（可选）本地保存 → 吊销轮换」闭环；用薄刀一次闭合该洞，对齐 Orca/合约鉴权与 Linear 式 personal API key，且 **不动** 刚闭邻面与明示跳过项。

---

## 1. 目标

成功标准：已登录会话（既有 JWT / 已配置 token）可用 CLI **1.80.0** 做 Access Token **list / create / revoke**；api_client 有对应 helpers；复用既有 `/api/access-tokens` CRUD；语义对齐既有 BE（create 必填 `name`、可选 `description`；列表**永不**回原文；create 响应含一次性 `token`；delete 按 id + 当前用户所有权）；**不**改 E79–E95 邻面主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E97；**不做** OAuth2 client 管理、**不做** token 续期/改名 PATCH（BE 无此端点）。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `GET /api/access-tokens` → `data: AccessTokenResponse[]`（无 `token` 字段）  
  - `POST /api/access-tokens` body `{ "name": str, "description"?: str }` → `data: AccessTokenCreateResponse`（含一次性 `token`）  
  - `DELETE /api/access-tokens/{token_id}` → 成功消息；404「Token 不存在」  
- 鉴权：沿用路由级 `authenticate`；仅操作**当前用户**自己的 token  
- **不**本轮改 `AccessToken` 模型 / 过期策略 / `vk_` 前缀 / FE Profile 页；**不**做 OAuth2 表；**不**做 refresh 轮换  
- **不**改 project-repos / reactions / display-prefs / saved-views / board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template / VCS 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`access-token.ts` + Profile 页已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI（主交付）

- **Q2a** 命令形状（**新**顶层组 `access-token`；与 `config set-access-token` 并存、职责分离）：  
  - `opentask access-token list [--json]`  
  - `opentask access-token create --name NAME [--description TEXT] [--save] [--json]`  
  - `opentask access-token revoke TOKEN_ID [--json]`（别名 `rm`）  
  - 备选 Q2b 短名 `token …`（不选——与 JWT/`config` token 歧义）  
  - 备选 Q2c 挂 `config access-token …`（不选——污染 config；管理面应独立）  
  - 备选 Q2d 仅 create（不选——半截，缺 list/revoke）  
- **Q3a** 语义对齐 BE：api_client  
  - `list_access_tokens()` → `GET /api/access-tokens`  
  - `create_access_token(name, description=None)` → `POST /api/access-tokens` body **snake 或与 FE 一致的 `{name, description?}`**（本端点 schema 即 snake `name`/`description`）  
  - `delete_access_token(token_id)` → `DELETE /api/access-tokens/{token_id}`  
  - create 成功：`--json` 输出完整 `data`（含 `token`）；human 模式**醒目打印一次**完整 `token`，并提示「仅此一次可见」  
  - `--save`（可选）：将本次 `token` 写入本地 `config.access_token`（覆盖需确认或要求显式 `--save`；**默认不写**，避免静默替换生产钥）  
  - **不**新增 GET-by-id（BE 无此端点）；**不**做 update/rename  
- **Q4a** human：`list` 薄表 id / name / token_prefix / expires_at / last_used_at；`create`/`revoke` 薄回显；**不**改 `config set-access-token` / `config show` 默认字段语义（可在 create 成功文案中交叉提示 `config set-access-token`）  
- **Q5a** pins → **1.80.0**；历史 epic 断言级联（`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` + 旧 epic 测试中的版本字面量）

### D · 安全 / 邻面 / no-emit

- 本地 only；不 push；不自开 E97  
- create 输出含密钥：测试用 mock；文档/acceptance 提醒勿把真实 `vk_` 写进仓库日志  
- 不改 E79–E95 邻面；无新 alembic；无新 webhook；formula no-emit  
- **不做** Initiative health / 甘特 / Push / 门户 / bulk project_id / watching filter / requirement-repos / 真 Git / OAuth2 client CRUD

---

## 2. 验收标准（Acceptance 摘要）

| # | 标准 |
|---|------|
| A1 | member（已鉴权会话）可用 `access-token list` 看到自己的 token 元数据（无原文） |
| A2 | `access-token create --name …` 返回一次性完整 `vk_…`；再次 list **看不到**原文，仅见 `token_prefix` |
| A3 | `access-token revoke <id>` 后 list 不再包含该 id；他人/不存在 id → 既有 404 语义 |
| A4 | `--save` 仅在显式传入时写入 `config.access_token`；默认不改本地配置 |
| A5 | api_client 三 helpers 正确 method + path；create body 含 name（+ optional description） |
| A6 | CLI pins **1.80.0**；命令 json/human |
| A7 | spy：未改 project-repos / reactions / display-prefs / view write / board-move / initiative projects / CF reorder / favorite / tag-group / label set/multi / project health / cycle / project-watchers / issue-template / milestone / issue_project_move / E79 roster / VCS link 主表面；无新 webhook；formula no-emit；无新 alembic；无 OAuth2 client CLI |
| A8 | FE 无回归；build ok；`f`+`r` 仍在 |

拟 acceptance 路径：`docs/superpowers/acceptances/2026-11-05-e96-access-token-cli-mid-acceptance.md`  
拟 plan 路径：`docs/superpowers/plans/2026-11-05-e96-access-token-cli-mid-plan.md`

---

## 3. ADR（Yuri 已确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Access Token CLI mid**（方案 A） |
| D2 | **无新 BE 路由 / 无新表 / 无 alembic**；复用 `/api/access-tokens` |
| D3 | CLI 顶层组 `access-token list\|create\|revoke`（`rm`）；与 `config set-access-token` 并存 |
| D4 | create 原文仅一次可见；`--save` 显式才写本地 config |
| D5 | pins **1.80.0**；历史 epic 版本断言级联 |
| D6 | 守 E40 D2/D7；不改 E63–E95 邻面主语义；不 push；不自开 E97；**不做** Initiative health/甘特/Push/门户 / bulk project_id / watching filter / OAuth2 client / 真 Git |

---

## 4. 开放问题（Yuri 已一键全收建议默认）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有三端点；备选 Q1b 另开 `/api/cli/access-tokens/...`（不选） |
| Q2 | CLI 命令挂载？ | **Q2a** 新顶层组 `access-token list\|create\|revoke`；备选 Q2b 短名 `token`（不选——歧义）；备选 Q2c 挂 `config` 下（不选）；备选 Q2d 仅 create（不选——半截） |
| Q3 | create 后是否自动写入本地 config？ | **Q3a** **仅** `--save` 显式写入 `config.access_token`；备选 Q3b 默认自动覆盖（不选——危险）；备选 Q3c 永远不写、只提示 `config set-access-token`（可接受，但 agent 闭环略差——推荐保留 opt-in `--save`） |
| Q4 | human 输出深度？ | **Q4a** list 薄表 id/name/prefix/expires/last_used + `--json` 全量；create 醒目打印一次 token；备选 Q4b list 省略 expires（不选——运维价值） |
| Q5 | VERSION？ | **Q5a** pins **1.80.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE；备选 Q6b 改 FE 文案/封装（不选——非本轮必须） |

---

## 5. Out of scope

- Customer 门户、Initiative 甘特、Activity Push、Recurrence Q2b  
- 表单公开附件、递归孙项、Bulk/Insights 多指派、深拷贝、模板 stubs  
- bulk_update `project_id`、`project list --watching`、Initiative health 独立 CLI  
- Issue comment update / 评论版本史加厚、Activity mark-read、form regenerate-token（薄刀另列）  
- Issue VCS unlink/update 重组（runners-up；非本轮）  
- OAuth2 client CRUD / SSO / 真 GitHub App / `/api/repositories` 真 Git  
- `requirement-repos`、AccessToken PATCH/rename/续期（BE 无端点）  
- **再改** E95 project-repos / E94 reactions / E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89–E79 邻面  
- 自开 E97；push / 开 PR

---

## 6. 实现约束（拍板后给大软）

| 项 | 约束 |
|----|------|
| 流程 | design **经 Yuri 拍板（本文件）** → plan → TDD → verify → acceptance；**本 commit 仅 design，尚未写码** |
| 分支 | `sprint/E96-S1`（自 E95 tip `2809068`） |
| 门禁 | BE full + directed spy；CLI full + directed；FE vitest + build；守 `f`+`r`；7377/9527 不强制停 |
| 本地 | only；不 push；不自开 E97 |
| 密钥 | 测试 mock `vk_`；禁止把真实 token 写入 acceptance / git |

---

## 附录 · runners-up（供 E97+；本 Epic 已拍板 Scheme A，下列仅供后续）

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
12. **再开 E79–E95 邻面** — 刚闭。  
13. **Activity mark-read CLI** — 过薄。  
14. **Issue comment update CLI** — 真洞；可后薄刀。  
15. **`form regenerate-token` CLI 命令** — 过薄。  
16. **Issue VCS unlink + update（可选 `issue vcs` 重组）** — 真洞但偏补丁；E95 后自然候选，本轮次于 Access Token。  
17. **`/api/repositories` 真 Git** — 过厚。  
18. **`requirement-repos` CLI** — 勿默认。  
19. **OAuth2 client CRUD CLI** — 另弧（≠ `access_tokens` 个人钥）。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.80.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E95-S1` @ `2809068aec94b62ad444eb1fe57612745b9b8ab1`  
- 分支：`sprint/E96-S1`  
- 入库设计：`docs/superpowers/specs/2026-11-05-e96-access-token-cli-mid-design.md`  
- 拟 plan：`docs/superpowers/plans/2026-11-05-e96-access-token-cli-mid-plan.md`  
- 拟 acceptance：`docs/superpowers/acceptances/2026-11-05-e96-access-token-cli-mid-acceptance.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E97**

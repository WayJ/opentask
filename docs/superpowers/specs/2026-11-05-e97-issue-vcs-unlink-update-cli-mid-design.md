# E97 Design：Issue VCS unlink + update CLI mid · CLI 1.81.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E97  
基线拟：`sprint/E96-S1` @ `d864818`（全文 `d864818d77c1c013bd48c69f011ed7a9b132a6b7`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E97-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**大软不自开 E98**。  
入库：`docs/superpowers/specs/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

> 注：`docs/product/PROJECT.md` 在本 tip **不存在**。本设计依据：
> 1. E90–E96 design/acceptance 附录 runners-up（硬排除 + 扫描洞）；
> 2. tip @ `d864818` 代码扫描（BE/FE/CLI 对照）；
> 3. 仓库内 roadmap：`docs/superpowers/roadmaps/2026-11-04-opentask-git-pr.md`（E11 Git/PR 主弧已闭；CLI/Agent 同契约仍列缺口）；
> 4. Linear 对齐 PRD canvas（`canvas_id` `656f4217-cbf0-48a3-9edb-168b4a36cbee`）——本轮**未重新打开 canvas 全文**；与 E95/E96 同口径以 runners-up + 代码扫描为主。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E96 连续闭合 … → Project Repos CLI mid（E95 · 1.79.0）→ Access Token CLI mid（E96 · 1.80.0）。

E96 附录 runners-up（硬排除）+ tip 扫描 @ `d864818`：

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
12. **再开 E79–E96 邻面** — **刚闭，勿默认**（含 access-token / project-repos / reactions / display-prefs / view write / board-move / initiative-projects）  
13. **Activity mark-read CLI** — BE/FE 齐、CLI 洞但 **过薄**（个人水位）  
14. **Issue comment update CLI** — 真洞；「编辑加厚」另弧，可后薄刀  
15. **`form regenerate-token` CLI 命令** — api_client 已有；**过薄**  
16. **（扫描 · 本轮主推）Issue VCS unlink + update CLI** — BE `DELETE /api/issues/{id}/vcs/links/{link_id}` + `PATCH …/vcs/links/{link_id}` **齐**；FE `deleteIssueVcsLink` + `patchIssueVcsLink` **齐**；CLI 已有 `branch-name` / `link-branch` / `link-pr` / `vcs-links`；api_client 已有 `delete_issue_vcs_link`，**缺** `update_issue_vcs_link`；CLI **零** unlink/update 命令——agent 可挂 branch/PR，**无法**脚本解除关联或改 PR status/title/url（E11 roadmap「CLI/Agent 同契约」半截）——Access Token 闭合后剩余最清晰的 **BE/FE 齐、CLI 半截** mid  
17. **`/api/repositories` 真 Git clone/commit/PR** — **过厚**；E11 深弧勿复活  
18. **`requirement-repos` CLI** — PGE/遗留；**勿默认**  
19. **OAuth2 client CRUD CLI** — 另弧（≠ E96 个人 `access_tokens`）  
20. **Workspace git status hooks CLI 旗标** — FE/WS 字段已齐；`workspace update` CLI 未暴露；可后薄刀，非本轮主推

代码实证 @ `d864818`：

| 面 | 现状 |
|----|------|
| BE Issue VCS | `GET …/vcs/branch-name`；`GET/POST …/vcs/links`；`DELETE/PATCH …/vcs/links/{link_id}`；create/update body **camelCase**（`branchName`/`prUrl`/`externalId`/`repoConfigId`）；`require_writer` 于写路径；挂 `APIRouter(prefix="/api/issues")` + workspace context |
| FE | `frontend/src/service/api/issue-vcs.ts` 五 helpers + `IssuePrPanel.vue` **齐**（含 delete/patch） |
| CLI | `issue branch-name` / `link-branch` / `link-pr` / `vcs-links` **有**；**无** unlink / update；api_client **有** delete、**无** patch helper |
| 邻面 | E95 Project RepoConfig（挂 Project）已闭；本洞是挂 **Issue** 的 `issue_vcs_links` 写闭环 |
| 明示跳过 | Push / 门户 / 甘特 / Initiative health / bulk `project_id` / `project list --watching` |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue VCS unlink + update CLI mid**：CLI **1.81.0** 补 `issue unlink-vcs` + `issue update-vcs`（保留既有 list/link 命令名）；api_client 补 `update_issue_vcs_link` → PATCH；复用既有 DELETE；**无**新表/webhook/路由；FE 已齐 → 零产品 FE | **薄→中薄**；闭合 E11「CLI/Agent 同契约」半截；单 sprint；agent 价值清晰（脚本挂/改/卸 branch·PR）；不触明示跳过面 |
| B | `issue comment update` CLI | 真洞；「评论版本史/编辑加厚」另弧；半截于版本史；本轮次于 VCS 闭环 |
| C | `activity mark-read` / `form regenerate-token` | 过薄 |
| D | `workspace update` 补 git status hooks 旗标 | 真洞但偏设置薄刀；可与 VCS 后置同列 runners-up |
| E | bulk_update `project_id` + integrity / `project list --watching` | 明示跳过；需 BE |
| F | Initiative health / 甘特 / Activity Push / 门户 / Q2b / … | 明示跳过 / prefer skip |
| G | 再开 access-token / project-repos / reactions / display-prefs / view write / board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |
| H | OAuth2 client CRUD / SSO / 真 GitHub App / `/api/repositories` 真 Git | 过厚或另弧 |

**已拍板：A（Issue VCS unlink + update CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E96 access-token / E95 project-repos / E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89–E79 邻面；CLI **1.81.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成 Initiative health / bulk project_id / watching filter / requirement-repos / 真 Git / OAuth2；**不**改既有 `link-branch`/`link-pr`/`vcs-links`/`branch-name` 默认语义（可文档交叉引用）；**不**强制重组为 `issue vcs` 子组（备选可后置）。

### Why this Epic now（一句话）

E95 补齐 Project↔Repo 配置、E96 补齐个人 API Key 管理后，**Issue VCS links** 仍是 agent 最高频的 Linear Git/PR 面之一——CLI 已能 suggest/list/link，却不能 unlink/update；用薄刀一次闭合 DELETE+PATCH，兑现 E11「CLI/Agent 同契约」，且 **不动** 刚闭邻面与明示跳过项。

---

## 1. 目标

成功标准：member+（既有会话鉴权 / writer）可用 CLI **1.81.0** 对 Issue VCS link 做 **unlink** 与 **update**；api_client 有对应 PATCH helper（DELETE 已有则接线 CLI）；复用既有 `/api/issues/{id}/vcs/links/{link_id}`；语义对齐既有 BE/FE（PATCH 可选 camelCase 字段；DELETE 成功消息；跨租户/缺资源既有错误）；**保留**既有 `branch-name`/`link-branch`/`link-pr`/`vcs-links`；**不**改 E79–E96 邻面主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E98；**不做**真 GitHub App / `/api/repositories` 真 Git / `requirement-repos`。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `DELETE /api/issues/{issue_id}/vcs/links/{link_id}` → `data: {id}`，message「已解除关联」  
  - `PATCH /api/issues/{issue_id}/vcs/links/{link_id}` body 可选  
    `{ "branchName"?, "prUrl"?, "provider"?, "externalId"?, "status"?, "title"? }` → `data: IssueVcsLink`  
- 鉴权：沿用 `require_workspace_context` + 写路径 `require_writer`；非法/缺资源既有错误语义不变  
- **不**本轮改 `issue_vcs_links` 模型 / webhook ingest / status hooks 默认策略 / FE `IssuePrPanel`；**不**做 requirement-repos；**不**做 `/api/repositories` git clone/commit/pr  
- **不**改 access-token / project-repos / reactions / display-prefs / saved-views / board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`issue-vcs.ts` delete/patch + `IssuePrPanel.vue` 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI（主交付）

- **Q2a** 命令形状（**扁平加命令**，对齐既有 `link-branch`/`link-pr`/`vcs-links` 命名；**不**本轮强制迁入 `issue vcs` 子组）：  
  - `opentask issue unlink-vcs ISSUE_REF LINK_ID [--json]`（别名 `vcs-unlink`）  
  - `opentask issue update-vcs ISSUE_REF LINK_ID [--status STATUS] [--title TEXT] [--pr-url URL] [--branch-name NAME] [--provider PROVIDER] [--external-id ID] [--json]`  
  - 既有保留：`issue branch-name` / `link-branch` / `link-pr` / `vcs-links`（语义不变）  
  - 备选 Q2b 新子组 `issue vcs list|link-branch|link-pr|unlink|update|branch-name` 并保留旧名别名（可后置；本轮不强制，以免扩散 diff）  
  - 备选 Q2c 仅 unlink（不选——半截，PATCH 面仍断）  
  - 备选 Q2d 顶层 `vcs …`（不选——缺 issue 上下文）  
- **Q3a** 语义对齐 BE/FE：api_client  
  - 既有 `delete_issue_vcs_link(issue_id, link_id)` → `DELETE …/vcs/links/{link_id}`（CLI 接线）  
  - **新增** `update_issue_vcs_link(issue_id, link_id, **kwargs)` → `PATCH …/vcs/links/{link_id}`；kwargs 发 **camelCase**（`branchName`/`prUrl`/`externalId`/…），对齐 BE schema 与 FE `patchIssueVcsLink` / 既有 `create_issue_vcs_link`  
  - `ISSUE_REF` 经既有 `_resolve_issue_id`（支持 issue_code / uuid）  
  - update：**至少提供一个**可变字段，否则 CLI 侧非零退出（避免空 PATCH）；`--status` 取值对齐既有 link-pr 习惯：`open|draft|merged|closed|unknown`（透传 BE，不在 CLI 硬拦未知值亦可，但文档示例用上述集合）  
  - **不**本轮改 create 路径字段；**不**新增 webhook 触发 CLI  
- **Q4a** human：`unlink-vcs` / `update-vcs` 成功薄回显 id/kind/status/url-or-branch；`vcs-links` 输出可保持现状（可选后薄刀对齐列）；**不**改 `issue show` 默认嵌入大块 VCS（后薄刀）  
- **Q5a** pins → **1.81.0**；历史 epic 断言级联（`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` + 旧 epic 测试中的版本字面量）

### D · 安全 / 邻面 / no-emit

- 本地 only；不 push；不自开 E98  
- VCS link 不含 access token 原文；测试勿写入真实私有仓库凭证；PR URL 按既有 ACL  
- 不改 E79–E96 邻面；无新 alembic；无新 webhook；formula no-emit  
- **不做** Initiative health / 甘特 / Push / 门户 / bulk project_id / watching filter / requirement-repos / 真 Git / OAuth2 client CRUD / comment 版本史加厚

---

## 2. 验收标准（Acceptance 摘要）

| # | 标准 |
|---|------|
| A1 | writer 可用 `issue unlink-vcs ISSUE LINK_ID` 解除关联；随后 `vcs-links` 不再含该 id |
| A2 | writer 可用 `issue update-vcs ISSUE LINK_ID --status merged [--title …] [--pr-url …]` 更新字段；`vcs-links`/`--json` 反映变更 |
| A3 | 空 update（无任何字段 flag）→ CLI 非零 + 清晰错误；缺 issue/link → 既有 API 错误语义 |
| A4 | viewer/非 writer 写路径 → 既有 403/权限语义（不本轮放宽） |
| A5 | api_client：`delete_issue_vcs_link` 被 CLI 使用；**新增** `update_issue_vcs_link` → PATCH + camelCase body |
| A6 | 既有 `branch-name`/`link-branch`/`link-pr`/`vcs-links` 回归绿；CLI pins **1.81.0** |
| A7 | spy：未改 access-token / project-repos / reactions / display-prefs / view write / board-move / initiative projects / CF reorder / favorite / tag-group / label set/multi / project health / cycle / project-watchers / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic；无 OAuth2 / 真 Git / requirement-repos |
| A8 | FE 无回归；build ok；`f`+`r` 仍在 |

拟 acceptance 路径：`docs/superpowers/acceptances/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-acceptance.md`  
拟 plan 路径：`docs/superpowers/plans/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-plan.md`

---

## 3. ADR（Yuri 已确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue VCS unlink + update CLI mid**（方案 A） |
| D2 | **无新 BE 路由 / 无新表 / 无 alembic**；复用 DELETE + PATCH `/api/issues/{id}/vcs/links/{link_id}` |
| D3 | CLI 扁平补 `unlink-vcs`（`vcs-unlink`）+ `update-vcs`；保留既有 list/link/branch-name 命令名 |
| D4 | api_client PATCH 发 **camelCase**，对齐 FE/BE；空 PATCH 由 CLI 拒绝 |
| D5 | pins **1.81.0**；历史 epic 版本断言级联 |
| D6 | 守 E40 D2/D7；不改 E63–E96 邻面主语义；不 push；不自开 E98；**不做** Initiative health/甘特/Push/门户 / bulk project_id / watching filter / OAuth2 client / 真 Git / requirement-repos |

---

## 4. 开放问题（Yuri 已一键全收建议默认）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有 DELETE/PATCH；备选 Q1b 另开 `/api/cli/issue-vcs/...`（不选） |
| Q2 | CLI 命令挂载？ | **Q2a** 扁平 `issue unlink-vcs` + `issue update-vcs`（保留旧命令）；备选 Q2b 新子组 `issue vcs …`+旧名别名（后置）；备选 Q2c 仅 unlink（不选——半截）；备选 Q2d 顶层 `vcs`（不选） |
| Q3 | PATCH body 字段命名？ | **Q3a** api_client 发 **camelCase**（对齐 BE/FE/既有 create）；备选 Q3b 改 snake 再在 client 映射（不选——与现 create 不一致） |
| Q4 | human 输出 / show 嵌入？ | **Q4a** unlink/update 薄回显 + `--json` 全量；**不**改 `issue show` 默认；备选 Q4b show 嵌入 VCS 列（后薄刀） |
| Q5 | VERSION？ | **Q5a** pins **1.81.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE；备选 Q6b 改 FE 文案/封装（不选——非本轮必须） |

---

## 5. Out of scope

- Customer 门户、Initiative 甘特、Activity Push、Recurrence Q2b  
- 表单公开附件、递归孙项、Bulk/Insights 多指派、深拷贝、模板 stubs  
- bulk_update `project_id`、`project list --watching`、Initiative health 独立 CLI  
- Issue comment update / 评论版本史加厚、Activity mark-read、form regenerate-token（薄刀另列）  
- Workspace git status hooks CLI 旗标（后薄刀）  
- OAuth2 client CRUD / SSO / 真 GitHub App / `/api/repositories` 真 Git  
- `requirement-repos`、强制重组全部 VCS 命令进 `issue vcs` 子组（Q2b 后置）  
- webhook ingest / status hooks 策略改写、自动开远程 PR  
- **再改** E96 access-token / E95 project-repos / E94 reactions / E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89–E79 邻面  
- 自开 E98；push / 开 PR

---

## 6. 实现约束（拍板后给大软）

| 项 | 约束 |
|----|------|
| 流程 | design **经 Yuri 拍板（本文件）** → plan → TDD → verify → acceptance；**本 commit 仅 design，尚未写码** |
| 分支 | `sprint/E97-S1`（自 E96 tip `d864818`） |
| 门禁 | BE full + directed spy；CLI full + directed；FE vitest + build；守 `f`+`r`；7377/9527 不强制停 |
| 本地 | only；不 push；不自开 E98 |
| 契约 | PATCH camelCase；空 update CLI 拒绝；不破坏既有 link/list 命令 |

---

## 附录 · runners-up（供 E98+；本 Epic 已拍板 Scheme A，下列仅供后续）

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
12. **再开 E79–E96 邻面** — 刚闭。  
13. **Activity mark-read CLI** — 过薄。  
14. **Issue comment update CLI** — 真洞；可后薄刀（版本史另弧）。  
15. **`form regenerate-token` CLI 命令** — 过薄。  
16. **Workspace git status hooks CLI 旗标** — FE/WS 已齐；`workspace update` 未暴露；后薄刀。  
17. **`issue vcs` 子组重组（Q2b）** — 本轮不强制；可后置别名迁入。  
18. **`/api/repositories` 真 Git** — 过厚。  
19. **`requirement-repos` CLI** — 勿默认。  
20. **OAuth2 client CRUD CLI** — 另弧（≠ E96 个人钥）。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.81.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E96-S1` @ `d864818d77c1c013bd48c69f011ed7a9b132a6b7`  
- 分支：`sprint/E97-S1`  
- 设计：`docs/superpowers/specs/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-design.md`  
- 拟 plan：`docs/superpowers/plans/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-plan.md`  
- 拟 acceptance：`docs/superpowers/acceptances/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-acceptance.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E98**；design 已拍板，等 plan/TDD

# E90 Design：Initiative Projects CLI mid · CLI 1.74.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E90  
基线拟：`sprint/E89-S1` @ `d8337ea`（全文 `d8337eae290d459d5639006c9a40cd6fd3fbfb45`；E89 design 基线 `dc4779c` ⊂ HEAD；E88 tip `d09142c` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E90-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E91**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e90-initiative-projects-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E90-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E89 连续闭合 … → Favorite Reorder CLI mid（E88 · 1.72.0）→ Custom Fields Reorder CLI mid（E89：`custom-field reorder` · 1.73.0）。

E89 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `d8337ea`：

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
12. **评论版本史 / 编辑加厚** — **另弧**  
13. **G-then-X** — **另弧**  
14. **复制附件/子树** — **过厚**  
15. **Issue merge** — **过厚**  
16. **Timed purge/hard-delete** — **后置**  
17. **`archived_at` dual-track** — **prefer skip**  
18. **Project 私有 ACL** — **另大弧**  
19. **bulk_update 支持 project_id + 同 integrity helper** — **可后薄刀**（`IssueBulkUpdate` tip 仍无 `project_id`；触 BE schema + E80 邻弧）  
20. **读路径 orphan milestone lazy-heal（Q4b）** — **后置**  
21. **`project list --watching` BE 过滤** — **后薄刀**（`list_projects` tip 无 `watching` Query；CLI `project list` 亦无 filter flag）  
22. **再开 CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **Initiative health CLI（独立 health get/set 弧）** — tip **无** 对称 `GET/POST /api/initiatives/{id}/health`；`to_response` 仅嵌套 `healthSummary`（关联项目聚合）— **不选为本轮主 Epic**（另扫）  
24. **自动健康评估 / AI 摘要** — **另弧**  
25. **（扫描）Display prefs CLI** — BE `GET/PUT /api/display-prefs/issue` + FE 已齐；E49 明示无 CLI 子命令 — agent 价值偏薄，可 runners-up  
26. **（扫描）Saved View write / favorite / save-as** — BE 齐；CLI 仅 `view list|show|use` — 真 mid 但面比「单资源关联」宽，runners-up  
27. **（扫描）Issue board/move** — BE `POST /api/issues/board/move` + FE 齐；CLI 零 — Kanban 位置薄洞，可 runners-up  
28. **（扫描）Initiative Projects CLI** — BE **`PUT /api/initiatives/{id}/projects`**（body `projectIds`）+ **`POST …/projects/{project_id}`** + **`DELETE …/projects/{project_id}`** **齐**；FE `fetchSetInitiativeProjects` **齐**（attach/detach FE 未单独封装，但 BE 可用）；CLI/api_client **仅** CRUD + relations（E65），**零** project set/attach/detach helpers — agent 无法脚本「把 Project 挂到 Initiative / 替换关联集」——实证为最清晰 mid 缺口（闭合 Linear Initiative↔Projects 脚本面；与 E86 set/multi、E88/E89 reorder「BE/FE 齐、CLI 洞」同构）

轮换离开刚闭弧：**CF reorder / favorite reorder / tag-group CLI / label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E89 CF reorder；本轮补的是 **Initiative↔Projects 关联脚本缺口**（BE/FE set 已齐，agent 无法用 CLI 维护关联）。

代码实证 @ `d8337ea`：

| 面 | 现状 |
|----|------|
| BE Initiatives projects | `PUT /api/initiatives/{id}/projects` body `{projectIds: string[]}`（**全集替换**，含 `[]` 清空；未知/跨 WS project → **400**）；`POST /{id}/projects/{project_id}` attach（幂等）；`DELETE /{id}/projects/{project_id}` detach；create/patch 亦可带 `projectIds`；`GET /{id}` 已 `include_projects=True`（含 `projectIds` + `projects[]` + 嵌套 `healthSummary`） |
| FE Initiatives | `fetchSetInitiativeProjects(id, projectIds)` → PUT **齐**；**无**独立 attach/detach FE helper（不阻塞 CLI 复用 BE） |
| CLI Initiative | `initiative list\|show\|create\|update\|delete` + `relations list` + `relation add\|remove`（E65）；api_client **无** `set_initiative_projects` / `attach_initiative_project` / `detach_initiative_project` — agent 无法脚本关联面 |
| Bulk project_id | `IssueBulkUpdate` **无** `project_id` — 仍薄刀/后置、触 BE |
| Project list watching | CLI/BE 仍无 watching 过滤 — 仍薄刀 |
| Linear 对齐 | agent 应能脚本「Initiative CRUD + 关联 Projects + relations」，与 Linear Initiatives 对齐 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Initiative Projects CLI mid**：CLI **1.74.0** `initiative projects set` + `initiative project attach\|detach`；api_client 三 helper；复用既有 PUT/POST/DELETE；**无**新表/webhook/路由；FE set 已齐 → 零产品 FE；`show` 已拿得到 projects（json）→ 人类表可薄补 Projects 列 | **薄→中薄**；闭合 Initiative↔Projects 脚本面；单 sprint；自然续「BE/FE 齐、CLI 洞」 |
| B | 仅文档说明用 FE 拖拽/设置 | 过薄；agent 仍断 |
| C | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service + E80 邻弧；任务标薄刀 |
| D | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| E | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| F | Display prefs / Saved View write / board-move | 真洞但价值或面宽次之（runners-up） |
| G | Initiative health 独立 CLI / 甘特 / Activity Push / 门户 / Q2b / … | 无对称 health 路由 / prefer skip / 勿默认 |
| H | 再开 CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Initiative Projects CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members / E65 relations 主语义（本轮只加 projects 关联，不改 relation 类型）；CLI **1.74.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成「Initiative health CLI」。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up；watching/bulk 需 BE） |
| Display prefs / Saved View write / board-move | runners-up（价值或面宽次之） |
| 再开 CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health 独立 CLI | tip 无对称 `/health` 路由 → 不选为本轮主 Epic |
| 仅文档 / 不暴露 CLI | 过薄 |

### Why this Epic now（一句话）

E65 补齐了 Initiative **relations** 脚本面，E85 补齐了 **Project** health，但 **Initiative↔Projects 关联** BE/FE（set）早已齐而 CLI **完全空洞**——agent 无法脚本「按 `projectIds` 替换 / attach / detach 关联」；用薄刀一次闭合 Linear-aligned Initiative 项目关联面，且 **不动** 刚闭的 CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead，也 **不**升级成 Initiative health / 甘特弧。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.74.0** 做 Initiative projects **set / attach / detach**；api_client 有对应 helpers；复用既有 `PUT/POST/DELETE /api/initiatives/{id}/projects…`；语义对齐既有 BE（set=全集替换含清空；未知 project **400**；attach 幂等；跨租户·权限既有）；**不**改 E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster / E65 relations 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E91。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `PUT /api/initiatives/{initiative_id}/projects` body `{ projectIds: string[] }`（**camelCase**）  
  - `POST /api/initiatives/{initiative_id}/projects/{project_id}`  
  - `DELETE /api/initiatives/{initiative_id}/projects/{project_id}`  
  - 既有 Initiative CRUD / relations（本轮不改语义）  
- writer 门禁不变；`_validate_projects`：缺/跨 WS → 400；set 为全量 `_replace_projects`（允许 `[]`）；attach 已存在则幂等；detach 不存在视为成功清空该边  
- **不**本轮改 Initiative 模型 / 甘特 / 独立 health 路由 / formula；**不**把 CF soft-update 或 Favorites 400 语义硬套错端点（本端点既有：**未知 project = 400**，与 CF reorder 忽略未知 id **不同**）  
- **不**改 CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template / relations 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`fetchSetInitiativeProjects` 已齐；本轮不强制补 FE attach/detach helper）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.74.0**

- **Q2a** 命令形状：  
  - `opentask initiative projects set <initiative_id> --ids ID1,ID2,... [--json]`（`--ids` 可空字符串/`--clear` 其一表达清空——实现时二选一或并存，默认 **`--ids` 允许空=清空** 对齐 BE `[]`）  
  - `opentask initiative project attach <initiative_id> <project_id> [--json]`  
  - `opentask initiative project detach <initiative_id> <project_id> [--json]`  
  - 备选兼容：`projects set` 位置参数 id 列表（若成本低可双通道；默认以 `--ids` 为主）  
- **Q3a** 语义对齐 BE：api_client  
  - `set_initiative_projects(initiative_id, project_ids)` → **PUT** + `{"projectIds": [...]}`  
  - `attach_initiative_project(initiative_id, project_id)` → **POST**  
  - `detach_initiative_project(initiative_id, project_id)` → **DELETE**  
  - 失败透传 BE 400/403/404/…  
- **Q4a** 挂在既有 `initiative` 组下（`projects` / `project` 子组）；不新开顶层命令；`initiative show`：**json 已含 projects**（BE GET include_projects）→ 默认人类表 **薄补** `Projects`/`projectIds` 摘要列（可选一行）；**不**改 relations 命令  
- **Q5a** pins → **1.74.0**；历史 epic 断言级联  
- **不**改 `initiative create|update|delete|relations|relation` 默认行为；**不**改 CF / favorite / tag-group / label / project health / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- writer 写路径对齐既有 BE；跨租户/缺资源既有  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate / E65 relation 类型枚举  
- 无 Push / 门户 / 甘特；**formula no-emit**  
- **不**新增 `/api/initiatives/{id}/health`；不把嵌套 `healthSummary` 扩成独立 health CLI Epic

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal / E65 relations 语义  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Display prefs CLI / Saved View write / board-move（runners-up）  
- Project 私有 ACL / 按 member 过滤 Issue  
- **Initiative health 独立 CLI** / 自动健康评估（无对称 `/health` 路由 / 另弧）  
- Formula emit；远程 push / 开 PR / **自开 E91**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE Initiative projects PUT/POST/DELETE 行为不变；writer 外写 403；未知 project 400；空 `projectIds` 可清空 |
| B | CLI **1.74.0** `initiative projects set` + `initiative project attach\|detach` 绿；失败透传 |
| C | api_client 三 helper 接线绿（PUT+`projectIds` / POST / DELETE）；历史 pins 级联 1.74.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster / E65 relations；无新 webhook；无新表/alembic；formula no-emit；无独立 initiative health 路由 |
| 门禁 | BE 定向（initiatives smoke 可选 + e90 spy）；CLI 定向 e90；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E91 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Initiative Projects CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 **PUT/POST/DELETE** `/api/initiatives/{id}/projects…`（body `projectIds`；非 `project_ids`） |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.74.0**；`initiative projects set --ids …` + `initiative project attach\|detach` |
| D5 | 语义 = 既有 BE（set 全集替换；未知 project 400；attach 幂等）；show 可薄补 Projects 可读列 |
| D6 | 守 E40 D2/D7；不改 E63–E89 邻面主语义；不 push；不自开 E91；**不做** Initiative health/甘特 Epic |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有 PUT/POST/DELETE；备选 Q1b 只做 set 不做 attach/detach（不选——BE 三通道已齐，CLI 一次补全更贴 agent） |
| Q2 | CLI 命令挂载？ | **Q2a** `initiative projects set` + `initiative project attach\|detach`；备选 Q2b 顶层 `initiative-projects`（不选——既有 `initiative` 组更贴） |
| Q3 | set 入参形状？ | **Q3a** `--ids ID1,ID2,...`（允许空=清空）；备选 Q3b 仅位置参数（可并存为兼容）；备选 Q3c 强制 `--clear` 才允许空（可加，但不取代空 `--ids`） |
| Q4 | 是否顺带动 show？ | **Q4a** 人类表薄补 Projects/`projectIds` 摘要（json 已有）；备选 Q4b 完全不动 show（可接受，但可观测性略差） |
| Q5 | VERSION？ | **Q5a** pins **1.74.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（set API 已齐；不强制补 attach/detach FE）；备选 Q6b 补 FE attach/detach helper（不选——非本轮必须） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：三 helper → PUT+`projectIds` / POST / DELETE（TDD）  
3. CLI 1.74.0：`initiative projects set` + `initiative project attach\|detach`（+ 可选位置参数 / 空 ids 清空）  
4. 可选：`initiative show` 人类表薄补 Projects  
5. pins 级联 1.74.0  
6. BE spy：无新路由/alembic；三端点 marker；邻面 marker；formula no-emit；**无**新 `/health`  
7. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `initiative projects set` 200：返回 `projectIds` 与传入一致；再 `initiative show --json` 校验  
- 空 `--ids` / 清空：关联为空列表  
- 未知 / 跨 WS project → 400（对齐既有 BE，**非** CF soft-ignore）  
- attach 幂等；detach 后列表不含该 id；writer 外 403  
- api_client helper 断言：set 用 `self.put` + `projectIds`；禁 `project_ids` / 禁误用 POST 做 set  
- CLI pins 1.74.0；命令 json/human  
- spy：未改 CF reorder / favorite reorder / tag-group / label set/multi / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster / E65 relations helpers；无新 webhook；formula no-emit；无新 alembic；无新 initiative `/health` 路由  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E91+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — prefer skip。  
6. **递归孙项进度** — prefer skip。  
7. **Bulk/Insights 多指派** — prefer skip。  
8. **深拷贝 duplicate project** — prefer skip。  
9. **模板内 Issue stubs** — prefer skip。  
10. **CSV start_date / start 提醒** — 后置。  
11. **depth≥2 / 服务端树** — 后置。  
12. **评论版本史 / 评论编辑 UX 加厚** — 另弧。  
13. **G-then-X 导航热键** — 另弧。  
14. **复制附件/子树** — 过厚。  
15. **Issue merge** — 过厚。  
16. **定时 purge / hard-delete** — 后置。  
17. **`archived_at` 双轨** — prefer skip。  
18. **Project 私有 ACL / 按 member 过滤 Issue** — 另大弧。  
19. **bulk_update 支持 project_id + 同 integrity helper** — 后薄刀（需 BE schema）。  
20. **读路径 orphan milestone lazy-heal（Q4b）** — 后置。  
21. **`project list --watching` BE 过滤** — 后薄刀（需 BE Query）。  
22. **再开 CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
23. **Initiative health 独立 CLI** — tip 无对称 `/health` 路由；嵌套 `healthSummary` 仅随 GET/projects 返回 — 另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  
25. **Display prefs CLI** — BE/FE 齐、CLI 空洞；agent 价值偏薄。  
26. **Saved View create/update/favorite/save-as CLI** — BE 齐；CLI 仅 list/show/use — 面较宽。  
27. **Issue board/move CLI** — BE/FE 齐；Kanban 位置薄洞。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.74.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E89-S1` @ `d8337eae290d459d5639006c9a40cd6fd3fbfb45`  
- 拟开：`sprint/E90-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e90-initiative-projects-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E91**

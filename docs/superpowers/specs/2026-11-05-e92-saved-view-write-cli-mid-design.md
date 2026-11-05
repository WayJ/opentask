# E92 Design：Saved View Write CLI mid · CLI 1.76.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E92  
基线拟：`sprint/E91-S1` @ `6acec05`（全文 `6acec05c78e29f9c0aa442c574f0b1739af2e108`；E91 design 基线 `651e3d8` ⊂ HEAD；E90 tip `4b7f34d` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E92-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**大软不自开 E93**。  
入库：`docs/superpowers/specs/2026-11-05-e92-saved-view-write-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E91 连续闭合 … → Initiative Projects CLI mid（E90 · 1.74.0）→ Issue Board Move CLI mid（E91：`issue board-move` · 1.75.0）。

E91 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `6acec05`：

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
19. **bulk_update 支持 project_id + 同 integrity helper** — **可后薄刀**（`IssueBulkUpdate` tip **仍无** `project_id`；触 BE schema + E80 邻弧）  
20. **读路径 orphan milestone lazy-heal（Q4b）** — **后置**  
21. **`project list --watching` BE 过滤** — **后薄刀**（`list_projects` tip **仍无** `watching` Query；CLI `project list` 仅输出 `watching_count`，无 filter flag）  
22. **再开 board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **Initiative health CLI（独立 health get/set 弧）** — tip **仍无** 对称 `GET/POST /api/initiatives/{id}/health`；`to_response` 仅嵌套 `healthSummary` — **不选为本轮主 Epic**  
24. **自动健康评估 / AI 摘要** — **另弧**  
25. **（扫描）Display prefs CLI** — BE `GET/PUT /api/display-prefs/issue` + FE 已齐；E49 明示无 CLI 子命令；api_client **零** helpers — agent 价值偏薄（个人 UI 偏好），runners-up  
26. **（扫描）Saved View write / favorite / save-as** — BE `POST/PATCH/DELETE` + `POST /{id}/favorite` + `POST /{id}/save-as` **齐**（既有 `backend/tests/api/test_saved_views.py` 覆盖 create/update/favorite/shared ACL/save-as/跨 WS）；FE `saved-views.ts` create/update/delete/favorite/save-as **齐**；CLI 仅 `view list|show|use`（读向）；api_client **仅** `list_saved_views` + `get_saved_view`，**零** write helpers — agent 无法脚本「保存/改/删/收藏/另存视图」——实证为最清晰 mid 缺口（面比「单端点」宽：5 写路径，但仍是 **BE/FE 齐、CLI 洞** 同构；单 sprint 可切；比 Display prefs 对 agent 价值高）  
27. **（刚闭）Issue board/move CLI** — E91 已闭；**勿重开**

轮换离开刚闭弧：**board-move / initiative-projects / CF reorder / favorite reorder / tag-group CLI / label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E91 board-move；本轮补的是 **Saved View 写路径脚本缺口**（BE/FE 已齐，agent 无法用 CLI create/update/delete/favorite/save-as）。

代码实证 @ `6acec05`：

| 面 | 现状 |
|----|------|
| BE saved-views | `GET/POST /api/saved-views`；`GET/PATCH/DELETE /{id}`；`POST /{id}/favorite` body `{is_favorite}`；`POST /{id}/save-as` body `{name?}`；create/update body **snake_case** `name`/`filter`/`sort`/`display`/`is_favorite`/`is_shared`；serialize 响应 **camelCase**（`isFavorite`/`isShared`/`workspaceId`…）；writer 门禁；共享视图 favorite → **403**；跨租户/无权 → 403/404 |
| FE Saved Views | `fetchCreateSavedView` / `fetchUpdateSavedView` / `fetchDeleteSavedView` / `fetchSetSavedViewFavorite` / `fetchSaveAsSavedView` → **齐** |
| CLI View | 仅 `view list\|show\|use`（E14 读向）；api_client **无** create/update/delete/favorite/save-as — agent 无法脚本持久化过滤器 / 共享 / 另存 |
| Display prefs | BE/FE 齐、CLI 空洞 — agent 价值偏薄（runners-up） |
| Bulk project_id | `IssueBulkUpdate` **仍无** `project_id` — 仍薄刀/后置、触 BE |
| Project list watching | BE `list_projects` **无** watching Query；CLI 仅展示 count — 仍薄刀 |
| Linear 对齐 | agent 应能脚本「Saved View CRUD + favorite + save-as」，与 Linear custom views 持久化对齐 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Saved View Write CLI mid**：CLI **1.76.0** 在既有 `view` 组下补 `create\|update\|delete\|favorite\|save-as`；api_client 五 helpers → 复用既有写端点；**无**新表/webhook/路由；FE 已齐 → 零产品 FE；可选 list/show 薄补 Favorite/Shared 列 | **中薄**；闭合 Saved View 脚本写面；单 sprint；自然续「BE/FE 齐、CLI 洞」；面宽于单端点但仍清晰 |
| B | 仅文档说明用 FE 保存视图 | 过薄；agent 仍断 |
| C | 仅 `view create` + `view delete`（缺 update/favorite/save-as） | 半截；agent 仍缺改/收藏/另存 |
| D | Display prefs CLI | 真洞但 agent 价值偏薄（个人 UI）；runners-up |
| E | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service + E80 邻弧；任务标薄刀 |
| F | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| G | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| H | Initiative health 独立 CLI / 甘特 / Activity Push / 门户 / Q2b / … | 无对称 health 路由 / prefer skip / 勿默认 |
| I | 再开 board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Saved View Write CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.76.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成「Initiative health CLI」或「Display prefs」或「bulk project_id」。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up；watching/bulk 需 BE） |
| Display prefs CLI | runners-up（agent 价值偏薄） |
| 再开 board-move / initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health 独立 CLI | tip 无对称 `/health` 路由 → 不选为本轮主 Epic |
| 仅文档 / 不暴露 CLI | 过薄 |
| 仅 create+delete 半截写面 | 过薄；favorite/save-as/update 仍断 |

### Why this Epic now（一句话）

E86–E91 连续闭合「BE/FE 齐、CLI 洞」关联/reorder/看板面，但 **Saved View 写路径** BE/FE（CRUD + favorite + save-as）早已齐而 CLI **仅读**（list/show/use）——agent 无法脚本「持久化过滤器 / 共享 / 收藏 / 另存」；用一刀闭合 Linear-aligned Saved View 脚本写面，且 **不动** 刚闭的 board-move / initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.76.0** 做 Saved View **create / update / delete / favorite / save-as**；api_client 有对应 helpers；复用既有 `/api/saved-views` 写端点；语义对齐既有 BE（writer 门禁；共享视图不可 favorite→403；save-as 产生个人副本；跨租户/无权 403/404）；**不**改 E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E93。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `POST /api/saved-views` body `{ name, filter, sort?, display?, is_favorite?, is_shared? }`（**snake_case** 请求体，与 FE/`test_saved_views` 一致）  
  - `PATCH /api/saved-views/{id}` 同字段可选  
  - `DELETE /api/saved-views/{id}`  
  - `POST /api/saved-views/{id}/favorite` body `{ is_favorite }`  
  - `POST /api/saved-views/{id}/save-as` body `{ name? }`  
  - 既有 GET list/show（本轮不改语义）  
- writer/鉴权门禁不变；共享视图 favorite → **403**；缺视图 / 无权 → 404/403；跨 WS 既有  
- **不**本轮改 IssueSavedView 模型 / Saved View FE / formula；**不**把本 Epic 做成 Display prefs  
- **不**改 board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`saved-views.ts` 写 helpers 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.76.0**

- **Q2a** 命令形状（挂在既有 `view` 组；保留 `list|show|use`）：  
  - `opentask view create --name NAME [--filter JSON] [--sort JSON] [--display JSON] [--favorite/--no-favorite] [--shared/--no-shared] [--json]`  
  - `opentask view update <view_id> [--name NAME] [--filter JSON] [--sort JSON] [--display JSON] [--favorite/--no-favorite] [--shared/--no-shared] [--json]`  
  - `opentask view delete <view_id> [--json]`  
  - `opentask view favorite <view_id> --on|--off [--json]`（或等价 `--favorite/--unfavorite`；**默认以 `--on/--off` 清晰布尔**）  
  - `opentask view save-as <view_id> [--name NAME] [--json]`  
  - 备选兼容：顶层 `saved-view …`（不选——既有 `view` 组已是用户面）  
  - `--filter`/`--sort`/`--display`：接受 JSON 字符串；非法 JSON → CLI 422 风格错误（不打 BE）  
- **Q3a** 语义对齐 BE：api_client  
  - `create_saved_view(...)` → **POST** `/api/saved-views` + snake_case body  
  - `update_saved_view(view_id, ...)` → **PATCH** `/api/saved-views/{id}` + snake_case body  
  - `delete_saved_view(view_id)` → **DELETE** `/api/saved-views/{id}`  
  - `set_saved_view_favorite(view_id, is_favorite: bool)` → **POST** `.../favorite` + `{is_favorite}`  
  - `save_as_saved_view(view_id, name=None)` → **POST** `.../save-as` + `{name?}`  
  - 请求体字段 **snake_case**（`is_favorite`/`is_shared`/`filter`…）；**不**误用响应侧 camelCase `isFavorite`/`isShared` 作为请求唯一键  
  - 失败透传 BE 403/404/422/…  
- **Q4a** 挂在既有 `view` 组下；不新开顶层命令；`view list`/`view show`：**可选**人类表薄补 `Favorite`/`Shared` 列（json 若已有则只补可读列）；**不**改 `view use` 默认行为（仍打印 filter JSON 供 agent 拼 `issue list`）  
- **Q5a** pins → **1.76.0**；历史 epic 断言级联  
- **不**改 `issue board-move|create|update|…` 默认行为；**不**改 initiative / CF / favorite-reorder / tag-group / label / project health / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- writer 写路径对齐既有 BE；跨租户/缺资源/共享 favorite 禁既有  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；**formula no-emit**  
- **不**新增 `/api/initiatives/{id}/health`；不把本 Epic 扩成 Display prefs 或 bulk project_id

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- **Display prefs CLI**（runners-up；本轮不做）  
- Project 私有 ACL / 按 member 过滤 Issue  
- **Initiative health 独立 CLI** / 自动健康评估（无对称 `/health` 路由 / 另弧）  
- Formula emit；远程 push / 开 PR / **自开 E93**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE saved-views 写路径行为不变；共享 favorite 403；save-as 个人副本；跨 WS/无权既有 |
| B | CLI **1.76.0** `view create\|update\|delete\|favorite\|save-as` 绿；失败透传；`list\|show\|use` 仍绿 |
| C | api_client 五 helpers 接线绿（POST/PATCH/DELETE + snake_case 请求体）；历史 pins 级联 1.76.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster；无新 webhook；无新表/alembic；formula no-emit；无独立 initiative health 路由 |
| 门禁 | BE 定向（`test_saved_views` smoke 可选 + e92 spy）；CLI 定向 e92；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E93 |

---

## 4. ADR（Yuri 已确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Saved View Write CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用既有 `/api/saved-views` 写端点（请求体 **snake_case**；响应仍为既有 camelCase serialize） |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.76.0**；`view create\|update\|delete\|favorite\|save-as`（保留 list/show/use） |
| D5 | 语义 = 既有 BE（writer；共享禁 favorite；save-as 个人副本）；list/show 可薄补 Favorite/Shared |
| D6 | 守 E40 D2/D7；不改 E63–E91 邻面主语义；不 push；不自开 E93；**不做** Initiative health/甘特 / Display prefs / bulk project_id Epic |

---

## 5. 开放问题（Yuri 已一键全收建议默认）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有 POST/PATCH/DELETE + favorite + save-as；备选 Q1b 另开 `/api/cli/saved-views/...`（不选——既有端点+测试已齐） |
| Q2 | CLI 命令挂载？ | **Q2a** 既有 `view` 组补 `create\|update\|delete\|favorite\|save-as`；备选 Q2b 新顶层 `saved-view`（不选——分裂用户面）；备选 Q2c 仅 create+delete（不选——半截） |
| Q3 | 请求体字段命名？ | **Q3a** api_client 发 **snake_case** `is_favorite`/`is_shared`/`filter`（对齐 BE/FE/test）；备选 Q3b 请求也发 camelCase `isFavorite`（不选——本端点 create/update 契约即 snake） |
| Q4 | 是否改 list/show/use？ | **Q4a** list/show **可选**薄补 Favorite/Shared；**不**改 `use`；备选 Q4b 大改 use 自动调 `issue list`（不选——越界） |
| Q5 | VERSION？ | **Q5a** pins **1.76.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（写 helpers 已齐）；备选 Q6b 改 FE 命名/封装（不选——非本轮必须） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：五 write helpers → POST/PATCH/DELETE + snake_case（TDD）  
3. CLI 1.76.0：`view create|update|delete|favorite|save-as`  
4. 可选：`view list`/`view show` 人类表薄补 Favorite/Shared  
5. pins 级联 1.76.0  
6. BE spy：无新路由/alembic；saved-views write markers；邻面 marker；formula no-emit；**无**新 initiative `/health`；**未改** board-move  
7. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `view create` 200：返回含 id/name；再 `view show` 校验 filter  
- `view update` 改 name/filter/favorite/shared；共享 ACL（member 改他人 shared → 403；owner 可）  
- `view favorite --on/--off`：个人视图绿；共享视图 → 403  
- `view save-as`：产生个人副本（`isShared=false`）；可选新 name  
- `view delete` 后 show → 404  
- 非法 `--filter` JSON → CLI 侧失败（不打 BE）  
- api_client helpers 断言：正确 method + path；body 含 snake_case `is_favorite`/`is_shared`；禁误用 camelCase 作为请求唯一键  
- CLI pins 1.76.0；命令 json/human；`list|show|use` 回归  
- spy：未改 board-move / initiative projects helpers / CF reorder / favorite reorder / tag-group / label set/multi / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic；无新 initiative `/health` 路由  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E93+；若 Yuri 改选可替换本草案）

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
22. **再开 board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / …** — 刚闭，勿默认。  
23. **Initiative health 独立 CLI** — tip 无对称 `/health` 路由；嵌套 `healthSummary` 仅随 GET/projects 返回 — 另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  
25. **Display prefs CLI** — BE/FE 齐、CLI 空洞；agent 价值偏薄。  
26. **（本轮主推已选）Saved View write CLI** — 若改选则回退到 Display prefs 或 bulk project_id。  
27. **Issue board/move CLI** — E91 已闭；勿重开。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.76.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E91-S1` @ `6acec05c78e29f9c0aa442c574f0b1739af2e108`  
- 拟开：`sprint/E92-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e92-saved-view-write-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E93**

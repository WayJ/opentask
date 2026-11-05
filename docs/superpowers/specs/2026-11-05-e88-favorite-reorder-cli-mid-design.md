# E88 Design：Favorite Reorder CLI mid · CLI 1.72.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E88  
基线拟：`sprint/E87-S1` @ `c82bc63`（全文 `c82bc632626501a14e8357ca0c3f0d3cff785508`；E87 design 基线 `efd94ba` ⊂ HEAD；E86 tip `a353f82` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E88-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E89**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e88-favorite-reorder-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E88-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E87 连续闭合 … → Label Set/Multi CLI mid（E86 · 1.70.0）→ Tag Group CLI mid（E87：`label group …` + list/create `--group-id` + update group-id str · 1.71.0）。

E87 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `c82bc63`：

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
21. **`project list --watching` BE 过滤** — **后薄刀**（`list_projects` tip 无 `watching` Query；CLI `project list` 亦无 flag）  
22. **再开 tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **Initiative health CLI** — tip 无对称 Project Health 式 BE；**不选**  
24. **自动健康评估 / AI 摘要** — **另弧**  
25. **（扫描）Favorite Reorder CLI** — E87 附录 #25；BE `PUT /api/favorites/reorder` + FE `fetchReorderFavorites` **已齐**；CLI/api_client **仅** `list|add|remove`，**零** reorder — 实证为最清晰 mid/薄中缺口（闭合侧栏收藏脚本顺序面）

轮换离开刚闭弧：**tag-group CLI / label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E87 tag-group；本轮补的是 **Favorites 重排序脚本缺口**（BE/FE 已齐，agent 无法用 CLI 调整侧栏顺序）。

代码实证 @ `c82bc63`：

| 面 | 现状 |
|----|------|
| BE Favorites | `GET/POST /api/favorites`；`DELETE /api/favorites/{id}`；**`PUT /api/favorites/reorder`** body `{ordered_ids: string[]}` **齐**；writer 门禁；`ordered_ids` 必须覆盖当前全部收藏否则 400；服务 `FavoriteService.reorder` 写 `position` |
| FE Favorites | `frontend/src/service/api/favorites.ts`：`fetchReorderFavorites(ordered_ids)` → `PUT /api/favorites/reorder` **齐**；侧栏/收藏 UI 已用 list/add/remove |
| CLI Favorite | `favorite list\|add\|remove`；api_client `list/add/remove_favorite`；**无** `favorite reorder`；**无** `reorder_favorites` helper — agent 无法脚本「按给定顺序重排侧栏收藏」 |
| Bulk project_id | `IssueBulkUpdate` **无** `project_id`；单发 `issue update --project` 已走 integrity — 仍薄刀/后置、触 BE |
| Project list watching | CLI `project list` 无 `--watching`；BE `list_projects` 无 watching Query — 仍薄刀 |
| Linear 对齐 | agent 应能脚本「侧栏收藏 CRUD + 重排」，与 Linear Favorites / sidebar pin order 对齐 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Favorite Reorder CLI mid**：CLI **1.72.0** `favorite reorder`；api_client `reorder_favorites`；复用既有 **`PUT /api/favorites/reorder`**；**无**新表/webhook/路由；FE 已齐 → 零产品 FE；可选薄补 `favorite list` 展示 `position` | **薄→中薄**；闭合 Favorites 脚本顺序面；单 sprint；自然续 E87「BE/FE 齐、CLI 洞」模式 |
| B | 仅文档说明用 FE 拖拽 | 过薄；agent 仍断 |
| C | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service + E80 邻弧；任务标薄刀 |
| D | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| E | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| F | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| G | 再开 tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Favorite Reorder CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.72.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up；watching/bulk 需 BE） |
| 再开 tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health CLI | tip 无对称 BE → 不选 |
| 仅文档 / 不暴露 CLI | 过薄 |

### Why this Epic now（一句话）

E87 补齐了 Tag Group 脚本 CRUD，但 **Favorites reorder** BE/FE 早已齐而 CLI **完全空洞**——agent 无法脚本「按 `ordered_ids` 重排侧栏收藏（须覆盖全集，否则 400）」；用薄刀一次闭合 Linear-aligned Favorites 顺序面，且 **不动** 刚闭的 tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.72.0** 做 `favorite reorder`（完整 `ordered_ids`）；api_client 有 `reorder_favorites`；复用既有 `PUT /api/favorites/reorder`；缺 id / 多余 id / 非全集 → 既有 BE 400；跨租户·缺收藏 既有行为；**不**改 E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E89。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `PUT /api/favorites/reorder` body `{ ordered_ids: string[] }`  
  - 既有 `GET/POST /api/favorites`；`DELETE /api/favorites/{favorite_id}`（本轮不改语义）  
- writer 门禁不变；`ordered_ids` 必须与当前用户·工作区收藏 id 集合相等（既有 400）；owned-only  
- **不**本轮改 Favorite 模型 / target_type 枚举 / 权限大改  
- **不**改 tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`fetchReorderFavorites` 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.72.0**

- **Q2a** 命令形状：  
  - `opentask favorite reorder --ids ID1,ID2,... [--json]`  
  - 备选兼容：位置参数 `opentask favorite reorder ID1 ID2 ...`（若实现成本低可双通道；默认以 `--ids` 为主，与既有 multi-id 风格一致）  
- **Q3a** 语义对齐 BE：传入列表须覆盖**当前全部**收藏 id（顺序即新 `position`）；失败透传 BE 400/403/404  
- **Q4a** 挂在既有 `favorite` 组下：`favorite reorder`；不新开顶层命令  
- **Q5a** `api_client.reorder_favorites(ordered_ids: list[str])` → `PUT /api/favorites/reorder`；**不**误用 POST（E87 附录笔误；tip 实为 **PUT**）  
- pins → **1.72.0**；历史 epic 断言级联  
- **可选薄补（Q4a 内）**：`favorite list` human/json 展示 `position`（若字段已返回）——不改 list 过滤语义  
- **不**改 `favorite add|remove` 默认行为；**不**改 tag-group / label / project health / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- writer 写路径对齐既有 BE；非全集 400；跨租户/缺资源既有  
- **不**引入 project-private ACL；不改 E79 roster；unpin ≠ unwatch（E8 D7）保持  
- 不触 tag-group / label set/multi / project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- Initiative health CLI / 自动健康评估（无对称 BE / 另弧）  
- custom-fields reorder CLI（同类洞，本轮不扩；runners-up）  
- Formula emit；远程 push / 开 PR / **自开 E89**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE `PUT /api/favorites/reorder` 行为不变；非全集 400；writer 外写 403；owned-only |
| B | CLI **1.72.0** `favorite reorder` 绿；失败透传 |
| C | api_client `reorder_favorites` 接线绿；历史 pins 级联 1.72.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster；无新 webhook；无新表/alembic；formula no-emit |
| 门禁 | BE 定向（既有 favorites smoke + e88 spy）；CLI 定向 e88；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E89 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Favorite Reorder CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 **`PUT /api/favorites/reorder`**（非 POST） |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.72.0**；`favorite reorder --ids …`（可选位置参数兼容） |
| D5 | 语义 = BE 全集覆盖 + position 重写；list 可选露 position |
| D6 | 守 E40 D2/D7；不改 E63–E87 邻面主语义；不 push；不自开 E89 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用 `PUT /api/favorites/reorder`；备选 Q1b `PATCH /api/favorites/{id}` 单条 position（不选——BE 已有批量 reorder） |
| Q2 | CLI 命令挂载？ | **Q2a** `favorite reorder`；备选 Q2b 顶层 `favorites-reorder`（不选——既有 `favorite` 组更贴） |
| Q3 | 入参形状？ | **Q3a** `--ids ID1,ID2,...` 为主；备选 Q3b 仅位置参数（可并存为兼容，不以 Q3b 为唯一） |
| Q4 | 是否顺带 list 露 position？ | **Q4a** 是（薄补，字段已有）；备选 Q4b 完全不动 list（可接受，略弱可观测） |
| Q5 | VERSION？ | **Q5a** pins **1.72.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（reorder API 已齐）；备选 Q6b 重做侧栏 DnD（不选——浪费） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：`reorder_favorites`（TDD）  
3. CLI 1.72.0：`favorite reorder --ids …`（+ 可选位置参数）  
4. 可选薄补：`favorite list` 展示 position  
5. pins 级联 1.72.0  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `favorite reorder` 200：顺序与 `ordered_ids` 一致；再 `favorite list` 校验 position  
- 非全集 / 未知 id → 400；writer 外 403；跨 WS 隔离  
- api_client helper 接线；CLI pins 1.72.0；命令 json/human  
- spy：未改 tag-group helpers/命令 / label set/multi / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E89+；若 Yuri 改选可替换本草案）

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
22. **再开 tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
23. **Initiative health CLI** — tip 无对称 BE；另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  
25. **custom-fields reorder CLI**（BE `POST?/PUT /api/custom-fields/reorder` 已有、CLI 缺）— 可后薄刀（本轮先 Favorites）。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.72.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E87-S1` @ `c82bc632626501a14e8357ca0c3f0d3cff785508`  
- 拟开：`sprint/E88-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e88-favorite-reorder-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E89**

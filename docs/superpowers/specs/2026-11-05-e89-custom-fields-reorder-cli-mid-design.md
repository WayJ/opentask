# E89 Design：Custom Fields Reorder CLI mid · CLI 1.73.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E89  
基线拟：`sprint/E88-S1` @ `d09142c`（全文 `d09142c7b3d175d67c35f9432c5773a2d0e1e359`；E88 design 基线 `34f151a` ⊂ HEAD；E87 tip `c82bc63` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E89-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E90**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e89-custom-fields-reorder-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E89-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E88 连续闭合 … → Tag Group CLI mid（E87 · 1.71.0）→ Favorite Reorder CLI mid（E88：`favorite reorder` + list `position` · 1.72.0）。

E88 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `d09142c`：

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
22. **再开 favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **Initiative health CLI** — tip 无对称 Project Health 式 BE；**不选**  
24. **自动健康评估 / AI 摘要** — **另弧**  
25. **（扫描）Custom Fields Reorder CLI** — E88 附录 #25；BE `POST /api/custom-fields/reorder` + FE `fetchReorderCustomFields` **已齐**；CLI/api_client **仅** `list|create|update|validate-formula`，**零** reorder — 实证为最清晰 mid/薄中缺口（闭合工作区 CF 脚本顺序面；与 E88 Favorites 同构）

轮换离开刚闭弧：**favorite reorder / tag-group CLI / label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E88 favorite；本轮补的是 **Custom Fields 重排序脚本缺口**（BE/FE 已齐，agent 无法用 CLI 调整 CF `position`）。

代码实证 @ `d09142c`：

| 面 | 现状 |
|----|------|
| BE Custom Fields | `GET/POST /api/custom-fields`；`GET/PATCH/DELETE /api/custom-fields/{id}`；**`POST /api/custom-fields/reorder`** body `{orderedIds: string[]}` **齐**；writer 门禁；`CustomFieldService.reorder` 对命中 id 写 `position`（未命中 id **忽略**；**不**强制全集覆盖——与 Favorites 400 语义不同） |
| FE Custom Fields | `frontend/src/service/api/custom-fields.ts`：`fetchReorderCustomFields(orderedIds)` → `POST /api/custom-fields/reorder` **齐**；workspace CF UI DnD 已用 |
| CLI Custom Field | `custom-field list\|create\|update\|validate-formula`；api_client 对应 helpers；list 已露 Pos；**无** `custom-field reorder`；**无** `reorder_custom_fields` helper — agent 无法脚本「按给定顺序重排工作区自定义字段」 |
| Bulk project_id | `IssueBulkUpdate` **无** `project_id`；单发 `issue update --project` 已走 integrity — 仍薄刀/后置、触 BE |
| Project list watching | CLI `project list` 无 `--watching` 过滤；BE `list_projects` 无 watching Query — 仍薄刀 |
| Linear 对齐 | agent 应能脚本「CF CRUD + 重排」，与 Linear Custom Fields / field order 对齐 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Custom Fields Reorder CLI mid**：CLI **1.73.0** `custom-field reorder`；api_client `reorder_custom_fields`；复用既有 **`POST /api/custom-fields/reorder`**（body **`orderedIds`**）；**无**新表/webhook/路由；FE 已齐 → 零产品 FE；list 已露 Pos → 可不改 list | **薄→中薄**；闭合 CF 脚本顺序面；单 sprint；自然续 E88「BE/FE 齐、CLI 洞」模式 |
| B | 仅文档说明用 FE 拖拽 | 过薄；agent 仍断 |
| C | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service + E80 邻弧；任务标薄刀 |
| D | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| E | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| F | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| G | 再开 favorite reorder / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Custom Fields Reorder CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.73.0**；formula no-emit（validate-formula 既有面不动；reorder **不**触 emit）；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up；watching/bulk 需 BE） |
| 再开 favorite reorder / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health CLI | tip 无对称 BE → 不选 |
| 仅文档 / 不暴露 CLI | 过薄 |

### Why this Epic now（一句话）

E88 补齐了 Favorites 脚本重排，但 **Custom Fields reorder** BE/FE 早已齐而 CLI **完全空洞**——agent 无法脚本「按 `orderedIds` 重排工作区 CF `position`」；用薄刀一次闭合 Linear-aligned CF 顺序面，且 **不动** 刚闭的 favorite reorder / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.73.0** 做 `custom-field reorder`（`orderedIds`）；api_client 有 `reorder_custom_fields`；复用既有 `POST /api/custom-fields/reorder`；语义对齐既有 BE（命中 id 写 position；未知 id 忽略；**不**误套 Favorites 全集 400）；跨租户·权限既有行为；**不**改 E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E90。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `POST /api/custom-fields/reorder` body `{ orderedIds: string[] }`（**camelCase**；**POST** 非 PUT——与 Favorites 不同）  
  - 既有 CF CRUD / validate-formula（本轮不改语义）  
- writer 门禁不变；service 对 `ordered_ids` 中存在于当前工作区（含 archived 列表源）的 id 赋 `position=idx`；未命中忽略；返回未归档 list  
- **不**本轮改 CustomField 模型 / formula 求值 / emit；**不**把 Favorites「全集覆盖 400」硬套到本端点  
- **不**改 favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`fetchReorderCustomFields` 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.73.0**

- **Q2a** 命令形状：  
  - `opentask custom-field reorder --ids ID1,ID2,... [--json]`  
  - 备选兼容：位置参数 `opentask custom-field reorder ID1 ID2 ...`（若实现成本低可双通道；默认以 `--ids` 为主，与 E88 favorite reorder 一致）  
- **Q3a** 语义对齐 BE：api_client 发 **`POST`** + body **`{"orderedIds": [...]}`**（勿发 `ordered_ids` / 勿用 PUT）；失败透传 BE 403/404/…  
- **Q4a** 挂在既有 `custom-field` 组下：`custom-field reorder`；不新开顶层命令；**list 已露 Pos** → 默认 **不改** list（已可观测）；若发现 json 缺 position 再薄补  
- **Q5a** `api_client.reorder_custom_fields(ordered_ids: list[str])` → `POST /api/custom-fields/reorder` with `orderedIds`；**不**误用 PUT；**不**与 `reorder_favorites` 混用  
- pins → **1.73.0**；历史 epic 断言级联  
- **不**改 `custom-field create|update|validate-formula` 默认行为；**不**改 favorite / tag-group / label / project health / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- writer 写路径对齐既有 BE；跨租户/缺资源既有  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；**formula no-emit**（reorder 只动 position；validate-formula 面不动）  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- Initiative health CLI / 自动健康评估（无对称 BE / 另弧）  
- 把 CF reorder 改成 Favorites 式「必须全集否则 400」（BE 既有软更新；本轮不改 BE）  
- Formula emit；远程 push / 开 PR / **自开 E90**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE `POST /api/custom-fields/reorder` 行为不变；writer 外写 403；软更新语义保持 |
| B | CLI **1.73.0** `custom-field reorder` 绿；失败透传 |
| C | api_client `reorder_custom_fields` 接线绿（POST + `orderedIds`）；历史 pins 级联 1.73.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster；无新 webhook；无新表/alembic；formula no-emit |
| 门禁 | BE 定向（CF smoke 可选 + e89 spy）；CLI 定向 e89；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E90 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Custom Fields Reorder CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 **`POST /api/custom-fields/reorder`**（body `orderedIds`；非 PUT / 非 `ordered_ids`） |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.73.0**；`custom-field reorder --ids …`（可选位置参数兼容） |
| D5 | 语义 = 既有 BE 软更新 position；list 已露 Pos → 默认不动 list |
| D6 | 守 E40 D2/D7；不改 E63–E88 邻面主语义；不 push；不自开 E90 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用 `POST /api/custom-fields/reorder`；备选 Q1b 改成 PUT 对齐 Favorites（不选——破坏既有 FE/契约） |
| Q2 | CLI 命令挂载？ | **Q2a** `custom-field reorder`；备选 Q2b 顶层 `cf-reorder`（不选——既有 `custom-field` 组更贴） |
| Q3 | 入参形状？ | **Q3a** `--ids ID1,ID2,...` 为主；备选 Q3b 仅位置参数（可并存为兼容，不以 Q3b 为唯一） |
| Q4 | 是否顺带动 list？ | **Q4a** 否（list 已有 Pos 列）；备选 Q4b 再确认 json 含 position（仅若缺再补） |
| Q5 | VERSION？ | **Q5a** pins **1.73.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（reorder API 已齐）；备选 Q6b 重做 CF DnD（不选——浪费） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：`reorder_custom_fields` → POST + `orderedIds`（TDD）  
3. CLI 1.73.0：`custom-field reorder --ids …`（+ 可选位置参数）  
4. pins 级联 1.73.0  
5. BE spy：无新路由/alembic；POST reorder 在位；邻面 marker；formula no-emit  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `custom-field reorder` 200：命中 id 的 position 与传入顺序一致；再 `custom-field list` 校验 Pos  
- 未知 id 被忽略（对齐既有 BE，非 Favorites 400）；writer 外 403；跨 WS 隔离  
- api_client helper 必须 `self.post` + `orderedIds`（断言源码；禁 PUT / `ordered_ids`）  
- CLI pins 1.73.0；命令 json/human  
- spy：未改 favorite reorder / tag-group helpers/命令 / label set/multi / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E90+；若 Yuri 改选可替换本草案）

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
22. **再开 favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
23. **Initiative health CLI** — tip 无对称 BE；另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.73.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E88-S1` @ `d09142c7b3d175d67c35f9432c5773a2d0e1e359`  
- 拟开：`sprint/E89-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e89-custom-fields-reorder-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E90**

# E87 Design：Tag Group CLI mid · CLI 1.71.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E87  
基线拟：`sprint/E86-S1` @ `a353f82`（全文 `a353f82a4833898c0cec907745884f36b5554241`；E86 design 基线 `f8b1b27` ⊂ HEAD；E85 tip `5fa6e3b` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E87-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E88**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e87-tag-group-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E87-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E86 连续闭合 … → Project Health CLI mid（E85 · 1.69.0）→ Label Set/Multi CLI mid（E86：`label set|update` + multi attach/detach · 1.70.0）。

E86 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `a353f82`：

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
19. **bulk_update 支持 project_id + 同 integrity helper** — **可后薄刀**  
20. **读路径 orphan milestone lazy-heal（Q4b）** — **后置**  
21. **`project list --watching` BE 过滤** — **后薄刀**  
22. **再开 label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **（扫描）Tag Group CLI** — E86 附录 #23；BE `/api/tag-groups` CRUD + FE labels 分组 UI **已齐**；CLI/api_client **零** group 命令 — 实证为最清晰 mid/薄中缺口  
24. **Initiative health CLI** — tip 无对称 Project Health 式 BE；**不选**  
25. **自动健康评估 / AI 摘要** — **另弧**

轮换离开刚闭弧：**label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E86 label set/multi；本轮补的是 **Tag Group 脚本 CRUD 缺口**（BE/FE 已齐，CLI 仅能在 `label update` 上带 `--group-id`，且类型为 int，与 BE `group_id: str` UUID **不齐**）。

代码实证 @ `a353f82`：

| 面 | 现状 |
|----|------|
| BE Tag Groups | `GET/POST /api/tag-groups`；`PATCH/DELETE /api/tag-groups/{id}` **齐**；writer 门禁；同 WS 名唯一 409；删组 `ondelete=SET NULL` 解绑 tags |
| BE Tags | `list_tags(?group_id=)` 过滤齐；`create_tag(group_id)` / `PATCH clear_group` 齐（E86 已接线 update） |
| FE Labels | `frontend/src/views/workspace/labels/index.vue` + `tagApi` createGroup/list 已齐 |
| CLI Label | `list\|create\|delete\|set\|update\|attach\|detach\|issue`；**无** `label group *`；api_client **无** `list/create/update/delete_tag_groups`；`label list` **无** `--group-id`；`label create` **无** `--group-id`；`label update --group-id` 现为 `type=int`（BE 为 UUID str）— agent 无法脚本建组/列组/改组/删组 |
| Project list watching | CLI `project list` 无 `--watching`；BE `list_projects` 无 watching Query — 仍薄刀 |
| Bulk project_id | `IssueBulkUpdate` **无** `project_id`；单发 `issue update --project` 已走 integrity — 仍薄刀/后置 |
| Linear 对齐 | agent 应能脚本「标签分组 CRUD + 按组列标 / 建标入组」，与 Linear Label Groups 对齐 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Tag Group CLI mid**：CLI **1.71.0** `label group list\|create\|update\|delete`；api_client tag-group helpers；薄加 `label list --group-id` + `label create --group-id`；**修正** `label update --group-id` 为 **str**（对齐 BE UUID）；复用既有 `/api/tag-groups` + tags；**无**新表/webhook/路由；FE 已齐 → 零产品 FE | **中薄→中厚**；闭合 Label 组脚本面；单 sprint；自然续 E86 |
| B | 仅 `label group list` 只读 | 过薄；建/改/删仍断 |
| C | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service；任务标薄刀；且换项目批量属 E80 邻弧 |
| D | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| E | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| F | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| G | 再开 label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Tag Group CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.71.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up） |
| 再开 label set/multi / project-health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health CLI | tip 无对称 BE → 不选 |
| 仅 group list 只读 | 过薄 |

### Why this Epic now（一句话）

E86 补齐了 Issue 标签 replace/update/multi，但 **Tag Group** BE/FE 早已齐而 CLI **完全空洞**——agent 无法脚本「建分组 / 列分组 / 改名改色排序 / 删组（tags SET NULL）」；顺带修正 E86 遗留的 `--group-id` int≠UUID。用中薄刀一次闭合 Linear Label Groups 脚本面，且 **不动** 刚闭的 set/multi / health / cycle / watchers / templates / milestones / move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.71.0** 做 `label group list|create|update|delete`；api_client 有对应 helpers；`label list --group-id` / `label create --group-id` 接线既有 BE；`label update --group-id` 接受 **str UUID**；跨租户/缺资源 404（既有 BE）；同名 409；删组后 tags.group_id SET NULL；**不**改 E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E88。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `GET/POST /api/tag-groups`  
  - `PATCH/DELETE /api/tag-groups/{group_id}`  
  - `GET /api/tags?group_id=`；`POST /api/tags`（可选 `group_id`）；既有 `PATCH /api/tags/{id}`  
- writer 门禁不变；跨租户·缺组 404；同 WS 重名 409；删组 SET NULL 不变  
- **不**本轮改 Tag/TagGroup 模型 / 颜色枚举 / 权限大改  
- **不**改 label set/multi 语义；不改 project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（labels 分组 UI 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.71.0**

- **Q2a** 命令形状：  
  - `opentask label group list [--json]`  
  - `opentask label group create --name NAME [--color ...] [--position N] [--json]`  
  - `opentask label group update <groupId> [--name ...] [--color ...] [--position N] [--json]`  
  - `opentask label group delete <groupId> [--json]`  
  - 薄读/写补齐：`opentask label list [--group-id ID] [--q ...] [--json]`  
  - `opentask label create --name ... [--color ...] [--group-id ID] [--json]`  
- **Q3a** `label update --group-id`：**str**（UUID）；保留 `--clear-group`；与 BE `TagUpdate.group_id: Optional[str]` 对齐（修 E86 int 漂移）  
- **Q4a** 子命令挂在既有 `label` 组下：`label group …`（贴 Linear「Labels / Groups」）；不新开顶层 `tag-group` 二进制  
- **Q5a** `api_client`：`list_tag_groups` / `create_tag_group` / `update_tag_group` / `delete_tag_group`；`list_tags` 已支持 `group_id` 则接线；`create_tag` 已有 `group_id` 参数则 CLI 暴露  
- pins → **1.71.0**；历史 epic 断言级联  
- **不**改 `label set|update|attach|detach|issue|delete` 既有默认行为（除 `--group-id` 类型修正）  
- **不**改 project health/timeline / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- writer 写路径对齐既有 BE；跨租户/缺资源 404；重名 409  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 label set/multi 主测语义以外的邻面；不触 project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E86 label set/multi 主表面（除 `--group-id` 类型对齐）/ E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- Initiative health CLI / 自动健康评估（无对称 BE / 另弧）  
- 再开 label set/multi / project-health / cycle / lead/members / parent / trash / links / threading / start_date / project-templates / multi-assignee / issue-templates / project-watchers  
- Formula emit；远程 push / 开 PR / **自开 E88**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE tag-groups CRUD / tags?group_id / create+patch group_id 行为不变；跨租户/缺资源 404；重名 409；writer 外写 403；删组 SET NULL |
| B | CLI **1.71.0** `label group list\|create\|update\|delete` 绿；`label list --group-id` / `label create --group-id` 绿；`label update --group-id` 接受 UUID str |
| C | api_client tag-group helpers 接线绿；历史 pins 级联 1.71.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E86 set/multi 主语义（除 group-id 类型）/ E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster；无新 webhook；无新表/alembic；formula no-emit |
| 门禁 | BE 定向（既有 tags/tag-groups smoke + e87 spy）；CLI 定向 e87；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E88 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Tag Group CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 `/api/tag-groups` + tags `group_id` |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.71.0**；`label group list\|create\|update\|delete` + list/create `--group-id` |
| D5 | `label update --group-id` = **str UUID**（修 E86 int 漂移）；删组语义 = BE SET NULL |
| D6 | 守 E40 D2/D7；不改 E63–E86 邻面主语义（除上述类型对齐）；不 push；不自开 E88 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用 `/api/tag-groups` + tags；备选 Q1b 嵌套 `/api/tags/groups` 别名（不选——已有独立 prefix） |
| Q2 | CLI 命令挂载？ | **Q2a** `label group …` 子组；备选 Q2b 顶层 `tag-group`（不选——既有 `label` 组更贴） |
| Q3 | `--group-id` 类型？ | **Q3a** str UUID（对齐 BE）；备选 Q3b 保持 int（不选——与 TagGroup.id 矛盾，E86 漂移） |
| Q4 | 是否顺带 `label list/create --group-id`？ | **Q4a** 是（薄补，BE 已支持）；备选 Q4b 仅 group CRUD（不选——列组后无法按组列标） |
| Q5 | VERSION？ | **Q5a** pins **1.71.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（分组 UI 已齐）；备选 Q6b 重做 labels 页（不选——浪费） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：tag-group CRUD helpers（TDD）  
3. CLI 1.71.0：`label group list|create|update|delete`  
4. 薄补：`label list --group-id` + `label create --group-id`；修正 `label update --group-id` → str  
5. pins 级联 1.71.0  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `label group create/list/update/delete` 200；重名 409；缺组 404；跨 WS 隔离；writer 外 403  
- 删组后 tags.group_id 为 null（BE 既有；CLI 侧可读 `label list` 验证）  
- `label list --group-id` / `label create --group-id`；`label update --group-id <uuid>` + `--clear-group`  
- api_client helpers 接线；CLI pins 1.71.0；命令 json/human  
- spy：未改 label set/multi 主路径 / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E88+；若 Yuri 改选可替换本草案）

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
19. **bulk_update 支持 project_id + 同 integrity helper** — 后薄刀。  
20. **读路径 orphan milestone lazy-heal（Q4b）** — 后置。  
21. **`project list --watching` BE 过滤** — 后薄刀。  
22. **再开 label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
23. **Initiative health CLI** — tip 无对称 BE；另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  
25. **favorite reorder CLI**（BE `POST /api/favorites/reorder` 已有、CLI 缺）— 可后薄刀。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.71.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E86-S1` @ `a353f82a4833898c0cec907745884f36b5554241`  
- 拟开：`sprint/E87-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e87-tag-group-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E88**

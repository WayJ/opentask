# E86 Design：Label Set/Multi CLI mid · CLI 1.70.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E86  
基线拟：`sprint/E85-S1` @ `5fa6e3b`（全文 `5fa6e3b8f79fde23b6fbcd59f3902ab578d71206`；E85 design 基线 `3a0add2` ⊂ HEAD；E84 tip `dde41b1` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E86-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E87**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e86-label-set-multi-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E86-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E85 连续闭合 … → Cycle CLI mid（E84 · 1.68.0）→ Project Health CLI mid（E85：`project health get|set` + `timeline` · 1.69.0）。

E85 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `5fa6e3b`：

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
22. **再开 project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **（扫描）Label `set`/multi（E85 附录首选）** — 实证后为真 mid 缺口  
24. **Initiative health CLI** — tip 无对称 Project Health 式 BE（仅 mission_center `/health` 无关）；**不选**  
25. **自动健康评估 / AI 摘要** — **另弧**

轮换离开刚闭弧：**project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E85 project-health；本轮补的是 **Label replace/`set` + multi CLI 缺口**（BE/FE 已齐，CLI 仅单条 attach/detach）。

代码实证 @ `5fa6e3b`：

| 面 | 现状 |
|----|------|
| BE Issue Tags | `GET/PUT /api/issues/{id}/tags`（replace 齐 · `TagService.replace_issue_tags`）；`POST/DELETE …/tags/{tag_id}` 单条；writer 门禁齐 |
| BE Tag CRUD | `GET/POST /api/tags`；`GET/PATCH/DELETE /api/tags/{id}`（**PATCH update 齐**）；groups 齐 |
| FE Labels | `issueApi.replaceTags` + store `replaceTags` + L picker 已齐；tag CRUD UI 已有 |
| CLI Label | `list\|create\|delete\|attach\|detach` **仅单 tag_id**；api_client **有** `attach_issue_tag` / `detach_issue_tag` / `list_issue_tags`，**无** `replace_issue_tags` / `update_tag`；**无** `label set` / `label update` / multi `--tag-id` |
| CLI Bulk | `issue bulk-update --tag-ids` 可批量 replace（跨多 issue）— **单 issue 脚本 replace 仍断**；agent 不能 `label set ISSUE-1 --ids 1,2,3` |
| Project Health | E85 已闭 · 1.69.0 — **本轮勿再开** |
| Linear 对齐 | agent 应能脚本「整组替换 Issue 标签 / 改标签元数据 / 一次挂多标」，而非只 attach/detach 单条或绕道 bulk-update |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Label Set/Multi CLI mid**：CLI **1.70.0** `label set`（→ PUT replace）+ `label update`（→ PATCH tag）+ attach/detach **多 `--tag-id`**；api_client `replace_issue_tags` / `update_tag`；可选 `label issue`/`label list --issue` 读 `list_issue_tags`；复用既有 BE；**无**新表/webhook/路由；FE 已齐 → 零产品 FE | **中厚**；E85 runner-up #23 首选；闭合 Label 脚本 replace 面；单 sprint |
| B | 仅 `label set`、无 update / 不多 tag attach | 过薄；元数据改仍断 |
| C | 仅增强 `attach` 多 id、无 PUT replace | 半齐；无法「清空后整组设」/幂等 replace |
| D | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| E | bulk project_id / Q4b lazy-heal / `project list --watching` | 任务标薄刀/后置 |
| F | 再开 project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead | 刚闭 |
| G | Project 私有 ACL / merge / 深拷贝 / 模板 stubs / Initiative health（无 BE） | 另大弧 / 过厚 / skip / 无对称 BE |

**建议拍板：A（Label Set/Multi CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.70.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置 |
| 再开 project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / … | 刚闭 |
| Initiative health CLI | tip 无对称 BE → 不选 |
| 仅 set 无 update | 过薄（PATCH tag 已齐、CLI 空洞） |
| 仅多 attach 无 replace | 半齐；缺幂等整组设 |

### Why this Epic now（一句话）

BE/FE 早已能 PUT replace Issue tags + PATCH tag 元数据，CLI 却停在单条 attach/detach——agent **无法**脚本「整组设标签 / 改色改名 / 一次挂多标」（只能绕道 `bulk-update --tag-ids`）。用中厚刀一次补上 **`label set` + `label update` + multi attach/detach + api_client**，闭合 Linear Label 脚本面，且 **不动** 刚闭的 project-health / cycle / watchers / issue-templates / milestones / project-move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.70.0** 做 `label set`（PUT replace）、`label update`（PATCH）、attach/detach **多 tag**；api_client 有对应 helpers；跨租户/缺资源 404（既有 BE）；**不**改 E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E87。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `PUT /api/issues/{issue_id}/tags`（body: `tag_ids: int[]`）  
  - `POST/DELETE /api/issues/{issue_id}/tags/{tag_id}`（既有单条；CLI 侧 multi 循环或同请求多次）  
  - `PATCH /api/tags/{tag_id}`（name/color/group_id/clear_group）  
  - `GET /api/issues/{issue_id}/tags`（可选读路径接线）  
- writer / tag-writer 门禁不变；跨租户·缺 issue/tag 404 不变  
- **不**本轮改 Tag 模型 / 组权限大改 / 颜色枚举  
- **不**改 project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`replaceTags` + tag CRUD UI 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量（无新纯函数则可不加）

### C · CLI **1.70.0**

- **Q2a** 命令形状：  
  - `opentask label set <issueRef> --ids 1,2,3 [--json]`（空 `--ids ""` / `--clear` → 清空；**Q3a**）  
  - `opentask label update <tagId> [--name ...] [--color ...] [--group-id ...] [--clear-group] [--json]`  
  - `opentask label attach <issueRef> --tag-id ID [--tag-id ID …]`（**Q4a** multi；保留既有位置参数 `attach ISSUE TAG` 兼容）  
  - `opentask label detach <issueRef> --tag-id ID [--tag-id ID …]`（同上）  
  - 可选薄读：`opentask label issue <issueRef> [--json]` → `list_issue_tags`  
- **Q5a** `api_client`：`replace_issue_tags` / `update_tag`（既有 attach/detach/list_issue_tags 保留）  
- pins → **1.70.0**；历史 epic 断言级联  
- **不**改 `label list|create|delete` 既有默认行为（attach/detach 单位置参数兼容）  
- **不**改 project health/timeline / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- writer/tag-writer 写路径对齐既有 BE；跨租户/缺资源 404  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- Initiative health CLI / 自动健康评估（无对称 BE / 另弧）  
- Tag group CLI 加厚（create/update/delete groups）— 可后薄刀，**本轮不强制**  
- 再开 project-health / cycle / lead/members / parent / trash / links / threading / start_date / project-templates / multi-assignee / issue-templates / project-watchers  
- Formula emit；远程 push / 开 PR / **自开 E87**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE PUT replace / PATCH tag / POST·DELETE attach 行为不变；跨租户/缺资源 404；writer 外写 403 |
| B | CLI **1.70.0** `label set` + `label update` + multi attach/detach 绿；位置参数 attach/detach 兼容 |
| C | api_client `replace_issue_tags` / `update_tag` 接线绿；历史 pins 级联 1.70.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主表面；无新 webhook；无新表/alembic；formula no-emit |
| 门禁 | BE 定向（既有 tags/issue-tags smoke + e86 spy）；CLI 定向 e86；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E87 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Label Set/Multi CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 PUT replace + PATCH tag + 既有 attach/detach |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.70.0**；`label set` + `label update` + multi `--tag-id` |
| D5 | `set` = 整组 replace（非 merge）；空 ids / `--clear` 清空 |
| D6 | 守 E40 D2/D7；不改 E63–E85 邻面主语义；不 push；不自开 E87 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用 PUT replace + PATCH tag + attach/detach；备选 Q1b 批量 multi-issue set 专用路由（不选——bulk-update 已覆盖） |
| Q2 | CLI 命令名？ | **Q2a** `label set` + `label update` + multi attach/detach；备选 Q2b 仅 `issue tags set` 挂 issue 组（不选——既有 `label` 组更贴 Linear） |
| Q3 | 清空语义？ | **Q3a** `--ids ""` 或 `--clear` → PUT `tag_ids=[]`；备选 Q3b 禁止清空（不选——replace API 已支持空） |
| Q4 | multi attach 形状？ | **Q4a** 可重复 `--tag-id` + 保留位置参数单 id 兼容；备选 Q4b 仅 comma `--ids`（不选——与 set 的 `--ids` 语义易混） |
| Q5 | VERSION？ | **Q5a** pins **1.70.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（replaceTags/UI 已齐）；备选 Q6b 重做 L picker（不选——浪费） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：`replace_issue_tags` / `update_tag`（TDD）  
3. CLI 1.70.0：`label set` + `label update` + multi attach/detach（兼容位置参数）  
4. 可选：`label issue` 读路径  
5. pins 级联 1.70.0  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `label set` PUT replace 200；空/`--clear` 清空；非法 tag 拒；跨 WS 隔离；writer 外 403  
- `label update` PATCH name/color/group；缺 tag 404  
- attach/detach 多 `--tag-id`；位置参数单 id 仍绿  
- api_client helpers 接线；CLI pins 1.70.0；命令 json/human  
- spy：未改 project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E87+；若 Yuri 改选可替换本草案）

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
22. **再开 project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
23. **Tag group CLI 加厚**（group create/update/delete/list 接线）— 后薄刀。  
24. **Initiative health CLI** — tip 无对称 BE；另扫后定。  
25. **自动健康评估 / AI 摘要** — 另弧。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.70.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E85-S1` @ `5fa6e3b8f79fde23b6fbcd59f3902ab578d71206`  
- 拟开：`sprint/E86-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e86-label-set-multi-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E87**

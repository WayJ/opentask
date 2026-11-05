# E82 Design：Issue Templates CLI mid · CLI 1.66.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E82  
基线拟：`sprint/E81-S1` @ `69b2112`（全文 `69b2112eb1d28f90af96ed626e19fe9932294025`；E81 design 基线 `4a9a1fa` ⊂ HEAD；E80 tip `f929dc8` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E82-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E83**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e82-issue-templates-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E82-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E81 连续闭合 … → Issue project-move integrity（E80）→ **Project milestones CLI mid（E81：issue_count + milestone CRUD CLI · 1.65.0）**。

E81 附录 runners-up（任务硬指引）+ tip 代码扫描：

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
21. **再开 milestones CLI / project-move / lead/members / parent / trash** — **刚闭，勿默认**  
22. **（扫描）Issue Templates CLI 对称 E72 + create `--template-id` + 缺 GET by id + FE seed 按钮** — **真缺口 · 本轮候选 mid**

轮换离开刚闭弧：**milestones CLI / project-move integrity / lead/members / parent-set / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage / TZ / 假日 / Initiative deps / 附件 ACL / Search / Insights**。  
**不**重开 E81 milestone serialize/CLI；本轮补的是 **Issue 模板生命周期 CLI + create 应用模板**，对称 E72 `project-template`。

代码实证 @ `69b2112`：

| 面 | 现状 |
|----|------|
| BE Issue Templates API | `GET/POST /api/issue-templates`、`POST /seed`、`PATCH/DELETE /{id}` 齐；`IssueTemplateService` CRUD + `ensure_seeds` + `get`；**无** `GET /{template_id}`（show 缺口） |
| create Issue | body `template_id` 已合并 payload（E9-S2） |
| FE | `workspace/issue-templates` 表 + 创建/编辑/删除；**无**显式 seed 按钮 / `fetchSeedIssueTemplates` |
| CLI | E72 有完整 `project-template *`；**无** `issue-template *`；**无** `issue create --template-id`；api_client **无** issue-template helpers |
| Linear 对齐 | Issue Template 工作区级；agent 应能管模板再 `create --template-id` |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue Templates CLI mid**：BE 补 `GET /{id}`；CLI **1.66.0** `issue-template list\|show\|create\|update\|delete\|seed` + `issue create --template-id`；FE seed 按钮 + api；无新 webhook；不改 E81/E80/E79/E72 主表面 | **中厚**；E81 runner-up #1；对称 E72；单 sprint |
| B | 仅 CLI list/create 两命令、无 GET/seed/create 旗标 | 过薄；缺 show/seed/对称 apply |
| C | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| D | bulk project_id / Q4b lazy-heal | 任务标薄刀/后置 |
| E | 再开 milestones / project-move / lead | 刚闭 |
| F | Project 私有 ACL / merge / 深拷贝 / 模板内 Issue stubs | 另大弧 / 过厚 / skip |

**建议拍板：A（Issue Templates CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members / E78 parent / E77 trash / E72 project-template 语义；CLI **1.66.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b | 薄刀 / 后置 |
| 再开 milestones / project-move / lead / parent / trash / … | 刚闭 |
| 仅 CLI 两命令无 GET/seed/create 旗标 | 过薄；升 mid 要 GET + seed + create `--template-id` + FE seed |

### Why this Epic now（一句话）

E72 已给 **Project** 模板完整 CLI，E9-S2 已有 Issue 模板 API/FE 与 create 合并，但 agent **仍无法**列举/展示/创建/更新/删除/seed Issue 模板，也无法 `issue create --template-id`——用中厚刀一次补上 **GET by id + CLI CRUD/seed + create 旗标 + FE seed**，闭合 Linear「先有 Issue Template 再开 Issue」脚本面，且 **不动** 刚闭的 milestones / project-move / lead。

---

## 1. 目标

成功标准：member+ 可用 CLI **1.66.0** 做 `issue-template list|show|create|update|delete|seed`；`issue create --template-id` 合并模板 payload；BE `GET /api/issue-templates/{id}`；FE 工作区模板页可一键 seed；viewer 写 403；跨租户 404；**不**改 E81 milestone / E80 helper / E79 roster / E72 project-template 主语义；**无**新 webhook；formula no-emit；**不**自开 E83。

### A · BE

- **Q1a** 新增 `GET /api/issue-templates/{template_id}` → `serialize_issue_template`（复用 `IssueTemplateService.get`；跨租户/不存在 404）  
- 既有 list（ensure seeds）/ seed / create / update / delete **行为不变**  
- **Q3a** delete 允许删 seed 与自定义（对齐既有 API；不另加 409 保护）  
- viewer 写 403（既有 `require_writer`）；跨租户 404  
- **不**改 milestone / project-move / lead/members / parent / trash / project-template routers  

### B · FE

- `workspace/issue-templates`：增加 **恢复内置 / Seed** 按钮 → `POST /api/issue-templates/seed`；`fetchSeedIssueTemplates`  
- vitest：纯函数如 `issueTemplateSourceLabel(source)` 或 seed 确认文案 helper（薄）  
- build ok；守 E63 `f`+`r`  
- **不**重做整页 CRUD（已有）

### C · CLI **1.66.0**

- 顶层组（对齐 E72 `project-template`）：  
  - `opentask issue-template list [--json]`  
  - `opentask issue-template show <templateId> [--json]`  
  - `opentask issue-template create --name NAME [--description ...] [--icon ...] [--payload-json '{...}'] [--sort-order N] [--json]`  
  - `opentask issue-template update <templateId> [--name ...] [--description ...] [--icon ...] [--payload-json ...] [--sort-order ...] [--json]`  
  - `opentask issue-template delete <templateId> [--json]`（**Q3a** 允许，含 seed）  
  - `opentask issue-template seed [--json]`（**Q4a** → `POST /seed`）  
- Issue：  
  - `issue create ... --template-id <id>`（**Q5a**；非法/跨租户随 BE 404/400）  
- `api_client` 补 issue-template list/get/create/update/delete/seed + `create_issue(..., template_id=)`  
- pins → **1.66.0**；历史 epic 断言级联  

### D · 安全 / 邻面 / no-emit

- 跨租户 404；viewer 写 403  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 milestone CRUD / project-move / parent / trash / links / 附件 / VCS / duplicate 主路径  
- **不**改 E72 `project-template` 命令与 payload 语义  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、**模板内 Issue stubs**、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E81 milestones CLI / issue_count / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- 再开 lead/members / parent / trash / links / threading / start_date / project-templates / multi-assignee  
- Formula emit；远程 push / 开 PR / **自开 E83**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | `GET /api/issue-templates/{id}` 200 + serialize；跨租户/缺失 404 |
| B | seed POST 后 list 含内置；viewer POST/PATCH/DELETE 403 |
| C | CLI **1.66.0** `issue-template list\|show\|create\|update\|delete\|seed` 绿 |
| D | `issue create --template-id` 合并 type/priority/description（空 title 可取模板 title）绿 |
| E | FE seed 按钮 + vitest；build ok；`f`+`r` 仍在 |
| F | 未改 E81 milestone / E80 helper / E79 roster / E72 project-template 主表面；无新 webhook；formula no-emit |
| 门禁 | BE 定向 e82/issue_templates；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E83 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue Templates CLI mid**（方案 A） |
| D2 | BE 补 GET by id；其余 CRUD/seed 复用既有 |
| D3 | 无新 webhook / 无新 timeline enum / 无新表 |
| D4 | CLI = **1.66.0**；`issue-template *` + `issue create --template-id` |
| D5 | delete **允许**含 seed（API 已开放）；seed 命令显式 |
| D6 | 守 E40 D2/D7；不改 E63–E81 邻面主语义；不 push；不自开 E83 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否补 GET by id？ | **Q1a** 是（CLI show / 对称 project-template）；备选 Q1b show 从 list 过滤（不选——浪费且无 404 语义） |
| Q2 | CLI 命令名？ | **Q2a** 顶层 `issue-template`（对齐 `project-template`）；备选 Q2b `issue template` 子组（不选——与 comment/link 子资源混淆） |
| Q3 | 可否删 seed 模板？ | **Q3a** 允许（既有 API）；备选 Q3b seed 403/409（不选——打破既有） |
| Q4 | 是否暴露 seed 命令/FE 按钮？ | **Q4a** CLI `seed` + FE 按钮；备选 Q4b 仅靠 list ensure（不选——缺显式运维面） |
| Q5 | Issue 创建旗标？ | **Q5a** `issue create --template-id` + pins **1.66.0**；备选 Q5b 仅 CRUD 不管 create（不选——对称缺口） |
| Q6 | FE 范围？ | **Q6a** seed 按钮 + api + 薄 vitest；不重做 CRUD；备选 Q6b 零 FE（不选——seed 运维面不完整） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. BE：`GET /{id}`（TDD）  
3. FE：seed 按钮 + api + vitest  
4. CLI 1.66.0 `issue-template *` + api_client  
5. CLI `issue create --template-id`  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- GET by id 200；跨 WS 404；viewer 写 403  
- seed → list 含 builtin seedKey；delete 自定义绿  
- CLI pins 1.66.0；list/show/create/update/delete/seed；create --template-id  
- spy：未改 `milestone/service.py` issue_count 路径 / `issue_project_move.py` / E72 project-template；无新 webhook；formula no-emit  
- FE vitest；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E83+；若 Yuri 改选可替换本草案）

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
21. **再开 milestones CLI / project-move / lead / parent / trash …** — 刚闭，勿默认。  
22. **（扫描）其它 mid**：Project watchers CLI 对称、cycle 容量加厚、label 批量 — 可后列；本轮不压过 Templates CLI。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.66.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E81-S1` @ `69b2112eb1d28f90af96ed626e19fe9932294025`  
- 拟开：`sprint/E82-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e82-issue-templates-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E83**

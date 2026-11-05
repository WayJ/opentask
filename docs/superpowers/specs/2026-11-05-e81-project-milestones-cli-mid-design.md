# E81 Design：Project milestones CLI mid · CLI 1.65.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E81  
基线拟：`sprint/E80-S1` @ `f929dc8`（全文 `f929dc8e2974a04fc8ee0e24427d18fbc95a5e8c`；E80 design 基线 `171ae4f` ⊂ HEAD；E79 tip `d84f6e4` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E81-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E82**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e81-project-milestones-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E81-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E80 连续闭合 … → Project lead + members（E79）→ **Issue project-move integrity mid（E80：换项目自清 milestone · CLI 1.64.0）**。

E80 附录 runners-up（任务硬指引）+ tip 代码扫描：

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
21. **（扫描）Project Milestone CRUD CLI + issue create/list --milestone + issue_count** — **真缺口 · 本轮候选 mid**  
22. **（扫描）Issue Templates CLI 对称 E72** — 次之（templates 轮换刚闭旁；本轮次之 runner-up）

轮换离开刚闭弧：**project-move integrity / lead/members / parent-set / trash / links / duplicate / threading / start_date / templates / multi-assignee / childProgress / 评论附件 / Form→Triage / TZ / 假日 / Initiative deps / 附件 ACL / Search / Insights**。  
**不**重开 E80 自清 helper；本轮补的是 **里程碑生命周期 CLI + 计数展示**，不是再改换项目语义。

代码实证 @ `f929dc8`：

| 面 | 现状 |
|----|------|
| BE Milestone API | `GET/POST/PATCH/DELETE /api/projects/{id}/milestones` 齐；`MilestoneService` CRUD；删时 FK `issues.milestone_id ON DELETE SET NULL` |
| serialize | **无** `issue_count`；FE 表无法一眼见占用 |
| FE | `workflow/project-detail` 已有里程碑表 + 创建/编辑/删除模态 |
| CLI | E80 仅 `issue update --milestone`/`--clear-milestone`；**无** `project milestone *`；**无** `issue create --milestone`；**无** `issue list --milestone`（BE list 已支持 `milestone_id`/`__none__`） |
| api_client | **无** list/create/update/delete milestone helpers |
| Linear 对齐 | Milestone 从属 Project；CLI 应能管里程碑再指派 Issue |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Project milestones CLI mid**：BE serialize + list 附 `issue_count`；CLI **1.65.0** `project milestone list\|create\|show\|update\|delete` + `issue create --milestone` + `issue list --milestone`；FE 详情表显示占用数；无新 webhook；不改 E80 helper | **中厚**；E80 后自然下一刀；单 sprint |
| B | 仅加 CLI list/create 两命令 | 过薄；缺 count/list 过滤/create 对称 |
| C | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| D | bulk project_id / Q4b lazy-heal | 任务标薄刀/后置 |
| E | Issue Templates CLI 对称 E72 | 真缺口但 templates 轮换旁；列入 runners-up |
| F | Project 私有 ACL / merge / 深拷贝 | 另大弧 / 过厚 |

**建议拍板：A（Project milestones CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E80 `apply_project_move_integrity` / E79 lead/members / E78 parent / E77 trash；CLI **1.65.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b | 薄刀 / 后置 |
| Issue Templates CLI | 真缺口；templates 轮换旁 → E82+ |
| 再开 project-move / lead / parent / trash / … | 刚闭 |
| 仅 CLI 两命令无 count | 过薄；升 mid 要 BE count + create/list 旗标 + FE 列 |

### Why this Epic now（一句话）

E80 已让 CLI **指派** milestone，但 agent **仍无法**创建/列举/更新/删除项目里程碑，且 BE/FE 看不到占用数——用中厚刀一次补上 **issue_count + CLI CRUD + create/list --milestone + FE 占用列**，闭合 Linear「先有 Milestone 再挂 Issue」脚本面，且 **不动** E80 换项目自清语义。

---

## 1. 目标

成功标准：member+ 可用 CLI **1.65.0** 对某 Project 做 milestone `list|create|show|update|delete`；`issue create --milestone` / `issue list --milestone`（含 `__none__`）可用；serialize/列表含 **`issue_count`**；FE 项目详情里程碑表展示占用；viewer 写 403；跨租户/跨项目 404；删里程碑依赖 DB `SET NULL`（**Q3a** 不另写业务清扫）；**不**改 E80 helper；**无**新 webhook；formula no-emit；**不**自开 E82。

### A · BE

- **Q1a** `serialize_milestone` 增加 `issue_count`（同 project+workspace 下 `issues.milestone_id = id AND NOT is_deleted` 计数）；list/get/create/update 响应均带  
- list 可选 **Q2a** `?status=planned|done` 过滤（省略=全部）；保持 position/created_at 排序  
- delete：**Q3a** 沿用 FK `ON DELETE SET NULL`；**不**手写批量 UPDATE；**不**新 timeline enum / **不**新 webhook（可选验收断言删后 issue.milestone_id 变 null）  
- 跨项目 milestone id → 404；viewer 写 403（既有 `require_writer`）；跨租户 404  
- **不**改 `apply_project_move_integrity` / `milestone_for_duplicate`；**不**改 lead/members/parent/trash  

### B · FE

- `workflow/project-detail` 里程碑表增加 **占用**列（`issue_count`）；删除确认文案可提「将清空 N 个 Issue 的里程碑引用」（若 count>0）  
- 类型/API 客户端认新字段；vitest：纯函数 `formatMilestoneIssueCount(n)` 或列 render helper  
- build ok；守 E63 `f`+`r`  
- **不**重做整页 CRUD（已有）

### C · CLI **1.65.0**

- 子组（对齐 E79 `project lead|member`）：  
  - `opentask project milestone list <projectId> [--status planned|done] [--json]`  
  - `opentask project milestone create <projectId> --name NAME [--description ...] [--target-date YYYY-MM-DD] [--status planned|done] [--position N] [--json]`  
  - `opentask project milestone show <projectId> <milestoneId> [--json]`  
  - `opentask project milestone update <projectId> <milestoneId> [--name ...] [--description ...] [--target-date ...] [--status ...] [--position ...] [--json]`  
  - `opentask project milestone delete <projectId> <milestoneId> [--json]`（**Q4a** 允许删；与 `project delete` CLI 禁删策略不同——里程碑可逆影响小且 API 已开放）  
- Issue：  
  - `issue create ... --milestone <id>`（须同请求/活动 project 合法；非法 400）  
  - `issue list --milestone <id|__none__>`（接既有 BE query）  
- `api_client` 补 milestone CRUD helpers  
- pins → **1.65.0**；历史 epic 断言级联  

### D · 安全 / 邻面 / no-emit

- 跨租户 404；viewer 写 403  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 parent/trash/links/附件/VCS/duplicate 主路径；不改 E80 integrity  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E80 换项目自清 / duplicate milestone 边 / Q4b lazy-heal  
- **bulk_update project_id**（后薄刀）  
- Issue Templates CLI（E82+ runner-up）  
- Project 私有 ACL / 按 member 过滤 Issue  
- 再开 lead/members / parent / trash / links / threading / start_date / templates / multi-assignee  
- Formula emit；远程 push / 开 PR / **自开 E82**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | list/get milestone 含 `issue_count`；挂 2 个 issue 后 count=2；删除后 issue.milestone_id null（SET NULL） |
| B | `?status=done` 仅回 done；跨项目/跨租户 404；viewer POST 403 |
| C | CLI **1.65.0** `project milestone list\|create\|show\|update\|delete` 绿 |
| D | `issue create --milestone` + `issue list --milestone`/`__none__` 绿 |
| E | FE 占用列 + vitest；build ok；`f`+`r` 仍在 |
| F | 未改 E80 helper / E79 roster / E78 parent；无新 webhook；formula no-emit |
| 门禁 | BE 定向 e81/milestone；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E82 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Project milestones CLI mid**（方案 A） |
| D2 | BE `issue_count` + 可选 status 过滤；删靠 FK SET NULL |
| D3 | 无新 webhook / 无新 timeline enum |
| D4 | CLI = **1.65.0**；`project milestone *` + issue create/list `--milestone` |
| D5 | milestone delete **允许** CLI（不同于 project delete 禁令） |
| D6 | 守 E40 D2/D7；不改 E63–E80 邻面主语义；不 push；不自开 E82 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | issue_count？ | **Q1a** serialize/list/get/create/update 均带；备选 Q1b 仅 list（不选） |
| Q2 | list 过滤？ | **Q2a** 可选 `?status=`；备选 Q2b 本轮不过滤（不选） |
| Q3 | 删除语义？ | **Q3a** DB SET NULL；不手写 bulk clear；不新 timeline/webhook；备选 Q3b 有引用则 409（不选——打破既有 API） |
| Q4 | CLI 是否允许 delete？ | **Q4a** 允许（API 已开放；影响小于 project delete）；备选 Q4b 禁删仅文档（不选） |
| Q5 | CLI 命令形态？ | **Q5a** `project milestone …` 子组（对齐 lead/member）；备选 Q5b 顶层 `milestone` 组（不选） |
| Q6 | Issue 旗标？ | **Q6a** `create --milestone` + `list --milestone`/`__none__` + pins **1.65.0**；备选 Q6b 仅 CRUD 不管 issue（不选——E80 后对称缺口） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. BE：`issue_count` + status filter（TDD）  
3. FE：占用列 + 删除提示 + vitest  
4. CLI 1.65.0 `project milestone *` + api_client  
5. CLI `issue create|list --milestone`  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- create milestone → list 含 id 且 issue_count=0  
- 两 issue 挂同一 milestone → count=2；delete milestone → 两 issue milestone_id null；count 路径 404  
- status 过滤；viewer 写 403；跨 WS 404  
- CLI pins 1.65.0；create/list --milestone；定向 e81  
- spy：未改 `issue_project_move.py` 行为；无新 webhook 名；formula no-emit  
- FE vitest；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E82+；若 Yuri 改选可替换本草案）

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
21. **Issue Templates CLI mid**（对称 E72；create `--template-id`）— **E82 优先候选**。  
22. **再开 project-move / lead / parent / trash …** — 刚闭，勿默认。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.65.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E80-S1` @ `f929dc8e2974a04fc8ee0e24427d18fbc95a5e8c`  
- 拟开：`sprint/E81-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e81-project-milestones-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E82**

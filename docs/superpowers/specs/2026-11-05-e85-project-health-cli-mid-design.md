# E85 Design：Project Health CLI mid · CLI 1.69.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E85  
基线拟：`sprint/E84-S1` @ `dde41b1`（全文 `dde41b115e39003789ed748428e08f21749ae7cc`；E84 design 基线 `02cd994` ⊂ HEAD；E83 tip `f066e88` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E85-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E86**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e85-project-health-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E85-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E84 连续闭合 … → Project Watchers CLI mid（E83 · 1.67.0）→ **Cycle CLI mid（E84：`cycle generate-upcoming|update|delete` · 1.68.0）**。

E84 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `dde41b1`：

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
22. **再开 cycle CLI / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **（扫描）Project health CLI（首选）/ Label `set`/multi（半齐）** — 实证后 **Project Health CLI mid** 为真 mid 缺口

轮换离开刚闭弧：**cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E84 cycle；本轮补的是 **Project Health CLI 缺口**（BE/FE 已齐，CLI 全无）。

代码实证 @ `dde41b1`：

| 面 | 现状 |
|----|------|
| BE Project Health | `GET/POST /api/projects/{id}/health`（`history` query）；`GET /{id}/timeline`；status ∈ `{on_track,at_risk,off_track}`；writer 门禁；`ProjectHealthService` + timeline + serialize 齐（E8-S2） |
| FE Project Health | `project.ts` 已有 `fetchProjectHealth` / `postProjectHealth`；project-detail UI 已有 |
| CLI Project | `list\|show\|create\|update\|delete` + E83 `watch\|unwatch\|watchers` + E79 lead/member + E81 milestone；api_client / core **全无** health / timeline helpers；`project show` 无 health 字段 |
| Label | CLI `attach\|detach` 单条；BE `PUT /api/issues/{id}/tags` replace 齐；bulk_update 已有 `tag_ids`；「set/批量」半齐 |
| Cycle | E84 已闭合 generate-upcoming/update/delete · 1.68.0 — **本轮勿再开** |
| Linear 对齐 | agent 应能脚本「读/报项目健康 / 写 note / 可选 timeline」，而非只在 FE 点选 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Project Health CLI mid**：CLI **1.69.0** nested `project health get\|set`（+ `--history`）+ 可选 `project timeline` + api_client；`project show` 附 latest health；复用既有 BE；**无**新表/webhook；不改 E84–E79 主表面；FE 已齐 → 零产品 FE | **中厚**；E84 runner-up #23 首选；闭合 Health 脚本面；单 sprint |
| B | 仅 `project show` 附 health 字段、无 set/history | 过薄；写路径仍断 |
| C | Label `set` → PUT replace；多 issue multi-attach | 半齐（replace + bulk `tag_ids`）；缺口糊；次之 → E86+ |
| D | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| E | bulk project_id / Q4b lazy-heal / `project list --watching` | 任务标薄刀/后置 |
| F | 再开 cycle / project-watchers / issue-templates / milestones / project-move / lead | 刚闭 |
| G | Project 私有 ACL / merge / 深拷贝 / 模板 stubs | 另大弧 / 过厚 / skip |

**建议拍板：A（Project Health CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.69.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置 |
| 再开 cycle / project-watchers / issue-templates / milestones / project-move / lead / … | 刚闭 |
| Label 批量 set/multi | replace API + bulk `tag_ids` 已半齐；缺口糊 → E86+ |
| 仅 show 附 health 无 set | 过薄 |

### Why this Epic now（一句话）

BE/FE 早已能 GET/POST Project Health + timeline，CLI 却在 E83 只补了 watchers、**完全没有** health helpers——agent **无法**脚本「读健康 / 报 at_risk + note / 拉 timeline」。用中厚刀一次补上 **health 组 + api_client + show 字段**，闭合 Linear Project Health 脚本面，且 **不动** 刚闭的 cycle / watchers / issue-templates / milestones / project-move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.69.0** 做 `project health get|set`（含 `--history`）与可选 `project timeline`；api_client 有对应 helpers；`project show` 附 latest health；跨租户/缺 project 404（既有 BE）；**不**改 E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E86。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `GET /api/projects/{project_id}/health?history=`  
  - `POST /api/projects/{project_id}/health`（body: `status`, `note?`）  
  - `GET /api/projects/{project_id}/timeline`（**Q4a** 纳入本轮，薄接线）  
- writer 门禁 / 跨租户·缺 project 404 不变（既有 `require_writer` + service）  
- status 枚举不变：`on_track` / `at_risk` / `off_track`  
- **不**本轮改健康算法 / 自动评估 cron / initiative health  
- **不**改 cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`project.ts` health + UI 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量（无新纯函数则可不加）

### C · CLI **1.69.0**

- **Q2a** 命令形状（对齐既有 nested `project lead|member|milestone` 组）：  
  - `opentask project health get <projectId> [--history] [--json]`  
  - `opentask project health set <projectId> --status on_track|at_risk|off_track [--note ...] [--json]`  
  - `opentask project timeline <projectId> [--json]`（**Q4a** 纳入）  
- **Q3a** `project show` 附 `health` / `health_status`（latest；失败时降级为空，不阻断 show）  
- **Q5a** `api_client`：`get_project_health` / `post_project_health` / `get_project_timeline`  
- pins → **1.69.0**；历史 epic 断言级联  
- **不**改 list/create/update/delete/watch/unwatch/watchers/lead/member/milestone 既有行为

### D · 安全 / 邻面 / no-emit

- writer-only 写路径（对齐既有 BE POST health）；跨租户/缺资源 404  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 cycle / project-watchers 主路径语义 / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- Label replace/`set` 批量 CLI（runners-up → E86+）  
- 自动健康评估 / AI 摘要 / initiative health CLI  
- 再开 cycle / lead/members / parent / trash / links / threading / start_date / project-templates / multi-assignee / issue-templates / project-watchers  
- Formula emit；远程 push / 开 PR / **自开 E86**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE GET/POST health + timeline 行为不变；跨租户/缺 project 404；writer 外 POST 403；非法 status 拒 |
| B | CLI **1.69.0** `project health get\|set` + `project timeline` 绿；`project show` 含 health 字段 |
| C | api_client 三 helpers 接线绿；历史 pins 级联 1.69.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主表面；无新 webhook；无新表/alembic；formula no-emit |
| 门禁 | BE 定向（既有 project_health smoke + e85 spy）；CLI 定向 e85；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E86 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Project Health CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 E8-S2 GET/POST health + timeline |
| D3 | 无新 webhook / 无新 timeline enum / 无新表 |
| D4 | CLI = **1.69.0**；nested `project health get\|set` + `project timeline` |
| D5 | 命令挂 nested `health` 组（对齐 lead/member/milestone），非扁平 `project-health-*` |
| D6 | 守 E40 D2/D7；不改 E63–E84 邻面主语义；不 push；不自开 E86 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有 GET/POST health + timeline；备选 Q1b 另做 bulk health 报表（不选——过厚） |
| Q2 | CLI 命令名？ | **Q2a** nested `project health get\|set` + `project timeline`；备选 Q2b 扁平 `project health-get`（不选——与 lead/milestone 组不一致） |
| Q3 | `project show` 是否附 health？ | **Q3a** 是（latest；拉取失败降级）；备选 Q3b 不附（不选——对称 E83 watching_count） |
| Q4 | timeline 是否本轮？ | **Q4a** 是（薄接线，同 HealthService）；备选 Q4b 推迟（不选——一端点一行） |
| Q5 | VERSION？ | **Q5a** pins **1.69.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（health UI/api 已齐）；备选 Q6b 重做 health 面板（不选——浪费） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：`get_project_health` / `post_project_health` / `get_project_timeline`（TDD）  
3. CLI 1.69.0 nested `project health get|set` + `project timeline`；`project show` 附 health  
4. pins 级联 1.69.0  
5. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- health get 200 + latest；`--history` 返回 history 列表  
- health set `on_track|at_risk|off_track` + optional note；writer 外 403；非法 status 拒；跨 WS 隔离  
- timeline 200；缺 project 404  
- `project show` JSON 含 health / health_status（或 latest 嵌套）  
- CLI pins 1.69.0；命令 json/human  
- spy：未改 cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E86+；若 Yuri 改选可替换本草案）

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
22. **再开 cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
23. **Label 批量**：`label set` → `PUT /{issue}/tags` replace；多 issue multi-attach — **E86 首选**（半齐：BE replace + bulk `tag_ids` 已有；CLI 仅单条 attach/detach）。  
24. **Initiative health CLI**（若有对称 BE）— 另扫后定。  
25. **自动健康评估 / AI 摘要** — 另弧（本轮只补 CLI 接线）。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.69.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E84-S1` @ `dde41b115e39003789ed748428e08f21749ae7cc`  
- 拟开：`sprint/E85-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e85-project-health-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E86**

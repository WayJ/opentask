# E91 Design：Issue Board Move CLI mid · CLI 1.75.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E91  
基线拟：`sprint/E90-S1` @ `4b7f34d`（全文 `4b7f34d4eeedd93fc0e22b4528bd22979229137d`；E90 design 基线 `a4dd51e` ⊂ HEAD；E89 tip `d8337ea` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E91-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**大软不自开 E92**。  
入库：`docs/superpowers/specs/2026-11-05-e91-issue-board-move-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E90 连续闭合 … → Custom Fields Reorder CLI mid（E89 · 1.73.0）→ Initiative Projects CLI mid（E90：`initiative projects set` + `initiative project attach|detach` · 1.74.0）。

E90 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `4b7f34d`：

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
22. **再开 initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **Initiative health CLI（独立 health get/set 弧）** — tip **仍无** 对称 `GET/POST /api/initiatives/{id}/health`；`to_response` 仅嵌套 `healthSummary` — **不选为本轮主 Epic**  
24. **自动健康评估 / AI 摘要** — **另弧**  
25. **（扫描）Display prefs CLI** — BE `GET/PUT /api/display-prefs/issue` + FE 已齐；E49 明示无 CLI 子命令；api_client **零** helpers — agent 价值偏薄，runners-up  
26. **（扫描）Saved View write / favorite / save-as** — BE `POST/PATCH/DELETE` + `favorite` + `save-as` **齐**；CLI 仅 `view list|show|use`；api_client **无** write helpers — 真 mid 但面比「单端点」宽（5+ 写路径），runners-up  
27. **（扫描）Issue board/move** — BE **`POST /api/issues/board/move`**（body **`issue_id`/`status`/`position`/`ordered_ids?` snake_case**）+ FE `issueApi.moveOnBoard` **齐**；既有 `backend/tests/api/test_issue_board.py` 覆盖 status+position / ordered_ids 重排 / 跨 WS 403；CLI/api_client **完全零** — agent 无法脚本「看板拖拽落盘（原子 status+position，可选同列重排）」——实证为最清晰 mid 缺口（闭合 Kanban 位置脚本面；与 E86–E90「BE/FE 齐、CLI 洞」同构；单端点、单 sprint）

轮换离开刚闭弧：**initiative-projects / CF reorder / favorite reorder / tag-group CLI / label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E90 Initiative Projects；本轮补的是 **Issue 看板落盘脚本缺口**（BE/FE 已齐，agent 无法用 CLI 原子改 status+position）。

代码实证 @ `4b7f34d`：

| 面 | 现状 |
|----|------|
| BE board/move | `POST /api/issues/board/move` body `{issue_id, status, position, ordered_ids?}`（**snake_case**，与 FE 一致）；原子更新 status+position；`ordered_ids` 可重写目标列 position；跨 WS → **403**；缺 Issue → **404** |
| FE Issue board | `issueApi.moveOnBoard({issue_id, status, position, ordered_ids?})` → POST **齐** |
| CLI Issue | `issue update` 可改 status，但 **无** `--position`、**无** board-move 命令；api_client **无** `move_issue_on_board` — agent 无法脚本 Kanban 落盘 / 同列重排 |
| Bulk project_id | `IssueBulkUpdate` **仍无** `project_id` — 仍薄刀/后置、触 BE |
| Project list watching | CLI/BE 仍无 watching 过滤 — 仍薄刀 |
| Linear 对齐 | agent 应能脚本「Issue CRUD + 看板落盘」，与 Linear board 拖拽语义对齐 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue Board Move CLI mid**：CLI **1.75.0** `issue board-move`（或 `issue board move`）；api_client 一 helper → POST + snake_case body；复用既有端点；**无**新表/webhook/路由；FE 已齐 → 零产品 FE；可选 `issue show` 薄补 Position 列 | **薄→中薄**；闭合 Kanban 脚本面；单 sprint；自然续「BE/FE 齐、CLI 洞」 |
| B | 仅文档说明用 FE 拖拽 | 过薄；agent 仍断 |
| C | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service + E80 邻弧；任务标薄刀 |
| D | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| E | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| F | Display prefs / Saved View write | 真洞但价值或面宽次之（runners-up） |
| G | Initiative health 独立 CLI / 甘特 / Activity Push / 门户 / Q2b / … | 无对称 health 路由 / prefer skip / 勿默认 |
| H | 再开 initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Issue Board Move CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.75.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成「Initiative health CLI」或「Saved View 全写面」。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up；watching/bulk 需 BE） |
| Display prefs / Saved View write | runners-up（价值或面宽次之） |
| 再开 initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health 独立 CLI | tip 无对称 `/health` 路由 → 不选为本轮主 Epic |
| 仅文档 / 不暴露 CLI | 过薄 |
| 仅给 `issue update` 加 `--position` | 过薄且 **不**覆盖 `ordered_ids` 同列重排；board/move 才是原子契约 |

### Why this Epic now（一句话）

E80 补齐了 Issue **换项目**，E86–E90 连续闭合「BE/FE 齐、CLI 洞」关联/reorder 面，但 **看板落盘** BE/FE（`POST /api/issues/board/move`）早已齐而 CLI **完全空洞**——agent 无法脚本「原子改 status+position / 可选同列 `ordered_ids` 重排」；用薄刀一次闭合 Linear-aligned Kanban 脚本面，且 **不动** 刚闭的 initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.75.0** 做 Issue **board-move**；api_client 有对应 helper；复用既有 `POST /api/issues/board/move`；语义对齐既有 BE（原子 status+position；可选 `ordered_ids` 重写列序；跨租户 403；缺资源 404）；**不**改 E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E92。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `POST /api/issues/board/move` body `{ issue_id, status, position, ordered_ids? }`（**snake_case**，与 FE/`test_issue_board` 一致；**非** `issueId`/`orderedIds`）  
  - 既有 Issue CRUD / bulk-update / update（本轮不改语义）  
- writer/鉴权门禁不变；跨 WS → 403；缺 Issue → 404；`ordered_ids` 含他列时可强制改 status（既有 service 行为）  
- **不**本轮改 Issue 模型 / 看板 FE / formula；**不**把 board-move 误做成仅 `issue.update` 的 position 字段补丁  
- **不**改 initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`issueApi.moveOnBoard` 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.75.0**

- **Q2a** 命令形状：  
  - `opentask issue board-move <issue_id> --status STATUS --position N [--ordered-ids ID1,ID2,...] [--json]`  
  - 备选兼容：`issue board move …` 子组（若成本低可双通道；默认以 **`board-move` 单命令** 为主，贴既有 `bulk-update` 命名）  
  - `--status` 取值对齐 `IssueStatus`：`open|in_progress|feedback|resolved|closed|rejected`（至少覆盖既有 CLI update 常用 + board 测试用到的）  
  - `--position` 必填（`>=0`）；`--ordered-ids` 可选 CSV  
- **Q3a** 语义对齐 BE：api_client  
  - `move_issue_on_board(issue_id, status, position, ordered_ids=None)` → **POST** `/api/issues/board/move` + snake_case body  
  - 失败透传 BE 403/404/422/…  
- **Q4a** 挂在既有 `issue` 组下；不新开顶层命令；`issue show`：**可选**人类表薄补 `Position`（json 若已有则只补可读列）；**不**改 `issue update` 默认行为（本轮 **不**顺手加 `--position` 到 update，以免与 board-move 双通道混淆——备选 Q4b 可加，默认不加）  
- **Q5a** pins → **1.75.0**；历史 epic 断言级联  
- **不**改 `issue create|update|delete|bulk-update|…` 默认行为；**不**改 initiative / CF / favorite / tag-group / label / project health / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- writer 写路径对齐既有 BE；跨租户/缺资源既有  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；**formula no-emit**  
- **不**新增 `/api/initiatives/{id}/health`；不把本 Epic 扩成 Saved View 全写面

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Display prefs CLI / Saved View write（runners-up）  
- Project 私有 ACL / 按 member 过滤 Issue  
- **Initiative health 独立 CLI** / 自动健康评估（无对称 `/health` 路由 / 另弧）  
- Formula emit；远程 push / 开 PR / **自开 E92**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE `POST /api/issues/board/move` 行为不变；跨 WS 403；缺 Issue 404；ordered_ids 重排语义不变 |
| B | CLI **1.75.0** `issue board-move` 绿；失败透传 |
| C | api_client helper 接线绿（POST + snake_case `issue_id`/`status`/`position`/`ordered_ids`）；历史 pins 级联 1.75.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster；无新 webhook；无新表/alembic；formula no-emit；无独立 initiative health 路由 |
| 门禁 | BE 定向（`test_issue_board` smoke 可选 + e91 spy）；CLI 定向 e91；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E92 |

---

## 4. ADR（Yuri 已确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue Board Move CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 **POST** `/api/issues/board/move`（body **snake_case**；非 camelCase） |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.75.0**；`issue board-move --status … --position … [--ordered-ids …]` |
| D5 | 语义 = 既有 BE（原子 status+position；可选 ordered_ids）；show 可薄补 Position |
| D6 | 守 E40 D2/D7；不改 E63–E90 邻面主语义；不 push；不自开 E92；**不做** Initiative health/甘特 / Saved View 全写 Epic |

---

## 5. 开放问题（Yuri 已一键全收建议默认）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有 POST `/api/issues/board/move`；备选 Q1b 另开 `/api/issues/{id}/board-move`（不选——既有端点+测试已齐） |
| Q2 | CLI 命令挂载？ | **Q2a** `issue board-move` 单命令（贴 `bulk-update`）；备选 Q2b `issue board move` 子组（可并存，默认不强制）；备选 Q2c 顶层 `board-move`（不选） |
| Q3 | body 字段命名？ | **Q3a** api_client 发 **snake_case** `issue_id`/`ordered_ids`（对齐 BE/FE/test）；备选 Q3b camelCase（不选——本端点契约即 snake） |
| Q4 | 是否改 `issue update` / show？ | **Q4a** **不**给 `issue update` 加 `--position`（避免双通道）；`issue show` 可选薄补 Position；备选 Q4b 同时给 update 加 `--position`（不选——本轮契约是 board-move） |
| Q5 | VERSION？ | **Q5a** pins **1.75.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（`moveOnBoard` 已齐）；备选 Q6b 改 FE 命名/封装（不选——非本轮必须） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：`move_issue_on_board` → POST + snake_case body（TDD）  
3. CLI 1.75.0：`issue board-move --status --position [--ordered-ids]`  
4. 可选：`issue show` 人类表薄补 Position  
5. pins 级联 1.75.0  
6. BE spy：无新路由/alembic；board/move marker；邻面 marker；formula no-emit；**无**新 initiative `/health`  
7. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `issue board-move` 200：返回 status/position 与传入一致；再 `issue show --json` 校验  
- 带 `--ordered-ids`：目标列顺序与 positions 重写（对齐 `test_issue_board`）  
- 跨 WS → 403；缺 Issue → 404；失败透传  
- api_client helper 断言：`self.post` + `/api/issues/board/move`；body 含 `issue_id`/`status`/`position`；禁误用 camelCase `issueId`/`orderedIds` 作为唯一键（若框架双写需注释；默认 snake）  
- CLI pins 1.75.0；命令 json/human  
- spy：未改 initiative projects helpers / CF reorder / favorite reorder / tag-group / label set/multi / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic；无新 initiative `/health` 路由  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E92+；若 Yuri 改选可替换本草案）

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
22. **再开 initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / …** — 刚闭，勿默认。  
23. **Initiative health 独立 CLI** — tip 无对称 `/health` 路由；嵌套 `healthSummary` 仅随 GET/projects 返回 — 另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  
25. **Display prefs CLI** — BE/FE 齐、CLI 空洞；agent 价值偏薄。  
26. **Saved View create/update/favorite/save-as CLI** — BE 齐；CLI 仅 list/show/use — 面较宽。  
27. **（本轮主推已选）Issue board/move CLI** — 若改选则回退到 Saved View write 或 Display prefs。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.75.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E90-S1` @ `4b7f34d4eeedd93fc0e22b4528bd22979229137d`  
- 拟开：`sprint/E91-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e91-issue-board-move-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E92**

# E93 Design：Display Prefs CLI mid · CLI 1.77.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E93  
基线拟：`sprint/E92-S1` @ `48e6bb3`（全文 `48e6bb3f1b9bd8c61acf482d2e3b6bc1383aa625`；E92 design 基线 `4df134a` ⊂ HEAD；E91 tip `6acec05` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E93-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**大软不自开 E94**。  
入库：`docs/superpowers/specs/2026-11-05-e93-display-prefs-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E92 连续闭合 … → Issue Board Move CLI mid（E91 · 1.75.0）→ Saved View Write CLI mid（E92：`view create|update|delete|favorite|save-as` · 1.76.0）。

E92 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `48e6bb3`：

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
22. **再开 saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / set-multi / health / cycle / watchers / templates / milestones / move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **Initiative health CLI（独立 health get/set 弧）** — tip **仍无** 对称 `GET/POST /api/initiatives/{id}/health`；`to_response` 仅嵌套 `healthSummary` — **不选为本轮主 Epic**  
24. **自动健康评估 / AI 摘要** — **另弧**  
25. **（扫描 · 本轮主推）Display prefs CLI** — BE `GET/PUT /api/display-prefs/issue` + FE `fetchIssueDisplayPrefs` / `fetchPutIssueDisplayPrefs` **齐**；既有 `backend/tests/api/test_display_prefs.py` + `test_e49_display_color_scale_icons.py` 覆盖；E49 明示 **无** CLI 子命令；api_client **零** display-prefs helpers；`opentask_cli` **无** `display`/`display-prefs` 组 — agent 无法脚本「读/写个人 Issue 列表·看板 Display」——实证为 **BE/FE 齐、CLI 洞** 中最清晰剩余 mid（单资源 GET+PUT；单 sprint；agent 价值偏薄属个人 UI，但 Saved View 写面已闭后它是少数干净 CLI 洞之一）  
26. **（刚闭）Saved View write CLI** — E92 已闭；**勿重开**  
27. **（刚闭）Issue board/move CLI** — E91 已闭；**勿重开**

轮换离开刚闭弧：**saved-view-write / board-move / initiative-projects / CF reorder / favorite reorder / tag-group CLI / label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E92 Saved View Write；本轮补的是 **个人 Display prefs 脚本缺口**（BE/FE 已齐，agent 无法用 CLI get/set）。

代码实证 @ `48e6bb3`：

| 面 | 现状 |
|----|------|
| BE display-prefs | `GET /api/display-prefs/issue` → `{display: null\|object}`；`PUT /api/display-prefs/issue` body `{display: {...}}`；display 内键 **snake_case**（`view_mode`/`group_by`/`swimlane_by`/`hide_empty_lanes`/`fields`/`custom_field_keys`/`conditional_formats`/`color_scales`/`icon_sets`）；upsert 按 `(workspace_id, user_id)`；validate+normalize（含 E37 cf: 维、E49 color_scales/icon_sets 上限）；跨 WS 既有 workspace 门禁 |
| FE Display prefs | `fetchIssueDisplayPrefs` / `fetchPutIssueDisplayPrefs(display)` → **齐**；`SavedViewDisplay` 契约 snake_case |
| CLI | **无** `display-prefs`/`display` 组；api_client **零** get/put helpers；E49 测试仍断言「无专用子命令」—— agent 无法脚本个人 Display 读写 |
| Bulk project_id | `IssueBulkUpdate` **仍无** `project_id` — 仍薄刀/后置、触 BE |
| Project list watching | BE `list_projects` **无** watching Query；CLI 仅展示 count — 仍薄刀 |
| Linear 对齐 | agent 应能脚本「个人 Issue Display prefs get/set」，与 Linear 个人视图偏好持久化弱对齐（偏 UI，但仍是干净 CLI 洞） |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Display Prefs CLI mid**：CLI **1.77.0** 新组 `display-prefs get\|set`；api_client 两 helpers → 复用既有 GET/PUT；**无**新表/webhook/路由；FE 已齐 → 零产品 FE；可选 human 薄摘要 view_mode/group_by/swimlane_by | **薄**；闭合剩余干净「BE/FE 齐、CLI 洞」；单 sprint；agent 价值偏薄但结构最清晰 |
| B | 仅文档说明用 FE Display 面板 | 过薄；agent 仍断 |
| C | 仅 `display-prefs get`（缺 set） | 半截；agent 仍缺写 |
| D | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service + E80 邻弧；任务标薄刀 |
| E | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| F | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| G | Initiative health 独立 CLI / 甘特 / Activity Push / 门户 / Q2b / … | 无对称 health 路由 / prefer skip / 勿默认 |
| H | 再开 saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Display Prefs CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.77.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成「Initiative health CLI」或「bulk project_id」或「再开 view write」。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up；watching/bulk 需 BE） |
| 再开 saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health 独立 CLI | tip 无对称 `/health` 路由 → 不选为本轮主 Epic |
| 仅文档 / 不暴露 CLI | 过薄 |
| 仅 get 半截 | 过薄；set 仍断 |

### Why this Epic now（一句话）

E86–E92 连续闭合「BE/FE 齐、CLI 洞」关联/reorder/看板/Saved View 写面后，**个人 Display prefs** BE/FE（`GET/PUT /api/display-prefs/issue`）早已齐而 CLI **完全空洞**——agent 无法脚本「读/写列表·看板个人 Display」；用薄刀一次闭合该洞，且 **不动** 刚闭的 saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead。

---

## 1. 目标

成功标准：member+ 可用 CLI **1.77.0** 做个人 Issue Display prefs **get / set**；api_client 有对应 helpers；复用既有 `/api/display-prefs/issue`；语义对齐既有 BE（workspace 门禁；缺 prefs → `display: null`；PUT upsert + validate/normalize；非法 display 键/cf 维 → 既有 422）；**不**改 E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E94。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `GET /api/display-prefs/issue` → `{ display: null | object }`  
  - `PUT /api/display-prefs/issue` body `{ display: { view_mode?, group_by?, swimlane_by?, hide_empty_lanes?, fields?, custom_field_keys?, conditional_formats?, color_scales?, icon_sets?, … } }`  
  - display 对象键 **snake_case**（与 `DEFAULT_DISPLAY` / FE `SavedViewDisplay` / `test_display_prefs` 一致）；**不**要求顶层 camelCase  
- workspace/鉴权门禁不变；缺行 → get 返回 `display: null`；PUT upsert；validate 失败既有 422  
- **不**本轮改 IssueDisplayPrefs 模型 / Display prefs FE / formula；**不**把本 Epic 做成 Saved View 再写或 bulk project_id  
- **不**改 board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template / saved-views 写路径主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`display-prefs.ts` get/put 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.77.0**

- **Q2a** 命令形状（**新**顶层组 `display-prefs`；E49「无子命令」将被本 Epic 取代）：  
  - `opentask display-prefs get [--json]`  
  - `opentask display-prefs set --display JSON [--json]`  
  - 备选兼容：`display get|set`（短别名，可选不做——优先完整名以免与「monitor/display」语义混淆）；备选 `issue display-prefs …`（不选——污染 issue 组且无 issue_id）  
  - `--display`：接受 JSON 对象字符串；非法 JSON → CLI 422 风格错误（不打 BE）；对象即 display 本体（cli 包成 `{display: …}` 再 PUT）  
- **Q3a** 语义对齐 BE：api_client  
  - `get_issue_display_prefs()` → **GET** `/api/display-prefs/issue`  
  - `put_issue_display_prefs(display: dict)` → **PUT** `/api/display-prefs/issue` + body `{ "display": <dict> }`（display 内键保持调用方/snake_case；**不**在 client 侧强制改写成 camelCase `viewMode`）  
  - 失败透传 BE 403/404/422/…  
- **Q4a** human 模式：`get` 可薄打印 `View mode` / `Group by` / `Swimlane by` / `Hide empty lanes` + 完整 display JSON（或 `--json` 全量）；`set` 成功后薄回显同上；**不**改 `view use` / `view create|…` / `issue list` 默认行为  
- **Q5a** pins → **1.77.0**；历史 epic 断言级联（含 E49 `test_e49_display_v2.py` 中「无专用子命令」断言 → **改为**断言组存在 / version 1.77.0）  
- **不**改 `view create|update|delete|favorite|save-as|list|show|use`；**不**改 `issue board-move|create|update|…`；**不**改 initiative / CF / favorite-reorder / tag-group / label / project health / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- 个人 prefs：仅当前 user × workspace；跨租户/缺资源既有  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 saved-view-write / board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；**formula no-emit**（E49 已有 display write no-webhook 守门，保持）  
- **不**新增 `/api/initiatives/{id}/health`；不把本 Epic 扩成 bulk project_id 或再开 view write

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- **Initiative health 独立 CLI** / 自动健康评估（无对称 `/health` 路由 / 另弧）  
- Formula emit；远程 push / 开 PR / **自开 E94**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE display-prefs get/put 行为不变；缺 prefs → null；PUT roundtrip；非法/超限既有 422 |
| B | CLI **1.77.0** `display-prefs get\|set` 绿；失败透传；非法 `--display` JSON 不打 BE |
| C | api_client 两 helpers 接线绿（GET + PUT `{display}`）；历史 pins 级联 1.77.0；E49「无子命令」断言更新 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster；无新 webhook；无新表/alembic；formula no-emit；无独立 initiative health 路由 |
| 门禁 | BE 定向（`test_display_prefs` smoke 可选 + e93 spy）；CLI 定向 e93；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E94 |

---

## 4. ADR（Yuri 已确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Display Prefs CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用既有 `GET/PUT /api/display-prefs/issue`（body `{display}`；display 内 **snake_case**） |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.77.0**；新组 `display-prefs get\|set` |
| D5 | 语义 = 既有 BE（个人 upsert；null when absent；validate/normalize）；human 可薄摘要 view_mode/group_by/swimlane_by |
| D6 | 守 E40 D2/D7；不改 E63–E92 邻面主语义；不 push；不自开 E94；**不做** Initiative health/甘特 / bulk project_id / 再开 view write Epic |

---

## 5. 开放问题（Yuri 已一键全收建议默认）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有 GET/PUT `/api/display-prefs/issue`；备选 Q1b 另开 `/api/cli/display-prefs/...`（不选——既有端点+测试已齐） |
| Q2 | CLI 命令挂载？ | **Q2a** 新顶层组 `display-prefs get\|set`；备选 Q2b 短名 `display get\|set`（不选——歧义）；备选 Q2c 挂 `issue` 下（不选——无 issue_id、污染 issue 组）；备选 Q2d 仅 get（不选——半截） |
| Q3 | PUT body / display 键命名？ | **Q3a** api_client 发 `{ "display": <dict> }`，dict 内保持 **snake_case**（`view_mode`/`group_by`/…，对齐 BE/FE/test）；备选 Q3b 在 client 侧改写成 camelCase `viewMode`（不选——本端点契约即 snake） |
| Q4 | human 输出深度？ | **Q4a** 薄摘要 + 可选完整 JSON（`--json` 全量）；备选 Q4b 逐字段 flags（`--view-mode`/`--group-by`…）（不选——面宽、与 JSON 契约重复；可后薄刀） |
| Q5 | VERSION？ | **Q5a** pins **1.77.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（get/put helpers 已齐）；备选 Q6b 改 FE 命名/封装（不选——非本轮必须） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：`get_issue_display_prefs` + `put_issue_display_prefs` → GET/PUT + `{display}`（TDD）  
3. CLI 1.77.0：新组 `display-prefs get|set`；注册到 `opentask_cli`  
4. 更新 E49「无专用子命令」断言 → 组存在 / version 级联  
5. pins 级联 1.77.0  
6. BE spy：无新路由/alembic；display-prefs GET/PUT markers；邻面 marker（含 E92 view write / E91 board-move）；formula no-emit；**无**新 initiative `/health`  
7. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `display-prefs get`：无 prefs → `display: null`；有 prefs → 含 view_mode/…  
- `display-prefs set --display '{…}'` roundtrip 后再 get 一致  
- 非法 `--display` JSON → CLI 侧失败（不打 BE）  
- BE 非法/超限（如 color_scales 过多）→ 透传 422  
- api_client helpers 断言：正确 method + path；PUT body 顶层键 `display`；display 内 snake_case；禁误用 camelCase `viewMode` 作为唯一请求键  
- CLI pins 1.77.0；命令 json/human；E49 断言更新  
- spy：未改 view write helpers / board-move / initiative projects / CF reorder / favorite reorder / tag-group / label set/multi / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic；无新 initiative `/health` 路由  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E94+；若 Yuri 改选可替换本草案）

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
22. **再开 saved-view-write / board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / …** — 刚闭，勿默认。  
23. **Initiative health 独立 CLI** — tip 无对称 `/health` 路由；嵌套 `healthSummary` 仅随 GET/projects 返回 — 另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  
25. **（本轮主推已选）Display prefs CLI** — 若改选则回退到 bulk project_id 或 `project list --watching`。  
26. **Saved View write CLI** — E92 已闭；勿重开。  
27. **Issue board/move CLI** — E91 已闭；勿重开。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.77.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E92-S1` @ `48e6bb3f1b9bd8c61acf482d2e3b6bc1383aa625`  
- 拟开：`sprint/E93-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e93-display-prefs-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E94**

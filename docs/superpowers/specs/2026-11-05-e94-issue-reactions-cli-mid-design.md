# E94 Design：Issue Reactions CLI mid · CLI 1.78.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E94  
基线拟：`sprint/E93-S1` @ `577f13d`（全文 `577f13d3c5f78f778dabbe7ae6ef1371502033c7`；E93 design 基线 `4e818d2` ⊂ HEAD；E92 tip `48e6bb3` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E94-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**大软不自开 E95**。  
入库：`docs/superpowers/specs/2026-11-05-e94-issue-reactions-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · Scheme **A** · **Q1a–Q6a 全收** · 2026-11-05 Asia/Shanghai。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E93 连续闭合 … → Saved View Write CLI mid（E92 · 1.76.0）→ Display Prefs CLI mid（E93：`display-prefs get|set` · 1.77.0）。

E93 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `577f13d`：

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
19. **bulk_update 支持 project_id + 同 integrity helper** — **可后薄刀**（`IssueBulkUpdate` tip **仍无** `project_id`；触 BE schema + E80 邻弧；bulk 路径现为整批 SQL UPDATE，接 integrity 需 per-issue 分支）  
20. **读路径 orphan milestone lazy-heal（Q4b）** — **后置**  
21. **`project list --watching` BE 过滤** — **后薄刀**（`list_projects` tip **仍无** `watching` Query；CLI `project list` 仅输出 `watching_count`，无 filter flag）  
22. **再开 display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / set-multi / health / cycle / watchers / templates / milestones / move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **Initiative health CLI（独立 health get/set 弧）** — tip **仍无** 对称 `GET/POST /api/initiatives/{id}/health`；`to_response` 仅嵌套 `healthSummary` — **不选为本轮主 Epic**  
24. **自动健康评估 / AI 摘要** — **另弧**  
25. **（刚闭）Display prefs CLI** — E93 已闭；**勿重开**  
26. **（刚闭）Saved View write CLI** — E92 已闭；**勿重开**  
27. **（扫描 · 本轮主推）Issue / Comment Reactions CLI** — BE `GET/POST/DELETE /api/issues/{id}/reactions` + `…/comments/{cid}/reactions` **齐**；FE `IssueReactions.vue` + `fetchIssueApi.getReactions/addReaction/removeReaction` + comment 三件套 **齐**；E21 仅接 Issue 级 FE；E27 接评论反应 FE + `notif prefs` CLI——**两边都没给 reaction 本身 CLI**；api_client **零** reaction helpers；`opentask issue` **无** `reaction` 子组——agent 无法脚本「读/加/撤 emoji 反应」——实证为 Display prefs 闭合后剩余最清晰的 **BE/FE 齐、CLI 洞** mid（复用既有路由；无新表；单 sprint）

轮换离开刚闭弧：**display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite reorder / tag-group CLI / label set/multi / project-health / cycle CLI / project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E93 Display Prefs；本轮补的是 **Issue/Comment 反应脚本缺口**（BE/FE 已齐，agent 无法用 CLI list/add/remove）。

代码实证 @ `577f13d`：

| 面 | 现状 |
|----|------|
| BE Issue reactions | `GET /api/issues/{id}/reactions` → `{rows,total}`；`POST …/reactions` body `{emoji}` → `{reaction_id}`；`DELETE …/reactions?emoji=`；既有成员校验 |
| BE Comment reactions | `GET/POST/DELETE /api/issues/{id}/comments/{cid}/reactions`；POST body `{emoji}`；DELETE `?emoji=`；返回 `reactions` map |
| FE | `IssueReactions.vue` + issue/comment API helpers **齐** |
| CLI | **无** `issue reaction` / comment-reaction 命令；api_client **零** helpers—— agent 无法脚本反应读写 |
| Bulk project_id | `IssueBulkUpdate` **仍无** `project_id` — 仍薄刀/后置、触 BE |
| Project list watching | BE `list_projects` **无** watching Query；CLI 仅展示 count — 仍薄刀 |
| Linear 对齐 | agent 应能脚本「Issue/评论 emoji 反应」，与 Linear reactions 弱对齐 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue Reactions CLI mid**：CLI **1.78.0** 新子组 `issue reaction list\|add\|remove` + 同 Epic 薄补 `issue comment reaction list\|add\|remove`；api_client 六 helpers → 复用既有 GET/POST/DELETE；**无**新表/webhook/路由；FE 已齐 → 零产品 FE；human 薄表 emoji/count | **薄**；闭合剩余干净「BE/FE 齐、CLI 洞」；单 sprint；agent 价值清晰（脚本互动） |
| B | 仅文档说明用 FE 点赞 | 过薄；agent 仍断 |
| C | 仅 Issue 级（缺 comment） | 半截；E27 评论反应仍无 CLI |
| D | bulk_update `project_id` + integrity | 真 mid 但触 BE schema/service + E80 邻弧；per-issue 分支厚于本洞 |
| E | `project list --watching` BE 过滤 | 薄刀；需 BE Query + CLI flag |
| F | Q4b orphan milestone lazy-heal | 后置；读路径 heal |
| G | Initiative health 独立 CLI / 甘特 / Activity Push / 门户 / Q2b / … | 无对称 health 路由 / prefer skip / 勿默认 |
| H | 再开 display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / label set/multi / project-health / cycle / watchers / templates / milestones / move / lead | 刚闭 |

**建议拍板：A（Issue Reactions CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.78.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`；**不**把本 Epic 做成「Initiative health CLI」或「bulk project_id」或「再开 display-prefs」。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置（runners-up；watching/bulk 需 BE） |
| 再开 display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead / … | 刚闭 |
| Initiative health 独立 CLI | tip 无对称 `/health` 路由 → 不选为本轮主 Epic |
| 仅文档 / 不暴露 CLI | 过薄 |
| 仅 Issue 半截（无 comment） | 过薄；E27 评论反应仍断 |

### Why this Epic now（一句话）

E86–E93 连续闭合「BE/FE 齐、CLI 洞」关联/reorder/看板/Saved View/Display prefs 后，**Issue/Comment Reactions** BE/FE（E21/E27 路由与组件）早已齐而 CLI **完全空洞**——agent 无法脚本「读/加/撤 emoji」；用薄刀一次闭合该洞，且 **不动** 刚闭的 display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite / tag-group / set/multi / health / cycle / watchers / templates / milestones / move / lead。

---

## 1. 目标

成功标准：member+ 可用 CLI **1.78.0** 做 Issue 与 Comment **reaction list / add / remove**；api_client 有对应 helpers；复用既有 `/api/issues/{id}/reactions` 与 `/api/issues/{id}/comments/{cid}/reactions`；语义对齐既有 BE（成员校验；emoji 必填；DELETE 缺反应 → 既有 404）；**不**改 E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E95。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `GET /api/issues/{issue_id}/reactions` → `{ rows: [{emoji,count,users?}], total }`  
  - `POST /api/issues/{issue_id}/reactions` body `{ "emoji": "👍" }` → `{ reaction_id }`  
  - `DELETE /api/issues/{issue_id}/reactions?emoji=👍`  
  - `GET /api/issues/{issue_id}/comments/{comment_id}/reactions` → `{ reactions: {emoji: userId[]} }`  
  - `POST …/comments/{comment_id}/reactions` body `{ "emoji": "…" }` → `{ reaction_id, reactions }`  
  - `DELETE …/comments/{comment_id}/reactions?emoji=`  
- 鉴权/成员门禁不变；非法/缺资源既有 403/404/422  
- **不**本轮改 reaction 模型 / FE 组件 / activity feed；**不**把本 Epic 做成 bulk project_id 或再开 display-prefs  
- **不**改 board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / milestone / project-move / lead / issue-template / saved-views / display-prefs 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`IssueReactions.vue` + issue/comment API helpers 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量

### C · CLI **1.78.0**

- **Q2a** 命令形状（挂 `issue` 下两子组，避免新顶层污染）：  
  - `opentask issue reaction list ISSUE [--json]`  
  - `opentask issue reaction add ISSUE --emoji EMOJI [--json]`  
  - `opentask issue reaction remove ISSUE --emoji EMOJI [--json]`（别名 `rm` 可选）  
  - `opentask issue comment-reaction list ISSUE COMMENT [--json]`  
  - `opentask issue comment-reaction add ISSUE COMMENT --emoji EMOJI [--json]`  
  - `opentask issue comment-reaction remove ISSUE COMMENT --emoji EMOJI [--json]`  
  - 备选 Q2b 顶层 `reaction` 组（不选——缺 issue 上下文、与 Linear 弱对齐差）  
  - 备选 Q2c 仅 Issue 三级（不选——半截，E27 评论反应仍断）  
- **Q3a** 语义对齐 BE：api_client  
  - `list_issue_reactions(issue_id)` → **GET** `/api/issues/{id}/reactions`  
  - `add_issue_reaction(issue_id, emoji)` → **POST** + body `{ "emoji": … }`  
  - `remove_issue_reaction(issue_id, emoji)` → **DELETE** + query `emoji=`  
  - `list_comment_reactions(issue_id, comment_id)` → **GET** `…/comments/{cid}/reactions`  
  - `add_comment_reaction(issue_id, comment_id, emoji)` → **POST** + `{ "emoji": … }`  
  - `remove_comment_reaction(issue_id, comment_id, emoji)` → **DELETE** + query `emoji=`  
  - 失败透传 BE 403/404/422/…  
- **Q4a** human 模式：`list` 薄表 emoji / count（issue）或 emoji / userIds（comment）；`add`/`remove` 成功薄回显；**不**改 `issue show` 默认嵌入大块（可选后薄刀一行 Reactions 摘要，本轮不做）  
- **Q5a** pins → **1.78.0**；历史 epic 断言级联  
- **不**改 `display-prefs` / `view create|update|delete|favorite|save-as|list|show|use` / `issue board-move|bulk-update|…`；**不**改 initiative / CF / favorite-reorder / tag-group / label / project health / cycle / watchers / milestone / lead / issue-template

### D · 安全 / 邻面 / no-emit

- 反应仅当前 user × 有权 Issue/Comment；跨租户/缺资源既有  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate  
- 无 Push / 门户 / 甘特；**formula no-emit**  
- **不**新增 `/api/initiatives/{id}/health`；不把本 Epic 扩成 bulk project_id 或再开 display-prefs

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- **Initiative health 独立 CLI** / 自动健康评估（无对称 `/health` 路由 / 另弧）  
- Formula emit；远程 push / 开 PR / **自开 E95**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE issue/comment reactions 行为不变；list/add/remove 透传；缺反应 DELETE → 既有 404 |
| B | CLI **1.78.0** `issue reaction list\|add\|remove` + `issue comment-reaction list\|add\|remove` 绿；失败透传；缺 `--emoji` 本地失败 |
| C | api_client 六 helpers 接线绿；历史 pins 级联 1.78.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster；无新 webhook；无新表/alembic；formula no-emit；无独立 initiative health 路由 |
| 门禁 | BE 定向（既有 reaction smoke 可选 + e94 spy）；CLI 定向 e94；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E95 |

---

## 4. ADR（Yuri 已确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue Reactions CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用既有 Issue + Comment reactions GET/POST/DELETE |
| D3 | 无新 webhook / 无新表 / 无 alembic |
| D4 | CLI = **1.78.0**；`issue reaction …` + `issue comment-reaction …` |
| D5 | 语义 = 既有 BE（成员门禁；emoji 必填；DELETE 404）；human 薄表 |
| D6 | 守 E40 D2/D7；不改 E63–E93 邻面主语义；不 push；不自开 E95；**不做** Initiative health/甘特 / bulk project_id / 再开 display-prefs Epic |

---

## 5. 开放问题（Yuri 已一键全收建议默认）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有 Issue + Comment reactions 六端点；备选 Q1b 另开 `/api/cli/reactions/...`（不选——既有端点+FE 已齐） |
| Q2 | CLI 命令挂载？ | **Q2a** `issue reaction list\|add\|remove` + `issue comment-reaction list\|add\|remove`；备选 Q2b 顶层 `reaction`（不选）；备选 Q2c 仅 Issue（不选——半截）；备选 Q2d 嵌 `issue comment reaction` 三级（可接受，但 click 层级深——优先扁平 `comment-reaction`） |
| Q3 | POST body / DELETE 传参？ | **Q3a** api_client POST `{ "emoji": <str> }`；DELETE query `emoji=`（对齐 BE/FE）；备选 Q3b path 参数（不选——BE 非如此） |
| Q4 | human 输出深度？ | **Q4a** list 薄表 + `--json` 全量；add/remove 薄回显；**不**改 `issue show` 默认；备选 Q4b show 嵌入 Reactions 列（后薄刀） |
| Q5 | VERSION？ | **Q5a** pins **1.78.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（helpers/组件已齐）；备选 Q6b 改 FE 命名/封装（不选——非本轮必须） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：六 reaction helpers → GET/POST/DELETE（TDD）  
3. CLI 1.78.0：`issue reaction` + `issue comment-reaction` 子组；注册到 `issue_cli`  
4. pins 级联 1.78.0  
5. BE spy：无新路由/alembic；reactions GET/POST/DELETE markers；邻面 marker（含 E93 display-prefs / E92 view write / E91 board-move）；formula no-emit；**无**新 initiative `/health`  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- `issue reaction list`：空 → rows=[]/total=0；有反应 → emoji/count  
- `issue reaction add --emoji '👍'` 后再 list 可见；`remove` 后再 list 消失  
- `issue comment-reaction` 三级对称  
- 缺 `--emoji` → CLI 侧失败（不打 BE）  
- 缺反应 DELETE → 透传 404  
- api_client helpers 断言：正确 method + path；POST body 键 `emoji`；DELETE 带 query  
- CLI pins 1.78.0；命令 json/human  
- spy：未改 display-prefs helpers / view write / board-move / initiative projects / CF reorder / favorite reorder / tag-group / label set/multi / project health get/set/timeline / cycle generate-upcoming/update/delete / project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit；无新 alembic；无新 initiative `/health` 路由  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E95+；若 Yuri 改选可替换本草案）

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
19. **bulk_update 支持 project_id + 同 integrity helper** — 后薄刀（需 BE schema；per-issue integrity）。  
20. **读路径 orphan milestone lazy-heal（Q4b）** — 后置。  
21. **`project list --watching` BE 过滤** — 后薄刀（需 BE Query）。  
22. **再开 display-prefs / saved-view-write / board-move / initiative-projects / CF reorder / favorite reorder / tag-group / label set/multi / project-health / cycle / project-watchers / issue-templates / milestones / project-move / lead / …** — 刚闭，勿默认。  
23. **Initiative health 独立 CLI** — tip 无对称 `/health` 路由；嵌套 `healthSummary` 仅随 GET/projects 返回 — 另扫后定。  
24. **自动健康评估 / AI 摘要** — 另弧。  
25. **（本轮主推已选）Issue/Comment Reactions CLI** — 若改选则回退到 bulk project_id 或 `project list --watching`。  
26. **Display prefs CLI** — E93 已闭；勿重开。  
27. **Saved View write CLI** — E92 已闭；勿重开。  

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.78.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E93-S1` @ `577f13d3c5f78f778dabbe7ae6ef1371502033c7`  
- 拟开：`sprint/E94-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e94-issue-reactions-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E95**

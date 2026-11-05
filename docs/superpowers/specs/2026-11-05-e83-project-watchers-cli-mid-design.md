# E83 Design：Project Watchers CLI mid · CLI 1.67.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E83  
基线拟：`sprint/E82-S1` @ `bcd8f88`（全文 `bcd8f88c927d6bd885149bcbfad0a0f832bf9c54`；E82 design 基线 `9e76efc` ⊂ HEAD；E81 tip `69b2112` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E83-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E84**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e83-project-watchers-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E83-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E82 连续闭合 … → Project milestones CLI mid（E81）→ **Issue Templates CLI mid（E82：GET by id + CLI CRUD/seed + create `--template-id` · 1.66.0）**。

E82 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `bcd8f88`：

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
21. **再开 issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
22. **（扫描）Project watchers CLI 对称、cycle 容量加厚、label 批量** — 实证后 **Project watchers CLI** 为真 mid 缺口

轮换离开刚闭弧：**issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E82 issue-template；本轮补的是 **Project 订阅 CLI 对称 Issue watchers**。

代码实证 @ `bcd8f88`：

| 面 | 现状 |
|----|------|
| BE Project Watchers | `GET/POST/DELETE /api/projects/{project_id}/watchers` 齐（E8-S2）；`ProjectWatcherService.list/watch/unwatch`；跨租户/缺项目 404；**无** username 富化（Issue 侧有 `enrich_watchers`） |
| BE Issue Watchers | 齐；CLI `issue watch\|unwatch\|watchers` + api_client 已接 |
| FE | `project-detail` 已有关注/取消关注 + `fetchProjectWatchers` / `watchProject` / `unwatchProject` |
| CLI Project | **无** `project watch\|unwatch\|watchers`；api_client **无** project-watcher helpers；`project show` **不**报 watching_count |
| Cycle | CLI 已有 list/show/create/activate/complete/**capacity**；缺 generate-upcoming / PATCH / DELETE（属「补完旧 E14 面」，非容量真缺口） |
| Label | CLI attach/detach 单条；BE 已有 `PUT /{issue_id}/tags` replace；bulk_update 已有 `tag_ids`；「批量」半齐，非最干净 mid |
| Linear 对齐 | Project watch 与 Issue watch 对称；agent 应能脚本订阅项目 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Project Watchers CLI mid**：CLI **1.67.0** `project watch\|unwatch\|watchers` + api_client；`project show` 报 watching_count；BE 可选 list 富化 username（对齐 Issue）；**无**新表/webhook；不改 E82/E81/E80/E79 主表面；FE 已齐 → 零产品 FE | **中厚**；E82 runner-up #22 首选；对称 Issue；单 sprint |
| B | 仅 CLI watch/unwatch 两命令、无 list/show 计数 | 过薄 |
| C | Cycle generate-upcoming + update/delete（「容量加厚」名不副实） | 补完旧面；capacity 已有；次之 |
| D | Label `set`/multi-attach 批量 | 半齐（replace API + bulk tag_ids 已在）；次之 |
| E | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| F | bulk project_id / Q4b lazy-heal | 任务标薄刀/后置 |
| G | 再开 issue-templates / milestones / project-move / lead | 刚闭 |
| H | Project 私有 ACL / merge / 深拷贝 / 模板 stubs | 另大弧 / 过厚 / skip |

**建议拍板：A（Project Watchers CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.67.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b | 薄刀 / 后置 |
| 再开 issue-templates / milestones / project-move / lead / … | 刚闭 |
| Cycle generate-upcoming / update / delete | capacity 已齐；属补完旧 CRUD，非「容量加厚」真缺口 |
| Label 批量 set/multi | replace API + bulk `tag_ids` 已半齐；缺口糊 |
| 仅 watch/unwatch 无 list/show 计数 | 过薄 |

### Why this Epic now（一句话）

Issue 侧早已可 `watch|unwatch|watchers`，BE/FE Project 订阅也齐，但 agent **仍无法**用 CLI 订阅/取消/列举项目关注者——用中厚刀一次补上 **CLI 三命令 + api_client + show 计数（+可选 list 富化）**，闭合 Linear「Project watch 对称 Issue」脚本面，且 **不动** 刚闭的 issue-templates / milestones / project-move / lead。

---

## 1. 目标

成功标准：member+（及 viewer 自订，对齐既有 BE：watch/unwatch **不**强制 writer）可用 CLI **1.67.0** 做 `project watch|unwatch|watchers`；`project show` 可见 watching_count；api_client 有 list/watch/unwatch；跨租户/缺项目 404；**不**改 E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表；formula no-emit；**不**自开 E84。

### A · BE

- **Q1a** **不**新增路由；复用既有 `GET/POST/DELETE /api/projects/{project_id}/watchers`  
- **Q3a** list/watch 响应可选 **enrich username/name**（对齐 `issue_watcher.enrich_watchers`；薄刀；无 schema 迁移）  
- 跨租户/缺项目 404（既有 `get_project_in_workspace`）  
- watch 幂等（既有）；unwatch 缺席 no-op（既有）  
- **不**改 milestone / project-move / lead/members / issue-template / cycle / tag 主表面  
- **不**本轮加 `project list --watching` BE 过滤（另薄刀）

### B · FE

- **Q6a** **零产品 FE 改动**（`project-detail` 关注按钮与 api 已齐）  
- 若 Q3a 富化落地：既有 FE 只多字段，无需改 UI  
- build ok；守 E63 `f`+`r`  
- 可选：零或极薄 vitest（仅当新增纯函数 helper；否则可不加）

### C · CLI **1.67.0**

- 对齐 Issue 扁平命令（**Q2a**）：  
  - `opentask project watch <projectId> [--json]`  
  - `opentask project unwatch <projectId> [--json]`  
  - `opentask project watchers <projectId> [--json]`  
- **Q4a** `project show`：拉取 watchers 后展示 `watching_count`（json 模式写入字段；失败时降级不阻断 show）  
- `api_client`：`list_project_watchers` / `watch_project` / `unwatch_project`  
- pins → **1.67.0**；历史 epic 断言级联  

### D · 安全 / 邻面 / no-emit

- 跨租户/缺项目 404；自订阅不强制 writer（对齐既有 BE）  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate 主路径  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- Cycle generate-upcoming / update / delete（runners-up）  
- Label replace/`set` 批量 CLI（runners-up）  
- `project list --watching` BE 过滤（后薄刀）  
- 再开 lead/members / parent / trash / links / threading / start_date / project-templates / multi-assignee / issue-templates  
- Formula emit；远程 push / 开 PR / **自开 E84**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE watchers GET/POST/DELETE 行为不变；跨租户/缺项目 404 |
| B | （若 Q3a）list/watch JSON 含 username/name 富化；无 alembic |
| C | CLI **1.67.0** `project watch\|unwatch\|watchers` 绿 |
| D | `project show` 含 watching_count（json 字段）绿 |
| E | FE 无产品回归；build ok；`f`+`r` 仍在 |
| F | 未改 E82 issue-template / E81 milestone / E80 helper / E79 roster 主表面；无新 webhook；formula no-emit |
| 门禁 | BE 定向（富化若做则测；否则既有 project watchers smoke）；CLI 定向 e83；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E84 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Project Watchers CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 E8-S2 watchers |
| D3 | 无新 webhook / 无新 timeline enum / 无新表 |
| D4 | CLI = **1.67.0**；`project watch\|unwatch\|watchers` + show counting |
| D5 | 命令形状对齐 Issue 扁平三命令（非 nested `project watcher *`） |
| D6 | 守 E40 D2/D7；不改 E63–E82 邻面主语义；不 push；不自开 E84 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有三端点；备选 Q1b 另做 `/watching` 聚合（不选——重复） |
| Q2 | CLI 命令名？ | **Q2a** 扁平 `project watch\|unwatch\|watchers`（对齐 issue）；备选 Q2b nested `project watcher list\|add\|remove`（不选——与 issue 不一致） |
| Q3 | list 是否富化 username？ | **Q3a** 是（对齐 issue enrich；薄）；备选 Q3b 仅 user_id（不选——CLI 表难读） |
| Q4 | show 是否带 watching_count？ | **Q4a** 是（额外 GET watchers；失败降级）；备选 Q4b 仅三命令（不选——缺发现面） |
| Q5 | VERSION？ | **Q5a** pins **1.67.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（已有关注 UI）；备选 Q6b 重做订阅条（不选——浪费） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. BE（可选 Q3a）：project watchers enrich username（TDD）  
3. CLI api_client helpers  
4. CLI 1.67.0 `project watch|unwatch|watchers`  
5. CLI `project show` watching_count  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- watch 幂等 200；unwatch 绿；list 行数；跨 WS / 缺项目 404  
- （Q3a）enrich 字段 username/name  
- CLI pins 1.67.0；watch/unwatch/watchers；show 含 watching_count  
- spy：未改 issue-template / milestone issue_count / issue_project_move / E79 roster；无新 webhook；formula no-emit  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E84+；若 Yuri 改选可替换本草案）

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
21. **再开 issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
22. **Cycle CLI 补完**：`generate-upcoming` + `update` + `delete`（capacity 已有；非容量加厚）— E84 候选。  
23. **Label 批量**：`label set` → `PUT /{issue}/tags` replace；多 issue multi-attach — E84 候选（半齐）。  
24. **Project health CLI 对称**（BE/FE 已有、CLI 无）— 可后列。  
25. **`project list --watching` BE 过滤** — 后薄刀。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.67.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E82-S1` @ `bcd8f88c927d6bd885149bcbfad0a0f832bf9c54`  
- 拟开：`sprint/E83-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e83-project-watchers-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E84**

# E84 Design：Cycle CLI mid · CLI 1.68.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E84  
基线拟：`sprint/E83-S1` @ `f066e88`（全文 `f066e8862e92e4b206de53df631597a333931d0c`；E83 design 基线 `dd3e920` ⊂ HEAD；E82 tip `bcd8f88` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E84-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E85**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e84-cycle-cli-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E84-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E83 连续闭合 … → Issue Templates CLI mid（E82 · 1.66.0）→ **Project Watchers CLI mid（E83：`project watch|unwatch|watchers` + show `watching_count` + BE enrich · 1.67.0）**。

E83 附录 runners-up（任务硬指引）+ tip 代码扫描 @ `f066e88`：

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
22. **再开 project-watchers / issue-templates / milestones / project-move / lead / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage** — **刚闭，勿默认**  
23. **（扫描）Cycle CLI 补完 generate-upcoming/update/delete、Label `set`/multi-attach、Project health CLI** — 实证后 **Cycle CLI mid** 为真 mid 缺口

轮换离开刚闭弧：**project-watchers / issue-templates / milestones / project-move / lead/members / parent / trash / links / duplicate / threading / start_date / project-templates / multi-assignee / childProgress / 评论附件 / Form→Triage**。  
**不**重开 E83 project-watchers；本轮补的是 **Cycle CLI 生命周期缺口**（BE/FE 已齐，CLI 半截）。

代码实证 @ `f066e88`：

| 面 | 现状 |
|----|------|
| BE Cycles | `GET/POST /api/cycles`；`GET/PATCH/DELETE /{id}`；`POST /{id}/activate\|complete`；`GET /capacity-hint`；**`POST /generate-upcoming`** 齐（E6）；`CycleService` 有 generate_upcoming / update / delete |
| FE Cycles | `cycles.ts` 已有 `fetchUpdateCycle` / `fetchDeleteCycle` / `fetchGenerateUpcoming` + activate/complete/capacity |
| CLI Cycle | 仅 `list\|show\|create\|activate\|complete\|capacity`；api_client **无** `update_cycle` / `delete_cycle` / `generate_upcoming_cycle` |
| Label | CLI `attach\|detach` 单条；BE `PUT /{issue}/tags` replace 齐；bulk_update 已有 `tag_ids`；「set/批量」半齐 |
| Project Health | BE `GET/POST /api/projects/{id}/health` + timeline 齐；FE project-detail 已有；CLI/api_client **全无** health helpers |
| Linear 对齐 | agent 应能脚本「生成下一迭代 / 改窗 / 删草稿」，而非停在 activate/complete |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Cycle CLI mid**：CLI **1.68.0** `cycle generate-upcoming\|update\|delete` + api_client；复用既有 BE；**无**新表/webhook；不改 E83–E79 主表面；FE 已齐 → 零产品 FE | **中厚**；E83 runner-up #22 首选；闭合 Cycle 脚本生命周期；单 sprint |
| B | 仅 `generate-upcoming` 一刀、无 update/delete | 过薄；生命周期仍断 |
| C | Project health CLI（get/post + show 字段） | 真 mid；但紧挨 E83 project-*，本轮优先轮换到 Cycle；列 E85 |
| D | Label `set` → PUT replace；多 issue multi-attach | 半齐（replace + bulk `tag_ids`）；缺口糊；次之 |
| E | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚 |
| F | bulk project_id / Q4b lazy-heal / `project list --watching` | 任务标薄刀/后置 |
| G | 再开 project-watchers / issue-templates / milestones / project-move / lead | 刚闭 |
| H | Project 私有 ACL / merge / 深拷贝 / 模板 stubs | 另大弧 / 过厚 / skip |

**建议拍板：A（Cycle CLI mid）。**  
其余列入附录 runners-up。

自检：不重开 E83 project-watchers / E82 issue-templates / E81 milestones / E80 `apply_project_move_integrity` / E79 lead/members；CLI **1.68.0**；formula no-emit；无 Push/甘特/门户；守 E63 `f`+`r`。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| bulk project + Q4b + `project list --watching` | 薄刀 / 后置 |
| 再开 project-watchers / issue-templates / milestones / project-move / lead / … | 刚闭 |
| Project health CLI | 真 mid；紧挨 E83 project 面，轮换优先 Cycle；E85 首选 |
| Label 批量 set/multi | replace API + bulk `tag_ids` 已半齐；缺口糊 |
| 仅 generate-upcoming 无 update/delete | 过薄 |

### Why this Epic now（一句话）

BE/FE 早已能 `generate-upcoming` / PATCH / DELETE Cycle，CLI 却停在 create/activate/complete/capacity——agent **无法**脚本「滚下一迭代 / 改日期窗 / 清草稿」。用中厚刀一次补上 **三命令 + api_client**，闭合 Linear Cycle 生命周期脚本面，且 **不动** 刚闭的 project-watchers / issue-templates / milestones / project-move / lead。

---

## 1. 目标

成功标准：writer+ 可用 CLI **1.68.0** 做 `cycle generate-upcoming|update|delete`；api_client 有对应 helpers；跨租户/缺 cycle 404（既有 BE）；**不**改 E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主语义；**无**新 webhook / 无新表 / **无新 BE 路由**；formula no-emit；**不**自开 E85。

### A · BE

- **Q1a** **不**新增路由；复用既有  
  - `POST /api/cycles/generate-upcoming`  
  - `PATCH /api/cycles/{cycle_id}`  
  - `DELETE /api/cycles/{cycle_id}`  
- writer 门禁 / 跨租户·缺 cycle 404 不变（既有 `require_writer` + `CycleService.get`）  
- **不**改 activate/complete/capacity-hint 语义  
- **不**本轮加 cycle 自动 cron / 容量算法变更  
- **不**改 project-watchers / milestone / project-move / lead / issue-template 主表面

### B · FE

- **Q6a** **零产品 FE 改动**（`cycles.ts` + UI 已齐）  
- build ok；守 E63 `f`+`r`  
- 可选：零 vitest 增量（无新纯函数则可不加）

### C · CLI **1.68.0**

- **Q2a** 命令形状（对齐既有扁平 cycle 组，非 nested）：  
  - `opentask cycle generate-upcoming [--json]`  
  - `opentask cycle update <cycleId> [--name ...] [--starts-at ...] [--ends-at ...] [--json]`  
  - `opentask cycle delete <cycleId> [--json]`（**Q3a**：不强制 `--yes`；与既有 `label delete` / `initiative delete` 一致；json 模式直接删）  
- **Q4a** `api_client`：`generate_upcoming_cycle` / `update_cycle` / `delete_cycle`  
- pins → **1.68.0**；历史 epic 断言级联  
- **不**改 list/show/create/activate/complete/capacity 既有行为（show 仍可附 capacity hint）

### D · 安全 / 邻面 / no-emit

- writer-only 写路径（对齐既有 BE）；跨租户/缺资源 404  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 project-watchers / issue-template / milestone / project-move / parent / trash / links / 附件 / VCS / duplicate 主路径  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板内 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **再改** E83 project-watchers / E82 issue-templates / E81 milestones / E80 换项目自清 / Q4b lazy-heal  
- **bulk_update project_id** / **`project list --watching`**（后薄刀）  
- Project 私有 ACL / 按 member 过滤 Issue  
- Project health CLI（runners-up → E85）  
- Label replace/`set` 批量 CLI（runners-up）  
- Cycle 容量算法加厚 / 自动排期 cron / 多 team cycle  
- 再开 lead/members / parent / trash / links / threading / start_date / project-templates / multi-assignee / issue-templates / project-watchers  
- Formula emit；远程 push / 开 PR / **自开 E85**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 既有 BE generate-upcoming / PATCH / DELETE 行为不变；跨租户/缺 cycle 404；writer 403 |
| B | CLI **1.68.0** `cycle generate-upcoming\|update\|delete` 绿 |
| C | api_client 三 helpers 接线绿；历史 pins 级联 1.68.0 |
| D | FE 无产品回归；build ok；`f`+`r` 仍在 |
| E | 未改 E83 project-watchers / E82 issue-template / E81 milestone / E80 helper / E79 roster 主表面；无新 webhook；无新表/alembic；formula no-emit |
| 门禁 | BE 定向（既有 cycles smoke + 若有 e84 定向）；CLI 定向 e84；FE vitest/build（无改则 smoke） |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E85 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Cycle CLI mid**（方案 A） |
| D2 | **不**新开 BE 路由；复用 E6 generate-upcoming / PATCH / DELETE |
| D3 | 无新 webhook / 无新 timeline enum / 无新表 |
| D4 | CLI = **1.68.0**；`cycle generate-upcoming\|update\|delete` |
| D5 | 命令挂在既有 `cycle` 组（扁平），非 nested `cycle gen *` |
| D6 | 守 E40 D2/D7；不改 E63–E83 邻面主语义；不 push；不自开 E85 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否新开 BE 路由？ | **Q1a** 否，复用既有三端点；备选 Q1b 另做 bulk generate N（不选——过厚） |
| Q2 | CLI 命令名？ | **Q2a** `cycle generate-upcoming\|update\|delete`；备选 Q2b 缩写 `cycle gen`（不选——与 FE/API 名不一致） |
| Q3 | delete 是否要 `--yes`？ | **Q3a** 否（对齐 label/initiative delete）；备选 Q3b 强制确认（不选——打断脚本） |
| Q4 | update 缺字段策略？ | **Q4a** 仅发送显式传入字段（PATCH partial）；备选 Q4b 全量必填（不选——破坏 PATCH） |
| Q5 | VERSION？ | **Q5a** pins **1.68.0**；备选 Q5b 不动版本（不选——破坏 epic 级联约定） |
| Q6 | FE 范围？ | **Q6a** 零产品 FE（cycles UI/api 已齐）；备选 Q6b 重做 cycle 管理页（不选——浪费） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. CLI api_client：`generate_upcoming_cycle` / `update_cycle` / `delete_cycle`（TDD）  
3. CLI 1.68.0 三命令  
4. pins 级联 1.68.0  
5. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- generate-upcoming 200 + 返回下一 cycle；writer 外 403；跨 WS 隔离  
- update partial（仅 name / 仅窗）；缺 id 404  
- delete 绿；再 get 404；幂等策略跟既有 BE  
- CLI pins 1.68.0；三命令 json/human  
- spy：未改 project-watchers enrich / issue-template / milestone / issue_project_move / E79 roster；无新 webhook；formula no-emit  
- FE 无回归；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E85+；若 Yuri 改选可替换本草案）

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
22. **再开 project-watchers / issue-templates / milestones / project-move / lead / parent / trash …** — 刚闭，勿默认。  
23. **Project health CLI 对称**（BE/FE 已有、CLI 无 get/post/history；可附 `project show` health 字段）— **E85 首选**。  
24. **Label 批量**：`label set` → `PUT /{issue}/tags` replace；多 issue multi-attach — E85+ 候选（半齐）。  
25. **Cycle 容量算法 / 多 team / 自动 cron** — 另弧（本轮只补 CLI 接线）。

（备选扫描但本轮不推：Webhook/PagerDuty 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.68.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E83-S1` @ `f066e8862e92e4b206de53df631597a333931d0c`  
- 拟开：`sprint/E84-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e84-cycle-cli-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E85**

# E75 Design：Issue 复制 mid — duplicate · CLI 1.59.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E75  
基线拟：`sprint/E74-S1` @ `98d5bf4`（全文 `98d5bf4eabb5bdad72df22dc8c08cf5250490869`；E74 design 基线 `52e0b1d`；E73 tip `9d76ea2` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E75-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E76**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e75-issue-duplicate-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E75-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E74 连续闭合 … → start_date（E73）→ **评论线程 mid（E74：nested replies · CLI 1.58.0）**。

E74 附录 runners-up（任务硬指引）：

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
11. **depth≥2 / 服务端树** — **后置**（刚做 threading）  
12. **评论版本史** — **另弧**

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ / Form→Triage / 评论附件 / childProgress / multi-assignee / project templates / start_date / comment threading**。

代码实证 @ `98d5bf4`：

| 面 | 现状 |
|----|------|
| Issue 创建 | `create_issue` 完整；模板 `template_id`（E9）；**无** `POST …/duplicate` |
| Triage duplicate | E9「标记重复」= Relation + decline — **语义≠** 复制新建 |
| Project 模板 | E72 明示 **不**复制 Issues |
| Linear 对齐 | Linear「Duplicate issue」一键复制字段开新 KEY |
| 评论/附件/线程 | E69/E74 **刚闭** — 本轮宜离开评论面 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue 复制 mid**：`POST /api/issues/{id}/duplicate`；新 `issue_code`；复制核心字段（见下）；status→`open`；**不**复制评论/附件/时间线/子项/关系/SLA/VCS；FE 详情「复制」+ 跳转；CLI **1.59.0** `issue duplicate`；无新 webhook 事件名（走既有 created） | **中厚**；对齐 Linear；单 sprint |
| B | Activity Push | 勿默认 |
| C–L | 门户/甘特/Q2b/附件/递归/Bulk/深拷贝/stubs/CSV start/depth≥2/评论版本史 | skip / 后置 / 另弧 |
| M | 评论编辑 UX（API 已有 updateComment） | 偏薄且贴 E74 评论面 |
| N | G-then-X 热键（E5 后置） | 偏 FE 薄；可另弧 |
| O | 复制时深拷贝附件+子树 | **过厚** |

**建议拍板：A（Issue 复制 mid）。**  
其余列入附录 runners-up。

自检：复制字段清单、与 triage duplicate 边界、不碰评论/附件、CLI **1.59.0**、非目标与 no-emit、不重开 E63–E74 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本史 | 后置 / 另弧 |
| 再开 threading / start_date / templates / assignees / childProgress / 评论附件 | 刚闭 |
| G-then-X / 评论编辑 UX | 偏薄或贴评论面 |
| Formula rollup / emit / 真 GitHub App | 禁或过厚 |

### Why this Epic now（一句话）

排期/协作/模板/评论弧刚齐，但仍 **缺 Linear 式一键复制 Issue**——站会重复开同类单只能手填；轮换离开 E63–E74 邻面后，用中厚刀补上 **duplicate API + 字段白名单 + FE/CLI**，且明确 **≠** triage「标记重复」、**≠** Project 模板灌 Issues。

---

## 1. 目标

成功标准：member+ 可对可见 Issue 调用 **duplicate** → 新建同 WS Issue（新 `issue_code`）；默认复制白名单字段；`status=open`；**不**复制评论/附件/文档/时间线/子 Issue/关系/watchers/SLA clocks/VCS links/triage；FE 详情入口并跳转新 Issue；CLI **1.59.0**；**不** Activity Push、**不**改 E63–E74 邻面主表面、**不** formula emit、**不**甘特/门户/评论再开。

### A · 复制白名单（BE）

**复制（Q1a）：**  
`title`（默认加后缀）、`description`、`type`、`priority`、`project_id`、`cycle_id`、`milestone_id`、`estimate_points`、`estimated_hours`、`start_date`、`due_date`、`parent_issue_id`（**Q2a：保留**，作同父兄弟；无父则根）、`assignee_ids`（E71 结表）、`tag_ids` / labels、**自定义字段值**（非 formula；formula 跳过）。

**不复制：**  
`status`（强制 `open`）、`reporter_id`（= actor）、评论/反应/附件/entity_documents、timeline、children、relations、watchers、SLA、VCS、`triage_status`、`started_at`/`resolved_at`/`closed_at`、comment_count/attachment_count→0。

- 路由：`POST /api/issues/{issue_id}/duplicate`  
  - body 可选覆盖：`{ title?, project_id?, cycle_id?, parent_issue_id?, assignee_ids? }`  
- 权限：与 create 同级（member+）；跨 WS 404  
- 标题后缀（**Q3a**）：`" (copy)"`（中文 UI 可显示「副本」但存储后缀固定 ASCII 便于 CLI）  
- 可选链接（**Q4a**）：新建后加 `relates_to` → 源 Issue（**非** triage `duplicates`）；备选 Q4b 不建关系  
- Audit：新 Issue `created`；action_data 可含 `duplicated_from`  
- **Q5a**：无新 webhook 事件名；若 create 已 fire `issue.created` 则照旧  
- 无新表则 **可无 alembic**；若需 `duplicated_from_id` 列则可选薄 alembic（**Q1 建议默认不建列**，只放 timeline/meta）

### B · FE

- 详情头/菜单：「复制 Issue」→ POST → `router.push` 新 id  
- 失败 toast；成功可轻提示带新 code  
- ⌘K 动作可选薄（非必须）  
- vitest：title suffix helper；build ok；守 E63 `f`+`r`

### C · CLI **1.59.0**

- `opentask issue duplicate <id> [--title …] [--json]`  
- 打印新 `issue_code` / id  
- pins → **1.59.0**（**Q6a**）

### D · 安全 / 邻面 / no-emit

- 跨租户 404；CF/tags/assignees 仍走既有同 WS 校验  
- formula **no-emit**；跳过 formula CF 值复制  
- **不**改 E63–E74 主表面（threading / start_date / templates / multi-assignee / childProgress / 评论附件 / Form / TZ / 假日 / 门户 仅 pins）  
- **不**与 triage `/triage/{id}/duplicate` 混名（路径与文案区分「复制」vs「标记重复」）

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项、Bulk/Insights 多指派  
- 深拷贝 project、模板 Issue stubs、CSV start_date、depth≥2、评论版本史  
- 复制评论/附件/子树/关系图/SLA/VCS  
- 再开 comment threading / start_date / project templates  
- Formula emit；远程 push / 开 PR / **自开 E76**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | duplicate → 新 id/code；白名单字段相等；status=open；counts=0 |
| B | 不复制评论/附件/子项/关系（除 Q4a relates_to）/watchers |
| C | 跨 WS 404；viewer 403；formula CF 不复制值 |
| D | FE 入口+跳转；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.59.0** + duplicate + pins |
| F | 无新 webhook 名；≠ triage mark-duplicate；不改 E63–E74 邻面；formula no-emit |
| 门禁 | BE 定向 duplicate；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E76 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue 复制 mid**（方案 A）；字段白名单复制；**无** Push / 甘特 / 门户 / 评论再开 |
| D2 | 不复制评论/附件/子树/SLA/VCS/watchers；status 重置 open |
| D3 | 保留 `parent_issue_id`（同父兄弟）；标题后缀 ` (copy)` |
| D4 | 默认建 `relates_to` → 源（非 triage duplicates） |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.59.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E63–E74 邻面；不 push；不自开 E76 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 是否落 `duplicated_from_id` 列？ | **Q1a** 不建列（timeline/meta 足够）；备选 Q1b 薄 alembic 列 |
| Q2 | parent？ | **Q2a** 保留同父；备选 Q2b 总是根（丢上下文） |
| Q3 | 标题后缀？ | **Q3a** ` (copy)`；备选 Q3b `（副本）`；Q3c 无后缀 |
| Q4 | 自动关系？ | **Q4a** `relates_to` → 源；备选 Q4b 无关系；Q4c `duplicates`（易与 triage 语义撞车，不选） |
| Q5 | webhook？ | **Q5a** 无新事件名，走既有 `issue.created`；备选 Q5b `issue.duplicated`（噪） |
| Q6 | CLI？ | **Q6a** `issue duplicate` + pins **1.59.0**；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. Service `duplicate_issue` + 字段白名单（TDD）  
3. API route + 权限/跨 WS（TDD）  
4. tags/CF/assignees 复制 + relates_to（TDD）  
5. FE 入口 + 跳转 + vitest  
6. CLI 1.59.0  
7. 邻面不动 / f+r / acceptance

---

## 7. 测试要点

- 源含 description/priority/project/cycle/milestone/estimate/start/due/tags/CF/assignees/parent → 新 Issue 对齐；新 code；status=open  
- 源有 2 评论 + 1 附件 + 1 子 → 新 Issue 无评论/附件/子  
- formula CF 值不出现在新 Issue  
- relates_to 指向源（Q4a）；**无** triage duplicates 关系  
- 跨 WS 404；viewer 403  
- spy：无新 webhook **事件名**；不触 E74 threading / E73 start_date 写路径 / E72 templates / E71 主表面改动；formula no-emit  
- CLI 1.59.0 pins；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E76+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — E31 非目标。  
6. **递归孙项进度** — prefer skip。  
7. **Bulk/Insights 多指派** — prefer skip。  
8. **深拷贝 duplicate project** — prefer skip。  
9. **模板内 Issue stubs** — prefer skip。  
10. **CSV start_date / start 提醒** — 后置。  
11. **depth≥2 / 服务端树** — 后置。  
12. **评论版本史 / 评论编辑 UX 加厚** — 另弧（刚闭 threading）。  
13. **G-then-X 导航热键** — E5 后置；可另弧。  
14. **复制附件/子树** — 过厚；本 Epic 明确不做。

（备选扫描但本轮不推：再开 threading/start_date/templates/multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.59.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E74-S1` @ `98d5bf4eabb5bdad72df22dc8c08cf5250490869`  
- 拟开：`sprint/E75-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e75-issue-duplicate-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E76**

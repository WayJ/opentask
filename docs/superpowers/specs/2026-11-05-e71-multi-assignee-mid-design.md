# E71 Design：多指派人 mid — issue_assignees · CLI 1.55.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E71  
基线拟：`sprint/E70-S1` @ `5f311f4`（全文 `5f311f4d75eb60d072cdc7d42375baab0e455aa8`；E70 design 基线 `076f0f6`；E69 tip `08e327f` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E71-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E72**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e71-multi-assignee-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E71-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E70 连续闭合 … → 评论附件（E69）→ **子问题进度汇总 mid（E70：`childProgress` · CLI 1.54.0）**。

E70 附录 runners-up（任务硬指引）：

1. **Activity Push** — 仍 **勿默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b advance** — **rotate off**  
5. **表单公开附件** — E31 非目标 / **prefer skip**  
6. **多指派人 mid** — **本轮候选**  
7. **递归孙项进度** — **prefer skip**（E70 刚做直接子）

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ·due / Form→Triage / 评论附件 / childProgress**。

代码实证 @ `5f311f4`：

| 面 | 现状 |
|----|------|
| 指派 | `issues.assignee_id` **单列** + `assignee` embed；列表/看板/bulk/CLI 均单人 |
| 通知 | `notify_assigned` / comment / status recipients **只认** `assignee_id`（+ reporter / watchers） |
| Webhook | 已有 `issue.assignee_changed`（E44）— 可复用，**勿新事件名** |
| Watcher | `issue_watchers` 已有结表模式可参考（非指派语义） |
| 估点 | `estimate_points` FE/CLI 已可读写 — **非本轮缺口** |
| Linear 对齐 | Linear 支持多 Assignees；OpenTask 站会/协作仍卡在单人 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **多指派人 mid**：结表 `issue_assignees`；`assignee_id` 镜像 **primary**；详情/列表嵌 `assignees[]`；写路径 `assignee_ids`（首=primary）；过滤 `assignee_id` 仍 primary、`assignee_any` 含任一；通知 fanout 全员；复用 `issue.assignee_changed`；FE 多选；CLI **1.55.0** | **中厚**；单 sprint 可交付；向后兼容 |
| B | Activity Push | 勿默认 |
| C | Customer 门户再厚 | prefer skip |
| D | Initiative 甘特 | prefer skip |
| E | Q2b recurrence / 表单公开附件 / 递归孙项 | rotate off / E31 / prefer skip |
| F | 仅 FE 假多选、BE 仍单列 | **过薄**；通知/过滤/CLI 假一致 |
| G | 去掉 `assignee_id`、全面迁 junction | **过厚**；破 filters/insights/bulk |

**建议拍板：A（多指派人 mid）。**  
Push / 门户 / 甘特 / Q2b / 表单附件 / 递归进度列入附录 runners-up。

自检：primary 镜像、上限、过滤语义、通知 fanout、webhook 复用、alembic、CLI **1.55.0**、非目标与 no-emit、不重开 E63–E70 邻面已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 勿默认 |
| Customer 门户再厚 | prefer skip |
| Initiative 甘特 | prefer skip |
| Q2b / 表单公开附件 / 递归孙项 | rotate off / E31 / E70 刚做直接子 |
| 再开 childProgress / 评论附件 / Form / TZ / 假日 / Search / Initiative 关系 | 刚闭 |
| Project 模板 | 另弧；E9 已 defer |
| Formula children rollup / emit | E40/E43 **永不** |
| 真 GitHub App / SSO | 过厚 |

### Why this Epic now（一句话）

单 `assignee_id` 是协作瓶颈——结对/值班无法同权出现在 Issue 上；E70 进度弧刚闭后轮换离开进度/附件/表单/TZ/门户/假日/依赖，用中厚刀补上 **结表多指派 + primary 兼容 + 通知 fanout + FE/CLI**，对齐 Linear Assignees，且复用既有 `issue.assignee_changed`、不重开 Push/甘特。

---

## 1. 目标

成功标准：Issue 可挂 **多名指派人**（有序；**首=primary**）；`issues.assignee_id` **始终镜像** primary（空列表→null）；详情/列表默认嵌 `assignees: UserInfo[]`（有序）；Create/Update 接受 `assignee_ids: string[]`（亦可继续只写 `assignee_id`＝仅 primary、清空协作者）；列表过滤：`assignee_id`/`me` 仍 **仅 primary**；新增 `assignee_any`（含 primary+协作者）；指派变更通知 **fanout 全员**（新加入收 `assigned`；移出不强制）；webhook **复用** `issue.assignee_changed`（payload 增 `assignee_ids`/`assignees`，**无新事件名**）；FE 详情多选+头像叠；CLI **1.55.0**；**不** Activity Push、**不**改 E63–E70 邻面主表面、**不** formula emit、**不**甘特/门户/递归进度。

### A · 数据 / BE

- alembic：表 `issue_assignees`（`id`, `workspace_id`, `issue_id`, `user_id`, `position` int 0-based, `created_at`）；`UNIQUE(issue_id, user_id)`；index `(workspace_id, user_id)`  
- 同步规则：写 `assignee_ids` → 替换结表行 + `issues.assignee_id = ids[0] or null`；只写 `assignee_id`（无 `assignee_ids`）→ primary 换人且 **清空协作者**（**Q2a**，语义清晰）  
- 上限：**Q3a** max **10**  
- 嵌入：`assignees` 有序；保留既有 `assignee`/`assignee_id` 字段（= primary）  
- 过滤：`assignee_id` / `me` = primary；`assignee_any=userId|me` = junction OR primary  
- 迁移：既有 `assignee_id` 非空行 → 插入 `position=0` 结表行（一次性 data migration）

### B · 通知 / Activity / webhook

- `notify_assigned`：对 **新加入** 的每位发 `assigned`（相对旧集合差集）  
- comment / status / 其它 `_recipients_for_issue`：**并入全部 assignees**（去重 + 排除 actor）  
- Activity / audit：指派变更记全量前后 `assignee_ids`（若现有 audit 字段够用则扩展 payload，不新开表）  
- **Q5a**：不新增 webhook 事件名；集合变化时 fire 既有 `issue.assignee_changed`（及既有 `issue.updated` 若当前路径已 fire）；payload 带 `assignee_id`（primary）+ `assignee_ids`

### C · FE

- 详情右栏：多选成员（primary 标星或首位）；头像叠 +「+N」  
- 列表/看板：有 payload 时显示叠头像（无则退化为单 `assignee`）  
- vitest：排序/上限/清空；build ok；守 E63 `f`+`r`

### D · CLI **1.55.0**

- `issue create|update --assignees id1,id2`（首=primary）；兼容既有 `--assignee-id`  
- `issue show` 打印 `Assignees:` 列表（primary 标注）  
- pins → **1.55.0**（**Q6a**）

### E · 安全 / 邻面 / no-emit

- 跨租户 404；仅同 WS 成员可入 `assignee_ids`（非法 id → 400）  
- formula **no-emit**；不把 assignees 做成 formula 字段  
- **不**改 E63–E70 主表面（childProgress / 评论附件 / Form enqueue / TZ / Initiative / 假日 / 门户 / 附件 ACL 仅 pins）  
- bulk update：本 Epic **Q4a** 仍只设 primary（`assignee_id`）；多指派 bulk 后置

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户再厚、Initiative 甘特、Recurrence Q2b、表单公开附件、递归孙项进度  
- 再开 childProgress / 评论附件 / Form→Triage / TZ / 假日 / Search / Insights / Initiative 关系  
- 去掉 `assignee_id` 列、改写 Insights 容量按多指派拆分、看板按「任一指派」泳道重构  
- Project 模板；公式跨 Issue rollup；Formula emit  
- 远程 push / 开 PR / **自开 E72**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 结表 + alembic；`assignee_id` 镜像 primary；迁移既有行 |
| B | 详情/列表嵌 `assignees[]`；Create/Update `assignee_ids`；上限 10 |
| C | `assignee_id`/`me`=primary；`assignee_any` 含协作者 |
| D | 新加入 fanout `assigned`；recipients 含全员；复用 `issue.assignee_changed` |
| E | FE 多选+叠头像；vitest+build；`f`+`r` 仍在 |
| F | CLI **1.55.0** + show/create/update + pins |
| G | 不新 webhook 名；不改 E63–E70 邻面；formula no-emit；bulk 仍单 primary |
| 门禁 | BE 定向（assignees CRUD + filter + notify spy）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E72 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **多指派人 mid**（方案 A）；结表 + primary 镜像 + FE/CLI；**无** Push / 甘特 / 门户 / 递归进度 |
| D2 | 表 `issue_assignees` + alembic；`assignee_id` 保留并镜像 primary |
| D3 | 写 `assignee_ids` 全量替换；只写 `assignee_id` → primary + **清协作者** |
| D4 | 过滤：`assignee_id`=primary；`assignee_any`=任一；max 10 |
| D5 | 不新增 webhook 事件名；集合变 → 既有 `issue.assignee_changed` |
| D6 | CLI = **1.55.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E63–E70 邻面；不 push；不自开 E72 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | primary 策略？ | **Q1a** 有序列表首=primary 且镜像 `assignee_id`；备选 Q1b 无 primary、废弃列（破兼容，过厚） |
| Q2 | 只 PATCH `assignee_id` 时协作者？ | **Q2a** 清空协作者（语义：「设单人负责人」）；备选 Q2b 仅换 primary、保留协作者（易漏） |
| Q3 | 人数上限？ | **Q3a** 10；备选 Q3b 5（偏紧） / Q3c 无上限（滥用） |
| Q4 | bulk update？ | **Q4a** 本 Epic 仍只 primary；备选 Q4b 同步支持 `assignee_ids`（偏厚） |
| Q5 | webhook？ | **Q5a** 复用 `issue.assignee_changed`，无新事件名；备选 Q5b 新 `issue.assignees_changed`（噪音/订阅分裂） |
| Q6 | CLI？ | **Q6a** `--assignees` + show 列表 + pins **1.55.0**；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic 表 + 既有 `assignee_id` → position=0 回填（TDD）  
3. Service：replace assignees / mirror primary / 上限校验（TDD）  
4. API embed + Create/Update + `assignee_any` 过滤（TDD）  
5. 通知 fanout + webhook payload 扩展 + spy  
6. FE 多选/叠头像 + vitest  
7. CLI 1.55.0  
8. 邻面不动 / f+r / acceptance

---

## 7. 测试要点

- 空 → `[a,b]`：结表 2 行、`assignee_id=a`；a、b 收 `assigned`（若路径要求）  
- `[a,b]` → `[b]`：结表仅 b；`assignee_id=b`  
- 只 PATCH `assignee_id=c`：结表仅 c；协作者清空（Q2a）  
- 上限 11 → 400  
- 列表 `assignee_id=a` 不含「仅协作者为 a」；`assignee_any=a` 含  
- 跨 WS user id → 400；跨租户 issue → 404  
- spy：无新 webhook **事件名**；集合变 fire `issue.assignee_changed`；不触 E70 childProgress 写、E69 attach、E68 enqueue、E67 TZ、E66 ACL 主路径；formula no-emit  
- CLI 1.55.0 pins；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E72+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — E31 非目标。  
6. **递归孙项进度（E70 Q2b）** — prefer skip（刚做直接子）。  
7. **Project 模板 mid** — E9 defer；另弧可后置。  
8. **Bulk 多指派 / Insights 按多指派拆分** — 本 Epic Q4a 后置。

（备选扫描但本轮不推：再开 childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.55.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E70-S1` @ `5f311f4d75eb60d072cdc7d42375baab0e455aa8`  
- 拟开：`sprint/E71-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e71-multi-assignee-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E72**

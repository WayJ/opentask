# E74 Design：评论线程 mid — nested replies · CLI 1.58.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E74  
基线拟：`sprint/E73-S1` @ `9d76ea2`（全文 `9d76ea2cb6094f438e6544ba85a75a35357b9388`；E73 design 基线 `be2a150`；E72 tip `6911e71` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E74-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E75**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e74-comment-threading-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E74-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E73 连续闭合 … → project templates（E72）→ **Issue start_date mid（E73：计划开始日 · CLI 1.57.0）**。

E73 附录 runners-up（任务硬指引）：

1. **Activity Push** — 仍 **勿默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b advance** — **rotate off**  
5. **表单公开附件** — **prefer skip**  
6. **递归孙项进度** — **prefer skip**  
7. **Bulk/Insights 多指派** — **prefer skip**  
8. **深拷贝 duplicate project** — **prefer skip**  
9. **模板内 Issue stubs** — **prefer skip**  
10. **CSV start_date / start-driven reminders** — **后置**（刚做 start_date）

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ·due / Form→Triage / 评论附件 / childProgress / multi-assignee / project templates / start_date**。

代码实证 @ `9d76ea2`：

| 面 | 现状 |
|----|------|
| Comment 模型 | `issue_comments.parent_id` + `replies` relationship **已有** |
| API / Service | `add_comment(..., parent_id=)` 接受字段，但 **缺** 同 Issue / 深度校验 |
| FE 详情 | 评论 **扁平** `v-for`；`handleAddComment` **不传** parentId；无「回复」按钮 / 无缩进树 |
| Store/API 客户端 | `addComment(issueId, content, parentId?)` **已预留** |
| CLI | `issue comment add` **无** `--parent-id` |
| E69 | 评论附件刚闭 — 本轮 **不**再开附件 ACL/上传主表面；回复可复用既有挂载 |
| Linear 对齐 | Linear 评论可回复成线程；OpenTask 只能顶层串行 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **评论线程 mid**：BE 校验 parent 同 Issue + **深度上限**；GET 仍扁平带 `parent_id`；FE 组树 +「回复」+ 缩进；通知 fanout 含父评作者；CLI **1.58.0** `--parent-id`；**无** alembic（列已在）；**不** Push / 不重开 E69 附件 Epic | **中厚**；补齐已有列；单 sprint 可交付 |
| B | Activity Push | 勿默认 |
| C–J | 门户/甘特/Q2b/表单附件/递归/Bulk 多指派/深拷贝/stubs/CSV start | prefer skip / 后置 |
| K | 无限深度嵌套 + 服务端树形 payload | 偏厚；环/性能风险 |
| L | 仅 FE 假缩进、不写 parent_id | **过薄**；刷新丢失 |

**建议拍板：A（评论线程 mid）。**  
其余 runners-up 列入附录。

自检：深度上限、同 Issue 校验、软删子评、FE 树、CLI **1.58.0**、非目标与 no-emit、不重开 E63–E73 / E69 附件主表面已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 勿默认 |
| Customer 门户 / Initiative 甘特 | prefer skip |
| Q2b / 表单附件 / 递归 / Bulk 多指派 / 深拷贝 / stubs | skip |
| CSV start_date / start 提醒 | 刚交 E73；后置 |
| 再开 start_date / templates / multi-assignee / childProgress / 评论**附件** / Form / TZ | 刚闭 |
| 真 GitHub App / SSO / formula rollup | 过厚或禁 |

### Why this Epic now（一句话）

`parent_id` 与客户端 API **早已预留**，但详情仍扁平、无回复、无深度校验——协作只能顶层刷屏；E73 排期弧刚闭后轮换离开日期/模板/指派/进度/附件上传/表单/TZ/门户，用中厚刀补上 **线程校验 + FE 树/回复 + CLI**，对齐 Linear 回复叙事，且不重开 Push/甘特/E69 附件 Epic。

---

## 1. 目标

成功标准：可对 **顶层评论** 发回复（`parent_id`）；BE 拒绝跨 Issue parent、自指、超深；列表/详情仍返回扁平行（含 `parent_id`），FE **组树展示**缩进 +「回复」；父评作者进入通知 recipients（去重）；CLI **1.58.0** `issue comment add --parent-id`；**不** Activity Push、**不**改 E63–E73 邻面主表面、**不**重做 E69 附件 ACL/上传、**不** formula emit、**不**甘特/门户。

### A · BE（无新表）

- `add_comment` 增强（**Q1a 深度=1**：仅允许 parent 为 **根评论** `parent_id IS NULL`；备选 Q1b 深度≤2）  
- 校验：parent 存在、同 `issue_id`、未软删、非自指；失败 → 400  
- GET comments：保持扁平 + `parent_id`（**Q2a**）；可选 `?tree=1` **不做**（防双契约）  
- 软删（**Q3a**）：删父后子评仍在库，但列表默认 **隐藏子评**（或随父一并 `is_deleted` 标记——实现选一，验收钉「对用户不可见」）  
- 通知：回复时 recipients ∪ 父评 `user_id`（排除 actor）；类型仍 `commented`（**Q5a** 无新 webhook / 无新 notif type 名也可）  
- **无** alembic

### B · FE

- 详情评论区：按 `parent_id` 建树；根评下缩进展示 replies  
- 每条根评「回复」→ 聚焦回复框并带 `replyTo`；提交传 `parentId`  
- 深度>1 的历史脏数据：降级挂到根或扁平尾（防御）  
- 附件/反应：复用既有组件（不改 E69/E27 主契约）  
- vitest：`buildCommentTree`；build ok；守 E63 `f`+`r`

### C · CLI **1.58.0**

- `issue comment add <id> … --parent-id <commentId>`  
- `issue comment list` 可选显示 Parent；`--json` 含 `parent_id`  
- pins → **1.58.0**（**Q6a**）

### D · 安全 / 邻面 / no-emit

- 跨租户 404 不变  
- **Q5a**：不新增 webhook 事件名；沿用既有 comment/issue.updated 路径  
- formula **no-emit**  
- **不**改 E69 附件上传/ACL 主表面（回复评论若已支持挂附件则自然可用，不扩 cap/API）  
- **不**改 E63–E73 主表面（start_date / templates / multi-assignee / childProgress / Form / TZ / 假日 / 门户 仅 pins）

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户再厚、Initiative 甘特、Recurrence Q2b、表单公开附件、递归孙项、Bulk/Insights 多指派  
- 深拷贝 duplicate、模板 Issue stubs、CSV start_date、start 驱动提醒  
- 无限深度、服务端树形 JSON、评论编辑全文版本史  
- 重开 E69 附件 Epic / E27 反应模型大改  
- Formula emit；远程 push / 开 PR / **自开 E75**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 根→回复 OK；parent 跨 Issue / 对回复再回（若 Q1a）/ 自指 → 400 |
| B | GET 扁平含 `parent_id`；FE 树+缩进+回复入口 |
| C | 软删父后用户侧不见其子（Q3a） |
| D | 父评作者可收通知（非 actor）；无新 webhook 名 |
| E | CLI **1.58.0** + `--parent-id` + pins |
| F | 无 alembic；不改 E63–E73 / E69 附件主表面；formula no-emit |
| 门禁 | BE 定向 threading；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E75 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **评论线程 mid**（方案 A）；校验 + FE 树 + CLI；**无** Push / 甘特 / 门户 / 附件再开 |
| D2 | 无 alembic；复用 `parent_id` |
| D3 | 深度上限 **1**（仅回根评） |
| D4 | API 扁平；FE 客户端组树 |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.58.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E63–E73 邻面；不 push；不自开 E75 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 深度？ | **Q1a** 仅 1 层（parent 必须为根）；备选 Q1b ≤2（稍厚） |
| Q2 | 响应形状？ | **Q2a** 继续扁平 + `parent_id`；备选 Q2b 服务端 `replies[]` 树（双契约） |
| Q3 | 删父？ | **Q3a** 用户侧隐藏子（实现：级联软删或查询过滤）；备选 Q3b 子提升为根（易乱） |
| Q4 | 通知？ | **Q4a** recipients ∪ 父评作者；备选 Q4b 仅既有 assignee/watcher（弱） |
| Q5 | webhook？ | **Q5a** 无新事件名；备选 Q5b `issue.comment_replied`（噪） |
| Q6 | CLI？ | **Q6a** `--parent-id` + list 可见 Parent + pins **1.58.0**；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. BE validate parent/depth + 单测（TDD）  
3. 软删可见性 + 通知 recipients（TDD）  
4. FE `buildCommentTree` + 回复 UI + vitest  
5. CLI 1.58.0  
6. 邻面不动 / f+r / acceptance

---

## 7. 测试要点

- 根评下回复 → 200，`parent_id` 正确  
- parent 他 Issue / 软删父 / 对回复再回（Q1a）/ 自指 → 400  
- list 扁平含两行；FE tree 根 1 子 1  
- 软删父 → 用户 list 不见子  
- 通知 spy：父作者在 recipients；无新 webhook **事件名**  
- 不触 E73 start_date / E72 templates / E71 assignees / E70 progress / E69 attach **主路径改动**；formula no-emit  
- CLI 1.58.0 pins；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E75+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — E31 非目标。  
6. **递归孙项进度** — prefer skip。  
7. **Bulk/Insights 多指派** — prefer skip。  
8. **深拷贝 duplicate project** — prefer skip。  
9. **模板内 Issue stubs** — prefer skip。  
10. **CSV start_date / start 驱动提醒** — E73 后置。  
11. **深度≥2 / 服务端树 payload** — 本 Epic Q1a/Q2a 后置。  
12. **评论编辑版本史** — 另弧。

（备选扫描但本轮不推：再开 start_date/templates/multi-assignee/childProgress/评论附件上传/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.58.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E73-S1` @ `9d76ea2cb6094f438e6544ba85a75a35357b9388`  
- 拟开：`sprint/E74-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e74-comment-threading-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E75**

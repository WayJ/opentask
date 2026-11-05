# E77 Design：Issue 回收站 mid — trash/restore · CLI 1.61.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E77  
基线拟：`sprint/E76-S1` @ `d7c718c`（全文 `d7c718c12ffc376c9dfbfe455aa3f8f66c8ef5b2`；E76 design 基线 `83273b4`；E75 tip `6de4382` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E77-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E78**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e77-issue-trash-restore-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E77-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E76 连续闭合 … → Issue 复制（E75）→ **Issue 外链 mid（E76：issue_links · CLI 1.60.0）**。

E76 附录 runners-up（任务硬指引）：

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
15. **trash/restore** — **本轮候选**  
16. **Project lead/members** — candidate（贴 E72；ACL 易胀）  
17. **convert/set-parent** — candidate（贴 E70）  
18. **Issue merge** — candidate（常过厚）

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ / Form→Triage / 评论附件 / childProgress / multi-assignee / project templates / start_date / comment threading / issue duplicate / issue external links**。

代码实证 @ `d7c718c`：

| 面 | 现状 |
|----|------|
| 软删 | `issues.is_deleted`；`delete_issue` 只置位；列表/get **默认排除** |
| Restore | **无** `POST …/restore`；无 trash 列表 API；无 FE 回收站 |
| CLI delete | **刻意拒绝**（防 AI 误删）；无 `issue restore` / `issue trash` |
| Timeline | 有 delete 相关路径；**无** `restored` / trash 叙事 |
| Linear 对齐 | Linear Archive / 可找回；OpenTask 删了等于「单向消失」（数据仍在库） |
| 邻面 | E76 外链 / E75 复制刚闭 — 本轮宜离开链接与复制面 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue 回收站 mid**：`GET /api/issues/trash`（或 list `?deleted=1`）；`POST /api/issues/{id}/restore`；可选 bulk restore；timeline `restored`；FE 回收站页/入口 + 恢复；CLI **1.61.0** `issue trash` / `issue restore`（**仍禁止** CLI hard-delete）；无新表（复用 `is_deleted`）；无 Push | **中厚**；最高 ROI；单 sprint；离开刚闭弧 |
| B | Activity Push | 勿默认 |
| C–N | 门户/甘特/Q2b/附件/递归/Bulk/深拷贝/stubs/CSV/depth≥2/评论版本/G-then-X/复制附件 | skip / 后置 / 另弧 |
| O | Project lead + members | 贴 E72；写 ACL 易胀成大 Epic |
| P | Convert / set-parent 专用 UX+CLI `--parent` | 贴 E70；BE 已有 parent 校验 |
| Q | Issue merge | 过厚（评论/关系/关单） |
| R | 真 Archive 列 `archived_at` 与 `is_deleted` 双轨 | 概念分裂；偏厚 |

**建议拍板：A（Issue 回收站 mid）。**  
其余列入附录 runners-up。

自检：与 hard-delete/Archive 边界、权限、子项策略、CLI 仍禁删、CLI **1.61.0**、非目标与 no-emit、不重开 E63–E76 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| 再开 links / duplicate / threading / start_date / templates / … | 刚闭 |
| Project lead/members | 贴 E72；ACL 膨胀风险 |
| Convert/set-parent | 贴 E70 子项面 |
| Issue merge | 过厚 |
| 双轨 archived_at | 与现有 `is_deleted` 重复；本轮不引入第二生命周期 |

### Why this Epic now（一句话）

软删早已落库，但 **无法列出/恢复**——误删只能改库；外链/复制弧刚齐后操作面更忙，轮换离开 E63–E76 邻面，用中厚刀补上 **trash 列表 + restore + FE/CLI**，对齐「可找回」预期，且明确 **≠** 物理删除、**≠** 另建 Archive 状态机。

---

## 1. 目标

成功标准：member+ 可 **列出本 WS 已软删 Issue** 并 **restore**（`is_deleted=false`）；viewer 只读 trash（**Q1a**）或不可见（备选）；跨 WS 404；FE 回收站入口 + 恢复；CLI **1.61.0** `issue trash` / `issue restore`；**CLI 仍禁止 delete**；**不** Activity Push、**不**改 E63–E76 邻面主表面、**不** formula emit、**不**自开 E78。

### A · API / BE（无新表 · Q2a）

- `GET /api/issues/trash`  
  - 仅 `is_deleted=true` 且 `workspace_id=当前 WS`  
  - 分页同 list 惯例；默认按 `updated_at` desc（删除时间近似）  
  - 返回字段对齐精简 Issue 列表（code/title/status/priority/project/updated_at/deleted meta）  
- `POST /api/issues/{id}/restore`  
  - 将 `is_deleted=false`；404 若跨 WS 或不存在；已活 Issue → **Q3a** 200 幂等（或 409 备选）  
- 可选薄：`POST /api/issues/trash/restore-bulk` `{ issueIds }`（**Q4a** 本轮不做；单条足够）  
- **不**新增 hard-delete 端点；现有 DELETE 保持软删  
- Timeline：**Q5a** `restored`（action_data 可空或 `{ from: "trash" }`）；删除路径若已有 timeline 则不改语义  
- Webhook：**Q5a** 无新事件名（不发 `issue.restored`）；formula no-emit  
- 子项：**Q6 切片内 Q2** — **Q2a** restore **只恢复目标 Issue**，不级联子树；子项若仍 deleted 保持 deleted（文档写清）

权限：restore = member+；trash list = **Q1a** viewer+ 只读（与 list 对称）；viewer restore → 403。

### B · FE

- 导航/Issue 列表入口：「回收站」→ 表格列出已删；行内「恢复」  
- 恢复成功 toast + 从 trash 移除；可深链到详情（详情对 deleted 可读或 restore 后跳转——**Q1 细节：详情对 deleted member 可读只读条 + 恢复按钮**）  
- vitest：纯函数/状态 helper 若有；build ok；守 E63 `f`+`r`

### C · CLI **1.61.0**

- `opentask issue trash [--json] [--limit N]`  
- `opentask issue restore <id|code> [--json]`  
- **保持** `issue delete` CLI 拒绝（安全）；文档一句说明 Web UI / API 软删 + restore  
- pins → **1.61.0**

### D · 安全 / 邻面 / no-emit

- 跨租户 404；viewer 写 403  
- 不碰 attachments / links / VCS / relations 表结构  
- 不改 E63–E76 主表面（仅 CLI pins）  
- 无 Push / 门户 / 甘特；formula no-emit

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项、Bulk/Insights 多指派  
- 深拷贝 project、模板 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- 物理 hard-delete / 定时 purge / `archived_at` 双轨  
- Project lead/members、convert/set-parent、Issue merge（本轮不绑）  
- 再开 issue_links / duplicate / threading / start_date / templates  
- Formula emit；远程 push / 开 PR / **自开 E78**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | trash 列表仅本 WS 软删；默认 list/get 仍排除 deleted |
| B | restore → 重现于默认 list；幂等（Q3a）；跨 WS 404；viewer restore 403 |
| C | 不级联子树（Q2a）；不 hard-delete；无新 alembic 表 |
| D | FE 回收站 + 恢复；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.61.0** + trash/restore；`issue delete` 仍拒 |
| F | timeline `restored`；无新 webhook 名；formula no-emit；不改 E63–E76 邻面 |
| 门禁 | BE 定向 e77/trash；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E78 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue 回收站 mid**（方案 A）；复用 `is_deleted`；**无** 新 Archive 列 / Push / 甘特 / 门户 |
| D2 | trash list + restore；不级联子树；不 CLI delete |
| D3 | 无 hard-delete / purge 本轮 |
| D4 | timeline `restored`；无新 webhook 事件名 |
| D5 | CLI = **1.61.0** |
| D6 | 守 E40 D2/D7：永不 formula emit；不改 E63–E76 邻面；不 push；不自开 E78 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | viewer 可见 trash？ | **Q1a** viewer 可读 trash / 不可 restore；备选 Q1b 仅 member+ 见 trash |
| Q2 | 子项？ | **Q2a** 只恢复目标；不级联；备选 Q2b 级联未删父下的 deleted 子（复杂，不选） |
| Q3 | 对已活 Issue restore？ | **Q3a** 200 幂等；备选 Q3b 409 |
| Q4 | bulk restore？ | **Q4a** 本轮不做；备选 Q4b 薄 bulk |
| Q5 | timeline / webhook？ | **Q5a** `restored` timeline；无新 webhook 名；备选 Q5b `issue.restored` 事件（噪） |
| Q6 | CLI？ | **Q6a** `issue trash` + `issue restore` + pins **1.61.0**；delete 仍拒；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. Service `list_trashed` + `restore_issue`（TDD）  
3. API trash + restore + 权限/跨 WS（TDD）  
4. Timeline `restored`（TDD）  
5. FE 回收站页/入口 + 恢复  
6. CLI 1.61.0  
7. 邻面不动 / f+r / acceptance

---

## 7. 测试要点

- 软删后默认 list 不可见；trash 可见；restore 后 list 可见、trash 消失  
- 跨 WS 404；viewer restore 403；member restore 200 幂等  
- 父删子删：只 restore 父 → 子仍 deleted；不自动建关系变更  
- spy：无 hard DELETE SQL；无新 webhook **事件名**；formula no-emit  
- 不触 E76 links / E75 duplicate / E74 threading / E73 start_date / E72 templates  
- CLI 1.61.0 pins；`issue delete` 仍错误退出；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E78+；若 Yuri 改选可替换本草案）

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
12. **评论版本史 / 评论编辑 UX 加厚** — 另弧。  
13. **G-then-X 导航热键** — E5 后置；另弧。  
14. **复制附件/子树** — 过厚。  
15. **Project lead + members** — 贴 E72；ACL 易胀。  
16. **Convert / set-parent 专用 CLI/UX** — 贴 E70。  
17. **Issue merge** — 过厚。  
18. **定时 purge / hard-delete** — 本 Epic 明确不做；另刀。  
19. **`archived_at` 双轨 Archive** — 与 `is_deleted` 分裂；另弧。

（备选扫描但本轮不推：再开 links/duplicate/threading/start_date/templates/multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.61.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E76-S1` @ `d7c718c12ffc376c9dfbfe455aa3f8f66c8ef5b2`  
- 拟开：`sprint/E77-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e77-issue-trash-restore-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E78**

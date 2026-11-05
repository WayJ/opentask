# E79 Design：Project lead + members mid · CLI 1.63.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E79  
基线拟：`sprint/E78-S1` @ `6fe2b57`（全文 `6fe2b575984ae2813304798d68cd246cd80ca347`；E78 design 基线 `d2e30be`；E77 tip `04d5118` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E79-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E80**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e79-project-lead-members-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E79-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E78 连续闭合 … → Issue 回收站（E77）→ **Issue 父子转换 mid（E78：set-parent/convert · CLI 1.62.0）**。

E78 附录 runners-up（任务硬指引）：

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
15. **Project lead/members** — **本轮候选**（贴 E72；ACL 风险用 Q 钉死「仅名册」）  
16. **Issue merge** — **过厚**  
17. **Timed purge/hard-delete** — **后置**（刚做 trash）  
18. **`archived_at` dual-track** — **prefer skip**  
19. **换项目清无效 milestone/cycle** — 真缺口偏薄；本轮次之 runner-up  

轮换离开刚闭弧：**trash / parent-set / links / duplicate / threading / start_date / templates / multi-assignee / childProgress / 评论附件 / Form→Triage / TZ / 假日 / Initiative deps / 附件 ACL / Search / Insights**。

代码实证 @ `6fe2b57`：

| 面 | 现状 |
|----|------|
| Project 模型 | `projects` 有 name/dates/health；**无** `lead_id`；**无** `project_members` 表 |
| ACL | 仍以 **WorkspaceMember**（owner/member/viewer）为准；项目级私有化未做 |
| Watchers | `project_watchers` 已有（health Inbox 扇出）— **≠** lead/members 名册 |
| E72 templates | 可 apply milestones；模板 **未** 携带 lead/members |
| FE | 项目设置/详情 **无** 负责人 / 成员编辑 |
| CLI | `project list/show/create/update/…`；**无** `project lead` / `project member *` |
| Linear 对齐 | Linear Project lead + members 一等字段 |

另扫到的真缺口（本轮不绑）：换 `project_id` 时 FE 只传 `{project_id}`，BE **不**自动清跨项目 `milestone_id`（cycle 为 WS 作用域，通常可保留）→ 偏薄完整性刀，列入附录。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Project lead + members mid**：`lead_id` + `project_members` 名册；CRUD API；FE 项目设置；CLI **1.63.0**；**不**改 WS ACL / 不做私有项目；不重开 E72 模板深拷贝 | **中厚**；对齐 Linear；单 sprint；离开 parent/trash |
| B | Activity Push | 勿默认 |
| C–N | 门户/甘特/Q2b/附件/递归/Bulk/深拷贝/stubs/CSV/depth≥2/评论版本/G-then-X/复制附件 | skip / 后置 / 另弧 |
| O | 换项目清 milestone/cycle | 真缺口但偏薄；runner-up |
| P | Issue merge | 过厚 |
| Q | purge / `archived_at` | 刚闭 trash；后置 / skip |
| R | Project lead **带写 ACL / 私有项目** | 易胀成大 Epic；本轮禁 |

**建议拍板：A（Project lead + members mid · roster-only）。**  
其余列入附录 runners-up。

自检：与 E72 templates 边界（本 Epic 不改模板 schema / apply 深拷贝）、与 project_watchers 边界（watch ≠ member）、CLI **1.63.0**、非目标与 no-emit、不重开 E63–E78 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at | 刚闭 trash；后置 / skip |
| Issue merge | 过厚 |
| 再开 parent / trash / links / duplicate / … | 刚闭 |
| 换项目清 milestone | 有价值但偏薄；本轮要中厚产品面（名册 + FE + CLI） |
| lead+members **改 ACL** | 膨胀风险；本轮 Q 钉死 roster-only |

### Why this Epic now（一句话）

E72 模板已落地但 **Project 仍无 Linear 式负责人/成员名册**；父子/回收站弧刚闭后轮换离开 Issue 关系面，用中厚刀补上 **lead + members（仅名册/展示/筛选，不改 ACL）+ FE + CLI**，且不碰 merge、私有项目、模板深拷贝。

---

## 1. 目标

成功标准：member+ 可为同 WS Project 设置 **lead**、增删 **members**；序列化出现在 project show/list；FE 项目设置可编辑；CLI **1.63.0**；跨 WS / 非成员用户拒；viewer 只读；**不**改变 issue/project 读写 ACL（仍 WS 角色）；**不** Activity Push、**不**改 E63–E78 邻面主表面、**不** formula emit、**不**自开 E80。

### A · BE

- 表：  
  - `projects.lead_id` → FK `users.id` NULL（**Q1a** 单 lead；备选 Q1b 多 lead 不做）  
  - `project_members(project_id, user_id, role?, created_at)` 唯一 `(project_id, user_id)`（**Q2a** 独立表；备选 Q2b 仅 JSON 数组——不选，难约束）  
- **Q3a** lead **自动**属于 members（设 lead 时 upsert member）；清 lead 不强制移除 member  
- 成员必须为 **同 WS** WorkspaceMember（任意角色含 viewer 可入名册）；跨 WS user → 400  
- API（建议）：  
  - `PATCH /api/projects/{id}` 可写 `lead_id`（null 清）  
  - `GET/POST/DELETE /api/projects/{id}/members`（或等价 nested）  
- 序列化：`lead`（id/name/avatar 摘要）+ `members[]`；list 可精简为 `lead_id` + `member_count`（**Q4a** list 精简、show 完整）  
- **不**据此拒绝 issue 读写；**不**新建 webhook 事件名（**Q5a**）；formula no-emit  
- 删用户/退 WS：**Q6a** 软处理——lead/member 行保留或 SET NULL lead + 删 member 行（实现选：user 仍在则显示；不在则序列化为 null / 跳过）；不做定时 purge  

权限：写 member+（WS）；跨租户 404；viewer 403 写。

### B · FE

- 项目设置/详情：Lead 选择器（WS 成员搜索）；Members 多选增删  
- 列表/卡片可选展示 lead 头像  
- 不据此隐藏项目（ACL 不变）  
- vitest：序列化/helper 若抽纯函数；build ok；守 E63 `f`+`r`

### C · CLI **1.63.0**

- `opentask project lead set <project> <user>`  
- `opentask project lead clear <project>`  
- `opentask project member add|remove <project> <user>`  
- `opentask project member list <project>`  
- 打印 lead/members；`--json`  
- pins → **1.63.0**；历史 epic 断言级联  

### D · 安全 / 邻面 / no-emit

- 跨租户 404；viewer 写 403  
- **不**引入 project-private ACL / 不改 issue 可见性  
- 不触 trash/parent/links/duplicate/attachments/VCS 主路径  
- 不改 E70 childProgress；不改 E72 template apply 语义（**可不**把 lead 写入模板——非目标）  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板 Issue stubs、CSV start_date、depth≥2 评论树、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **Project 级 ACL / 私有项目 / 按 member 过滤可见 Issue**  
- 把 lead/members 写入 E72 template schema / apply  
- 再开 trash / parent / links / duplicate / threading / start_date / templates / multi-assignee  
- 换项目自动清 milestone（另刀 runner-up）  
- Formula emit；远程 push / 开 PR / **自开 E80**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 设 lead / 清 lead；members add/remove；同 WS 约束；跨 WS 拒 |
| B | show 含 lead+members；list 含 lead_id 或精简字段；无新 webhook 名 |
| C | viewer 写 403；不改 issue/project 读 ACL；lead upsert 入 members（Q3a） |
| D | FE 可编辑 lead/members；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.63.0** + `project lead *` / `project member *` + pins |
| F | 不改 E63–E78 邻面；formula no-emit；无 Push/甘特/门户；不改 E72 apply |
| 门禁 | BE 定向 e79/lead/members；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E80 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Project lead + members mid**（方案 A）；roster-only |
| D2 | 新列 `lead_id` + 表 `project_members`；无 timeline enum 也可（非 Issue 时间线）；无新 webhook 名 |
| D3 | **不**改 WS/Issue ACL；不做私有项目 |
| D4 | 不改 E72 template apply；不深拷贝成员进模板 |
| D5 | CLI = **1.63.0** |
| D6 | 守 E40 D2/D7；不改 E63–E78 邻面；不 push；不自开 E80 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | lead 基数？ | **Q1a** 单 `lead_id`；备选 Q1b 多 lead（不做） |
| Q2 | members 存储？ | **Q2a** `project_members` 表；备选 Q2b JSON（不选） |
| Q3 | lead 与 members 关系？ | **Q3a** 设 lead 时 upsert 进 members；清 lead 保留 member 行 |
| Q4 | list 载荷？ | **Q4a** list：`lead_id` + `member_count`；show：完整 lead+members |
| Q5 | webhook？ | **Q5a** 无新事件名；备选 Q5b `project.lead_changed`（噪） |
| Q6 | CLI？ | **Q6a** `project lead set\|clear` + `project member add\|remove\|list` + pins **1.63.0**；备选 Q6b 仅 `project update --lead` |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic：`lead_id` + `project_members`（TDD）  
3. API set lead / members CRUD + 序列化（TDD）  
4. FE 项目设置 + vitest  
5. CLI 1.63.0 `project lead|member *`  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- set lead → `lead_id`；自动出现在 members（Q3a）  
- clear lead → `lead_id` null；members 可仍含原用户  
- add/remove member；重复 add 幂等；跨 WS user → 400  
- viewer 写 403；非成员 WS → 404  
- spy：issue 读写权限矩阵不变；无新 webhook **事件名**；formula no-emit  
- 不触 E78 parent / E77 trash / E76 links / E75 duplicate / E72 apply 行为  
- CLI 1.63.0 pins；FE vitest；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E80+；若 Yuri 改选可替换本草案）

1. **换项目时自动清无效 milestone**（cycle 为 WS 作用域通常保留）— **真缺口偏薄**；建议下一薄刀或并入完整性小 Epic。  
2. **Activity 实时/推送加厚** — 仍勿默认。  
3. **Customer 门户再厚** — prefer skip。  
4. **Initiative 甘特精修** — prefer skip。  
5. **Recurrence Q2b advance** — rotate off。  
6. **表单公开附件** — prefer skip。  
7. **递归孙项进度** — prefer skip。  
8. **Bulk/Insights 多指派** — prefer skip。  
9. **深拷贝 duplicate project** — prefer skip。  
10. **模板内 Issue stubs** — prefer skip。  
11. **CSV start_date / start 提醒** — 后置。  
12. **depth≥2 / 服务端树** — 后置。  
13. **评论版本史 / 评论编辑 UX 加厚** — 另弧。  
14. **G-then-X 导航热键** — 另弧。  
15. **复制附件/子树** — 过厚。  
16. **Issue merge** — 过厚。  
17. **定时 purge / hard-delete** — 刚闭 trash；后置。  
18. **`archived_at` 双轨** — prefer skip。  
19. **Project 私有 ACL / 按 member 过滤 Issue** — 另大弧（本 Epic 明确非目标）。  

（备选扫描但本轮不推：再开 trash/parent/links/duplicate/threading/start_date/templates/multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.63.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E78-S1` @ `6fe2b575984ae2813304798d68cd246cd80ca347`  
- 拟开：`sprint/E79-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e79-project-lead-members-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E80**

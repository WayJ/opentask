# E78 Design：Issue 父子转换 mid — set-parent / convert · CLI 1.62.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E78  
基线拟：`sprint/E77-S1` @ `04d5118`（全文 `04d5118673284f4c7d3b8ff1e9294c9c407f7b37`；E77 design 基线 `b1754a5`；E76 tip `d7c718c` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E78-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E79**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e78-issue-set-parent-convert-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E78-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E77 连续闭合 … → Issue 外链（E76）→ **Issue 回收站 mid（E77：trash/restore · CLI 1.61.0）**。

E77 附录 runners-up（任务硬指引）：

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
15. **Project lead/members** — candidate（贴 E72；ACL 易胀）  
16. **convert/set-parent** — **本轮候选**  
17. **Issue merge** — often thick  
18. **timed purge/hard-delete** — **后置**（刚做 trash）  
19. **`archived_at` dual-track** — **prefer skip**

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ / Form→Triage / 评论附件 / childProgress / multi-assignee / project templates / start_date / comment threading / duplicate / external links / trash-restore**。

代码实证 @ `04d5118`：

| 面 | 现状 |
|----|------|
| parent 校验 | `_validate_parent_issue_id`（同 WS、禁自环、祖先环检测）已有 |
| Update API | `IssueUpdate.parent_issue_id` 可写；**无** timeline `parent_changed` |
| FE | 可「在此下建子」；详情显示父链；**无**「设为某 Issue 子项 / 提升为根 / 换父」选择器 |
| CLI | `issue update` **无** `--parent` / `--clear-parent`；`api_client.update_issue` 已可选 `parent_issue_id` |
| childProgress | E70 只读聚合 — **≠** 改父子关系 UX |
| Linear 对齐 | Linear「Make sub-issue of…」/「Convert to issue」一等动作 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **父子转换 mid**：补 timeline `parent_changed`（薄 alembic ADD VALUE）；FE 详情「设为子项 / 换父 / 提升为根」；CLI **1.62.0** `issue parent set\|clear`（或 `update --parent`）；复用既有校验；无 Push / 不重开 E70 进度公式 | **中厚**；对齐 Linear；单 sprint；离开 trash/links |
| B | Activity Push | 勿默认 |
| C–N | 门户/甘特/Q2b/附件/递归/Bulk/深拷贝/stubs/CSV/depth≥2/评论版本/G-then-X/复制附件 | skip / 后置 / 另弧 |
| O | Project lead + members | 贴 E72；写 ACL 易胀 |
| P | Issue merge | 过厚 |
| Q | purge / `archived_at` | 刚闭 trash；后置 / skip |
| R | 换项目时清 milestone/cycle | 真缺口但偏薄修；可 runner-up |

**建议拍板：A（Issue 父子转换 mid）。**  
其余列入附录 runners-up。

自检：与 E70 childProgress 边界（本 Epic 改关系，不改进度聚合）、环检测、跨 WS、CLI **1.62.0**、非目标与 no-emit、不重开 E63–E77 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at | 刚闭 trash；后置 / skip |
| Project lead/members | 贴 E72；ACL 膨胀 |
| Issue merge | 过厚 |
| 再开 trash / links / duplicate / threading / … | 刚闭 |
| 换项目清 milestone | 有价值但偏薄；本轮要中厚产品动作 |

### Why this Epic now（一句话）

父子列与环检测早已可写，但 **产品动作面缺失**——不能像 Linear 一样「挂到某父 / 提升为根」；回收站弧刚闭后轮换离开删除/外链/复制，用中厚刀补上 **parent 变更 UX + timeline + CLI**，且不重开 E70 进度聚合、不碰 merge/深拷贝子树。

---

## 1. 目标

成功标准：member+ 可将可见 Issue **设为同 WS 另一 Issue 的子项**、**更换父**、或 **清空父（提升为根）**；环/自环/跨 WS 拒；viewer 只读；timeline 记 `parent_changed`；FE 详情入口；CLI **1.62.0**；**不** Activity Push、**不**改 E63–E77 邻面主表面（含不改 childProgress 计算）、**不** formula emit、**不**自开 E79。

### A · BE

- 复用 `PUT /api/issues/{id}` 的 `parent_issue_id`（**Q1a** 不另开 `/convert` 除非 FE 需要别名；备选 Q1b 薄 `POST …/set-parent`）  
- 清空父：**Q2a** 显式 `parent_issue_id: null`（JSON null）；省略字段则不改  
- 变更时写 timeline **`parent_changed`**（action_data `{ from, to }`；to=null 表示根）— 需 alembic **ADD VALUE**（同 E77 `restored` 模式；**无新表**）  
- 校验：既有同 WS、禁自环、祖先环；父不得为软删（**Q3a** 拒 deleted 父 → 400）  
- **不**改 children 进度聚合逻辑（E70 只读面不动）  
- Webhook：**Q4a** 无新事件名（不发 `issue.parent_changed` webhook）；formula no-emit  
- 深度：**Q5a** 不强制 max-depth（环检已够）；备选 Q5b max depth=5

权限：写 member+；跨 WS 404；viewer 403。

### B · FE

- 详情头/菜单：  
  - 「设为子项…」→ Issue 搜索选择器（同 WS、排除自身与会成环的祖先/子孙——客户端可先排除自身，环由 BE 终裁）  
  - 「提升为根」（仅当已有父）  
  - 可选：「更换父」同选择器  
- 成功后刷新父链 / children；toast  
- vitest：环排除 helper 若抽纯函数；build ok；守 E63 `f`+`r`

### C · CLI **1.62.0**

- **Q6a** `opentask issue parent set <issue> <parent>`  
- `opentask issue parent clear <issue>`  
- 打印新 parent / null；`--json`  
- pins → **1.62.0**；历史 epic 断言级联  

### D · 安全 / 邻面 / no-emit

- 跨租户 404；viewer 写 403  
- 不触 trash/links/duplicate/attachments/VCS 主路径  
- 不改 E70 `childProgress` 计算；不改 E74 comment `parent_id`  
- 无 Push / 门户 / 甘特；formula no-emit

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板 Issue stubs、CSV start_date、depth≥2 评论树、评论版本史、G-then-X、复制附件/子树  
- Issue merge、Project lead/members、purge/hard-delete、`archived_at`  
- 再开 trash / links / duplicate / threading / start_date / templates  
- 拖拽看板改父子、多父、跨 WS 父  
- Formula emit；远程 push / 开 PR / **自开 E79**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | set-parent → `parent_issue_id` 更新；clear → null；环/自环/跨 WS 拒 |
| B | timeline `parent_changed`（from/to）；无新表；无新 webhook 名 |
| C | 软删父拒（Q3a）；不改 childProgress 实现；不级联改子树其它字段 |
| D | FE 设为子项 / 提升为根；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.62.0** + `issue parent set\|clear` + pins |
| F | 不改 E63–E77 邻面；formula no-emit；无 Push/甘特/门户 |
| 门禁 | BE 定向 e78/parent；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E79 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue 父子转换 mid**（方案 A）；复用 update + 校验；补 timeline/FE/CLI |
| D2 | 无新业务表；alembic 仅 enum ADD VALUE `parent_changed` |
| D3 | 不改 E70 进度聚合；不 merge；不深拷贝子树 |
| D4 | 无新 webhook 事件名；formula no-emit |
| D5 | CLI = **1.62.0** |
| D6 | 守 E40 D2/D7；不改 E63–E77 邻面；不 push；不自开 E79 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | API 形态？ | **Q1a** 复用 PUT `parent_issue_id`；备选 Q1b 另 `POST …/set-parent` |
| Q2 | 清空父？ | **Q2a** JSON `null`；备选 Q2b 哨兵 `""`（不选） |
| Q3 | 软删父？ | **Q3a** 400；备选 Q3b 允许（易脏） |
| Q4 | webhook？ | **Q4a** 无新事件名；备选 Q4b `issue.parent_changed`（噪） |
| Q5 | max-depth？ | **Q5a** 不限（环检足够）；备选 Q5b depth≤5 |
| Q6 | CLI？ | **Q6a** `issue parent set\|clear` + pins **1.62.0**；备选 Q6b 仅 `update --parent` |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic ADD VALUE `parent_changed` + enum（TDD timeline）  
3. update_issue 写 timeline + 软删父拒（TDD）  
4. FE 选择器 + 提升为根 + vitest  
5. CLI 1.62.0 `issue parent *`  
6. 邻面不动 / f+r / acceptance

---

## 7. 测试要点

- A→B 为父：A.parent=B；timeline from/to；列表/详情父链更新  
- clear：parent=null；timeline to=null  
- 自环 / A→B 且 B 祖先含 A → 400；跨 WS 父 → 404/400  
- 软删父 → 400（Q3a）  
- spy：不改 childProgress 函数体；无新 webhook **事件名**；formula no-emit  
- 不触 E77 trash / E76 links / E75 duplicate / E74 comment parent_id  
- CLI 1.62.0 pins；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E79+；若 Yuri 改选可替换本草案）

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
16. **Issue merge** — 过厚。  
17. **定时 purge / hard-delete** — 刚闭 trash；后置。  
18. **`archived_at` 双轨** — prefer skip。  
19. **换项目时自动清无效 milestone/cycle** — 真缺口偏薄；可另刀。

（备选扫描但本轮不推：再开 trash/links/duplicate/threading/start_date/templates/multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.62.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E77-S1` @ `04d5118673284f4c7d3b8ff1e9294c9c407f7b37`  
- 拟开：`sprint/E78-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e78-issue-set-parent-convert-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E79**

# E76 Design：Issue 外链 mid — issue_links · CLI 1.60.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E76  
基线拟：`sprint/E75-S1` @ `6de4382`（全文 `6de4382e7e75a3e0d1c2e9a962f32439d2667944`；E75 design 基线 `78e12bb`；E74 tip `98d5bf4` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E76-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E77**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e76-issue-external-links-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E76-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E75 连续闭合 … → comment threading（E74）→ **Issue 复制 mid（E75：duplicate · CLI 1.59.0）**。

E75 附录 runners-up（任务硬指引）：

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
14. **复制附件/子树** — **过厚**（刚做 thin duplicate）

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ / Form→Triage / 评论附件 / childProgress / multi-assignee / project templates / start_date / comment threading / issue duplicate**。

代码实证 @ `6de4382`：

| 面 | 现状 |
|----|------|
| Issue 附件 | E66 ACL + 上传/下载齐全；**文件**非 URL |
| Customer | 有单字段 `external_url`；**Issue 无**结构化外链表 |
| VCS | E11 `issue_vcs_links` = PR/分支契约；**≠** 任意 URL |
| Relations | E20 blocks/relates = **Issue↔Issue**；**≠** 外站链接 |
| Entity docs | E10 短 Markdown；非书签式 URL 列表 |
| Linear 对齐 | Linear Issue「Links」挂任意 URL + 标题；OpenTask 只能塞描述/附件/PR |
| 软删 | `is_deleted` 单向；**无** restore/回收站 UI（另候选） |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue 外链 mid**：alembic `issue_links`；CRUD API；详情「链接」区；CLI **1.60.0** `issue link`；timeline 薄记；无 Push / 无附件复用 | **中厚**；对齐 Linear Links；单 sprint；离开刚闭弧 |
| B | Activity Push | 勿默认 |
| C–N | 门户/甘特/Q2b/表单附件/递归/Bulk/深拷贝/stubs/CSV start/depth≥2/评论版本/G-then-X/复制附件 | skip / 后置 / 另弧 |
| O | Issue 回收站/restore（补齐软删 undo） | 中偏薄；可 runner-up |
| P | Project lead + members | 贴 E72 项目面；ACL 易胀 |
| Q | Convert / set-parent 专用命令 | 贴 E70 子项面；CLI 缺 `--parent` 但 BE 已有 |
| R | Issue merge | 过厚（评论/关系/关单语义） |

**建议拍板：A（Issue 外链 mid）。**  
其余列入附录 runners-up。

自检：与附件/VCS/Customer URL/Issue relations 边界、URL 校验、上限、CLI **1.60.0**、非目标与 no-emit、不重开 E63–E75 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| 再开 duplicate / threading / start_date / templates / assignees / childProgress / 评论附件 | 刚闭 |
| 回收站/restore | 有价值但偏「删改修」；本轮优先补 **Linear 外链产品面** |
| Project lead/members | 贴 E72；ACL 范围易胀 |
| Convert/set-parent / Issue merge | 贴子项或过厚 |
| Formula rollup / emit / 真 GitHub App | 禁或过厚 |

### Why this Epic now（一句话）

复制/排期/协作/评论弧刚齐，Issue 仍 **无法结构化挂设计稿/Notion/监控面板等 URL**——只能塞描述或当附件上传；轮换离开 E63–E75 邻面后，用中厚刀补上 **`issue_links` + 详情区 + CLI**，对齐 Linear Links，且明确 **≠** 文件附件、**≠** VCS PR 链、**≠** Issue↔Issue relations。

---

## 1. 目标

成功标准：member+ 可对可见 Issue **增删改查外链**（url + 可选 title）；viewer+ 只读；列表/详情返回 `links[]` 或详情嵌套；跨 WS 404；CLI **1.60.0**；**不** Activity Push、**不**改 E63–E75 邻面主表面、**不** formula emit、**不**甘特/门户/附件上传再开、**不**自开 E77。

### A · 数据与 API（BE）

**Q1a 表 `issue_links`：**

| 列 | 说明 |
|----|------|
| `id` | UUID PK |
| `workspace_id` | 租户；索引 |
| `issue_id` | FK → issues CASCADE |
| `url` | Text/String(2048)；必填 |
| `title` | String(255) 可空；空则 FE 显示 hostname |
| `position` | Int；同 Issue 内排序（**Q2a** 追加到末尾） |
| `created_by` | user id |
| `created_at` / `updated_at` | |

- 索引：`(issue_id, position)`；`(workspace_id, issue_id)`  
- 上限：**Q3a** 每 Issue ≤ **50** 条  
- URL 校验：**Q4a** 仅 `http://` / `https://`（拒 `javascript:` / 相对路径 / 空）

路由（均需 workspace 上下文）：

- `GET    /api/issues/{id}/links`  
- `POST   /api/issues/{id}/links` body `{ url, title? }`  
- `PATCH  /api/issues/{id}/links/{link_id}` body `{ url?, title?, position? }`  
- `DELETE /api/issues/{id}/links/{link_id}`  
- 可选薄：`PUT /api/issues/{id}/links/reorder` `{ linkIds: string[] }`（**Q2a** 有 PATCH position 则可后置 reorder）

权限：写 = member+；读 = viewer+；跨 WS / 非成员 → **404**（与 Issue get 同型）。

Timeline（**Q5a**）：`link_added` / `link_removed`（action_data: `{ link_id, url, title? }`）；**不**为每次 title 微调刷时间线（仅 url 变更可记 `link_updated` 或跳过——默认 **仅 add/remove**）。

Webhook：**Q5a** 无新事件名；不 emit formula；不强制新 webhook。

### B · FE

- 详情侧栏/下方「链接」折叠区：列表（favicon 可省略，hostname + title）；「添加」输入 url（+ 可选标题）；行内打开（新标签）、编辑、删除  
- 空态文案：「添加设计稿、文档或仪表盘链接」  
- vitest：url 校验 / hostname helper；build ok；守 E63 `f`+`r`

### C · CLI **1.60.0**

- `opentask issue link list <issue>`  
- `opentask issue link add <issue> <url> [--title …] [--json]`  
- `opentask issue link rm <issue> <link-id> [--json]`  
- 可选：`issue link update …`  
- pins → **1.60.0**（**Q6a**）；历史 epic 版本断言级联

### D · 安全 / 邻面 / no-emit

- 跨租户 404；viewer 写 403  
- **不**走附件存储 / ACL 签名 URL（外链非文件）  
- **不**写入 `issue_vcs_links`；**不**建 IssueRelation  
- formula **no-emit**；不改 E63–E75 主表面（仅 CLI pins）  
- **不** Activity Push / 门户 / 甘特

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项、Bulk/Insights 多指派  
- 深拷贝 project、模板 Issue stubs、CSV start_date、depth≥2、评论版本史、G-then-X、复制附件/子树  
- 文件附件上传、VCS/PR 链加厚、Issue↔Issue relations 新类型、富文本内嵌预览/OG 抓取、病毒扫描  
- 回收站/restore、Project lead/members、Issue merge、Convert/set-parent（本轮不绑）  
- Formula emit；远程 push / 开 PR / **自开 E77**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | alembic `issue_links`；CRUD 绿；每 Issue ≤50；非法 URL 400 |
| B | 跨 WS 404；viewer 读 OK / 写 403 |
| C | FE 详情链接区增删；外开新标签；vitest+build；`f`+`r` 仍在 |
| D | CLI **1.60.0** + `issue link *` + pins |
| E | timeline 仅 add/remove（Q5a）；无新 webhook 名；formula no-emit |
| F | ≠ 附件 / ≠ VCS / ≠ IssueRelation；不改 E63–E75 邻面 |
| 门禁 | BE 定向 e76/links；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E77 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue 外链 mid**（方案 A）；`issue_links` + 详情区 + CLI；**无** Push / 甘特 / 门户 / 附件再开 |
| D2 | 仅 http(s) URL；与 Document 附件、VCS、IssueRelation 分表分路径 |
| D3 | 每 Issue 上限 50；position 追加末尾 |
| D4 | Timeline 记 add/remove；无新 webhook 事件名 |
| D5 | CLI = **1.60.0** |
| D6 | 守 E40 D2/D7：永不 formula emit；不改 E63–E75 邻面；不 push；不自开 E77 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 表结构？ | **Q1a** `issue_links(url, title?, position, …)`；备选 Q1b 塞进 JSON 列（难筛/难 CLI） |
| Q2 | 排序？ | **Q2a** `position` + 追加末尾；PATCH 可改；完整 reorder 端点可后置 |
| Q3 | 上限？ | **Q3a** 50；备选 Q3b 20；Q3c 无上限 |
| Q4 | URL 协议？ | **Q4a** 仅 http/https；备选 Q4b 再允 `mailto:`（噪） |
| Q5 | timeline / webhook？ | **Q5a** timeline add/remove；无新 webhook 名；备选 Q5b `issue.link_added` 事件（噪） |
| Q6 | CLI？ | **Q6a** `issue link list|add|rm` + pins **1.60.0**；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic `issue_links` + model/schema（TDD）  
3. Service CRUD + URL 校验 + 上限（TDD）  
4. API routes + 权限/跨 WS（TDD）  
5. Timeline add/remove（TDD）  
6. FE 详情链接区 + vitest  
7. CLI 1.60.0  
8. 邻面不动 / f+r / acceptance

---

## 7. 测试要点

- 同 Issue 增 2 链 → list 顺序稳定；title 空时 API 仍 200  
- 第 51 条 → 400；`javascript:alert(1)` / 相对路径 → 400  
- 跨 WS 404；viewer POST 403；member DELETE 200  
- spy：不写 attachments / issue_vcs_links / issue_relations；formula no-emit；无新 webhook **事件名**  
- 不触 E75 duplicate / E74 threading / E73 start_date / E72 templates / E71 主表面  
- CLI 1.60.0 pins；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E77+；若 Yuri 改选可替换本草案）

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
14. **复制附件/子树** — 过厚（E75 thin duplicate 刚闭）。  
15. **Issue 回收站 / restore** — 补齐 `is_deleted` undo + trash 列表；中偏薄；可下一刀。  
16. **Project lead + members** — 贴 E72；ACL 易胀。  
17. **Convert / set-parent 专用 CLI/UX** — 贴 E70；BE 已有 parent 校验。  
18. **Issue merge** — 过厚。

（备选扫描但本轮不推：再开 duplicate/threading/start_date/templates/multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.60.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E75-S1` @ `6de4382e7e75a3e0d1c2e9a962f32439d2667944`  
- 拟开：`sprint/E76-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e76-issue-external-links-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E77**

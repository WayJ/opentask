# E70 Design：子问题进度汇总 mid — childProgress · CLI 1.54.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E70  
基线拟：`sprint/E69-S1` @ `08e327f`（全文 `08e327fcedb5f59f8183d7c9a21aee9a8388e8e3`；E69 design 基线 `a5d1a91`；E68 tip `35f1e0a` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E70-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E71**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e70-subissue-progress-rollup-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E70-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E69 连续闭合 … → Form→Triage（E68）→ **评论附件 mid（E69：`issue_comment` Documents · ACL 复用 · CLI 1.53.0）**。

E69 附录 runners-up（不绑定）：

1. **Activity Push** — 仍 **勿默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b advance** — **rotate off**  
5. **表单公开附件** — E31 非目标 / **prefer skip**

任务硬约束：轮换离开 **门户 / 假日 / Initiative deps / 附件 ACL / TZ·due / Form→Triage / 评论附件** 刚闭弧。

代码实证 @ `08e327f`：

| 面 | 现状 |
|----|------|
| 父子 Issue | `parent_issue_id` + `GET …/children` + 详情嵌入 `children: IssueChildSummary[]`（id/code/title/status）；FE 可建子项 |
| 进度 | **无** `childProgress` / 完成百分比；父详情看不到「3/5 done」；列表无徽章 |
| Initiative health | E10 已有 Project 健康 worst-of 汇总 — **模式可参考**，实体轴不同 |
| Formula | E40/E43 明示 **不做跨 Issue / children rollup 公式**；本 Epic 是 **结构父子进度**，非 formula CF |
| 评论附件等 | E69 **刚闭**；本轮宜离开 |
| Roadmap 扫描 | Linear 父 Issue 展示子项完成度；runners-up 均不宜默认；无 alembic 的聚合 mid 可单 sprint 交付 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **子问题进度汇总 mid**：详情默认带 `childProgress`；列表 `?include=childProgress`；闭合集=resolved/closed/rejected（对齐 due-reminder CLOSED_STATUSES）；FE 进度条/分数；CLI **1.54.0**；**无** Push / 门户 / 甘特 / 附件再开 | **中厚**；复用 children 查询；无新表；单 sprint 可交付 |
| B | Activity Push | 勿默认 |
| C | Customer 门户再厚 | prefer skip |
| D | Initiative 甘特 | prefer skip |
| E | Q2b recurrence advance / 表单公开附件 | rotate off / E31 非目标 |
| F | 多指派人 mid | 需结表；偏厚；可后置 |
| G | 仅 FE 前端数 children status | **过薄**；列表/CLI 不一致 |

**建议拍板：A（子问题进度汇总 mid）。**  
Push / 门户 / 甘特 / Q2b / 表单附件 / 多指派人列入附录 runners-up。

自检：闭合集语义、列表 opt-in、FE/CLI **1.54.0**、非目标与 no-emit、与 formula rollup 边界已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 勿默认 |
| Customer 门户再厚 | prefer skip |
| Initiative 甘特 | prefer skip |
| Q2b / 表单公开附件 | rotate off / E31 |
| 再开评论附件 / Form / TZ / 假日 / Search | 刚闭 |
| 多指派人 / Project 模板 | 更厚或另弧 |
| Formula children rollup | E40/E43 **永不**本路径 |

### Why this Epic now（一句话）

父子 Issue 早已可建可列，但 **父级看不到子项完成度**——排期/站会只能人工点进 children；E69 评论附件弧刚闭后轮换离开附件/表单/TZ/门户/假日/依赖，用中厚刀补上 **结构化 `childProgress` + 详情/列表/CLI**，正好对齐 Linear 父 Issue 进度叙事，且不碰 formula 跨 Issue rollup 禁区、不重开 Push/甘特。

---

## 1. 目标

成功标准：有子项的 Issue 在 **详情** 返回 `childProgress`；**列表** 可 `?include=childProgress` opt-in；进度含 `total` / `done` / `open` / `percent`（及可选 byStatus）；FE 父详情进度条+分数、列表可选徽章；CLI **1.54.0** `issue show` 展示；无子项时 `total=0`、`percent=null` 或 0（**Q3a**）；**不** Activity Push、**不**改 E57–E69 邻面、**不** formula emit、**不**甘特/门户/附件再开。

### A · 语义（BE）

- **Done 集（Q1a）**：`resolved` | `closed` | `rejected`（与 E39 `CLOSED_STATUSES` 对齐）  
- `open` = total − done（含 `open`/`in_progress`/`feedback`）  
- `percent` = round(done/total*100) if total>0 else **null**（Q3a）  
- **仅直接子**（Q2a）：不递归孙项（避免树爆；递归列为备选 Q2b）  
- 软删子项不计（`is_deleted`）

### B · API（BE）

- 详情 `GET /api/issues/{id}`：默认附  
  `childProgress: { total, done, open, percent, byStatus?: {…} }`  
- 列表 `GET /api/issues?include=childProgress`：**Q4a** opt-in 批量聚合（单查询 `parent_issue_id IN (…) GROUP BY`）；默认不加以免列表成本  
- `GET /api/issues/{id}/children` 不变；可选在响应根加同构 `childProgress`（薄）  
- **无** alembic

### C · FE

- 详情：子问题区上方进度条 + `done/total`；无子项不渲染条  
- 列表/看板：若 payload 有 progress，小徽章（如 `2/5`）；无 include 则不请求加重（详情页自带）  
- vitest：percent 边界（0 子、全 done、混合）；build ok；守 E63 `f`+`r`

### D · CLI **1.54.0**

- `issue show` 打印 `ChildProgress: 2/5 (40%)`（无子项省略或 `—`）  
- 可选 `issue list --include childProgress`（若 list 旗标已有 include 风格则对齐）  
- pins → **1.54.0**（**Q6a**）

### E · 安全 / 邻面 / no-emit

- 跨租户 404 不变；progress 仅聚合可见子项（同 WS）  
- **Q5a**：不新增 webhook；读路径不 fire  
- formula **no-emit**；**不**把 progress 做成 formula 字段  
- **不**改 E57–E69 主表面（评论附件 / Form enqueue / TZ / Initiative relations / 假日 / 门户 / Search / 附件 ACL 仅 pins）

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户再厚、Initiative 甘特、Recurrence Q2b、表单公开附件  
- 再开评论附件 / Form→Triage / TZ 语义 / 假日 / Search / Insights  
- 多指派人、Project 模板、公式跨 Issue/children rollup（E40/E43 禁）  
- 自动把父 status 设为子项聚合结果（可后置 automation）  
- Formula emit；远程 push / 开 PR / 自开 E71

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 详情默认 `childProgress`；done 集=resolved/closed/rejected；仅直接子 |
| B | 列表无 include 无字段；`?include=childProgress` 有且与详情一致 |
| C | 0 子 → total=0、percent=null；全 done → 100 |
| D | FE 进度条+分数；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.54.0** + show 展示 + pins |
| F | 无新 webhook；不改 E57–E69 邻面；formula no-emit |
| 门禁 | BE 定向（issues children + progress）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E71 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **子问题进度汇总 mid**（方案 A）；聚合 + FE/CLI；**无** Push / 甘特 / 门户 / 附件再开 |
| D2 | Done = resolved/closed/rejected；仅直接子；无 alembic |
| D3 | 详情默认带；列表 opt-in `include=childProgress` |
| D4 | 0 子 percent=null；不自动改父 status |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.54.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不做 formula children rollup；不改 E57–E69 邻面；不 push；不自开 E71 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | Done 集？ | **Q1a** resolved/closed/rejected（对齐 E39）；备选 Q1b 仅 closed（偏窄，resolved 不算完） |
| Q2 | 深度？ | **Q2a** 仅直接子；备选 Q2b 递归（需环防护/深度 cap，偏厚） |
| Q3 | 0 子 percent？ | **Q3a** `null`；备选 Q3b `0`（易被当成「零进度」误读） |
| Q4 | 列表策略？ | **Q4a** `?include=childProgress` opt-in；备选 Q4b 列表总带（多一次聚合） |
| Q5 | webhook？ | **Q5a** 不新增、读不 fire；备选 Q5b 子 status 变更发父 `issue.updated`（易噪，且非本 Epic 写路径） |
| Q6 | CLI？ | **Q6a** show 展示 + pins **1.54.0**；可选 list include；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. `compute_child_progress(children|ids)` helper + 单测（TDD）  
3. 详情默认嵌入 + 列表 include 聚合（TDD）  
4. FE 进度条/徽章 + vitest  
5. CLI 1.54.0  
6. no-emit / 邻面不动 / f+r spy + acceptance

---

## 7. 测试要点

- 父+5 子（2 resolved / 1 closed / 2 open）→ done=3、total=5、percent=60  
- 无子 → total=0、percent=null  
- 软删子不计  
- 列表无 include 无 key；有 include 与详情一致  
- 跨 WS 子不可见（同既有 children 隔离）  
- spy：无新 webhook；不触 E69 comment attach / E68 enqueue / E67 TZ / E66 ACL 主路径；formula no-emit  
- CLI 1.54.0 pins  
- FE vitest；build ok；elegant-router `f`+`r` 仍在

---

## 附录 · runners-up（供 E71+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — E31 非目标。  
6. **多指派人 mid** — 需结表；本轮为进度汇总让路。  
7. **递归孙项进度（Q2b）** — 有树深需求再开。

（备选扫描但本轮不推：再开评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.54.0**

# E61 Design：Insights 共享报表 mid — personal→WS 共享只读团队报表 · CLI 1.45.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E61  
基线拟：`sprint/E60-S1` @ `950256e`（全文 `950256e8a5266295903b71498111ef542c9a5d75`；E60 design 基线 `0fb0df5`；E59 tip `ccc5b4f` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E61-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E62**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e61-insights-shared-reports-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E61-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E60 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ Webhook 可观测（E54）→ Insights 效能加厚（E55）→ SLA policy 日历覆盖（E56）→ Webhook 死信告警（E57）→ 国家/地区假日包（E58）→ Insights 再厚/效能日报（E59：多 label OR +「我的报表」+ digest）→ **Search FTS mid（E60：方言全文 + description + CLI search）**。

E60 附录 runners-up（不绑定）：

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」；**默认不重开**  
2. **假日包扩容 thin**（再加 EU/UK 或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 已隔 E59+E60 两轮；可作附录  
3. **Insights 共享报表 thin-mid**（personal→shared / 只读团队报表；仍砍拖拽构建器）— E59 刚交 personal；**E60 明示「隔一轮再评估」→ 本轮正好** → **本草案收之**

代码实证 @ `950256e`：

| 面 | 现状 |
|----|------|
| Insights 报表 | E59 `insights_saved_reports`：**personal-only**（`owner_user_id` + 本人 CRUD）；cap 20/用户/WS；`is_default`≤1；list/create/patch/delete；**无** `visibility` / shared / 团队只读列表；digest 仍绑本人 default |
| Insights 聚合 | E24→E55→E59：summary/export + 多 label OR + cycleSnapshot；**无**共享报表应用路径差异 |
| Search | E60 刚闭：PostgresFTS / SQLiteFTS / ILike；Issue+description；CLI **1.44.0** `search`；本轮宜 **轮换离开** |
| SLA 日历 | E50→E53→E56→E58 弧已闭；再开包扩容非最高 ROI |
| Webhook | E44→E51→E54→E57 出站弧已闭 |
| Activity | E52 watching+反应+铃铛；**无** Push / 浏览器 Notification |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | E60 明示最高 ROI 让路项回到 **Insights 共享报表**（隔一轮）；要求轮换离开刚闭的 Search；Activity Push 非「明显最优」不默认；假日包扩容 / 评论全文 / 门户·App·依赖图 次之或过厚 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Insights 共享报表 mid**：在既有 `insights_saved_reports` 上加 **visibility**（`personal` \| `workspace`）；owner 可分享/取消；WS 成员 **list 可见 shared + 本人 personal**；非 owner **只读**（不可 patch/delete/改 filters；可 **另存为我的**）；digest **仍仅用本人 default**（不偷偷改成共享）；FE「团队报表」分区 + 分享开关；CLI **1.45.0**；**无**拖拽构建器 / **无** BI / **无** Slack Incoming / **无** Activity Push / **不**改 E60 Search / E57–E58 主表面 | **中厚且轮换离开 Search**；接 E60 #3 / E59 Q3b 让路项；复用既有表与 summary，单 sprint 可交付 |
| B | Activity 实时/Push（WS 扇出 / 浏览器 Notification / FCM） | 单列易溢；非「明显最优」；**默认不重开** |
| C | 假日包扩容 thin（EU/UK/2027） | 有价值但薄；日历弧非本轮最高 ROI；作 runners-up |
| D | 评论全文入索 thin-mid（IssueComment → SearchBackend） | 刚闭 Search 弧上再厚；与 prefer rotate OFF Search 冲突；作附录 |
| E | Customer 公开门户 / 真 GitHub App / Initiative 依赖图 / Formula emit | 过厚或排除；emit **永不** |
| F | 仅文档约定「把 filters JSON 贴到 Slack」无产品面 | **过薄** |

**建议拍板：A（Insights 共享报表 mid）。**  
Activity Push、假日包扩容、（可选）评论全文入索列入附录 runners-up。

自检：visibility/ACL、list 合同、只读边界、digest 不变、FE/CLI **1.45.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity 实时/Push | 单列易溢；非「明显最优」；任务明确要求勿默认 |
| 假日包扩容 EU/UK/2027 | 有价值但薄；非最高 ROI |
| 评论全文 / 再开 Search | 刚闭 E60；明确要求轮换离开 |
| Customer 门户 / GitHub App / Initiative 依赖图 | 过厚或排除 |
| 再开 webhook / Formula emit / 重做 E52–E60 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E59 把「我的报表」立起来了，但团队仍无法把常用切片挂成工作区只读报表——每人各自另存、digest 也只看自己的默认；E60 刚把 Search FTS 基建闭完后轮换回来，用中厚刀把 **personal→workspace 共享（只读）+ 另存为个人 + CLI** 补上，正好把效能面从「能自用」抬到「能对齐团队切片」，且不重开 Push、报表构建器或 Search 大战。

---

## 1. 目标

成功标准：Workspace 成员（viewer+，对齐 E24/E55/E59）可将本人 Insights 报表 **分享为 workspace 可见**（或取消分享）；任意成员可 **列出**「我的 personal + WS 内 shared」并 **应用 filters 打既有 summary/export**；非 owner 对 shared **只读**（不可改/删；可 **另存为我的** 副本）；digest **仍只消费本人 `isDefault` personal 报表**（shared 不自动进 digest）；FE `/insights` 分「我的 / 团队」；CLI **1.45.0**；跨租户隔离；**不**引入拖拽构建器、**不** Slack Incoming、**不** Activity Push、**不**改 E60 Search / E57 webhook 告警 / E58 假日包主表面、**不** formula emit。

### A · visibility 模型（BE）

- 扩展 `insights_saved_reports`：新增 `visibility`（建议 `String`：`personal` \| `workspace`；默认 **`personal`** — **Q1**）  
- alembic：列 + 回填既有行 → `personal`；可选部分索引 `(workspace_id, visibility)`  
- **不做** `team` / 指定成员 ACL / 链接令牌 / 公开匿名

### B · ACL 与 API（BE）

- `GET /api/insights/reports`：返回 **本人 personal ∪ 本 WS visibility=workspace**（**Q2a**）；每条带 `visibility`、`ownerUserId`、`canEdit`（仅 owner）  
- `POST /api/insights/reports`：默认 `personal`；可选创建即 `workspace`（需 **Q3a** member+ 写；viewer 仅 personal — 或 viewer 也可 share，见 Q3）  
- `PATCH /api/insights/reports/{id}`：  
  - owner：可改 name/filters/`isDefault`/`visibility`  
  - 非 owner：**403/404**（**Q4a** 建议 404 对齐既有非本人）  
- `DELETE`：仅 owner  
- 新便利（薄）：`POST /api/insights/reports/{id}/fork`（或 create 带 `fromReportId`）→ 复制 filters 为 **本人 personal**（**Q5a**）  
- 应用报表：仍 **Q4a from E59**——FE/CLI 读 filters 再打既有 summary/export；**不**强制专用 summary 端点  
- cap：personal 仍 **20/用户/WS**；shared 另计 **Q6a** 建议每 WS shared **≤50**（防炸）

### C · digest 边界（BE）

- `isDefault`：**仅 personal** 可标默认；若 share 时已是 default → **保留** default（仍属本人）或要求先取消 default 再？→ **Q6 相关：建议允许 shared+default 仅对 owner digest 生效，list 对他人不展示 isDefault 或展示但不影响他人**  
- `run-digest`：**不**改为消费他人 shared；逻辑保持 E59（每用户本人 default → 否则全 WS 切片）  
- **不**因分享向全员 Inbox 广播

### D · FE

- `/insights`：「我的报表」+「团队报表」分区（或同一下拉分组）  
- owner：分享 / 取消分享开关；编辑/删除  
- 非 owner：应用 / **另存为我的**；无编辑删除  
- vitest：list 合并、canEdit、fork filters round-trip  
- **不做**拖拽构建器、多看板、报表评论、@提及

### E · CLI **1.45.0**

- `insights reports list [--mine|--shared|--all] [--json]`  
- `insights reports create … [--visibility personal|workspace]`  
- `insights reports set-visibility <id> personal|workspace`（或 patch）  
- `insights reports fork <id> [--name]`  
- 保留既有 delete / summary `--label-ids` / run-digest  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.45.0**

### F · 安全 / 租户 / no-emit

- 读权限对齐 E24/E55/E59（viewer+）；写/分享对齐 Q3  
- 跨租户 404；shared 不得泄漏他 WS  
- **不**新增 outbound webhook 事件、**不**改 fire 路径  
- formula **no-emit**；读/分享路径 spy 不触发 `fire_webhooks` / automations（除既有 Inbox/邮件）  
- **不**改 E60 Search / E57 alerts / E58 holiday-packs 主表面（仅 CLI version pins）

## 2. 非目标

- 拖拽自定义报表构建器 / 任意维度透视 / BI 大屏  
- Slack Incoming / PagerDuty / 浏览器 Notification / Activity Push / FCM  
- 再开 Search（评论全文、附件 OCR、Meili/Elastic、vector）  
- 再开 SLA 日历（ICS、州包、冲突矩阵、EU/UK/2027 主表面）  
- 改 E57 webhook 告警 / E58 holiday-packs / E51 pack/HMAC / E60 SearchBackend  
- Formula 物化 emit（E40 D2/D7）  
- Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动  
- 报表级细粒度 ACL（指定人/角色）、公开链接、匿名访问  
- 内置 cron（digest 仍外部 tick）  
- 远程 push / 开 PR / 自开 E62

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 既有行默认 personal；visibility 列迁移绿 |
| B | owner 可 share/unshare；成员 list 见 shared；非 owner 不可 patch/delete；fork 得 personal 副本 |
| C | digest 仍按本人 default；分享不广播 Inbox；不改 E59 日账本语义 |
| D | FE 我的/团队分区 + 分享/另存为；vitest；build ok |
| E | CLI **1.45.0** + list 过滤 + set-visibility + fork + pins |
| F | 跨租户隔离；formula no-emit spy；不改 E57–E58 / E60 主表面 |
| 门禁 | BE 定向（E61+E59+E55 insights）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E62 |

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **Insights 共享报表 mid**（方案 A）；visibility personal\|workspace + 只读共享 + fork + CLI；**无** Push / Search 再开 / 报表构建器 / SLA 再开 |
| D2 | 复用既有 `insights_saved_reports` + summary/export；不新建第二套聚合引擎或报表表 |
| D3 | 共享 = **WS 级只读可见**；无指定人 ACL / 公开链 |
| D4 | 写/删/改 visibility = **仅 owner**；非 owner 可应用 filters + fork |
| D5 | digest **不**消费他人 shared；仍 E59 本人 default / 全 WS 回落 |
| D6 | CLI = **1.45.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E57/E58/E60 主表面；非目标见 §2；不 push；不自开 E62 |

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | visibility 存什么？ | **Q1a** 列 `visibility` ∈ {`personal`,`workspace`}，默认 `personal`；备选 Q1b 布尔 `is_shared`（难扩展） |
| Q2 | list 默认范围？ | **Q2a** 默认返回 mine∪shared（`--all` 语义）；备选 Q2b 默认仅 mine，shared 需显式 query |
| Q3 | 谁可以 share（visibility→workspace）？ | **Q3a** **member+** 可分享自己的报表；viewer 仅 personal（与 Insights 写边界对齐 E55）；备选 Q3b 任意 viewer+ 可分享（更松） |
| Q4 | 非 owner 访问写接口？ | **Q4a** **404**（对齐 E59 非本人）；备选 Q4b 403 |
| Q5 | 另存为形态？ | **Q5a** `POST …/reports/{id}/fork`（复制 filters → 本人 personal，name 默认「副本 · {name}`」）；备选 Q5b 仅文档化「手动 create」 |
| Q6 | shared 上限与 default？ | **Q6a** 每 WS shared **≤50**；`isDefault` 仅对 owner digest 有意义，他人 list 可省略或只读展示；分享不自动清 default。备选 Q6b shared 与 personal 合计硬顶 20（过紧） |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. alembic visibility + 回填 personal（TDD）  
3. BE list/ACL/share/unshare + cap（TDD）  
4. BE fork + digest 回归（TDD）  
5. FE 分区 + 分享/另存为  
6. CLI 1.45.0  
7. 门禁 + acceptance tip  

## 7. 测试要点

- 迁移：旧行 personal；默认创建 personal  
- owner share → 他成员 list 可见；unshare 后消失  
- 非 owner patch/delete → 404；fork → 新 personal 且 filters 一致  
- digest：分享他人 default 不影响；本人 default 仍生效；日账本幂等  
- spy：无 fire_webhooks；不触 E57 alert eval / E58 holiday apply / E60 reindex；formula no-emit  
- CLI 1.45.0 pins + list/set-visibility/fork  
- FE vitest 分组与 canEdit  

---

## 附录 · runners-up（供 E62+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」不重开。  
2. **假日包扩容 thin**（再加 EU/UK 或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 已隔两轮；可作下一薄刀。  
3. **评论全文入索 thin-mid**（`IssueComment.body` → E60 SearchBackend；仍无 Meili/Elastic）— 刚闭 Search；隔一轮后再评。

（备选扫描但本轮不推：Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动 — Roadmap 排除或过厚。Webhook 再厚 / PagerDuty — 出站弧已闭。Formula emit — 永不本轮。重做 E52–E60 表面 — 无增量，不推。）

## CLI 版本

**1.45.0**

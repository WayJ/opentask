# E63 Design：Customer Request 公开状态门户 mid · CLI 1.47.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E63  
基线拟：`sprint/E62-S1` @ `0a5706b`（全文 `0a5706b4c61b63f8115184e6cff4300527d0d0ae`；E62 design 基线 `6fdeba8`；E61 tip `9e8d281` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E63-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E64**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e63-customer-request-public-status-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E63-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E62 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ Webhook 可观测（E54）→ Insights 效能加厚（E55）→ SLA policy 日历覆盖（E56）→ Webhook 死信告警（E57）→ 国家/地区假日包（E58）→ Insights 再厚/效能日报（E59）→ Search FTS mid（E60）→ Insights 共享报表（E61）→ **评论全文入索 mid（E62：IssueComment → SearchBackend `comments` 组 · CLI 1.46.0）**。

E62 附录 runners-up（不绑定）：

1. **假日包扩容 thin**（EU/UK 与/或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 已隔 E59–E62 四轮；**薄**；非本轮 mid 首选  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 后再评估；单列易溢；非「明显最优」；**默认不重开**  
3. **Customer 门户薄边 / Initiative 依赖图薄刀** — Roadmap 常排除或过厚；**本草案把 #3 收成中厚「公开状态门户」**（非完整自助门户）

代码实证 @ `0a5706b`：

| 面 | 现状 |
|----|------|
| Customer | E22：`customers` + `customer_requests` + Request↔Issue M2M；内部 CRUD；**无** `status_token`、**无**公开读、**无**客户侧回复 |
| Forms | E31：`/api/public/forms/{token}` 可匿名建 Issue（可选挂 CustomerRequest）；提交成功即断；**客户无法回头看进度** |
| Search | E60→E62 弧刚闭（Issue/Project/Doc/Member + Comment FTS）；本轮宜 **轮换离开** |
| Insights | E55→E59→E61 刚闭；宜轮换离开 |
| SLA 日历 | E50→E53→E56→E58 已闭；假日包扩容有价值但 **薄** |
| Webhook | E44→E51→E54→E57 出站弧已闭 |
| Activity | E52 watching+反应+铃铛；**无** Push / 浏览器 Notification |
| Initiative | E10 CRUD+健康；**无**依赖图 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | E62 明示轮换离开 Search；假日包扩容薄、Activity Push 非明显最优不默认；**Customer 公开状态**接 E22「不做公开门户」缺口 + E31 公开表单「提交后失联」，中厚刀可单 sprint 交付；完整自助门户 / GitHub App / Initiative 依赖图仍过厚 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Customer Request 公开状态门户 mid**：Request 增 `status_token`（可空→启用时生成）；成员可 enable/rotate/revoke；公开 `GET /api/public/customer-requests/{token}` 返回 **脱敏**状态卡（title/status/updatedAt/可选 linked issue codes 计数或 code 列表）；可选 `POST …/replies` 把客户留言落为 **内部 IssueComment**（挂首个 linked Issue，无 Issue 则落 Request 备注/专用公开回复表）；FE `/r/:token` blank layout + 详情「复制公开链接」；CLI **1.47.0**；对齐 E31 token/rate-limit 模式；**无**客户账号、**无**完整门户导航、**无**附件、**无** Activity Push、**不**改 E60–E62 Search / E57–E58 / E61 主表面 | **中厚且轮换离开 Search/Insights**；接 E62 #3；复用 E31 公开契约；单 sprint 可交付 |
| B | 假日包扩容 thin（EU/UK/2027） | 有价值但薄；与 prefer mid-thick 冲突；作 runners-up |
| C | Activity 实时/Push（WS 扇出 / 浏览器 Notification / FCM） | 单列易溢；非「明显最优」；**默认不重开** |
| D | 再开 Search（snippet 高亮 / Doc 分面 / Meili） | **刚闭 E60→E62**；与 prefer rotate OFF Search 冲突 |
| E | Initiative 依赖图 mid / 真 GitHub App / 完整 Customer 自助门户 / Formula emit | 过厚或排除；emit **永不** |
| F | 仅在 Form 提交成功页展示「请联系客服查进度」文案 | **过薄**；无持久查询面 |

**建议拍板：A（Customer Request 公开状态门户 mid）。**  
假日包扩容、Activity Push、Initiative 依赖图薄刀列入附录 runners-up。

自检：token 生命周期、脱敏契约、可选回复落点、rate-limit、FE/CLI **1.47.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| 假日包扩容 EU/UK/2027 | 有价值但薄；E58–E62 多次评为非最高 ROI |
| Activity 实时/Push | 单列易溢；非「明显最优」；任务明确要求勿默认 |
| 再开 Search / Insights | E60→E62 / E59→E61 刚闭；明确要求轮换离开 |
| Initiative 依赖图 / 真 GitHub App / 完整门户 | 过厚或排除 |
| 再开 webhook / Formula emit / 重做 E52–E62 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E31 让客户能 **匿名提交**，E22 让团队能在内部管 Request——但提交后客户 **看不见进度**；E60→E62 Search 弧刚闭后轮换离开，用中厚刀给 CustomerRequest 补上 **魔法链接状态页（+可选回复）**，正好把「能收单」抬到「能对外对齐状态」，且不重开完整门户、Push、假日包大战或 Search。

---

## 1. 目标

成功标准：Workspace **writer+**（owner/member，对齐 E22/E31）可对某 CustomerRequest **启用/轮换/撤销**公开 `status_token`；持 token 的匿名访客可 `GET` **脱敏状态卡**（至少 title、status、updatedAt；可选 linked issue 摘要）；可选开启时访客可 `POST` 一条回复并落入团队可见面；FE 公开页 `/r/:token` + 详情「复制公开链接」；CLI **1.47.0**；跨租户不泄漏；rate-limit；**不**引入客户账号体系、**不** Activity Push、**不**改 E60–E62 Search / E57 webhook 告警 / E58 假日包 / E61 Insights 主表面、**不** formula emit。

### A · 模型 + token 生命周期（BE）

- `customer_requests` 增列：`status_token`（String，nullable，unique partial/全局 unique where not null）、`status_token_enabled`（bool，默认 false）、可选 `public_replies_enabled`（bool，默认 false）  
- alembic 新修订（建议 `v8e9f0a1b2c6` 一类）  
- `POST /api/customer-requests/{id}/status-link/enable` → 生成 `secrets.token_urlsafe(24)`（对齐 E31）  
- `POST …/status-link/rotate` → 换新 token（旧立刻失效）  
- `POST …/status-link/revoke` → 清空 token + enabled=false  
- 权限：写 = owner/member；读管理面 = viewer+（可见「已启用」与复制 URL，**不**在 list 默认泄露 token 明文——详情/专用字段返回）

### B · 公开 API（BE）

- `GET /api/public/customer-requests/{token}` → 200 脱敏卡；未知/已撤销 → **404**（不区分）  
- 脱敏卡建议形状：  
  `{ title, status, priority?, updatedAt, customerName?, linkedIssueCount, linkedIssueCodes?, publicRepliesEnabled, recentPublicReplies? }`  
  **不**返回 workspaceId、内部 member 邮箱、Issue description、内部评论全文  
- 可选：`POST /api/public/customer-requests/{token}/replies` body `{ body: string }`  
  - 若 `public_replies_enabled=false` → 403/404（建议 **404** 对齐禁用形态）  
  - 落点 **Q3a**：优先挂 **首个 linked Issue** 为 `IssueComment`（`comment_type=COMMENT`，作者 = request.created_by 或 WS 系统占位策略见 Q3）；无 linked Issue 时写入 `customer_request_public_replies` 小表（id/request_id/body/created_at）供内部详情只读展示  
- rate-limit：对齐 E31（默认 30/60s/token；`OPENTASK_PUBLIC_REQUEST_RATE_LIMIT=0` 关）

### C · 内部表面（BE）

- Request 详情响应增 `statusLink: { enabled, url?, publicRepliesEnabled }`（token 仅 enable/rotate 响应或显式 `include_token=1` 时给出，避免 list 泄露）  
- Inbox：**本轮默认不广播**公开回复（Q5a）；可选后置 `customer_request_public_reply` 通知类型  
- **不**改 E31 form submit 契约（成功页可薄链「若团队已分享状态链接可查询」——非必须）

### D · FE

- 公开页 `/r/:token`（blank layout，对齐 `/f/:token`）：展示状态 + 可选回复框  
- Request 详情：开关「公开状态链接」+ 复制 + 轮换/撤销 + 「允许公开回复」  
- vitest：脱敏字段 / 缺 token 态；build ok

### E · CLI **1.47.0**

- `opentask request status-link enable|rotate|revoke|show <id>`  
- `opentask request public-status <token> [--json]`（打公开 GET，便于代理探测）  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.47.0**

### F · 安全 / 租户 / no-emit

- token 猜测空间对齐 E31；禁用/撤销一律 404  
- 公开路径 **不**触发 formula emit；spy：不 `fire_webhooks`（或仅当落 IssueComment 时走既有 comment webhook——**Q4a 默认：公开回复落评论时允许既有 comment 出站，不新增事件名**）  
- **不**改 E60–E62 SearchBackend / E57 alerts / E58 holiday-packs / E61 Insights 主表面（仅 CLI version pins）

---

## 2. 非目标

- 客户账号 / SSO / 魔法邮箱登录 / 多 Request 门户导航  
- 完整 Customer 自助门户（列表/筛选/附件上传/品牌域名）  
- Activity Push / 浏览器 Notification / FCM  
- 假日包 EU/UK/2027、ICS、州包、外网拉取  
- Search / Insights 再厚；Meili/Elastic  
- 真 GitHub App、Initiative 依赖图、原生移动  
- Formula 物化 emit（E40 D2/D7）  
- 远程 push / 开 PR / 自开 E64

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | enable/rotate/revoke 正确；旧 token 立刻 404；跨租户 404 |
| B | 公开 GET 脱敏；无 token/已撤销 404；rate-limit 可测 |
| C | 可选公开回复：开启时可写；关闭 404；落点按 Q3a；内部可见 |
| D | FE `/r/:token` + 详情链接管理；vitest+build |
| E | CLI **1.47.0** + status-link / public-status + pins |
| F | 不改 E57–E58 / E60–E62 / E61 主表面；formula no-emit spy；公开路径无新 webhook 事件名（Q4a） |
| 门禁 | BE 定向（E63+E22/E31 相关）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E64 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Customer Request 公开状态门户 mid**（方案 A）；status_token + 公开状态卡 + 可选回复 + CLI；**无** Push / 完整门户 / Search 再开 / 假日包扩容 |
| D2 | 公开契约对齐 E31：`/api/public/.../{token}`；未知/禁用一律 404 |
| D3 | 脱敏优先：公开响应不含 workspaceId、成员 PII、Issue 正文、内部评论 |
| D4 | 回复落点默认挂首个 linked Issue 评论；无 Issue 时用专用 public_replies 表 |
| D5 | rate-limit 进程内存，对齐 E31 默认阈值 |
| D6 | CLI = **1.47.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E57/E58/E60–E62/E61 主表面；非目标见 §2；不 push；不自开 E64 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 公开卡是否暴露 linked issue codes？ | **Q1a** 暴露 `linkedIssueCodes: string[]`（仅 code，无 title/desc）；备选 Q1b 仅 `linkedIssueCount`（更保守、客户难引用） |
| Q2 | token 默认何时生成？ | **Q2a** 显式 enable 才生成（默认关）；备选 Q2b 创建 Request 自动生成（易误享） |
| Q3 | 公开回复作者与落点？ | **Q3a** 落首个 linked Issue 为 COMMENT；`created_by` = request.created_by（团队身份代理）；无 Issue → `customer_request_public_replies` 表；备选 Q3b 一律只写 public_replies 表（不进 Issue 时间线） |
| Q4 | 公开回复是否 fire 既有 webhooks？ | **Q4a** 若落 IssueComment，走既有 comment 出站（不新增事件名）；纯 public_replies 行 **不** fire；备选 Q4b 全部静默（可能丢集成） |
| Q5 | 公开回复是否写 Inbox？ | **Q5a** 本轮不写 Inbox（降噪）；备选 Q5b 给 request.created_by / watchers 写 `customer_request_public_reply` |
| Q6 | CLI 表面？ | **Q6a** `request status-link enable\|rotate\|revoke\|show` + `request public-status <token>`；备选 Q6b 仅 show URL（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic token 列 + public_replies 表（TDD）  
3. enable/rotate/revoke + 权限/跨租户（TDD）  
4. 公开 GET 脱敏 + rate-limit + 404 形态（TDD）  
5. 公开 replies + 落点 Q3a（TDD）  
6. FE `/r/:token` + 详情开关（vitest）  
7. CLI 1.47.0  
8. no-emit / webhook 边界 spy + acceptance

---

## 7. 测试要点

- enable → GET 200；revoke/rotate 旧 token 404  
- 脱敏：无 workspaceId / 无成员 email / 无 Issue description  
- 跨 WS：他租户 id 不能 enable；公开 token 不泄露他租户  
- public_replies_enabled 开关；关闭时 POST 404  
- 有/无 linked Issue 两种落点  
- rate-limit 触发 429（或项目既有形态）  
- spy：formula no-emit；不触 E57 alert eval / E58 holiday apply / E61 share / E62 reindex  
- CLI 1.47.0 pins + status-link/public-status  
- FE vitest；build ok

---

## 附录 · runners-up（供 E64+；若 Yuri 改选可替换本草案）

1. **假日包扩容 thin→可升 mid**（EU/UK + CN/US 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 已隔四轮；薄刀随时可插；若改选可升为多区多年 mid。  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 后再评估；单列易溢；非「明显最优」不重开。  
3. **Initiative 依赖图 mid**（Initiative↔Initiative blocks/blocked_by + FE 轻量关系条；仍砍甘特精修）— E10 后置项；仅当战略规划入口升高再开。

（备选扫描但本轮不推：再开 Search snippet 高亮 / Meili — 刚闭 E62。再开 Insights BI / Slack Incoming — 刚闭 E61。Webhook / PagerDuty — 出站弧已闭。Formula emit — 永不本轮。真 GitHub App / 完整客户自助门户 — 过厚。重做 E52–E62 表面 — 无增量，不推。）

## CLI 版本

**1.47.0**

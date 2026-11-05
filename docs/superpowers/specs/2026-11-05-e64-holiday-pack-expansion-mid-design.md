# E64 Design：假日包扩容 mid — EU/UK + 2027 年卷 · CLI 1.48.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E64  
基线拟：`sprint/E63-S1` @ `0a53ef7`（全文 `0a53ef76eac785f750b2760bad36137ad2f546d4`；E63 design 基线 `ea2119c`；E62 tip `0a5706b` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E64-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E65**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e64-holiday-pack-expansion-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E64-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E63 连续闭合 … → Search FTS（E60）→ Insights 共享报表（E61）→ 评论全文入索（E62）→ **Customer Request 公开状态门户 mid（E63：status_token + `/r/:token` + 可选公开回复 · CLI 1.47.0）**。

E63 附录 runners-up（不绑定）：

1. **假日包扩容 thin→可升 mid**（EU/UK + CN/US 2027；仍砍 ICS / 州包 / 外网拉取）— E58 已隔 E59–E63 **五轮**；loader 已按 region/year 发现；**本草案升 mid 收之**  
2. **Activity 实时/推送加厚**（WS 扇出 / 浏览器 Notification / FCM）— 单列易溢；非「明显最优」；**默认不重开**  
3. **Initiative 依赖图 mid**（Initiative↔Initiative blocks/blocked_by + FE 轻量关系条）— E10 后置；战略入口未升高则次之

代码实证 @ `0a53ef7`：

| 面 | 现状 |
|----|------|
| 假日包 | E58：静态 `data/holiday_packs/{REGION}/{year}.json`；**仅 CN/2026 + US/2026**；`list/show/preview/apply`；pack wins；`applied_holiday_packs`；FE 折叠；CLI holiday-packs；**无** EU/UK、**无** 任何 2027 卷、**无** 批量多年 apply |
| SLA 日历 | E50 周窗 + E53 WS exceptions + E56 policy.calendar + E58 apply；扩容 = 数据+发现面，不重开日历引擎 |
| Customer 公开 | E63 刚闭（status-link / `/r/:token`）；本轮宜 **轮换离开** |
| Search / Insights | E60–E62 / E59–E61 刚闭；宜轮换离开 |
| Activity | E52 铃铛；**无** Push / Notification / FCM |
| Initiative | E10：`initiatives` + `initiative_projects`；**无** Initiative↔Initiative 依赖边 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | 要求轮换离开刚闭 Customer 门户 / Search / Insights；Activity Push 勿默认；假日包扩容是 E63 #1 且可升 mid（多区多年同交付）；Initiative 依赖图仍偏规划厚刀 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **假日包扩容 mid**：仓内新增 **EU + UK 2026** 精选包 + **CN/US/EU/UK 2027** 年卷；复用 E58 `list/show/preview/apply`（pack wins、null 物化、重算 cap 500）；FE 假日包列表自然多出新区/年；CLI **1.48.0**（list 可按 `--region/--year` 筛；可选 `apply` 保持单包，另见 Q3 批量）；**无** ICS、**无** 州/省包、**无** 外网拉取、**无** 冲突矩阵 UI、**不**改 E63 公开门户 / E60–E62 Search / E61 Insights / E57 告警主表面 | **中厚**：多区多年数据 + 筛/发现契约 + 回归；接 E63 #1；单 sprint 可交付 |
| B | Activity Push（WS / Notification / FCM） | 单列易溢；非明显最优；**默认不重开** |
| C | Initiative 依赖图 mid | 有价值但规划面更大；E10 后置未升温；作 runners-up |
| D | 再开 Customer 门户（多 Request 列表 / 附件 / 品牌域） | **刚闭 E63**；与 rotate OFF 冲突；过厚 |
| E | 再开 Search / Insights / Webhook / Formula emit | 刚闭或永不；不推 |
| F | 仅贴 EU 2026 一个 JSON、无测/无 CLI | **过薄**；与 prefer mid-thick 冲突 |

**建议拍板：A（假日包扩容 mid）。**  
Activity Push、Initiative 依赖图、（可选）下一刀门户加厚列入附录 runners-up。

自检：静态包版权/来源注记、发现面回归、apply 幂等、重算 cap、FE/CLI **1.48.0**、非目标与 no-emit 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 单列易溢；非「明显最优」；任务明确勿默认 |
| Initiative 依赖图 | 战略入口未升高；关系模型+FE 图易溢 sprint |
| 再开 Customer / Search / Insights | 刚闭 E63 / E60–E62 / E61；明确轮换离开 |
| 真 GitHub App / 完整门户 / Formula emit | 过厚或永不 |

### Why this Epic now（一句话）

E58 把「一键合并精选假日」立起来了，但仓内 **只有 CN/US 2026**——EU/UK 团队与跨年滚动仍靠手工例外；E63 刚把 Customer 公开状态闭完后轮换离开，用中厚刀把 **EU/UK + 2027 年卷**一次性补齐（仍砍 ICS/州包/外网），正好把日历包从「示范两国」抬到「可跨国跨年选用」，且不重开 Push、依赖图或门户大战。

---

## 1. 目标

成功标准：Workspace 成员可在既有 E58 API/FE/CLI 上 **发现并 preview/apply** 新增静态包——至少 **EU/2026、UK/2026、CN/2027、US/2027、EU/2027、UK/2027**；既有 CN/US 2026 回归不变；apply 仍 pack wins、写入 WS 或 policy.calendar.exceptions、记 `applied_holiday_packs`、重算 cap 500；CLI **1.48.0**；**不**引入 ICS/外网/州包；**不**改 E63 公开门户 / E57–E62 邻面主表面；**不** formula emit。

### A · 静态包数据（BE）

- 新增文件（建议路径沿用 E58）：  
  - `data/holiday_packs/EU/2026.json`、`UK/2026.json`  
  - `data/holiday_packs/CN/2027.json`、`US/2027.json`、`EU/2027.json`、`UK/2027.json`  
- 每包含 `region/year/name/sourceNote/holidays[{date,kind,label?}]`；CN 可含 `forced_open` 调休；EU/UK 默认 `closed` 为主  
- `sourceNote` 必须可追溯（官方公告/议会日历摘要级，**非**实时 API）  
- loader `list_packs` 自动发现新区/年（已按目录扫描——回归测须覆盖 6+ 新包）

### B · API（BE）

- 复用：`GET /holiday-packs`、`GET /holiday-packs/{region}/{year}`、`POST …/preview`、`POST …/apply`  
- **加法（建议）**：list 支持可选 query `region`、`year`（Q2a）——便于 FE/CLI 过滤；不影响无参全量 list  
- apply 目标仍 Q1a：默认 WS `business_hours.exceptions`；可选 `target=policy` + `policyId`（对齐 E58 既有）  
- 冲突：pack wins（E58）；超 `MAX_EXCEPTIONS` → 400  
- 重算：既有 cap 500；不新开后台队列产品面

### C · FE

- 假日包折叠：列表展示新区/年；preview diff；apply 确认  
- 可选：region/year 筛（若 B 落地）  
- vitest：list 含 EU/UK/2027 键；build ok

### D · CLI **1.48.0**

- 既有 `sla holiday-packs list|show|preview|apply` 钉版  
- list 增 `--region` / `--year`（与 B 对齐）  
- pins：pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION` → **1.48.0**

### E · 安全 / 租户 / no-emit

- apply 权限对齐 E58（writer+）  
- 跨租户：policy/WS 目标必须本 WS  
- **不**新增 webhook 事件；spy：apply 路径不无公式 emit；不触 E63 status-link / E57 alert eval / E61 share / E62 reindex  
- **不**改 E63 公开门户主表面（仅 CLI version pins）

---

## 2. 非目标

- ICS 订阅 / 外网拉取 holiday API / 自动年度 cron 产品化  
- 州/省/邦包（US-CA、DE-BY 等）  
- 冲突矩阵可视化 / 三方 merge UI  
- Activity Push / Notification / FCM  
- Customer 门户再厚 / Search / Insights 再开  
- Initiative 依赖图、真 GitHub App、原生移动  
- Formula emit  
- 远程 push / 开 PR / 自开 E65

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 新包 6 份可 load；`list` 含 EU/UK 2026 + 四区 2027；CN/US 2026 回归 |
| B | preview/apply WS 与（若有）policy 目标；pack wins；applied_holiday_packs 记账 |
| C | 非法 region/year → 404；超 cap → 400；跨租户 404 |
| D | FE 可见新区/年 + preview/apply；vitest+build |
| E | CLI **1.48.0** + list 过滤 + pins |
| F | 无 ICS/外网；不改 E57–E63 邻面主表面；formula no-emit spy |
| 门禁 | BE 定向（E64+E58）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E65 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **假日包扩容 mid**（方案 A）；EU/UK 2026 + CN/US/EU/UK 2027 + 发现/过滤；**无** Push / ICS / 州包 / 门户再开 |
| D2 | 复用 E58 loader + preview/apply；不新引擎 |
| D3 | 静态仓内 JSON only；`sourceNote` 必填可追溯 |
| D4 | 冲突策略保持 **pack wins**；重算 cap 500 |
| D5 | list 可选 `region`/`year` 过滤（加法） |
| D6 | CLI = **1.48.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E57–E63 邻面主表面；不 push；不自开 E65 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | EU 包粒度？ | **Q1a** 单一 `EU` 超集（欧盟机构常见公共假日并集/精选，注明非各国劳动法全集）；备选 Q1b 拆 DE/FR（面更大，本轮易溢） |
| Q2 | list 过滤？ | **Q2a** 可选 `region` + `year` query/CLI flags；备选 Q2b 仅全量 list（FE 客户端滤） |
| Q3 | 是否批量 apply 多年？ | **Q3a** 本轮仍 **单 region+year apply**（对齐 E58）；备选 Q3b `apply-batch`（易超 exceptions cap，推后） |
| Q4 | 2027 CN 调休？ | **Q4a** 若官方安排已公布则写入 `forced_open`；未公布则仅写已知 `closed` 并在 sourceNote 标明「调休待补」；备选 Q4b 无官方则整包不做 2027 CN（留下洞） |
| Q5 | UK 是否含苏格兰等地区假？ | **Q5a** 仅 England & Wales 公共假日精选；备选 Q5b 强行并集四国（噪） |
| Q6 | CLI 输出？ | **Q6a** list 支持 `--region/--year`；show/preview/apply 契约不变；`--json` 全透传；备选 Q6b 仅 bump version（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. 编写 6 份静态 JSON + unit loader 发现测（TDD）  
3. list 过滤 API + 回归 E58 apply（TDD）  
4. FE 列表/筛 + vitest  
5. CLI 1.48.0  
6. no-emit spy + acceptance

---

## 7. 测试要点

- `list_packs` 含 EU/UK/2026 与四区 2027；旧 CN/US 2026 仍在  
- `load_pack` 校验 region/year 匹配；缺包 404  
- preview/apply pack wins；applied_holiday_packs 增行  
- list `region=EU&year=2027` 过滤  
- 跨租户 / 权限负例回归 E58  
- spy：无新 webhook 事件名；不触 E63/E57/E61/E62；formula no-emit  
- CLI 1.48.0 pins + flags  
- FE vitest；build ok

---

## 附录 · runners-up（供 E65+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 后再评估；单列易溢；非「明显最优」不重开。  
2. **Initiative 依赖图 mid**（Initiative↔Initiative blocks/blocked_by + FE 轻量关系条；仍砍甘特精修）— E10 后置；战略入口升高再开。  
3. **Customer 门户再厚 thin-mid**（公开页展示 recent public replies 线程 / Form 成功页深链 status URL）— E63 刚交；隔一轮后再评。

（备选扫描但本轮不推：再开 Search / Insights — 刚闭。Webhook / PagerDuty — 出站弧已闭。真 GitHub App / ICS 订阅 / 州包 — 过厚或非目标。Formula emit — 永不。重做 E52–E63 表面 — 无增量，不推。）

## CLI 版本

**1.48.0**

# E53 Design：SLA 节假日/例外日 thin — 例外日历跳过营业分钟 · CLI 1.37.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E53  
基线拟：`sprint/E52-S1` @ `a73f89a`（全文 `a73f89a02875b4566557af76a101030f49ffb940`；feature tip `53ee5f6`；design 基线 `abb96db`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E53-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E54**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e53-sla-holidays-exceptions-thin-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E53-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E52 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 thin → Formula query surfaces v2 → WS Activity Feed v1（E47）→ SLA first-response + pause timeline → Formula Display v2 → **SLA business hours thin（E50）** → 专用 webhook pack + 订阅过滤 FE（E51）→ **Activity Feed 加厚 v2（E52：watching + 行内反应 + 薄铃铛）**。

E52 附录 runners-up（不绑定）：

1. **SLA 节假日/例外日 thin**（仍砍优先级矩阵）— E50 交营业时后已隔 **E51+E52 两轮**；日历面可开  
2. **Webhook 投递可观测加厚**（按钩子成功率仪表 / 死信箱 UI）— 偏运维小刀；单列偏薄  
3. **Activity 实时/推送加厚**（WS 扇出 / 浏览器 Notification）— E52 刚交薄铃铛，刻意再隔  

代码实证 @ `a73f89a`：

| 面 | 现状 |
|----|------|
| SLA business hours | E50：`workspaces.timezone` + `business_hours` JSON（enabled + 每日最多 2 段）；`add_business_minutes` / `elapsed_business_minutes` **只看 weekday windows**；**无**例外日/节假日集合 |
| SLA clock | create/pause/resume/recompute 已走营业分钟加法器；配置变更批量重算 running/paused（cap 500） |
| FE | `settings/sla` + `businessHours.ts` 薄周历；**无**例外日列表编辑 |
| CLI | **1.36.0**；`sla business-hours show\|set`；**无** holidays/exceptions 子命令；下一刀 **1.37.0** |
| Webhook | E51 pack + 投递日志按事件过滤；有 `WebhookDeliveryLog`（success/pending_retry/dead）但 **无** 成功率仪表 / 死信箱专页 |
| Activity | E52 watching + reactions + `activity_read_cursors` 铃铛齐；**无** Push / 实时 WS（设计非目标） |
| Formula | E49 Display 齐；E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | Initiatives/Docs、Estimates、Relations、Customer、Insights、Git-PR 等厚 Linear 面近期已交；当前最高 ROI 缺口落在 **SLA 日历闭合**（E50 明确砍掉的例外日） |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **SLA 节假日/例外日 thin**：WS 级例外日集合（关闭日 ± 可选强制营业日）；`add_business_minutes` / elapsed **跳过 closed 日、强制 open 日覆盖周窗**；FE 薄例外列表；配置变更重算；CLI **1.37.0**；**无**国家日历包自动导入 / policy 优先级矩阵 | **中厚且连贯**；闭合 E50→E53 SLA 日历弧；对齐支持台「法定假/调休」；单 sprint 可交付 |
| B | Webhook 投递可观测加厚（成功率仪表 / 死信箱 UI / 按钩子聚合） | 有价值但偏运维小刀；E51 刚交 pack，单列撑不起整 Epic 厚度；可附录或与薄刀并捆 |
| C | Activity 实时/Push 加厚（浏览器 Notification / FCM / WS 扇出） | E52 刚交薄铃铛；单 sprint 易溢；默认再隔 |
| D | 完整国家日历包 + policy 级覆盖 + 优先级矩阵 | **单 sprint 必溢**；与 thin 冲突 |
| E | Formula emit / 重做 E51–E52 表面 | 打破 E40 D7 / 无增量；**永不本轮** |

**拍板：A（SLA 节假日/例外日 thin）。**  
Webhook 可观测、Activity Push 列入附录供 E54+ / runners-up。

自检：例外日语义、与 E50 周窗加法器并存、存储/迁移、配置重算、FE/CLI **1.37.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Webhook 投递可观测加厚 | 偏薄运维；E51 宜再沉淀；可作 E54 或与小刀并捆 |
| Activity 实时/Push | E52 刚厚；Push/WS 必溢；铃铛已够下一产品切片 |
| 完整国家日历包 / policy 矩阵 | 运维+测试爆炸；本轮刻意 thin |
| Formula emit / 重做 E51 webhook pack / 重做 E52 Activity | 无增量或破 D7；永不本轮 |
| Initiatives/Docs / Estimates / Relations 等 | Roadmap 近期已闭合；非当前最高缺口 |

### Why this Epic now（一句话）

E50 只交付「周内营业窗」；真实支持台 SLA 仍会在国庆/调休日错算 deadline。隔开 E51（webhook）+ E52（Activity）两轮后，把 **例外日（关闭/强制营业）** 接进既有营业分钟加法器，正好闭合日历弧，且不重开 Push 或 webhook 仪表大战。

---

## 1. 目标

成功标准：工作区可维护 **例外日** 列表（本地日历日）：**closed** 日全日不计营业分钟；可选 **forced_open** 日即使周窗为空也按指定窗口（或默认工作日窗）计营业分钟；`add_business_minutes` / `elapsed_business_minutes` / pause-resume / 配置变更重算 **共用**同一例外语义；跨租户隔离；FE 薄例外列表（增删改）；CLI **1.37.0**；**不**引入国家日历包自动导入 / policy 优先级矩阵 / Activity Push / webhook 仪表盘 / formula emit / 进程内 cron。

### A · 例外日模型（BE）

- 例外记录：`{ date: YYYY-MM-DD（WS timezone 本地日）, kind: closed|forced_open, windows?: 0..2 段 HH:MM 半开 }`（**Q1**）  
  - `closed`：该本地日 **无视** 周窗，全日非营业  
  - `forced_open`：该本地日 **覆盖** 周窗；若未给 `windows` 则用「一键工作日默认」或当天原周窗（**Q2**）  
- 落点：**Workspace 级**（对齐 E50 Q1a；**Q3a**）；本轮 **不允许** SlaPolicy 覆盖（**Q4a**）  
- 加法器：`add_business_minutes` / `elapsed_business_minutes` 增加 `exceptions` 参数（或从 WS 读）；扫描日时先查例外再查周窗  
- pause/resume / first_response / time_in_status **共用**  
- 配置变更后：沿用 E50 批量重算 running/paused `deadline_at`（cap 500）  
- enabled=false（营业时总开关关）时：例外日 **不生效**，回退墙钟（与 E50 一致）

### B · 存储 / migration（**Q5**）

- 建议：**Q5a** `workspaces.business_hours` JSON 扩 `exceptions: [{date, kind, windows?}]`（无新表；与 E50 同列；上限如 366 条/年防炸）  
  - 备选 **Q5b** 独立表 `workspace_business_exceptions`（清晰查询；多 1 migration）  
- 非法日期 / 重复 date / 未知 kind → 400；跨年允许  
- **禁止**国家日历包实体；**禁止**优先级矩阵列

### C · FE

- 在既有 SLA / business-hours 设置旁：例外日列表（日期 + kind + 可选窗口）+ 增删；空态文案  
- 可选：「从下周窗预览下月日历」只读提示（非必须）  
- vitest：例外归一化 / closed 日跳过样例  
- **不做**完整月历拖拽大战、ICS 导入 UI

### D · CLI **1.37.0**

- `sla business-hours` 下增 `exceptions list|add|remove`（或 `sla holidays ...` 别名，**Q6**）  
- `show` JSON 含 `exceptions`  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.37.0**

### E · 安全 / 租户 / no-emit

- 读写按 WS admin（对齐 E50 SLA settings）  
- 跨租户 404；日期/kind 白名单  
- 配置写路径 **不** 额外 fire webhook/automation（breach 既有路径不变）  
- formula **no-emit** spy  
- 无 Redis / 进程内 cron；不扩 E51 webhook 事件包；不改 E52 Activity 表面

## 2. 非目标

- 国家/地区日历包自动导入（中国法定假一键同步等）  
- SLA policy 级例外覆盖 / 优先级矩阵 / 多日历冲突 UI  
- ICS/Outlook 订阅同步  
- Activity Push / FCM / 实时 WS / 浏览器 Notification  
- Webhook 成功率仪表 / 死信箱专页 / 历史回放  
- Formula 物化 emit（E40 D2/D7）  
- 重做 E51 事件包 / 重做 E52 watching·反应·铃铛  
- 远程 push / 开 PR / 自开 E54

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 可 CRUD 合法例外日；非法 date/kind/重复被拒 |
| B | `closed` 日：跨该日的 `deadline_at` 跳过全日；单测钉死样例（含跨周末+节假） |
| C | `forced_open` 日：即使周窗该 weekday 为空，仍按例外窗口计分钟 |
| D | `businessHours.enabled=false` 时例外不生效（墙钟回退） |
| E | pause/resume / first_response 共用例外语义；配置变更批量重算；跨租户隔离 |
| F | 配置写无额外 webhook/automation；formula no-emit spy |
| G | FE 薄例外列表 + vitest；build ok |
| H | CLI **1.37.0** + exceptions 子命令 + version 断言 |
| 门禁 | BE 定向（E53+E50+E48/E45 SLA）+ 全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E54 |

## 4. ADR（Yuri 已确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **SLA 节假日/例外日 thin**（方案 A）；**无**国家包自动导入 / policy 矩阵 / Push / webhook 仪表 |
| D2 | 例外语义挂在既有营业分钟加法器；`run_due` 仍比 UTC `deadline_at` |
| D3 | Workspace 级；本轮无 policy 覆盖 |
| D4 | `closed` 全日非营业；`forced_open` 覆盖周窗 |
| D5 | 存储见 Q5（默认扩 `business_hours.exceptions` JSON）；配置变更批量重算 |
| D6 | CLI = **1.37.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不扩 E51 pack；不改 E52 Activity 主表面；非目标见 §2；不 push；不自开 E54 |

## 5. 开放问题（已全部按建议关闭）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | 例外 kind 是否只要 `closed`，还是要 `forced_open`（调休）？ | **Q1a 两者都要**（支持台调休刚需；仍 thin） |
| Q2 | `forced_open` 未给 windows 时用什么？ | **Q2a 复用「工作日默认窗」**（若 WS 有 Mon–Fri 窗则取周一窗；否则 09:00–18:00 单段）；备选 Q2b 强制要求 windows |
| Q3 | 例外挂 WS 还是 policy？ | **Q3a Workspace 级**（对齐 E50） |
| Q4 | policy 是否允许覆盖例外？ | **Q4a 本轮不允许** |
| Q5 | JSON 扩列 vs 独立表？ | **Q5a 扩 `business_hours.exceptions`**（少 migration；与 E50 同列）；上限 366 |
| Q6 | CLI 子命令名？ | **Q6a** `sla business-hours exceptions …`（挂既有组）；别名 `sla holidays` 可选不必须 |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. 纯函数：exceptions 接入 `add_business_minutes` / elapsed + 单测（TDD）  
3. API CRUD + normalize + 配置变更重算（TDD）  
4. FE 薄例外列表  
5. CLI 1.37.0  
6. 门禁 + acceptance tip  

## 7. 测试要点

- 纯函数：closed 跳过、forced_open 覆盖空周窗、closed 优先于周窗、enabled=false 回退  
- 与跨周末样例组合；pause/resume 剩余  
- CRUD 权限 / 跨租户 / 重复 date  
- spy：配置写无 emit；breach 既有路径不变；formula no-emit  
- CLI 1.37.0 pins + exceptions 命令  

---

## 附录 · runners-up（供 E54+；若 Yuri 改选可替换本草案）

1. **Webhook 投递可观测加厚**（按钩子成功率仪表 / 死信箱 UI / 聚合过滤）— E51 沉淀后再开；可作薄运维刀或与小刀并捆。  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification）— E52 铃铛落地后再评估；单列易溢。  
3. **SLA policy 级营业时/例外覆盖 thin**（仍砍完整优先级矩阵）— 仅当多品牌支持台强需求；本轮刻意 WS-only。

（Formula emit — 永不本轮。重做 E51 webhook pack / E52 Activity — 无增量，不推。）

## CLI 版本

**1.37.0**

# E56 Design：SLA policy 日历覆盖 thin — policy 级时区/周窗/例外覆盖 · CLI 1.40.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E56  
基线拟：`sprint/E55-S1` @ `2ad57ca`（全文 `2ad57caa7798516f183a45a6a6f37914d562dada`；design 基线 `6e2c8d3`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E56-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E57**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e56-sla-policy-calendar-overlay-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E56-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E55 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ Webhook 可观测（E54）→ **Insights 效能加厚（E55：切片 + 估点速度 + CSV）**。

E55 附录 runners-up（不绑定）：

1. **SLA policy 级营业时/例外覆盖 thin**（仍砍完整优先级矩阵 / 国家包）— E53 WS 例外再沉淀后、多品牌支持台有强信号时开  
2. **Activity 实时/Push 加厚**（WS 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢  
3. **Webhook 失败告警薄刀**（Inbox/email 当死信超过阈值）— E54 刚交可观测；单列过薄

代码实证 @ `2ad57ca`：

| 面 | 现状 |
|----|------|
| SLA 日历 | E50 WS `timezone` + `business_hours`（enabled + 每日最多 2 段）+ E53 `exceptions`（closed\|forced_open；cap 366）；加法器 / pause-resume / 配置变更重算（cap 500）**一律读 WS** |
| SlaPolicy | E42–E48：metric / start|stop|pause statuses / target_minutes / notify*；**无** timezone / windows / exceptions 列 |
| Insights | E55 已中厚（过滤 + velocity + CSV）；再叠报表构建器/日报偏厚或运维旁路 |
| Webhook | E44 账本 + E51 pack + E54 stats/死信箱；**无**告警引擎 |
| Activity | E52 watching+反应+铃铛；**无** Push / 实时 WS |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | Initiatives/Docs、Estimates、Relations、Customer、Insights、Git-PR 厚主面近期已交；E50/E53 明确把 **policy 覆盖**标为「本轮不允许」；隔开 E54/E55 后，日历弧下一刀正是 **policy 覆盖 thin** |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **SLA policy 日历覆盖 thin**：`SlaPolicy` 可选覆盖 WS 的 timezone / 周窗 / 例外（或显式 inherit）；create/pause/resume/recompute **按 policy 解析有效日历**；FE 在 policy 编辑薄加「日历覆盖」；配置变更仅重算该 policy 的 running/paused；CLI **1.40.0**；**无**国家包 / **无**多 policy 冲突矩阵 / **无** Push / **无**死信告警 | **中厚且 Linear/支持台对齐**；闭合 E50→E53→E56 日历弧；多品牌/多区域 SLA 的真实缺口；单 sprint 可交付 |
| B | Activity 实时/Push | E52 铃铛未满产品观察；Push/WS/FCM 单 sprint 必溢；默认再隔 |
| C | Webhook 死信告警薄刀（阈值→Inbox/email） | E54 刚交仪表+死信；单列过薄；宜再沉淀或与更厚刀并捆 |
| D | Insights 再厚（多 label AND-OR / 持久化报表 / Slack digest） | E55 刚交中厚；立刻再叠易变报表构建器大战 |
| E | Customer 门户 / Search FTS / GitHub App / Initiative 依赖图 / Formula emit | 门户·App·依赖图偏厚或排除；FTS 偏基建；emit **永不** |

**拍板：A（SLA policy 日历覆盖 thin）。**  
Activity Push、Webhook 死信告警、Insights 再厚列入附录 runners-up。

自检：覆盖语义、与 WS 继承合并、存储/migration、按 policy 重算、FE/CLI **1.40.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity 实时/Push | E52 铃铛后仍缺产品观察；Push/WS 必溢 |
| Webhook 死信告警 | E54 刚交可观测；告警引擎单列过薄 |
| Insights 再厚 / 报表构建器 | E55 刚闭合；再叠易溢 |
| Customer / FTS / GitHub App / Initiative 依赖图 | 主面已交或明确排除/过厚 |
| Formula emit / 重做 E50–E55 表面 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E50/E53 把 Workspace 日历闭合后，多品牌/多区域支持台仍只能「全 WS 同一套假日」——E50 Q2a / E53 Q4a 刻意砍掉的 **policy 级覆盖** 现已隔开 E54（webhook 可观测）+ E55（Insights）两轮；用中厚刀让单条 SlaPolicy 可选覆盖时区/周窗/例外，正好闭合 SLA 日历产品弧，且不重开 Push 或告警大战。

---

## 1. 目标

成功标准：owner 可在 **SlaPolicy** 上可选设置日历覆盖（timezone / weekday windows / exceptions）；未覆盖字段 **继承** WS（E50/E53）；该 policy 下 issue 时钟的 create/pause/resume/recompute / run-due **使用解析后的有效日历**；FE 在既有 SLA policy 表单薄加「日历覆盖」；变更该 policy 日历后 **仅**重算该 policy 的 running/paused（cap 同 E50，建议仍 500）；CLI **1.40.0**；跨租户隔离；**不**引入国家日历包、**不**做多 policy 冲突优先级矩阵 UI、**不**改 E52 Activity / E54 webhook / E55 Insights 主表面、**不** formula emit。

### A · 覆盖模型（BE）

- 有效日历解析（建议）：  
  - `effective_timezone = policy.calendar.timezone ?? ws.timezone`  
  - `effective_windows = policy.calendar.windows ?? ws.business_hours.windows`  
  - `effective_exceptions = policy.calendar.exceptions ?? ws.business_hours.exceptions`  
  - `enabled` 语义见 **Q2**（建议：WS `business_hours.enabled=false` 仍全局回退墙钟；policy 不可「强开」全局开关，避免偷偷绕过 WS 总闸）  
- 覆盖粒度见 **Q1**（建议整包 `calendar` JSON：缺省/`null` = 全继承；提供对象则可部分字段覆盖）  
- 例外条目形状 **对齐 E53**（`date` / `kind: closed|forced_open` / 可选 `windows`；cap 366）  
- 周窗形状 **对齐 E50**（每日最多 2 段半开 HH:MM）  
- IANA timezone 校验对齐 E50  
- 非法 JSON / 未知 kind / 重复 date → 400；跨租户 policy 404

### B · 时钟路径接线

- 凡调用 `add_business_minutes` / `elapsed_business_minutes` 的 create / pause / resume / recompute / run-due：**按 clock.policy_id 解析有效日历**，不再无条件读 WS  
- WS 日历变更：仍批量重算该 WS 下 **使用继承（无覆盖）** 的 running/paused；对已覆盖 policy 的钟 **跳过或按「继承字段是否受影响」精细化**（见 **Q3**；建议 Q3a：WS 变更重算全部 running/paused，因部分覆盖仍可能继承 timezone/windows/exceptions 之一——实现简单、正确优先）  
- Policy 日历变更：重算 **该 policy_id** 的 running/paused（cap 500）  
- enabled=false（policy 禁用）仍对齐 E42：tick 跳过；不自动 cancel

### C · 存储 / migration（**Q4**）

- 建议：**Q4a** `sla_policies.calendar` JSON nullable（`{ timezone?, windows?, exceptions? }`；`null`/缺列 = 全继承）  
  - 备选 Q4b 三列 `calendar_timezone` / `calendar_windows` / `calendar_exceptions`（更宽表；迁移啰嗦）  
- Alembic 一版；SQLite 测友好  
- **禁止**国家日历包实体；**禁止** priority / conflict-rank 列

### D · FE

- 既有 `settings/sla` policy 创建/编辑：折叠「日历覆盖」——Timezone / 周窗 / 例外列表；空 = 继承 WS（展示只读「继承自工作区」提示）  
- 「清除覆盖」一键回继承  
- vitest：normalize 覆盖 merge / 空覆盖 ≡ WS  
- **不做**月历拖拽大战、ICS 导入、多 policy 冲突可视化

### E · CLI **1.40.0**

- `sla policy create|update` 增日历覆盖参数（建议 `--calendar-json` 与/或 `--timezone` / `--clear-calendar`；见 **Q5**）  
- `sla policy show` JSON 含 `calendar` + 可选 `effectiveCalendar`（见 **Q6**）  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.40.0**

### F · 安全 / 租户 / no-emit

- policy CRUD 权限对齐 E42（owner 写；member+ 读 issue sla）  
- 跨租户 404  
- **不**新增 webhook 事件、**不**改 HMAC / 死信箱、**不**改 Activity / Insights  
- formula **no-emit**；日历读写路径 spy 不触发 fire_webhooks / automations（除既有 SLA breach 路径保持原样）

## 2. 非目标

- 国家日历包自动导入 / ICS 订阅 / 多地区法定假库  
- 多 SlaPolicy 冲突优先级矩阵 / 按客户选日历的规则引擎  
- Activity Push / FCM / 实时 WS / 浏览器 Notification  
- Webhook 死信告警引擎 / 失败日报  
- Insights 报表构建器 / 多 label AND-OR / Slack digest  
- 重做 E50 周窗语义 / 重做 E53 例外形状（只复用）  
- Formula 物化 emit（E40 D2/D7）  
- Customer 公开门户、GitHub App 安装 UX、Initiative 依赖图、原生移动端  
- 远程 push / 开 PR / 自开 E57

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 无覆盖 policy ≡ 今日 E53 行为（回归 WS 日历）；有覆盖时 deadline 按 policy 日历；跨租户 404 |
| B | create/pause/resume/recompute/run-due 均走 effective calendar；样例：WS 周一休息 + policy forced_open 周一 → 该 policy 钟计入营业分钟 |
| C | alembic 可升级；`calendar=null` 旧行行为不变 |
| D | FE 覆盖表单 + 清除覆盖 + vitest；build ok |
| E | CLI **1.40.0** + policy 日历参数 + version pins |
| F | 不新增 webhook 事件名；formula no-emit spy；不改 E52/E54/E55 主表面 |
| 门禁 | BE 定向（E56+E53+E50+E48/E45 相关）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E57 |

## 4. ADR（Yuri 已确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **SLA policy 日历覆盖 thin**（方案 A）；**无**国家包 / 冲突矩阵 / Push / 死信告警 / Insights 再厚 |
| D2 | 覆盖挂 `SlaPolicy.calendar` JSON；缺省全继承 WS（E50/E53） |
| D3 | 时钟路径一律按 policy 解析 effective calendar；复用既有 `add_business_minutes` / exceptions 语义 |
| D4 | Policy 日历变更 → 重算该 policy 的 running/paused（cap 500）；WS 变更重算策略见 Q3 |
| D5 | FE 落点 = 既有 SLA policy 表单薄加；不新开导航 |
| D6 | CLI = **1.40.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E52 Activity / E54 webhook / E55 Insights 主表面；非目标见 §2；不 push；不自开 E57 |

## 5. 开放问题（已全部按建议关闭）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | 覆盖粒度：整包 `calendar` 还是逐字段强制三选一？ | **Q1a 整包 JSON 可选字段覆盖**（`timezone?`/`windows?`/`exceptions?` 各自可缺省继承）；备选 Q1b 只能「全继承 / 全覆盖」二态 |
| Q2 | policy 能否在 WS `business_hours.enabled=false` 时仍用营业分钟？ | **Q2a 否**——WS 总闸关闭则全局墙钟；policy 覆盖只在总闸开启时生效；备选 Q2b policy 可强开营业分钟 |
| Q3 | WS 日历变更时，已部分覆盖的 policy 钟如何重算？ | **Q3a 重算该 WS 全部 running/paused**（简单正确；部分继承字段仍可能变）；备选 Q3b 仅重算「无覆盖或覆盖未钉死该字段」的 policy |
| Q4 | 存储形态？ | **Q4a `sla_policies.calendar` JSON nullable**；备选 Q4b 三独立列 |
| Q5 | CLI 写入形态？ | **Q5a `--calendar-json` + `--clear-calendar`**（与 E50/E53 JSON 风格一致）；备选 Q5b 一长串拆散 flag |
| Q6 | `policy show` 是否计算 `effectiveCalendar`？ | **Q6a 是**（调试友好；只读拼装）；备选 Q6b 只回存贮 `calendar` |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Alembic + model `calendar` + normalize/merge 纯函数（TDD）  
3. BE 时钟路径改走 effective calendar + policy PATCH 重算（TDD；回归 E50/E53）  
4. FE policy 表单日历覆盖  
5. CLI 1.40.0  
6. 门禁 + acceptance tip  

## 7. 测试要点

- 无覆盖回归：同 WS 例外/周窗下 deadline ≡ E53  
- 仅 timezone 覆盖；仅 windows 覆盖；仅 exceptions 覆盖；三字段全覆盖  
- WS enabled=false → 墙钟（Q2a）  
- Policy 日历变更 → 仅该 policy 钟 deadline 更新；cap  
- 跨租户；非法 calendar；重复 exception date  
- spy：日历读写无 fire_webhooks；不触碰 Insights export / webhook stats / activity cursors  
- CLI 1.40.0 pins + calendar-json / clear-calendar / show effectiveCalendar  

---

## 附录 · runners-up（供 E57+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢。  
2. **Webhook 失败告警薄刀**（Inbox/email 当死信超过阈值）— 可挂在 E54 之后；本轮刻意不做告警引擎。  
3. **Insights 再厚 / 效能日报**（多 label OR、持久化「我的报表」、可选邮件 digest）— E55 刚交中厚；宜再沉淀。  

（备选扫描但本轮不推：Search FTS 基建、Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动 — Roadmap 排除或过厚。Formula emit — 永不本轮。重做 E50–E55 表面 — 无增量，不推。）

## CLI 版本

**1.40.0**

# E51 Design：专用 webhook pack + 订阅事件过滤 FE · CLI 1.35.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E51  
基线拟：`sprint/E50-S1` @ `1902384`（全文 `1902384035097eb52f3b5840626a1737b703e1d3`；feature tip `b290178`；design 基线 `a77e2cf`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E51-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E52**。  
建议入库路径：`docs/superpowers/specs/2026-11-05-e51-webhook-pack-subscription-filter-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E51-S1`。开放问题 Q1–Q6 均按建议默认关闭。

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E50 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 thin → Formula query surfaces v2 → WS Activity Feed → SLA first-response + pause timeline → Formula Display v2 → **SLA business hours thin**。

E50 验收后 SLA 运维弧（E42→E45→E48→E50）已齐套；E50 附录与 E48/E49 附录仍把下一刀标为（不绑定）：

1. **专用 webhook pack** `issue.cycle_changed` / `issue.estimate_changed`（± `project_changed` / `sla_paused`）**捆订阅事件过滤 FE** — 抬到中厚集成闭环  
2. **Activity Feed 加厚**（反应/订阅/推送）— E47 薄 FE 后已隔 E48–E50；仍偏产品化 UI 重  
3. 完整节假日/优先级大战、Formula emit — **明确不推**

代码实证 @ `1902384` / feature tip `b290178`：

| 面 | 现状 |
|----|------|
| Timeline | E41 已写 `cycle_changed` / `estimate_changed` / `project_changed`；E48 已写 `sla_paused` / `sla_resumed` |
| Webhook `WEBHOOK_EVENTS` | 仅 `issue.created/updated/status_changed`、`comment.created`、`issue.custom_field_changed`、`issue.sla_breached`、`issue.assignee_changed`、`issue.label_added/removed` — **无** cycle/estimate/project/sla_paused 专用名 |
| 更新路径 | `issue_service` 在 cycle/estimate/project 变更时 fire `issue.updated`（± `changed[]`）；**不** fire 专用事件 |
| FE webhooks | 设置页已有事件 CheckboxGroup（绑 `WEBHOOK_EVENTS` + labels）；**缺**新事件选项与标签；投递日志按事件过滤/预设 UX 偏薄 |
| Activity | E47 JSON 游标薄 FE；无反应/订阅/推送 |
| SLA / Formula Display | E50 business hours 齐；E49 Display v2 齐；**不再**本轮主刀 |
| CLI | **1.34.0**；下一刀 **1.35.0** |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **专用 webhook pack + 订阅事件过滤 FE**：扩展 `WEBHOOK_EVENTS` + 在 cycle/estimate/project/sla pause 写路径 fire 专用事件；FE 事件勾选/标签/预设 + 投递日志按事件过滤；CLI **1.35.0**；payload 对齐既有 envelope | **中厚且连贯**；闭合 outbound 弧（E29→E41→E44→E51）；订阅方可精选事件而不吞全量 `issue.updated`；单 sprint 可交付 |
| B | Activity Feed 加厚（反应/订阅/推送） | UI/产品化重；E47 API 已够读；宜再沉淀或独立 Epic |
| C | 仅加事件名、不碰 FE | **过薄**；撑不起 Epic 厚度约定 |
| D | SLA 节假日/policy 覆盖 / 优先级矩阵 | E50 明确非目标；单 sprint 必溢 |
| E | Formula emit / 物化写路径 | 打破 E40 D7；**永不本轮** |

**拍板：A（专用 webhook pack + 订阅事件过滤 FE）。**  
Activity 加厚、节假日大战列入附录供 E52+ / runners-up。

自检：事件名清单、与 `issue.updated` 并存策略、FE 过滤厚度、CLI **1.35.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Feed 加厚 | 产品化 UI Epic；E47 沉淀未满「再隔一轮」以外的强 ROI 信号 |
| SLA 节假日/policy 覆盖 | E50 刚砍；避免立刻重开运维大战 |
| 仅 webhook 事件名（无 FE） | 过薄；Way 厚度约定要求整 Epic |
| Formula emit | 打破 E40 D7；永不本轮 |

## 1. 目标

成功标准：工作区 outbound webhook 可订阅 **专用** `issue.cycle_changed` / `issue.estimate_changed` / `issue.project_changed` / `issue.sla_paused`（± `issue.sla_resumed`，见 Q1）；对应写路径在 timeline 已有动作时 **额外** fire 专用事件（与既有 `issue.updated` / breach 路径并存，见 Q2）；FE 设置页事件勾选覆盖新事件 + 投递日志可按事件过滤（薄预设 OK）；跨租户隔离；CLI **1.35.0**；**不**引入节假日表 / SLA policy 覆盖 / Activity 反应订阅推送 / formula emit / 进程内 cron。

### A · 事件包（BE）

- 扩展 `WEBHOOK_EVENTS`（及校验白名单）加入：
  - `issue.cycle_changed`
  - `issue.estimate_changed`
  - `issue.project_changed`
  - `issue.sla_paused`
  - （可选）`issue.sla_resumed` — **Q1**
- 接线：`issue_service` 在 cycle / estimate_points / project 实际变更分支 fire 专用事件；`SlaService` pause（± resume）路径 fire `sla_paused`（± `sla_resumed`）
- Payload：沿用 E44 envelope（`type` / `workspaceId` / `data`）；`data` 至少含 issue id/code + old/new 相关字段；HMAC / 投递重试语义不变
- **并存**：专用事件 **不替代** `issue.updated`（Q2a）；订阅方可只勾专用事件以减噪
- 未知事件名仍 400；既有钩子 `events_json` 不含新名则 **不** 收到新事件（兼容）

### B · 订阅事件过滤 FE

- 扩展 `frontend/src/service/api/webhooks.ts` 的 `WEBHOOK_EVENTS` + `WEBHOOK_EVENT_LABELS`（中英标签）
- 设置页 CheckboxGroup 自动带出新选项；可选「集成常用」预设（cycle/estimate/project/sla_*）一键勾选（Q3）
- 投递日志：按 `event_type` 过滤（薄；下拉或多选）；vitest 覆盖 labels / 预设 normalize
- **不做**完整订阅中心 / 多渠道路由 / Zapier 式图形编排

### C · CLI **1.35.0**

- `webhook` 命令：list/create/update 事件枚举文档与校验同步新名；可选 `webhook events` 列出允许集
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.35.0**

### D · 安全 / 租户 / no-emit

- 读写按 WS 成员权限（对齐现网 webhook admin）
- 跨租户 404；URL/事件白名单不变
- **不**因「只扩展事件枚举的只读」触发 automation；formula **no-emit** spy 守住
- 配置变更（钩子 CRUD）路径不额外 fire 业务 issue 事件（测达既有行为）

## 2. 非目标

- 节假日 / 例外日 / 国家日历包；SLA policy 级营业时覆盖 / 优先级矩阵  
- Activity Feed 反应 / 关注订阅 / 推送 / 富媒体  
- Formula 物化 emit（E40 D2/D7）  
- 回放/补发历史事件；Webhook 图形编排 / 多渠道路由  
- Redis / 进程内 cron；远程 push / 开 PR / 自开 E52

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | `WEBHOOK_EVENTS` 含约定专用名；非法事件名 400 |
| B | cycle / estimate / project 变更时专用事件被 fire；payload 含 old/new；同时 `issue.updated` 行为不变（Q2a） |
| C | sla pause（± resume）fire `issue.sla_paused`（± `sla_resumed`）；与 `issue.sla_breached` 不互相替代 |
| D | 钩子未订阅新事件时不投递；订阅后投递成功并入 delivery log |
| E | FE 勾选新事件 + 标签；投递日志可按事件过滤；vitest 绿；build ok |
| F | 跨租户隔离；formula no-emit spy；HMAC/重试语义回归 |
| G | CLI **1.35.0** + version 断言 |
| 门禁 | BE 定向+全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E52 |

## 4. ADR（Yuri 已确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **专用 webhook pack + 订阅事件过滤 FE**（方案 A）；**无** Activity 加厚 / SLA 日历大战 / 薄「只加事件名」 |
| D2 | 专用事件与 `issue.updated` **并存**（不替代）；订阅方可精选减噪 |
| D3 | 事件名对齐 timeline action：`cycle_changed` / `estimate_changed` / `project_changed` / `sla_paused`（± `sla_resumed`） |
| D4 | FE = 扩展勾选 + 标签 + 投递日志事件过滤（± 薄预设）；不做订阅中心 |
| D5 | 投递/HMAC/重试沿用 E44；无回放 |
| D6 | CLI = **1.35.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；非目标见 §2；不 push；不自开 E52 |

## 5. 测试要点

- BE：各专用事件 fire / 未订阅不投 / 与 `issue.updated` 并存；pause/resume；跨租户  
- FE：labels 覆盖新事件；预设 normalize；投递日志过滤  
- spy：formula no-emit；钩子 CRUD 无额外业务 emit  
- CLI 1.35.0 pins + events 枚举

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE：扩展 `WEBHOOK_EVENTS` + fire 接线（TDD）  
3. FE：labels / 勾选 / 投递日志过滤 + vitest  
4. CLI 1.35.0  
5. 门禁 + acceptance tip

## 7. 开放问题（已全部按建议关闭）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | 事件包是否含 `issue.sla_resumed`？ | **Q1a 含**（与 E48 timeline `sla_resumed` 对称；成本低） |
| Q2 | 专用事件是否替代 `issue.updated`？ | **Q2a 不替代**（并存；减噪靠订阅勾选） |
| Q3 | FE「集成常用」预设要不要？ | **Q3a 要**（一键勾选 cycle/estimate/project/sla_*；可清空） |
| Q4 | `project_changed` 是否必须进本包？ | **Q4a 必须**（E41 timeline 已有；与 cycle/estimate 同族） |
| Q5 | 是否做历史回放/补发？ | **Q5a 不做**（非目标；避免运维面膨胀） |
| Q6 | CLI 是否新增 `webhook events` 子命令？ | **Q6a 要**（列出允许集；create/update 帮助指向它） |

---

## 附录 · runners-up（供 E52+；若 Yuri 改选可替换本草案）

1. **Activity Feed 加厚**（反应、关注订阅、推送）— E47 API 已够读；产品化 UI 重，宜独立 Epic。  
2. **SLA 节假日/例外日 thin**（仍砍优先级矩阵）— 仅当支持台强需求；E50 刚交，默认再隔至少一轮。  
3. **Webhook 投递可观测加厚**（按钩子成功率仪表 / 死信箱 UI）— 可挂在本包之后的小刀，或并入 E52 若本包砍薄。

（Formula emit — 永不本轮。）

## CLI 版本

**1.35.0**

## Why this Epic now（一句话扩写）

SLA 弧已在 E50 收口；timeline 早有 cycle/estimate/project/sla_paused 动作，但 outbound `WEBHOOK_EVENTS` 与 fire 路径仍缺专用名，集成方只能吞 `issue.updated`。把专用事件包与订阅勾选/投递日志过滤捆成中厚 Epic，正好闭合 E29→E44 的 outbound 弧，且不重开 SLA 日历大战或 Activity UI 重活。

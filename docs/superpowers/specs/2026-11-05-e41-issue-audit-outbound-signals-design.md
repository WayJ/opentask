# E41 Design：Issue audit & outbound signals（活动加厚 + timeline export + CF webhook）

日期：2026-11-05（Asia/Shanghai）  
Epic：E41  
基线：`sprint/E40-S1` @ `098d1c3`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E41-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E42**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E41-S1`。建议路径  
`docs/superpowers/specs/2026-11-05-e41-issue-audit-outbound-signals-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E25–E40 已交付自定义字段全栈（含 formula 只读列）、自动化（含 `custom_field_changed` / delay）、Board CF 泳道、到期提醒。  
E29 出站 Webhook 仅 `issue.created|updated|status_changed` + `comment.created`；E36 `_emit_custom_field_changed` **只打 automations，不打 webhook**。  
`issue_timeline` + 详情「活动」已有主路径，但 **CF / cycle / estimate / project 变更未入账**；**无 timeline CSV/JSON export**。

E40 附录候选：

1. Webhook `custom_field_changed` outbound（薄：E29 `events[]` + E36 emit 旁路）
2. Issue activity 加厚 + export（CF/cycle/estimate → timeline + CSV/CLI）
3. SLA clocks（策略×状态机×tick；厚过单 sprint）

另扫仓库缺口：

| 候选 | 现状 | 相对 ROI |
|------|------|----------|
| Webhook CF outbound | E29 无事件；E36 已有 changes[] | 薄；单独开 Epic 偏瘦 |
| Activity thicken + export | timeline 枚举无 CF/cycle/estimate/project；无 export | 中厚；补审计面 |
| SLA clocks | 无 | 过厚；避免 |
| Formula 过滤 / 泳道 / 物化 emit | E40 明示非目标 | 可后置；本轮不堵审计 |
| Git PR / Initiatives | 已有独立 roadmap | 不重复 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| A | **合并**：活动加厚（CF/cycle/estimate/project）+ timeline export + Webhook `issue.custom_field_changed` | **厚且连贯**：「写路径审计 + 出站信号」；单 sprint 可控若砍 SLA/全量事件包/实时 feed |
| B | 仅 Activity thicken + export | 中厚；Webhook CF 仍留缺口，下轮又薄插空 |
| C | 仅 Webhook CF outbound | 实现小，不符「加厚 Epic」；审计面仍缺 |

**拍板建议：A（Issue audit & outbound signals）。**  
SLA / formula 过滤物化 / 全量 webhook 事件包列入附录供 E42+。

自检：无 TBD；PG enum 扩展、导出上限、webhook 事件名、FE/CLI **1.25.0**、非目标已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| 仅 Webhook CF | 太薄；与 Activity 同源写路径，合并更省往返 |
| 仅 Activity export | 可交付，但丢掉 E36→E29 显式接线的高 ROI 薄片 |
| SLA clocks | 策略 CRUD + 状态时钟 + 违约 tick；易溢出 |
| Formula 物化 / 过滤 / 泳道 | E40 ADR D2/D7；另开安全与产品面 |

## 1. 目标

成功标准：Issue 写路径把 **CF / cycle / estimate / project** 变更写入 `issue_timeline`；详情「活动」可读；可 **export** 单 Issue 或 WS 过滤的 timeline CSV；出站 Webhook 可订阅 **`issue.custom_field_changed`**（接 E36 changes，**不含** formula 读时结果）；跨租户隔离；FE 展示/导出入口 + webhook 事件多选；CLI **1.25.0**；**不**引入进程内 cron / SLA。

### A · Timeline 加厚（数据模型 + 写路径）

- `TimelineAction` / PG enum `timeline_action` 新增（字符串值）：
  - `custom_field_changed`
  - `cycle_changed`
  - `estimate_changed`
  - `project_changed`
- 迁移：`h4c5d6e7f8a2_issue_timeline_audit_actions`（命名按仓内 Alembic 惯例）
  - PostgreSQL：`ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS '…'`（逐值；注意 PG 事务限制时按仓内既有模式拆/用 `commit_as_you_go` 惯例）
  - SQLite / 测试：与现有 ENUM 存储兼容（字符串即可）
- Python `TimelineAction` enum 同步四值
- 写路径：
  1. **CF**：`CustomFieldService.upsert_issue_values` 在既有 `changes[]` 提交后，对每个实际变更 `_add_timeline`（或经 IssueService 助手）：
     - `action_type=custom_field_changed`
     - `action_data={fieldId, fieldKey, from, to}`（值已序列化标量/JSON 可 JSON 化；过长截断至 2KB/字段）
     - **不**为 formula 计算变化写 timeline（无物化、无 upsert）
  2. **cycle / estimate / project**：`IssueService.update_issue`（及等价 bulk 单字段路径若已走同一 update）在字段实际变化时各写一条：
     - `cycle_changed`：`{from, to}`（cycle id 或 null）
     - `estimate_changed`：`{from, to}`（number|null）
     - `project_changed`：`{from, to}`（project id 或 null）
  3. 无变化不写；best-effort 不阻断主写（与现 `_add_timeline` 同事务优先；失败则随主事务回滚——**ADR：与现有 status/priority timeline 同事务**）
- `serialize` / API 响应：既有 `GET /api/issues/{id}/timeline` 自然返回新 `action_type`；无需新表

### B · Timeline export

- `GET /api/issues/{issue_id}/timeline/export.csv`
  - 权限：与读 Issue 同（workspace member+；viewer 可读）；强制 `X-Workspace-Id`；跨租户 404
  - Query 可选：`limit`（默认 5000，硬顶 **10000**）、`action_type`（可重复或逗号分隔过滤）
  - CSV 列：`created_at,action_type,user_id,user_name,field_key,from_value,to_value,action_data_json`
  - `Content-Disposition: attachment; filename="issue-{code}-timeline.csv"`
- （可选同 Epic 薄加）`GET /api/issues/timeline/export.csv`：**WS 级**按 `updated_since` / `issue_id` / `action_type` 过滤；硬顶 **10000** 行；无则标 Gaps 不做
- **拍板：本 Epic 必做单 Issue export；WS 级 export 做**（复用 list ACL + 同一 CSV schema），避免只做半截审计

### C · FE

- Issue 详情「活动」：`formatTimelineAction` 增四类文案（中文）：
  - CF：`将自定义字段 {key} 从 {from} 改为 {to}`
  - cycle / estimate / project：对称文案
- 详情活动区：导出按钮 → 下载单 Issue CSV（`export.csv`）
- `/settings/webhooks`：事件多选增 **`issue.custom_field_changed`**（label：自定义字段变更）
- 不改 Automations / Formula / Board 主路径

### D · CLI **1.25.0** + Webhook 事件

- Webhook：
  - `WEBHOOK_EVENTS` += `"issue.custom_field_changed"`
  - 在 `_emit_custom_field_changed` 旁路（每条 change 或聚合一次——**拍板：每个 changed field 一条事件**，与 automation 对齐；payload 见 §3）
  - `fire_webhooks(..., event_type="issue.custom_field_changed", data={...})`
  - **不**因 formula 读时结果变化触发
  - FE/CLI create|update `--events` 校验自动吃新枚举
- CLI **1.25.0**：
  - `issue timeline <id|code> [--limit N] [--json]`（若尚无：列出活动）
  - `issue timeline-export <id|code> [--out FILE] [--action-type …]`
  - `issue timeline-export-workspace [--out FILE] [--since ISO] [--action-type …]`（WS 级）
  - webhook help / 测试夹具事件列表含新事件
  - version → **1.25.0**（全仓 version 断言同步 bump）

## 2. 数据模型（摘要）

**改：**
- PG/SQLAlchemy enum `timeline_action` +4 值
- `TimelineAction` Python enum +4
- `WEBHOOK_EVENTS` + `issue.custom_field_changed`

**不改：**
- `issue_timeline` 表结构（仍 `action_data` JSON）
- `workspace_webhooks` 表结构（events_json 已是数组）
- formula / automations 表

**复用：**
- E19/E27 既有 `_add_timeline` 模式
- E29 `fire_webhooks` / HMAC / delivery log
- E36 `changes[]` 形状（`field_key`/`field_id`/`from`/`to`）

## 3. API

| 面 | 行为 |
|----|------|
| 写路径（无新路由） | upsert CF / update issue → timeline 行；CF → 可选 webhook |
| `GET /api/issues/{id}/timeline` | 既有；新 action_type 对 FE 透明 |
| `GET /api/issues/{id}/timeline/export.csv` | 单 Issue CSV；member+ 读；limit 硬顶 |
| `GET /api/issues/timeline/export.csv` | WS 级 CSV；query：`since`/`issueId`/`actionType`/`limit` |
| Webhook CRUD | events 允许集含 `issue.custom_field_changed` |
| 投递 body | 沿用 E29 envelope；`type=issue.custom_field_changed`；`data`：`{ id, issueCode, title, fieldId, fieldKey, from, to, actorUserId? }` |

权限：读 timeline/export = 与 Issue 读同；webhook 写仍 **owner**（E29）；强制 `X-Workspace-Id`；跨租户 404。

## 4. FE

- `views/issue/detail/index.vue`：`formatTimelineAction` + 导出按钮
- `views/workspace/webhooks`（或既有 settings/webhooks）：事件选项 +1
- typings：`TimelineAction` 联合类型 +4
- 最小 vitest：formatter 单测；webhook events 常量含新事件（若有前端常量）

## 5. CLI

- **1.25.0**
- `issue timeline` / `timeline-export` / `timeline-export-workspace`
- webhook `--events` 可含 `issue.custom_field_changed`
- help 示例与 version 断言全仓同步

## 6. 安全 / 租户

- export 仅当前 WS；issue_id 必须属 WS
- CSV 不输出其它租户字段；`action_data` 已存内容原样导出（无二次扩权）
- webhook 仍 HMAC；CF 值进 payload 视为租户数据——仅订阅方 URL；**不**因 export/webhook 绕过 member ACL
- formula 计算结果 **永不** 写 timeline / 发 webhook（延续 E40 D7）
- 大导出：硬顶 10000；超限截断并在响应头 `X-OpenTask-Truncated: true`（或 CSV 首行注释——**拍板用响应头 + 仍 200**）
- 无任意代码执行；无新 SSRF 面（webhook URL 校验沿用 E29）

## 7. 非目标

- SLA 策略引擎 / 违约时钟 / 内置 cron
- 全量补齐其它 webhook 事件（`issue.cycle_changed` 等）——cycle/estimate 已由 `issue.updated` 的 `changed[]` 覆盖
- Formula 物化、过滤、Board 泳道、读时结果 emit
- 活动无限流式分页 UI 重做、审计合规保留策略（TTL）
- WS 仪表盘「全局活动 feed」产品化（export 足够）
- Slack OAuth / Zapier 专用
- 远程 push / 开 PR / 自开 E42

## 8. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | 四类 timeline 可写入；CF upsert / cycle / estimate / project 变更可见；无变更不写；跨 WS 404 |
| B | 单 Issue + WS 级 CSV export；limit 硬顶；权限与租户正确 |
| C | FE 活动文案；导出按钮；webhook 事件多选含新事件 |
| D | CLI 1.25.0 + timeline/timeline-export(+workspace) + webhook 事件；version 断言 |
| Webhook | CF 变更投递 `issue.custom_field_changed`；签名/log 复用；formula 不触发 |
| 门禁 | BE 定向+全量绿（记 passed/skip）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E42 |

## 9. ADR

| ID | 决定 |
|----|------|
| D1 | Epic 合并 Activity 加厚 + export + CF webhook outbound（方案 A） |
| D2 | 新 timeline actions：`custom_field_changed` / `cycle_changed` / `estimate_changed` / `project_changed` |
| D3 | PG enum `ADD VALUE`；与 Python enum / FE 联合类型同步 |
| D4 | CF timeline 与 webhook 均基于 E36 `changes[]`；每字段一条 |
| D5 | Webhook 事件名 **`issue.custom_field_changed`**（对齐 E29 `issue.*` 前缀） |
| D6 | formula 读时结果不写 timeline、不发 webhook |
| D7 | 单 Issue + WS 级 CSV export；硬顶 10000；截断头 `X-OpenTask-Truncated` |
| D8 | timeline 写入与现有 status 等 **同事务**（非 fire-and-forget） |
| D9 | CLI **1.25.0**；全仓 version 断言同步 |
| D10 | 非目标见 §7；不 push；不自开 E42 |

## 10. 测试要点

- BE：update cycle/estimate/project → 对应 timeline；无变更不写
- BE：upsert CF 两字段变更 → 两条 `custom_field_changed`；并 fire webhook（可用 httpx mock / delivery log）
- BE：formula 字段无 upsert / 无 webhook
- BE：export.csv 列与过滤；跨租户 404；超限截断头
- BE：webhook events 校验接受新事件；未订阅不投递
- FE：formatter 四类；事件选项存在
- CLI：version 1.25.0；timeline-export 写文件；webhook create 含新事件
- 回归：E29 旧事件；E36 automations 仍触发；E40 formula 只读

## 11. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Migration enum + TimelineAction + update_issue / CF upsert 写 timeline（TDD）  
3. Export CSV 两路由（TDD）  
4. Webhook 事件 + `_emit` 旁路 `fire_webhooks`（TDD）  
5. FE 活动文案 + 导出 + webhook 多选  
6. CLI 1.25.0  
7. 门禁 + acceptance tip  

---

## 附录 · 本轮未选但仍高 ROI（供 E42+）

1. **SLA clocks**：策略 × 状态时钟 × 外部 tick（独立厚 Epic）。  
2. **Formula 过滤 / SmartSearch / 泳道 / 可选物化 emit**：在审计与安全策略明确后再开。  
3. **Webhook 事件包加厚**：`issue.assignee_changed` / label 等专用事件（今日多由 `issue.updated` 覆盖）。  

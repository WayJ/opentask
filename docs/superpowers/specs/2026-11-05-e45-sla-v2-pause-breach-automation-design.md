# E45 Design：SLA v2 thin — pause + breach→automation

日期：2026-11-05（Asia/Shanghai）  
Epic：E45  
基线：`sprint/E44-S1` @ `ff57fed`（design `2984a54`；acceptance 文件 tip 仍写 `fbb1514`，属 tip-bump 残余）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E45-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E46**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E45-S1`。开放问题 Q1–Q6 已关闭（Q4 取 Q4b：本轮不做 timeline）。建议路径  
`docs/superpowers/specs/2026-11-05-e45-sla-v2-pause-breach-automation-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E42 交付 **SLA clocks v1**：`sla_policies`（仅 `time_in_status`）+ `issue_sla_clocks`（`running|met|breached|cancelled`）+ 状态写路径启停 + 外部 `POST /api/sla/run-due` → Inbox `sla_breached` + 可选 webhook `issue.sla_breached`；FE `/settings/sla` + 徽标；CLI 1.26.0。  
明确非目标：**暂停**、**breach→automation 动作链**、营业日历、first-response metric。

E43 Formula surfaces、E44 webhook 事件包+投递可靠性已落地；E42–E44 附录连续把 **SLA v2** 标为下一高 ROI。v1 时钟语义已沉淀两轮 Epic，本轮用 **v2 薄片** 闭合「等客户时不计时」与「违约可自动升级」——对齐 Linear/支持台 SLA 的日常闭环，且不引入营业日历运维面。

现状缺口（代码实证 @ `ff57fed`）：

| 面 | 现状 |
|----|------|
| `CLOCK_STATUSES` | `running` / `met` / `breached` / `cancelled` — **无** `paused` |
| `SlaPolicy` | `start_statuses` / `stop_statuses` / `target_minutes`；**无** pause 状态集 |
| `sync_clocks` | 仅 stop→`met` 或 start→新 `running`；进 `feedback` 等态若未配 stop 则时钟继续跑 |
| `run_due` | breach → Inbox + webhook；**不** `fire_automations` |
| `TRIGGER_TYPES` | 无 `issue.sla_breached` / `sla_breached` |
| FE 徽标 | running/met/breached；无 paused 文案 |
| CLI | policy CRUD + issue sla + run-due；无 pause 配置面 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **SLA v2 thin**：策略可配 `pause_statuses`；时钟 `paused` + 累计已用分钟；离开 pause → 续跑并重算 `deadline_at`；`run_due` breach 后 `fire_automations(issue.sla_breached)`；FE/CLI **1.29.0** | **中厚且连贯**；闭合 E42 附录 #3 核心两刀；无营业日历 |
| B | Formula range / sort-by-formula / Display 条件格式 | E43 等值过滤刚齐；增强面；非运营闭环 |
| C | WS 全局活动 feed 产品化 | UI 重；E41 CSV 已够审计 |
| D | 完整 SLA v2（营业日历 + first-response + pause + 升级） | **单 sprint 必溢** |
| E | 仅 `TRIGGER_TYPES += sla_breached`（无 pause） | **过薄**；pause 才是 v1→v2 体感差 |

**拍板建议：A（SLA v2 thin — pause + breach→automation）。**  
Formula range/sort、全局 feed、营业日历 / first-response 列入附录供 E46+。

自检：pause 状态机、deadline 重算、automation 触发契约、权限、FE/CLI **1.29.0**、非目标已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Formula range / sort / 条件格式 | E43 刚交付；列表增强非阻塞；ROI 低于 SLA 运营闭环 |
| 全局活动 feed | 产品化 UI Epic；审计导出已有 |
| 营业日历 / 时区矩阵 | 运维+测试面大；v2 thin 刻意砍掉 |
| first-response metric | 新时钟语义（首评/首回复）；宜独立 Epic |
| 仅 automation 触发、无 pause | 薄；支持台「等客户」场景仍假违约 |

## 1. 目标

成功标准：WS 可为 time-in-status 策略配置 **暂停状态集**；Issue 进入 pause 态时时钟 **暂停且不计时**；离开 pause（回到非 stop 的工作态）时 **续跑** 并按剩余目标重算 deadline；`run-due` 违约后除 Inbox/webhook 外触发 **Automations**（新 trigger）；FE 可配 pause 并展示 paused 徽标；跨租户隔离；CLI **1.29.0**；**不**引入营业日历 / 新 metric / 进程内 cron。

### A · 策略：`pause_statuses`

- `sla_policies` 新增列 `pause_statuses`（JSON list[str]，默认 `[]`）  
- CRUD / serialize 透出 `pauseStatuses`  
- 校验：必须是合法 `IssueStatus` 值；与 `start_statuses` / `stop_statuses` **可重叠时的优先级见 ADR D3**（建议：stop > pause > start）  
- 空列表 = 不启用暂停（兼容 v1 行为）  
- **建议默认空**；文档示例可写 `["feedback"]`（IssueStatus 已有「等待反馈」）

### B · 时钟状态机加厚

扩展 `CLOCK_STATUSES` += `paused`。

`issue_sla_clocks` 新增列（扩表，少表）：

| 列 | 含义 |
|----|------|
| `elapsed_before_pause_minutes` | int，默认 0；每次进入 pause 时累加「本段 running 已用墙钟分钟」 |
| `paused_at` | datetime nullable；当前 pause 起点 |

行为（`sync_clocks`，同事务）：

1. 若存在 `running` 且 `new_status` 满足 **stop** → `met`（同 v1；**优先于 pause**）。  
2. 若存在 `running` 且 `new_status ∈ pause_statuses` →  
   - `elapsed_before_pause_minutes += floor((now - started_at_or_last_resume) 墙钟分钟)`（实现：用「本段起点」；见下）  
   - `status=paused`，`paused_at=now`；**不**改 `deadline_at` 历史值或可保留作审计（续跑时重算）。  
3. 若存在 `paused` 且 `new_status` 满足 stop → `met`（`stopped_at=now`；保持 elapsed）。  
4. 若存在 `paused` 且 `new_status ∉ pause_statuses` 且 **不** stop：  
   - 续跑：`status=running`；`paused_at=null`；  
   - `deadline_at = now + timedelta(minutes=max(0, target_minutes - elapsed_before_pause_minutes))`；  
   - 「本段起点」记入实现细节：建议另加 `segment_started_at`（datetime，running 段起点）**或** 复用语义——进入 running/resume 时设 `segment_started_at=now`；pause 时用 `now - segment_started_at` 累加 elapsed。  
5. 若 `new_status ∈ start` 且无 running/paused → 新建 running（同 v1）；若已有 paused **不**另开第二条（每 policy 至多一条活跃钟：running|paused）。  
6. `cancelled`：策略删除/禁用时的既有行为保持；paused 同行可 cancelled。

`run_due` 扫描条件：**仅** `status=='running' AND deadline_at<=now`（**paused 永不被 tick breach**）。

序列化 `GET /issues/{id}/sla`：增 `elapsedBeforePauseMinutes` / `pausedAt` / 剩余分钟对 paused 显示「已暂停 · 已用 X / 目标 Y」。

### C · breach → automation

- `TRIGGER_TYPES` += `issue.sla_breached`（与 webhook / Inbox 命名对齐；**开放问题 Q1**）  
- `SlaService.run_due` 在标 `breached` + Inbox + webhook **之后**（同 clock 事务或紧随 flush）：  
  `await fire_automations(..., trigger_type="issue.sla_breached", issue=issue, actor_user_id=None, event={policyId, policyName, deadlineAt, breachedAt, clockId})`  
- 动作复用既有 `ACTION_TYPES`（`set_priority` / `set_assignee` / `add_label` / `add_comment` / `set_status` / `set_custom_field`）——**不**本轮新造 action  
- 冷却 / `delay_minutes`（E38）若规则配置了 delay，走既有 pending 队列；默认立即执行  
- **幂等**：同一 clock 仅 breach 一次 → automation 只火一次（同 v1 双跑 skip）  
- 失败隔离：automation 异常记 `errors[]`，不回滚已 breached（与 webhook try/except 同风格）

### D · FE

- `/settings/sla`：策略表单多选 **暂停状态**（中文：暂停计时的状态）；帮助文案「进入这些状态时 SLA 暂停；离开后按剩余时间续跑」  
- Issue 详情徽标：`paused` → 琥珀色「已暂停」+ 已用/目标  
- Automations 设置：触发下拉 + `issue.sla_breached`（文案：SLA 违约）  
- 最小 vitest：pauseStatuses 序列化；徽标分支；trigger 常量

### E · CLI **1.29.0**

- `sla policy create|update` 增 `--pause` 可重复 / `--json-body` 已可带 `pauseStatuses`  
- `sla issue` 输出含 paused 字段  
- automation create 帮助列出新 trigger  
- version → **1.29.0**；全仓历史 version 断言同步

### F · 数据模型摘要

**修改：**  
- Alembic（建议 `l8a9b0c1d2e6`，`down_revision` = E44 `k7f8a9b0c1d5`）：  
  - `sla_policies.pause_statuses` JSON NOT NULL default `[]`  
  - `issue_sla_clocks.elapsed_before_pause_minutes` INT NOT NULL default 0  
  - `issue_sla_clocks.paused_at` DateTime NULL  
  - `issue_sla_clocks.segment_started_at` DateTime NULL（若 ADR 选显式段起点；迁移时对既有 running 回填 `started_at`）  
- `CLOCK_STATUSES` += `paused`  
- `TRIGGER_TYPES` += `issue.sla_breached`  

**写路径：** `SlaService.sync_clocks` / `run_due`；automation 枚举  
**复用：** E42 时钟；E26/E38 automations；E29/E44 webhooks；外部 run-due  
**不改：** formula emit 禁令；HMAC；营业日历

## 2. 安全 / 租户 / 威胁模型

- 一切 query/tick 带 `workspace_id`；跨租户 404  
- 策略写：owner；run-due：member+（对齐 E42）  
- automation 在 breach 路径执行：沿用规则 ACL / 租户边界；`actor_user_id=None` 时注意 self-skip / 通知语义（与现 tick 一致）  
- pause_statuses 仅枚举合法 status，防任意字符串  
- `elapsed` / deadline 重算用 UTC naive 墙钟；防负分钟（`max(0, …)`）  
- 无进程内 cron；无营业时复杂注入

## 3. 非目标

- 营业时间 / 时区矩阵 / 节假日日历  
- first-response / resolution 等新 metric  
- 策略优先级 / IssueType 绑定 / 每项目覆盖  
- 多段 pause 的精细审计 UI（账本级 pause 历史表 YAGNI；单行累计足够）
- `sla_paused` / `sla_resumed` timeline 动作（Q4b；E46+ 可选）  
- 新 automation **action** 类型；breach 升级专用「pager」通道  
- Formula range/sort；WS 全局活动 feed；其它专用 webhook  
- Redis / 进程内 cron；远程 push / 开 PR / 自开 E46

## 4. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | 策略可设 `pauseStatuses`；非法 status 400；空=关闭暂停；跨 WS 404 |
| B | running → 入 pause 态 → `paused`；`run-due` 不 breach paused；已用分钟累加 |
| C | 离开 pause 回工作态 → `running` + `deadline_at` 按剩余重算；再耗尽可 breach |
| D | pause 中直接 stop/关闭 → `met`；stop 优先于 pause |
| E | breach → Inbox + webhook（回归）+ **automation** `issue.sla_breached` 执行动作；双跑不双火 |
| F | FE：pause 多选 + paused 徽标 + automation 触发项 |
| G | CLI **1.29.0** + pause 配置/展示 + version 断言 |
| H | 回归：E42 无 pause 策略行为不变；E44 webhook 可靠性；E43 formula 不 emit |
| 门禁 | BE 定向+全量绿（记 passed/skip；`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E46 |

## 5. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = **SLA v2 thin：pause + breach→automation**（方案 A） |
| D2 | 仍仅 metric=`time_in_status`；墙钟 UTC naive；**无**营业日历 |
| D3 | 状态优先级：**stop > pause > start**（同一次 sync） |
| D4 | 活跃钟 = `running|paused`；每 (issue,policy) 至多一条 |
| D5 | `run_due` **只**扫 `running`；paused 豁免违约 |
| D6 | 续跑：`deadline_at = now + (target - elapsed_before_pause)`；剩余≤0 → 保持 running 且 deadline≤now，下一次 tick breach |
| D7 | Automation trigger 名 = **`issue.sla_breached`**；动作复用既有 ACTION_TYPES |
| D8 | breach 路径：先落库 breached → Inbox → webhook → automations；后两者失败不回滚 breach |
| D9 | CLI **1.29.0**；全仓 version 断言同步 |
| D10 | 非目标见 §3；不 push；不自开 E46 |

## 6. 测试要点

- BE：policy 含 pause=`feedback`；in_progress→feedback → paused；elapsed>0；run-due 不 breach  
- BE：feedback→in_progress → running；deadline ≈ now+(target-elapsed)；拨 deadline 过去 + run-due → breached  
- BE：paused → resolved → met  
- BE：running → resolved 仍 met（无 pause 配置回归）  
- BE：breach 时 automation spy 含 `issue.sla_breached`；set_priority 落地；再 run-due 不双火  
- BE：跨 WS / 非法 pause status 400  
- FE：pauseStatuses；徽标 paused；trigger 常量  
- CLI：1.29.0；`--pause feedback`；issue 输出 paused  
- 回归：E42 clocks；E38 delay 规则若订 sla_breached；E44 deliveries；E43 no-emit

## 7. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Migration + model 字段 + CLOCK/TRIGGER 枚举（TDD）  
3. `sync_clocks` pause/resume + serialize（TDD）  
4. `run_due` → `fire_automations`（TDD）  
5. FE 设置 / 徽标 / automation 触发  
6. CLI 1.29.0  
7. 门禁 + acceptance tip  

## 8. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | automation trigger 用 `issue.sla_breached` 还是短名 `sla_breached`？ | **`issue.sla_breached`** |
| Q2 | 是否新增 `segment_started_at` 列，还是 pause 时用 `started_at` 差演算？ | **显式 `segment_started_at`**（迁移回填） |
| Q3 | pause 中 `deadline_at` 旧值：保留审计还是清空？ | **保留旧值**；resume 时覆盖 |
| Q4 | 进入 pause 时是否写 timeline？ | **否（Q4b）**；本轮仅时钟行 + 徽标，不做 `sla_paused`/`sla_resumed` timeline |
| Q5 | `feedback` 是否作为创建策略默认 pause？ | **否**；默认 `[]`，示例文档推荐 |
| Q6 | breach→automation 是否允许 `set_status` 绕回 start 造成震荡？ | **允许但文档警告**；本轮不加特殊禁令 |

---

## 附录 · 本轮未选但仍高 ROI（供 E46+）

1. **Formula range / sort-by-formula / Display 条件格式**（接 E43 等值过滤）。  
2. **WS 全局活动 feed**：产品化时间线（E41 CSV 已够审计导出）。  
3. **SLA 营业日历 / first-response metric / 策略优先级**。  
4. 其它专用 webhook（`issue.cycle_changed` / `estimate_changed`）。

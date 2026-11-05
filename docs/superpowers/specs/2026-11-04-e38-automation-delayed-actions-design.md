# E38 Design：Automation delayed / scheduled actions（延迟动作 + 外部 tick）

日期：2026-11-04（Asia/Shanghai）  
Epic：E38  
基线：`sprint/E37-S1` @ `faac64a`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E38-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E39**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E38-S1`。建议路径  
`docs/superpowers/specs/2026-11-04-e38-automation-delayed-actions-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E26 交付 Automations lite（即时 after-commit 执行）；E33/E36 加厚 CF 条件/动作与 `custom_field_changed`。**E26/E33/E36/E37 反复把「延迟 / cron / 多步流水线」标为非目标。**  
E35 已建立可复用模式：`POST …/run-due` **外部 tick**、UTC、无进程内 cron、单条失败隔离。

日常 Linear 缺口：规则匹配后「等 N 分钟再改状态 / 留言 / 设 CF」（SLA 升级、冷却期、跟进提醒），今日只能即时执行。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| A | 进程内 `asyncio.sleep` / APScheduler 在匹配时 sleep 再执行 | 请求挂起或常驻调度；与 E35「无内置 cron」冲突；难测、难水平扩展 |
| B | **匹配时若 `delay_minutes≥1` 写入 `automation_pending_actions`；`POST /api/automations/run-due` 外部 tick 到期执行**（采纳） | 对齐 E35；单测友好；运维用同一类 cron 调 recurrences + automations |
| C | 仅 CLI 本地 sleep 循环调即时 API | 无服务端语义；FE/Saved 规则不可靠 |

**拍板建议：B。**  
不做多步流水线 UI、不做 RRULE、不做 Inbox/email due digest（另候选）、不做公式字段、不做 webhook 新事件。

自检：无 TBD；延迟边界 / 到期再校验 / 防刷屏 / 租户 / CLI 1.22.0 已写清；单 sprint 可交付。

### 为何不是其它 E37 附录候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Due reminders + digest tick | 高 ROI，但叠 E27/E30 偏好与邮件面；宜独立 Epic |
| Formula custom fields | 求值安全面大，厚且易拖长 |
| Webhook `custom_field_changed` | 薄扩展（E29 events[]）；可插空做，不如解锁延迟工作流 |

## 1. 目标

成功标准：规则可配置延迟分钟数；匹配后入队而非立即执行；外部 `run-due` 到期执行既有 action；规则禁用/删除与 Issue 删除不留脏执行；跨租户隔离；FE/CLI 可配；CLI **1.22.0**。

### A · 数据模型 + 入队

- 新表 **`automation_pending_actions`**（名称可微调，ADR D1）：
  - `id` (uuid str)
  - `workspace_id` (FK workspaces, CASCADE)
  - `rule_id` (FK automation_rules, CASCADE)
  - `issue_id` (FK issues, CASCADE)
  - `action_type` (str，快照自规则)
  - `action_config_json` (JSON，**执行时用的 config 快照**；含业务字段，**不含**或剥离 `delay_minutes` 以免二次延迟)
  - `run_at` (DateTime UTC naive)
  - `status`：`pending` | `done` | `cancelled` | `failed`
  - `actor_user_id`（入队时的 actor / rule.created_by）
  - `error_message` (nullable text，failed 时)
  - `created_at` / `executed_at` (nullable)
  - 索引：`(workspace_id, status, run_at)`；`(rule_id, issue_id, status)` 辅助去重
- **`delay_minutes`**：存在 **`action_config_json.delay_minutes`**（int）；`0` / 缺省 / `null` → **即时**（现行路径，零行为变化）
  - 合法写范围：**1…10080**（7 天）；`<0` 或非 int 或 `>10080` → 规则 create/update **400**
  - 即时路径：匹配后仍直接 `_execute_action`（与今相同）
  - 延迟路径：匹配且条件通过后 **INSERT pending**（`run_at = now_utc + delay_minutes`），**不**立即执行 action
- **去重（防刷屏）**：同一 `(rule_id, issue_id)` 已有 `status=pending` 时：
  - **默认**：忽略新入队（保留原 `run_at`），记 debug log（ADR D4）
  - 不在本 Epic 做「刷新 run_at」开关
- 规则 **disable / delete**：将该规则下 `pending` → `cancelled`（delete 亦可靠 FK CASCADE 删行；disable 必须显式 cancel）
- Issue 删除：FK CASCADE 清 pending

### B · Tick：`POST /api/automations/run-due`

- 权限：**member+**（与 E35 run-due / E26 写一致）；强制 `X-Workspace-Id`；仅处理**当前 WS**
- 语义：选取 `status=pending AND run_at <= now(UTC)`，按 `run_at asc, created_at asc`；**一次 tick 每条 pending 最多处理 1 次**
- 单条流程：
  1. 加载 rule：若不存在 / `enabled=false` → 标 `cancelled`，跳过执行
  2. 加载 issue：若不存在或不属本 WS → `cancelled`
  3. **再匹配 `condition_json`**（对**当前** issue 状态）；不匹配 → `cancelled`（ADR D5：到期以真相为准，避免过期误伤）
  4. 调用既有 `_execute_action`（action_type + **快照** action_config，已无 delay）；成功 → `done` + `executed_at`；异常 → `failed` + `error_message`，**不阻断**同 tick 其它行
- 响应形状（对齐 E35 精神）：
  ```json
  {
    "processed": 3,
    "executed": 2,
    "cancelled": 1,
    "failed": 0,
    "errors": [{"pendingId":"…","ruleId":"…","issueId":"…","message":"…"}]
  }
  ```
- **不内置 cron**；文档注明可由外部与 `POST /api/recurrences/run-due` 一同调度
- 可选（薄）：`GET /api/automations/pending?status=pending` member+ 列表（分页可先 limit 100）；非必须若 FE 不做队列页——**建议做最小 list** 便于 CLI/验收

### C · FE `/workspace/automations`

- 创建/编辑动作区：增加 **「延迟（分钟）」** 数字输入（0=立即；占位说明最大 10080）
- 写入 `actionConfig.delayMinutes` 或 snake `delay_minutes`（BE 读写均接受 camel/snake，与 E33 风格一致）
- 列表摘要：若 delay>0，展示 `delay Nh/Nm → {action}`
- **不做**完整 pending 队列管理 UI（非目标可列为 Gaps）；可选在页顶展示「本 WS 待执行 N」若 B 提供 list
- 既有 trigger/condition/CF 编辑器不变

### D · CLI **1.22.0**

- `opentask automation run-due` → `POST /api/automations/run-due`
- `automation create|update`：`--action-config` JSON 已可带 `delay_minutes`；help 示例：
  - `opentask automation create --name 'SLA' --trigger issue.status_changed --action set_priority --action-config '{"priority":"high","delay_minutes":60}'`
- 可选：`automation pending` → list pending（若 API 有）
- version → **1.22.0**（全仓历史 version 断言同步 bump）

## 2. 数据模型（摘要）

**改：**无强制改 `automation_rules` 表结构（delay 进 action_config）。  
**增：**`automation_pending_actions`（§A）。  
**复用：**`AutomationService.run_for_event` / `_execute_action` / `_match_condition`；E26 depth 防环。

入队伪代码（匹配成功后）：

```
delay = parse_delay(rule.action_config_json)  # 0 = immediate
cfg_exec = strip_delay(rule.action_config_json)
if delay <= 0:
    await _execute_action(rule, issue, actor, config_override=cfg_exec)
else:
    if exists pending (rule_id, issue_id):
        return  # D4
    insert pending(run_at=utcnow()+timedelta(minutes=delay), action_type, action_config_json=cfg_exec, …)
```

## 3. API

| 面 | 行为 |
|----|------|
| 既有 automations CRUD | create/update 校验 `delay_minutes`；序列化原样回传 actionConfig |
| `POST /api/automations/run-due` | 见 §B |
| `GET /api/automations/pending`（建议） | query `status` 默认 `pending`；返回摘要列表 |
| 无 | 不改 issue 写路径公开契约；仅 executor 内部分流 |

权限：member+ 写与 run-due；viewer 读规则 OK、run-due/写 pending **403**；强制 `X-Workspace-Id`；跨租户 403/404。

## 4. FE

- Automations 表单：`delayMinutes` 控件 ↔ actionConfig
- `summarizeAutomationRule`：含 delay
- 不改 Board/List/CF 设置（E37 已交付）

## 5. CLI

- **1.22.0**
- `automation run-due` + help/测；version 断言全仓同步
- create 示例含 `delay_minutes`

## 6. 安全 / 租户

- pending 行强绑 `workspace_id`；run-due 只扫当前 WS
- 执行前再次确认 issue.workspace_id == pending.workspace_id
- actor：入队时快照的 `actor_user_id`；若空则 `rule.created_by`；再空则用调用 run-due 的用户（对齐 E35 D8 精神）
- 延迟执行走同一套 action 校验（CF 属本 WS、状态枚举等）；失败标 failed，不半写原则保持 E33
- **防环**：`_execute_action` 内 `automation_depth+=1` 行为不变；从 run-due 进入时 depth 默认 0，与「用户写后触发」一致——即延迟动作执行中产生的同步 after-commit 仍受 depth≥1 抑制二次规则（与今日即时路径同构）
- **不**在延迟动作成功后再自动入队同一规则（除非新的用户/同步事件再次匹配）；依赖 D4 去重

## 7. 非目标

- 多步流水线 / 可视化步骤图 / 条件分支链
- 进程内 cron、Celery beat、RRULE、workspace 时区矩阵（**一律 UTC**）
- Due date reminders / Inbox digest / 邮件 digest（E27/E30 附录另案）
- Formula CF；Webhook 事件集扩展（`custom_field_changed` outbound）
- 拖拽改 CF / multi_select 泳道（E37 非目标延续）
- pending 的人工「立即执行」按钮、改期 UI（可列 Gaps）
- 远程 push / 开 PR / 自开 E39

## 8. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | `delay_minutes` 校验；0=即时；≥1 入队；重复 pending 不双写；disable→cancel |
| B | `run-due` 到期执行；条件不再匹配→cancel；单条失败隔离；跨租户不泄漏 |
| C | FE 可设延迟并展示摘要 |
| D | CLI 1.22.0 + `automation run-due` + help/测 |
| 门禁 | BE 定向+全量绿（记录 passed/skip）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E39 |

## 9. ADR

| ID | 决定 |
|----|------|
| D1 | 新表 `automation_pending_actions`；delay 存在 `action_config.delay_minutes`，不新增 rules 列 |
| D2 | **不内置 cron**；外部 `POST /api/automations/run-due`；时区 **UTC naive** |
| D3 | `delay_minutes` ∈ 0…10080；写规则时非法 → 400；0/缺省=即时 |
| D4 | 同一 `(rule_id, issue_id)` 仅一条 `pending`；已有则跳过新入队 |
| D5 | tick 时 **重评 condition** + rule.enabled；失败/不匹配 → cancelled/failed，不执行 |
| D6 | 执行使用**入队时 action 快照**（type+config 去 delay）；规则日后改 action 不影响已入队行 |
| D7 | 防环复用 E26 `automation_depth`；run-due 入口 depth=0 |
| D8 | 一次 tick 对每条 due pending **最多尝试 1 次**；不在本 tick 内因失败自动重入队 |
| D9 | CLI **1.22.0**；全仓 version 断言同步 |
| D10 | 非目标见 §7；不 push；不自开 E39 |

## 10. 测试要点

- BE：即时路径回归（delay 0/缺省）；delay 入队 `run_at`；未到期 run-due 不执行；到期执行 set_status/add_comment/set_custom_field
- BE：条件失效 → cancelled；rule disable → cancelled；跨 WS 403；viewer run-due 403
- BE：重复触发同规则同 issue 不产生第二条 pending
- BE：非法 delay_minutes 400
- FE：表单读写 delay；摘要
- CLI：version 1.22.0；`automation run-due` help；config 含 delay 的 create 烟测（可 mock）
- 回归：无 delay 的 E26/E33/E36 规则行为不变

## 11. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Migration + pending model + 入队分流（TDD）  
3. `POST /api/automations/run-due`（+ 可选 pending list）  
4. FE delay 控件 + 摘要  
5. CLI 1.22.0  
6. 门禁 + acceptance tip  

---

## 附录 · 本轮未选但仍高 ROI（供 E39+）

1. **Due reminders + digest tick**：到期前 Inbox/email；`POST /api/…/run-due-reminders`；补 E27/E30 digest 非目标。  
2. **Formula custom fields**：只读计算列；独立厚 Epic（安全求值）。  
3. **Webhook `custom_field_changed`**：E29 events[] 扩展，接 E36 emit 出站（薄）。  

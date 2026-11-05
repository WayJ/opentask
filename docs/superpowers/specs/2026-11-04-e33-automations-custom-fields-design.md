# E33 设计：Automations × Custom Fields（加厚 E26）

日期：2026-11-04（Asia/Shanghai）  
Epic：E33  
基线：`sprint/E32-S1` @ `b5a7418`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E33-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E34**。

## 1. 目标

在 E26 自动化之上，让规则能 **按自定义字段条件匹配**，并能 **写入自定义字段**（E25/E32）。

### A · 条件 `customField`
- `condition_json` 增加键 `customField`（camel）/ `custom_field`（snake，等价）
- 形状：`{ key|fieldId|id, op, value? }`
- **ops**：`eq` | `neq` | `contains`（multi_select 成员包含；text 子串）| `is_set` | `is_empty`
- 与既有 `statusIn` / `priorityIs` / `hasLabel` **AND**
- 未知 field（本 WS 无此 key/id）→ **规则不匹配**，不 500
- 类型语义对齐 E25 `validate_value`；匹配失败当不匹配，不抛

### B · 动作 `set_custom_field`
- `ACTION_TYPES` 新增 `set_custom_field`
- `action_config`：`{ key|fieldId, value }`（`value: null` 清空）
- 走 `CustomFieldService.upsert_issue_values`；校验失败 **logger.warning**（execution log），rollback 脏会话，**不半写**、不回滚主写
- 保持 E26 防环：`automation_depth`；action 内 depth≥1；本期无 `custom_field_changed` 触发器，即便日后加也不会因 set CF 死循环

### C · FE
- `/workspace/automations`：条件区可选 CF（下拉 key）+ op + 值；动作可选 `set_custom_field` + CF + 值
- 列表增加摘要列（条件/动作含 CF 时展示 `cf:key op value` / `set cf:key=…`）
- 仍保留 JSON 高级编辑（与 helper 同步）

### D · CLI **1.17.0**
- `automation create|update`：`--condition` / `--action-config` JSON 已覆盖 CF；`ACTIONS` 含 `set_custom_field`
- 新增 `automation update RULE_ID`（可选 name/trigger/action/configs/condition/enabled）
- version → **1.17.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 条件键名主用 `customField`；兼容 `custom_field`；单对象即可（多 CF 条件本期不做数组） |
| D2 | op 固定五枚举；`contains`：multi=成员；text=子串；其余类型 `contains` 退化为 `eq` |
| D3 | 未知 field → match=False；归档字段：条件可读历史值；动作写入归档字段失败（E25 既有）并记 log |
| D4 | 动作名 `set_custom_field`（与 E26 snake 风格一致）；config 接受 `key` 或 `fieldId`/`field_id` |
| D5 | 防环仍靠 `automation_depth`；set_custom_field **不** 发新 trigger（本期非目标） |
| D6 | 校验失败只 log + return；不抛到 fire_automations 外层（与其它 action ValueError 路径一致：外层 catch） |
| D7 | FE：helper 控件写回 `conditionText`/`actionConfigText`；列表 `summarizeAutomationRule` |
| D8 | CLI 1.17.0；create 已支持 JSON；补 `update`；全仓 version 断言同步 bump |
| D9 | 不做多步流水线、cron、Webhook 新事件、公式字段、AI 派单；不 push；不自开 E34 |

## 3. 非目标

多步流水线、cron/延迟、出站 Webhook 新事件、公式字段、AI 派单、远程 push、E34。

## 4. 验收摘要

- 条件 CF ops + 未知 field 不匹配；`set_custom_field` + 校验失败不半写 + 防环
- FE 编辑器/摘要；CLI 1.17.0 create|update
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**

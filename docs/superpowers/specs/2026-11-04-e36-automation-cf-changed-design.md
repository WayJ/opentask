# E36 Design：Automation trigger `custom_field_changed`

日期：2026-11-04（Asia/Shanghai）  
基线：`sprint/E35-S1` @ `0945f73`  
状态：**Yuri 代审通过（design ok）**

## 1. 背景与目标

E33 已支持条件 `customField` 与动作 `set_custom_field`，但**无**「字段变更」触发器（acceptance Gaps）。本 Epic 补齐：当 Issue 自定义字段值变化时触发规则。

成功标准：改 CF → 匹配规则执行；`set_custom_field` 仍受 depth≤1 防环；跨租户安全；FE/CLI 可配置；CLI **1.20.0**。

## 2. 方案对比（Yuri 拍板）

| 方案 | 做法 | 取舍 |
|------|------|------|
| A | 仅在 `upsert_issue_values` / PATCH values 后发事件 | 覆盖主路径，实现小 |
| B | 通用 Issue domain event bus + 多订阅 | 过重 |
| C | 轮询 diff | 不可靠 |
| **选 A** | 在 CF 写入成功路径 emit `custom_field_changed`，自动化执行器订阅 | 与 E26 after-commit 一致 |

## 3. 设计

### 3.1 触发器
- `trigger.type = custom_field_changed`
- 可选过滤：`field_key` / `field_id`（空=任意 CF）；可选 `from`/`to`（空=不限）
- Payload：`issue_id`, `field_key`, `old_value`, `new_value`, `workspace_id`

### 3.2 条件（接 E33 Gaps）
- 允许同一规则多个 `customField` 条件 **AND**（数组，最多 5；超限 400）
- 单条件形态保持 E33 ops

### 3.3 执行与防环
- 沿用 depth≤1：本轮因 CF 变更触发的规则若再 `set_custom_field`，**不再**二次触发 `custom_field_changed`
- 其它 trigger（status 等）行为不变

### 3.4 API / FE / CLI
- 规则 CRUD schema 扩展；旧规则兼容
- FE Automations：触发器选「自定义字段变更」+ 字段下拉 + 可选 from/to；条件支持多条 CF
- CLI **1.20.0**：create/update 支持新 trigger；help 示例

### 3.5 权限与租户
- 与 E26 相同；字段必须属当前 workspace

## 4. 非目标

多步流水线、cron、Slack、公式字段、看板 CF 泳道、远程 push、自开 E37。

## 5. 测试要点

- 改 CF 触发；field 过滤；from/to；多条件 AND
- set_custom_field 不二次触发
- 跨租户；viewer 403
- FE/CLI 烟测；BE/CLI/FE 绿

## 6. ADR

| ID | 决定 |
|----|------|
| D1 | emit 点：CF upsert 成功 after-commit |
| D2 | 防环：CF-changed 触发链 depth≤1，禁二次 CF-changed |
| D3 | 多条件 AND，max 5 |
| D4 | CLI 1.20.0 |

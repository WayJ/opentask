# E25 设计：Issue Custom Fields（对齐 Linear lite）

日期：2026-11-04（Asia/Shanghai）  
Epic：E25  
基线：`sprint/E24-S1` @ `29ecfe5`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E25-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E26**。

## 1. 目标

### A · 字段定义（Workspace）
- 表 `custom_fields`：`id`、`workspace_id`、`name`、`key`（slug，WS 内唯一）、`type`（`text`|`number`|`single_select`|`multi_select`|`date`|`boolean`）、`options_json`（select 用）、`position`、`archived_at`、`created_by`、时间戳
- CRUD：`GET/POST /api/custom-fields`；`GET/PATCH/DELETE /api/custom-fields/{id}`
- owner/member 可写定义；viewer 读 OK、写 403
- **有取值时归档优于硬删**；无取值可硬删
- 强制 `X-Workspace-Id`；跨租户 403/404

### B · Issue 取值
- 表 `issue_custom_field_values`：`issue_id` + `field_id` + `value_json`（按 type 校验）；UNIQUE(issue_id, field_id)
- Issue **详情**默认带 `customFields: [{fieldId,key,name,type,value,options?}]`
- Issue **列表**默认不带；`?include=custom_fields` 才附带（防膨胀）
- `PATCH /api/issues/{id}/custom-fields` 批量 upsert（`values: [{fieldId|key, value}]`；`value=null` 清除）
- SmartSearch **本期不做** `field:value`

### C · 前端
- `/workspace/custom-fields`：定义 CRUD + 拖拽/按钮排序（position）
- Issue 详情可编辑区；创建页可选填（创建后 PATCH）
- **列表列展示本期不做**（ADR：仅详情，避免 DisplayOptions 大改）

### D · CLI
- `opentask custom-field list|create`
- `opentask issue set-field ISSUE KEY VALUE`
- version **1.9.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | `key` 规范化为小写 slug：`^[a-z][a-z0-9_-]{0,63}$`；创建时可从 name 自动生成；WS 内唯一（含已归档，避免复活冲突） |
| D2 | `options_json`：select 类型为 `[{value,label}]` 数组；`value` 稳定、`label` 展示；非 select 存 `[]` |
| D3 | 取值校验：`text`→str；`number`→int/float；`boolean`→bool；`date`→`YYYY-MM-DD` 字符串；`single_select`→options 内 value；`multi_select`→value 数组且 ⊆ options |
| D4 | 硬删：无 `issue_custom_field_values` 行时可 DELETE；有值 → 409，须先 archive（`archived_at`） |
| D5 | 归档字段：详情/列表取值仍可读历史值；新 PATCH 对归档字段 → 400；定义列表默认隐藏归档（`?includeArchived=true`） |
| D6 | Issue 详情默认带 `customFields`；列表默认不带，`include=custom_fields`（逗号分隔可扩）才带 |
| D7 | FE 路由挂在 Workspace 菜单 `/workspace/custom-fields`（与 labels/templates 同级）；不做 `/settings/*` 别名 |
| D8 | 列表列/DisplayOptions **本期不做**（成本高）；ADR 标明仅详情可编辑 |
| D9 | 创建 Issue：创建页拉字段定义，提交成功后若有填写再 `PATCH .../custom-fields`（不改 IssueCreate 契约，减耦合） |
| D10 | CLI **1.9.0**；`set-field` 支持 KEY-N / UUID；VALUE 对 multi_select 用逗号分隔；boolean 用 `true`/`false` |
| D11 | 不做公式/关联实体/字段级权限/Automations/Slack/Insights 深化/`field:` SmartSearch；不 push；不自开 E26 |

## 3. 非目标

公式字段、关联实体字段、字段级权限、Automations、Slack、Insights 深化、SmartSearch `field:value`、列表自定义列、远程 push、E26。

## 4. 验收摘要

- 字段定义 CRUD + 归档/硬删规则 + viewer 403 + 跨租户负例
- 取值类型校验；详情默认带；列表默认不带 / include 可带；批量 PATCH
- FE 设置页 + Issue 详情编辑；CLI 1.9.0
- BE/CLI pytest 绿；FE 不恶化；本地 tip；**不 push**

# E26 设计：Automations lite（Linear 式工作流规则）

日期：2026-11-04（Asia/Shanghai）  
Epic：E26  
基线：`sprint/E25-S1` @ `dfae2ae`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E26-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E27**。

## 1. 目标

### A · 模型与 API
- 表 `automation_rules`：`id`、`workspace_id`、`name`、`enabled`、`trigger_type`、`trigger_config_json`、`condition_json`（可选）、`action_type`、`action_config_json`、`created_by`、`position`、时间戳
- **Triggers**：`issue.created` | `issue.status_changed` | `issue.assignee_changed` | `label_added`
- **Actions**：`set_status` | `set_assignee` | `add_label` | `set_priority` | `add_comment`（`comment_type=system`，正文前缀 `[automation]` / meta 标明规则）
- CRUD：`GET/POST /api/automations`；`GET/PATCH/DELETE /api/automations/{id}`；`POST /api/automations/{id}/enable|disable`
- owner/member 可写；viewer 读 OK、写 403；强制 `X-Workspace-Id`；跨租户 403/404
- 执行器：对应写路径 **after commit** best-effort；失败 log、不回滚主写

### B · 条件（薄）
- `condition_json` 简单 AND：`statusIn: string[]`、`priorityIs: string`、`hasLabel: tagId|name`
- 无条件 / `null` / `{}` → 总匹配

### C · 前端 `/workspace/automations`
- 规则列表、开关、创建/编辑表单（trigger/action 下拉 + JSON/字段 config）
- 空状态；Workspace 侧栏子路由入口（与 custom-fields 同级）

### D · CLI
- `opentask automation list|create|enable|disable`
- version **1.10.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 单表 `automation_rules`；trigger/action 用固定枚举字符串；config 存 JSON |
| D2 | **防环**：`contextvars` `automation_depth`；用户写路径 depth=0 触发规则；执行 action 时 depth+=1；depth≥1 时不再二次匹配规则（单次请求深度≤1） |
| D3 | 执行器 best-effort：独立 try/except + 独立 commit（action 内再走既有 service）；主写已 commit；失败只记 log |
| D4 | `label_added` 挂在 TagService `attach_tag` 与 `replace_issue_tags` 新增标签路径；本仓库 Labels ≡ Tags |
| D5 | `add_comment` 用 `comment_type=system`，`meta_data={source:"automation", ruleId, ruleName}`，正文带 `[automation]` 前缀 |
| D6 | trigger_config：`issue.status_changed` 可选 `to`/`from`；`issue.assignee_changed` 可选 `to`；`label_added` 可选 `tagId`；`issue.created` 可空 |
| D7 | action_config：`set_status.status`；`set_assignee.assigneeId`；`add_label.tagId`；`set_priority.priority`；`add_comment.content` |
| D8 | condition：AND；`statusIn` / `priorityIs` / `hasLabel`（int id 或标签名）；全满足才跑 action |
| D9 | FE 路由 `/workspace/automations`（Workspace 菜单）；不做独立侧栏 Nav 组件 |
| D10 | CLI **1.10.0**；create 用 `--trigger` / `--action` / `--trigger-config` / `--action-config` / `--condition` JSON 字符串 |
| D11 | 不做多步流水线、延迟/cron、出站 Webhook、Slack、自定义脚本、AI 派单；不 push；不自开 E27 |

## 3. 非目标

多步流水线、时间延迟/cron、Webhook 出站、Slack、自定义脚本、AI 自动派单、远程 push、E27。

## 4. 验收摘要

- 规则 CRUD + enable/disable + viewer 403 + 跨租户
- 触发→动作（含防环）pytest；FE 页 + CLI 1.10.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**

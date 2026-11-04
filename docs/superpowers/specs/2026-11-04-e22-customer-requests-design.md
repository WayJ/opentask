# E22 设计：Customer Requests（对齐 Linear）

日期：2026-11-04（Asia/Shanghai）  
Epic：E22  
基线：`sprint/E21-S1` @ `4450441`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E22-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E23**。

## 1. 目标

### A · Customers
- Workspace 级 Customer：`name`、`domains[]`（可选 JSON）、`external_url`、`notes`、`created_by`
- CRUD API；独立 `/customers` 列表 + detail；侧栏「客户」入口（类 Linear IA）
- viewer 只读；强制 `X-Workspace-Id`；跨租户 403/404

### B · Requests
- CustomerRequest：`title`、`body`、`customer_id`、`status`（`open`/`completed`/`canceled`）、`priority` 可选、`created_by`
- CRUD；列表可按 `customer_id` / `status` / `issue_id` 筛
- **关联 Issue**：链接表 `customer_request_issues`（M2M）；Request 详情挂/解挂；Issue 详情显示关联 Requests（有则显示）
- 新建 Request 可「创建并链到新 Issue」（预填标题 = request.title）

### C · 产品面
- Issue 详情轻量「客户需求」区（count>0 才显示）
- Customers / Requests 空状态引导
- 不做 SLA / 邮件入箱自动建 / 公开门户

### D · CLI（薄）
- `customer list|create`、`request list|create|link-issue`；version **1.7.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | `customers.domains` 用 JSON list（跨 SQLite/PG）；空数组默认 |
| D2 | Request↔Issue 用独立链接表 `customer_request_issues(request_id, issue_id)`，CASCADE；同 WS 校验 |
| D3 | 创建 Request 时 `createAndLinkIssue=true` → 调 `IssueService.create_issue`（title=request.title，description=body），再写链接行；可选 `projectId` |
| D4 | 写操作 `require_writer`（owner/member）；viewer 读 OK、写 403 |
| D5 | 跨租户：实体不在当前 WS → **404**（不泄露存在性）；缺 `X-Workspace-Id` 由既有 deps 拒绝 |
| D6 | 路由：`/api/customers`、`/api/customer-requests`；FE `/customers`、`/customers/detail`、`/requests`、`/requests/detail` |
| D7 | Issue 详情：`GET /api/customer-requests?issue_id=`；仅当 total>0 渲染区块 |
| D8 | priority 可选，取值对齐 Issue：`low`/`medium`/`high`/`urgent` 或 null |
| D9 | CLI 1.7.0 最小集；`request link-issue <request_id> <issue_id|KEY-N>` |
| D10 | 不做 Insights/WS 实时/Slack/自定义字段/自动化/评论 Reactions/`label:` BE；不 push；不自开 E23 |

## 3. 非目标
Insights 图表、WebSocket 实时、Slack、自定义字段、自动化、评论 Reactions、`label:` BE 参数、远程 push、SLA、邮件门户。

## 4. 验收摘要
- Customers/Requests CRUD + 跨租户负例 + viewer 只读
- Request↔Issue 挂解挂；createAndLinkIssue；Issue 详情有则显示
- FE 列表/空状态/侧栏；CLI 1.7.0
- BE/CLI pytest 绿；FE lint/build/相关 vitest 不恶化；本地 tip；**不 push**

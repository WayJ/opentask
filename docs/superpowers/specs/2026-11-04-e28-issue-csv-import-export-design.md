# E28 设计：Issue CSV Import / Export

日期：2026-11-04（Asia/Shanghai）  
Epic：E28  
基线：`sprint/E27-S1` @ `be27e7d`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E28-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E29**。

## 1. 目标

### A · Export
- `GET /api/issues/export.csv`：当前 WS + 与 list 同常用过滤（status / assignee / cycle / project / search / priority / type）
- 列：`issue_code,title,status,priority,assignee_email,reporter_email,labels,cycle,estimate,due_date,created_at,updated_at`
- viewer+ 可导出；强制 `X-Workspace-Id`；上限 **10000** 行；`StreamingResponse` text/csv

### B · Import
- `POST /api/issues/import` multipart `file`；member+（viewer 403）
- 列映射：title 必填；可选 status/priority/assignee_email/labels/due_date/estimate/issue_code
- `issue_code` 本 WS 已存在 → 更新；不给或未命中 → 创建并分配新 KEY-N
- 返回 `{created,updated,errors:[{row,message}]}`；单行失败不阻断；整文件非法 400
- assignee 须为本 WS 成员，否则该行 error

### C · FE
- Issue 列表：Export 下载；Import 对话框（选文件 + 结果摘要）；模板 CSV 下载

### D · CLI
- `issue export [--out file.csv]`、`issue import file.csv`；version **1.12.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 导出路径固定 `GET /api/issues/export.csv`；模板 `GET /api/issues/import/template.csv`；导入 `POST /api/issues/import`（multipart 字段名 `file`） |
| D2 | `assignee_email` / `reporter_email` 列语义 = 本地 **username**（UserModel 无 email；OAuth 映射同此）；导入按 username 大小写不敏感解析，且须为本 WS 成员 |
| D3 | `estimate` ↔ `estimate_points`；`labels` = 本 WS Tag 名，`;` 或 `,` 分隔；缺失标签 **find-or-create**；`cycle` = Cycle.name（本 WS 精确匹配，找不到则该行 error） |
| D4 | Upsert：给定 `issue_code` 且本 WS 未删除命中 → update 可变列；空 code 或未命中 → create + `_generate_issue_code`（未命中的外部 code **忽略**，避免跨租户撞全局唯一码） |
| D5 | Export 上限 `EXPORT_MAX_ROWS=10000`；超限截断并在 CSV 首注释行标明（或仅截断；ADR：静默截断至 10k，响应头 `X-Export-Truncated: true`） |
| D6 | viewer 可 export / 下模板；import 需 owner/member（复用 `require_writer`） |
| D7 | 过滤与 list 对齐的 query：`status,priority,type,project_id,assignee_id,cycle_id,search`；`assignee_id=me` 解析为当前用户 |
| D8 | FE：列表头 Export / Import；Import 用 `NModal`+文件选择；API 经 `downloadRequest`（补 X-Workspace-Id）与 multipart `request` |
| D9 | CLI 1.12.0；`issue export` 写 stdout 或 `--out`；`issue import` 打印 created/updated/errors |
| D10 | 非目标：Jira/Linear 同步、附件、自定义字段列、Slack；不 push；不自开 E29 |

## 3. 非目标

Linear/Jira API 同步、附件导入、自定义字段列、Slack、远程 push、E29。

## 4. 验收摘要

- Export 列与过滤 + 租户；Import 创建/更新/错误行/权限；模板
- FE 列表入口；CLI 1.12.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**

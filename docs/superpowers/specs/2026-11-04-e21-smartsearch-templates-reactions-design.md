# E21 设计：SmartSearch 驱动列表 · Templates · Reactions · 选中序 · CLI

日期：2026-11-04（Asia/Shanghai）  
Epic：E21  
基线：`sprint/E20-S1` @ `db9c87b`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E21-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E22**。

## 1. 目标

### A · SmartSearch 真正驱动列表
- `IssueSmartSearch` 解析 `assignee:@me` / `assignee:me` / `is:open|closed|…` / `label:` / `priority:` / `type:` / `cycle:` / `project:` / KEY-N 等，**落到** list API 查询参数（及既有 filters），不再把 assignee 塞进 search 字符串装饰。
- URL/`q`（及兼容的 cycle_id/scope）可深链复现；清空恢复默认。
- 去掉 `describe.skip('IssueSmartSearch…')`，vitest 绿。

### B · Templates 创建流打磨
- 创建页 `IssueTemplateSelector`：工作区模板 API 优先，静态 `ISSUE_TEMPLATES` fallback（ADR）。
- Alt+C → `/issue/create?pickTemplate=1`；`?templateId=` 预填保留。
- 去掉 TemplateSelector skip，vitest 绿。

### C · Reactions 复活
- 详情 `IssueReactions` 接现有 `/api/issues/{id}/reactions`（已有 store）；本期 **仅 Issue 级**。
- 去掉 Reactions skip，vitest 绿。

### D · Shift+X order 正规化
- 废除 `window.__opentaskIssueOrder`；在 `useIssueSelection` 同模块注册有序 id；list/board 均注册。

### E · CLI（薄）
- `issue list` 补 `--cycle`（对齐 SmartSearch `cycle:`）；version **1.6.0**。
- 既有 `--status/--priority/--type/--mine/--watching` 等已对齐，补测/文档。

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | `assignee:@me` / `assignee:me` → API `assignee_id=me`；裸 `@me` 同义 |
| D2 | `is:open`/`is:closed`/具体状态 → `filters.status` + API `status`；同时同步 tab（open/closed/all）作 UX |
| D3 | `label:`：**客户端**按 `tags[].name` 过滤（BE list 无 tag 参数）；不扩 BE 本 Epic |
| D4 | `cycle:` → `cycle_id`（支持 `__none__`）；`project:` → `project_id` |
| D5 | KEY-N（`/^[A-Za-z][A-Za-z0-9]*-\d+$/`）写入 `search`，复用现有 code/title 搜索 |
| D6 | 深链：`q`=原始搜索串；进入页 parse→apply；清空清 `q` 与相关 filter |
| D7 | 模板：WS API 有 rows 用 API；否则静态 ISSUE_TEMPLATES；Alt+C 打开选择器 |
| D8 | Reactions：仅 Issue 级；无 CommentReaction 模型，不做评论反应 |
| D9 | 有序 id：`useIssueSelection.setIssueOrder / getIssueOrder`；热键读 composable |
| D10 | CLI 1.6.0 加 `--cycle`；中文 docs；不 push；不自开 E22 |

## 3. 非目标
- Customer Requests / Insights / WebSocket / Slack
- 自定义字段 / 自动化 / 远程 push
- 换主题令牌；评论级 Reactions；BE label 过滤参数

## 4. 验收摘要
- SmartSearch 改 filter 后列表请求带对应 query；深链可复现；清空恢复
- 三类 describe.skip 去掉且 vitest 绿
- Alt+C / templateId 预填可用；Reactions 详情可点
- Shift+X 不依赖 window 全局；看板同样
- CLI 1.6.0 + `--cycle`；BE/CLI pytest 绿；本地 tip；**不 push**

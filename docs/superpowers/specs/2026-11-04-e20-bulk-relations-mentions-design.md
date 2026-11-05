# E20 设计：多选 Bulk · Relations 阻塞徽章 · Mentions/IssueReference

日期：2026-11-04（Asia/Shanghai）  
Epic：E20  
基线：`sprint/E19-S1` @ `f78d5ff`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E20-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E21**。

## 1. 目标

### A · 多选 + Bulk
- 列表/看板：键盘 **X** 切换当前焦点行选中；**Shift+X** 可选范围扩选（相对上次锚点）
- 选中后底栏 Bulk：改状态 / 指派 / 优先级 / Cycle / Labels（Tags）
- **Esc** 清空选中；输入框内忽略单键 X（`ignoreWhenEditable`）
- 复用并扩展 `POST /api/issues/bulk/update`：新增 `cycle_id`、`tag_ids`

### B · Relations 呈现
- 列表/看板卡片轻量 **blocks / blocked-by** 徽章；点击进详情 Relations 区
- 列表 payload 附 `blocks_count` / `blocked_by_count`
- 详情 Relations：可读可增删（对齐现有 Relation API）；跨租户负例保持

### C · Mentions / IssueReference（收 E18 skip）
- 复活 `UserMention.vue` / `IssueReference.vue`
- Markdown 渲染自动识别 `@user` 与 Issue code（`KEY-N` / `#CODE`）
- 评论区可用；去掉 `describe.skip`；相关 vitest 绿

### D · CLI（薄）
- `issue bulk-update` 最小命令；relations 已有则只补测/文档
- version **1.5.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | Bulk 扩展字段：`cycle_id`（可 `null` 清空）、`tag_ids`（整表替换；省略则不改标签） |
| D2 | Bulk 路由加 `require_workspace_context`：只更新本 WS 内且调用者有成员资格的 ID；越权 ID 忽略或整体 403（**采用：过滤后更新，返回实际 affected；全无权限则 403**） |
| D3 | 阻塞计数：`blocks`=as_source.blocks + as_target.is_blocked_by；`blocked_by`=as_source.is_blocked_by + as_target.blocks |
| D4 | 选中态用模块单例 composable（同 `useIssueFocus`），列表离开可 clear |
| D5 | Mentions 组件负责展示；解析正则与 BE `_MENTION_RE` / issue_code 对齐；Inbox @ 已有不重做 |
| D6 | 中文 docs；不 push；不自开 E21 |

## 3. 非目标
- Slack/邮件、Customer Requests、Insights、WebSocket
- 自定义字段 / 自动化引擎
- 换主题令牌、远程 push

## 4. 验收摘要
- X/Esc 多选 + Bulk 五项可改；跨租户 ID 不误改
- 列表/看板见阻塞徽章；详情可 CRUD relation
- UserMention / IssueReference 测绿；E18 skip 去掉
- CLI 1.5.0 bulk-update 绿；BE/CLI pytest 绿；相关 vitest 绿
- 本地 tip；**不 push**

# E23 Acceptance

状态：进行中  
分支：sprint/E23-S1  
基线：82795db  
tip：（收口补）

## Checklist
- [ ] A `/ws/workspace` + issue.*/inbox.created/comment.created；best-effort publish；跳过 actor
- [ ] B `useWorkspaceRealtime`；Inbox / Issue 列表·详情刷新；断线极简提示
- [ ] C 非成员/坏 token 拒绝；跨租户不串
- [ ] D CLI 保持 **1.7.0**（无用户可见契约）；README 注明
- [ ] BE/CLI 绿；FE 相关测不恶化；未 push；不自开 E24

## 测试数
- BE：（收口）
- CLI：（收口）
- FE：（收口）

## ADR 摘要
D1–D9 见 design：独立 `/ws/workspace`；query token+workspace_id；跳过 actor；inbox FE 自过滤；CLI 1.7.0。

## Gaps / 非目标（刻意不做）
Insights / Slack / 自定义字段 / 自动化 / Customer 深化 / 评论 Reactions / Agent hub 重写 / Redis 跨进程 / 远程 push / E24。

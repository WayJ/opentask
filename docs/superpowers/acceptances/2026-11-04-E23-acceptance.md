# E23 Acceptance

状态：齐套  
分支：sprint/E23-S1  
基线：82795db  
tip：24af4d15696f50c2931923ad21bb5bb33d012adc

## Checklist
- [x] A `/ws/workspace` + issue.*/inbox.created/comment.created；best-effort publish；跳过 actor
- [x] B `useWorkspaceRealtime`；Inbox / Issue 列表·详情刷新；断线极简提示（Header ●）
- [x] C 非成员/坏 token 拒绝；跨租户不串
- [x] D CLI 保持 **1.7.0**（无用户可见契约）；README 注明不接 WS
- [x] BE/CLI 绿；FE vitest/lint/build 不恶化；未 push；不自开 E24

## 测试数
- BE：857 passed, 24 skipped（E22 850 + E23 realtime 7）
- CLI：423 passed, 89 skipped（保持 1.7.0）
- FE：231 passed（E22 229 + realtime helpers 2）；lint 既有 10 errors 未新增；`npm run build` 成功

## ADR 摘要
D1–D9 见 design：独立 `/ws/workspace`；query token+workspace_id；跳过 actor；inbox FE 自过滤；CLI 1.7.0。

## Gaps / 非目标（刻意不做）
Insights / Slack / 自定义字段 / 自动化 / Customer 深化 / 评论 Reactions / Agent hub 重写 / Redis 跨进程 / 远程 push / E24。

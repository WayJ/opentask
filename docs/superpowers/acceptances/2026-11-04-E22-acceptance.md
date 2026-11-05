# E22 Acceptance

状态：齐套  
分支：sprint/E22-S1  
基线：4450441  
tip：2e6a8f0e92020c45c6fcaee8e77268f3c0652e30

## Checklist
- [x] A Customers CRUD + `/customers` + 侧栏 CustomersNav；viewer 只读；跨租户 404
- [x] B Requests CRUD + 筛 customer/status/issue；M2M `customer_request_issues`；createAndLinkIssue；挂/解挂
- [x] C Issue 详情「客户需求」区（有则显示）；Customers/Requests 空状态
- [x] D CLI **1.7.0** `customer list|create`、`request list|create|link-issue`
- [x] BE/CLI 绿；FE vitest/lint/build 不恶化；未 push；不自开 E23

## 测试数
- BE：850 passed, 24 skipped（E21 843 + E22 客户/需求 7）
- CLI：423 passed, 89 skipped（E21 420 + E22 help/version 3）
- FE：229 passed（全量 vitest）；lint 既有 10 errors 未新增；`npm run build` 成功

## ADR 摘要
D1–D10 见 design：domains JSON；链接表 M2M；createAndLinkIssue→Feature Issue；viewer 只读；跨租户 404；CLI 1.7.0。

## Gaps / 非目标（刻意不做）
Insights / WebSocket / Slack / 自定义字段 / 自动化 / 评论 Reactions / `label:` BE / SLA / 邮件入箱 / 公开门户 / 远程 push。

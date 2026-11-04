# E31 Acceptance：Public Issue Forms

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E31-S1`  
基线：`sprint/E30-S1` @ `06885b5`

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A 模型+CRUD+公开 API | ✅ | `issue_forms`；`/api/forms` CRUD + regenerate-token；`/api/public/forms/{token}` schema/submit |
| B 字段校验 | ✅ | title/description/priority/labels/assignee/custom_field/customer_id；字段级 errors；禁用/未知 404 |
| C FE settings + `/f/:token` | ✅ | `/settings/forms`；blank 公开页；复制链接/重生 token |
| D CLI 1.15.0 | ✅ | `form list\|create\|update\|delete\|url` |

## ADR 摘要
见 `docs/superpowers/specs/2026-11-04-e31-public-issue-forms-design.md` D1–D11。

要点：写=owner / 读=member+；公开无鉴权；submit actor=`created_by`；rate-limit 可 `OPENTASK_FORM_RATE_LIMIT=0` 关闭；可选 `createCustomerRequest`+`customer_id` 建 Request。

## 测试
- BE pytest：**901 passed** / 24 skipped（全量一次跑中 `test_user_search` jira wire 偶发失败，单跑复测绿；E31 新增 `test_issue_forms` 4P）
- CLI：**449 passed** / 89 skipped
- FE vitest：**252 passed**

## tip
- SHA：`sprint/E31-S1` tip（以 `git rev-parse HEAD` 为准）
- 未 push / 未开 PR
- **不自开 E32**

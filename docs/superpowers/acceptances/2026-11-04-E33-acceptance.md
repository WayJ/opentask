# E33 Acceptance：Automations × Custom Fields

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E33-S1`  
基线：`sprint/E32-S1` @ `b5a7418`

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A 条件 customField + ops | ✅ | `eq`/`neq`/`contains`/`is_set`/`is_empty`；camel+snake；未知 field → 不匹配不 500；与 status/priority/label AND |
| B 动作 set_custom_field | ✅ | 预校验后 upsert；失败 logger.warning；不半写、不污染主请求 session；防环 depth≤1 |
| C FE 编辑器 + 摘要 | ✅ | CF 下拉/op/值 helper；`set_custom_field` 动作；列表摘要列 |
| D CLI 1.17.0 | ✅ | ACTIONS+`set_custom_field`；`automation update`；`--condition`/`--action-config` JSON |

## ADR 摘要
见 `docs/superpowers/specs/2026-11-04-e33-automations-custom-fields-design.md` D1–D9。

要点：条件键 `customField`；动作 `set_custom_field`；未知 field 不匹配；校验失败只 log；CLI 1.17.0。

## 测试
- BE pytest：**911 passed** / 24 skipped（全量一次跑中 `test_user_search` jira wire 偶发失败，单跑复测绿；E33 新增 `test_e33_automations_custom_fields` 7P）
- CLI：**455 passed** / 89 skipped
- FE vitest：**259 passed**；`pnpm build` 成功

## tip
- SHA：以 `git rev-parse HEAD` 为准（本文件提交后 tip）
- 未 push / 未开 PR
- **不自开 E34**

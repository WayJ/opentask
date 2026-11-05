# E32 Acceptance：Custom Fields surfaces

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E32-S1`  
基线：`sprint/E31-S1` @ `6923085`

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A BE list `cf.<key>` 过滤 | ✅ | `cf.<key>=value` + 兼容 `cf=key=value`；类型 eq / multi contains；未知 key 空结果；跨租户隔离 |
| B SmartSearch `field:key:value` | ✅ | 主语法 `field:`，别名 `cf:`；落入 list `cf.*`；`?q=` 深链 |
| C Display 列 + list 渲染 | ✅ | `display_json.custom_field_keys`；面板勾选；列表动态列 + `include=custom_fields` |
| D CLI 1.16.0 `--cf` | ✅ | `issue list --cf key=value`（可重复） |

## ADR 摘要
见 `docs/superpowers/specs/2026-11-04-e32-custom-fields-surfaces-design.md` D1–D8。

要点：过滤用 `cf.<key>`；SmartSearch `field:key:value`；无效 key → 空集不 400；prefs 扩展 `custom_field_keys`；CLI 1.16.0。

## 测试
- BE pytest：**904 passed** / 24 skipped（全量一次跑中 `test_user_search` jira wire 偶发失败，单跑复测绿；E32 新增 `test_e32_custom_field_filters` 3P）
- CLI：**451 passed** / 89 skipped
- FE vitest：**255 passed**；`pnpm build` 成功

## tip
- SHA：`sprint/E32-S1` tip（以 `git rev-parse HEAD` 为准）
- 未 push / 未开 PR
- **不自开 E33**

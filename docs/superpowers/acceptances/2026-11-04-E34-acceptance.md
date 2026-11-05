# E34 Acceptance：CSV × Custom Fields

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E34-S1`  
基线：`sprint/E33-S1` @ `c1764e2`

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A Export `cf.<key>` | ✅ | 未归档字段按 position/created；过滤/10k/`X-Export-Truncated` 不变；无值空单元格 |
| B Import + 模板 | ✅ | 动态模板列头；类型校验；未知/非法 CF → `errors[]` partial，主字段仍计 created/updated；空单元格跳过 |
| C FE 文案/模板 | ✅ | Import 说明含 `cf.*`；模板 API 含当前 CF 列 |
| D CLI 1.18.0 | ✅ | export/import help 提 `cf.<key>`；version 1.18.0 |

## ADR 摘要
见 `docs/superpowers/specs/2026-11-04-e34-csv-custom-fields-design.md` D1–D9。

要点：列名 `cf.<key>`；未知/校验失败 CF partial success；空单元格跳过；boolean=`true`/`false`；multi=逗号；CLI 1.18.0。

## 测试
- BE pytest：**915 passed** / 24 skipped（全量一次跑中 auth/oauth2/vcs 等 22 条偶发失败，单跑复测全绿；E34 新增 `test_e34_csv_custom_fields` 3P；既有 `test_issue_csv` 3P 仍绿）
- CLI：**458 passed** / 89 skipped
- FE vitest：**260 passed**；`pnpm build` 成功

## tip
- SHA：以 `git rev-parse HEAD` 为准（本文件提交后 tip）
- 未 push / 未开 PR
- **不自开 E35**

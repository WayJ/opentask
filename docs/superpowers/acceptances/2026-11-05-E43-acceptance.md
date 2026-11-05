# E43 Acceptance：Formula surfaces v1

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E43-S1`  
基线：`bf57338`  
tip：`f98806d`

## 范围（已交付）
- **A** `coerce_cf_filter_value` 按 `formula_result_type` coerce；`apply_list_filters` 公式键不走 `IssueCustomFieldValue` SQL；批求值等值；null/error 不命中；与 number CF AND；cap 2000 → 400 `formula_filter_too_broad`
- **B** 表 `issue_formula_cache`（migration `j6e7f8a9b0c4`）；依赖 CF upsert / issue attrs / formula 定义变更 → 刷新或失效；**禁止** emit；过滤优先 cache，miss 回退求值回填；详情仍 `values_for_issues`（Q1）
- **C** SmartSearch `field:`/`cf:` 后端即生效；FE 建议文案补公式示例；分组/泳道选项标「计算值·只读」
- **D** BE prefs 允许 formula（result∈{number,text,boolean}）；FE `isGroupingCfType`；error→`__error__` / 空→`__empty__`；formula 泳道只读（跨泳道拖拽按 lane 隔离）
- **E** 未知/归档公式 → 空；跨 WS 不泄漏
- **F** CLI **1.27.0**；`--cf` help 注明 formula；全仓 version 断言已同步
- **G** 数据模型 + 写路径挂钩齐套

## ADR（落地）
- 延续 E40：不 emit；批求值/cache 等值；cap **2000**；cache 仅过滤；error 独立桶；等值 only；不 push / 不 E44

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1004 passed**, 1 failed（已知 flake `test_user_search`）, 24 skipped |
| CLI | **492 passed**, 89 skipped |
| FE vitest | **294 passed**（44 files） |
| FE build | **ok**（vite prod） |
| E43 专测 | BE `test_e43_formula_surfaces` 11P；CLI `test_e43_formula_surfaces` 2P |

## Gaps / 非目标（刻意不做）
- 物化进 `issue_custom_field_values` / 因公式结果 emit
- rollup / 脚本 / range / sort-by-formula
- SLA v2 / webhook 事件包 / 全局 feed
- push / PR / E44

## superpowers
`design/plan/TDD/verify/acceptance = ok`

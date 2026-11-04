# E37 Acceptance：Board / List CF 泳道

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E37-S1`  
基线：`ac42210`（E36 tip + E37 design）

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A prefs/views `cf:<key>` | ✅ | normalize 接受形态；写路径校验 WS+类型；非法 400；读非法回退 none；并入 custom_field_keys |
| B FE Board/List 分桶 | ✅ | groupIssuesBy/boardSwimlanes 支持 cf:；single_select/boolean/text|number|date；空桶 __empty__；Display 下拉含允许类型 CF；选中自动 include |
| C BE 薄校验 | ✅ | 复用 CF list；负例 unknown/archived/multi_select/跨租户 → 400；无新聚合 API |
| D CLI 1.21.0 | ✅ | `--group-by` 接受系统值或 cf:<key>；help 示例；version 1.21.0 |

## ADR
| ID | 决定 |
|----|------|
| D1 | 编码 `cf:<field_key>` |
| D2 | 允许 single_select/boolean/text/number/date；禁 multi_select |
| D3 | 写严格 400；读非法 → none |
| D4 | 矩阵客户端计算 |
| D5 | 拖拽不改 CF |
| D6 | CLI 1.21.0 |
| D7 | 非目标见 design §7；不 push；不自开 E38 |

## TDD
- 红：prefs 丢弃 cf: / 不 400；FE isGroupByKey/分桶失败；CLI 仍 1.20.0（已跑）
- 绿：`tests/api/test_e37_board_cf_swimlanes.py` **5P**；FE utils 增测绿；`tests/test_e37_cf_group_by.py` **3P**

## 测试
- BE pytest：**934 passed** / 24 skipped（全量一次跑中 `test_tasks_jira_wire::test_user_search` 1 条偶发失败，单跑复测绿；与 E37 无关）
- CLI：**466 passed** / 89 skipped
- FE vitest：**273 passed**；`pnpm/vite build` 成功

## 非目标（未做）
- multi_select 泳道 / 拖拽改 CF / 公式字段 / 服务端预聚合矩阵 / E38

## tip
- SHA：`b752db9`（`git rev-parse HEAD` = `b752db9203234ba1f2a767870d3662fb1bafbc64`）
- 未 push / 未开 PR
- **不自开 E38** · **STOP 待命**

`superpowers: design/plan/TDD/verify/acceptance = ok`

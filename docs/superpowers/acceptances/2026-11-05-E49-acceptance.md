# E49 Acceptance：Formula Display v2 — color scale + icon sets · CLI 1.33.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E49-S1`  
基线：`39b2f79`  
**tip：** `7115b92`（全文 `7115b92235b285e4697e4c4288256309f4d7b1a9`）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A colorScales[] | ✅ | 独立数组；≤5；手动 min/max；palette=`blue_red\|green_red\|mono\|yellow_blue\|purple_green`；field=`cf:*\|due_date\|estimate_points`；target cell\|row；客户端线性插值 |
| B iconSets[] | ✅ | 独立数组；≤5 sets × ≤8 rules；icon 枚举 Q5a；非法 icon 丢弃；cell 前缀（List 列 + Board 标题） |
| C BE normalize | ✅ | `normalize_display_json` + 写路径超限 400（`color_scales_too_many` / `icon_sets_too_many`）；与 E46 tint 并存；**无 migration** |
| D FE | ✅ | Display Options 色阶/图标集编辑器；List/Board `resolveRowBackground`（tint > scale）；vitest helpers |
| E CLI 1.33.0 | ✅ | pyproject + `__init__` + setup + `VERSION` + `opentask_cli.VERSION` 全钉；历史断言同步；`test_e49_display_v2` |
| F no-emit | ✅ | Display PUT/GET spy：`fire_webhooks` / `fire_automations` 未调用 |

## ADR 确认
- D1 Epic=Display v2 · D2 独立数组（Q1a）· D3 手动 domain + 固定 palette + tint>scale（Q2a/Q3a/Q4a）· D4 icon 小枚举（Q5a）· D5 无 migration（Q6a）· D6 仅 number/date 客户端求值 · D7 CLI **1.33.0** · D8 no-emit / 不 push / 不自开 E50

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1057 passed**, 24 skipped；1 fail `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` = **已知 flake**；定向 E49+E46 **6P**（E49 `test_e49_*` **4P**） |
| CLI | **509 passed**, 89 skipped；`test_e49_display_v2` **3P**；pins 全 **1.33.0** |
| FE | vitest **315 passed**（45 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- domain auto；自由 CSS/任意 hex；自定义 URL/SVG 图标；专用 cycle/estimate/sla_paused webhook；SLA 营业日历；Activity 加厚；Formula emit；Redis/cron；push/PR/E50
- Display Options 色阶/图标编辑器为「添加默认样例 + 删除」薄 UI（无逐字段表单控件）；完整可视化编辑可后续加厚
- Saved View 应用路径仍未单独回填 colorScales/iconSets 到会话 state（与 E46 conditionalFormats 同口径：个人 prefs 路径完整；View `display_json` 经 BE normalize 可存）

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；**无 push / 无 PR / 不自开 E50**

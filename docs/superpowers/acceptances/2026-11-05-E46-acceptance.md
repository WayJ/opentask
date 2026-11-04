# E46 Acceptance：Formula query surfaces v2

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E46-S1`  
基线：`b5b132e`  
**tip（收口填写；若滞后以 HEAD 为准）：** _pending_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A Range ops | □ | `cf.<key>[op]=`；stored+formula number/date；unsupported 400 |
| B Sort cf: | □ | nulls last；cap 2000；saved view sort_json |
| C conditionalFormats | □ | ≤10；枚举 tint；客户端；先匹配先赢；不进 CSV |
| D FE | □ | 比较符芯片；sort 菜单；Display 编辑；List/Board tint |
| E CLI 1.30.0 | □ | pyproject+`__init__`+setup(+VERSION) 全钉；SmartSearch 薄 |
| F 无新表 | □ | ADR D7 |

## ADR
- D1 surfaces v2 · D2 no-emit · D3 range number/date · D4 sort cap/nulls last · D5 formats≤10 · D6 Q1a/Q2a · D7 无 migration · D8 CLI 1.30.0 · D9 非目标

## 门禁（收口填）
- BE：_pending_
- CLI：_pending_
- FE vitest+build：_pending_
- known flake：`test_user_search`（若出现）

## 流程
- superpowers: design/plan/TDD/verify/acceptance = _pending_
- **无 push / 无 PR / 不自开 E47 / STOP**


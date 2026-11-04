# E49 Acceptance：Formula Display v2 — color scale + icon sets · CLI 1.33.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E49-S1`  
基线：`39b2f79`  
**tip：** _pending_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A colorScales[] | ⏳ | ≤5；手动 min/max；固定 palette；number/date；独立数组 |
| B iconSets[] | ⏳ | ≤5×8；固定 icon 枚举；cell 前缀 |
| C BE normalize | ⏳ | 超限 400；非法丢弃；无 migration |
| D FE | ⏳ | 编辑器 + List/Board；tint > scale；vitest |
| E CLI 1.33.0 | ⏳ | 全钉 + 历史断言同步 |
| F no-emit | ⏳ | Display 读/写 spy |

## ADR 确认
- D1 Epic=Display v2 · D2 独立数组（Q1a）· D3 手动 domain + 固定 palette + tint>scale（Q2a/Q3a/Q4a）· D4 icon 小枚举（Q5a）· D5 无 migration（Q6a）· D6 仅 number/date 客户端求值 · D7 CLI **1.33.0** · D8 no-emit / 不 push / 不自开 E50

## 门禁
| 面 | 结果 |
|----|------|
| BE | _pending_ |
| CLI | _pending_ |
| FE | _pending_ |

## Gaps / 非目标（未做）
- domain auto；自由 CSS/任意 hex；自定义 URL/SVG 图标；专用 cycle/estimate/sla_paused webhook；SLA 营业日历；Activity 加厚；Formula emit；Redis/cron；push/PR/E50

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = _pending_`
- **STOP**

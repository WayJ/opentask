# E41 Acceptance：Issue audit & outbound signals

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E41-S1`  
基线 design：`bf86c23`  
tip：_(待收口)_  
状态：**IN PROGRESS**

## 交付 A–D

| 面 | 内容 |
|----|------|
| A | TimelineAction +4；CF/cycle/estimate/project 写 timeline；formula 不写 |
| B | 单 Issue + WS 级 CSV export；硬顶 10000；`X-OpenTask-Truncated` |
| C | FE 活动文案 + 导出 + webhook 多选含 `issue.custom_field_changed` |
| D | CLI **1.25.0** + timeline/timeline-export(+workspace)；webhook 事件 |

## ADR（落地）
- D1–D10 见 design §9（收口时勾选确认）

## 门禁

| 面 | 结果 |
|----|------|
| BE 定向 | _pending_ |
| BE 全量 | _pending_ |
| CLI 全量 | _pending_ |
| FE vitest | _pending_ |
| FE build | _pending_ |

## 约束确认
- 未 push / 未开 PR / 未自开 E42

`superpowers: design/plan/TDD/verify/acceptance = _pending_`

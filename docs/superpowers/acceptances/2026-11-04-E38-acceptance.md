# E38 Acceptance：Automation delayed / scheduled actions

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E38-S1`  
基线：`9e8ce90`（E37 tip + E38 design）

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A 入队模型/校验/去重/disable→cancel | ⏳ | |
| B run-due + pending list | ⏳ | |
| C FE delay 控件+摘要 | ⏳ | |
| D CLI 1.22.0 | ⏳ | |

## ADR
| ID | 决定 |
|----|------|
| D1 | `automation_pending_actions`；delay 在 action_config |
| D2 | 无内置 cron；外部 run-due；UTC |
| D3 | delay 0…10080；0=即时 |
| D4 | 同 rule+issue 一条 pending |
| D5 | tick 重评 condition |
| D6 | 快照执行 |
| D7 | depth 防环不变 |
| D8 | 每条 tick 最多 1 次 |
| D9 | CLI 1.22.0 |
| D10 | 非目标；不 push；不自开 E39 |

## TDD
- （收口补）

## 测试
- BE / CLI / FE：（收口补）

## 非目标（未做）
- 多步流水线 / 内置 cron/RRULE / due digest / formula CF / webhook 扩展 / pending 改期 UI / push·PR / E39

## tip
- SHA：待填
- 未 push / 未开 PR
- **不自开 E39** · **STOP 待命**

`superpowers: design/plan/TDD/verify/acceptance = ok`

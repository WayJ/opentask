# E48 Acceptance：SLA first-response + pause timeline · CLI 1.32.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E48-S1`  
基线：`88ea4e8`  
**tip：** _(待收口)_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A first_response metric | ⏳ | SLA_METRICS += first_response；复用 clocks；非创建者首评 → met；assignee 不算；双 metric 并存；breach payload +metric |
| B pause timeline | ⏳ | sla_paused / sla_resumed；两 metric；不 fire webhook/automation；无 migration |
| C FE | ⏳ | 设置「首次响应」；徽标；timeline/Activity 文案；automation 帮助 |
| D CLI 1.32.0 | ⏳ | --metric；issue 输出 metric；四钉 + VERSION |
| E 守住 | ⏳ | 无 migration；无营业日历；formula no-emit spy；paused 不 tick |

## ADR 确认
- D1–D9 见 design（收口勾选）

## 门禁
| 面 | 结果 |
|----|------|
| BE | _(待跑)_ |
| CLI | _(待跑)_ |
| FE | _(待跑)_ |

## Gaps / 非目标
- 营业日历 / 策略优先级；cycle/estimate 专用 webhook；formula emit；**无 push / 无 PR / 不自开 E49**
- PG `timeline_action`：无 alembic；测试靠 conftest ADD VALUE（生产部署需同语句或后续薄 migration）

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`（收口）
- **STOP**

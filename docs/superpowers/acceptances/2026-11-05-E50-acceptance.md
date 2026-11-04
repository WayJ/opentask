# E50 Acceptance：SLA business hours thin · CLI 1.34.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E50-S1`  
基线：`a77e2cf`  
**tip：** _(收口补)_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 纯函数 | ⏳ | add/elapsed business minutes；normalize windows；IANA |
| B 存储/API | ⏳ | alembic WS timezone + business_hours；PATCH；无 policy 覆盖 |
| C SLA 接线 | ⏳ | create/pause/resume/run_due；配置变更重算；墙钟回退 |
| D pause 语义 | ⏳ | Q4a elapsed=营业分钟 when enabled；paused 不 tick |
| E FE | ⏳ | 薄设置 + vitest |
| F CLI 1.34.0 | ⏳ | pins + workspace/sla 读写 |
| G no-emit | ⏳ | 配置写 spy |

## ADR 确认
- D1 Epic=business hours thin · D2 加法器唯一 deadline 源 · D3 默认关→墙钟 · D4 pause 不计 · D5 WS 级无 policy 覆盖 · D6 Alembic+重算+≤2段 · D7 CLI **1.34.0** · D8 no-emit / 不 push / 不自开 E51

## 门禁
| 面 | 结果 |
|----|------|
| BE | _(收口补)_ |
| CLI | _(收口补)_ |
| FE | _(收口补)_ |

## Gaps / 非目标（未做）
- 节假日/优先级矩阵；专用 cycle/estimate webhook；Activity 加厚；Formula emit；Redis/cron；push/PR/E51

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`（收口勾）
- **STOP**；**无 push / 无 PR / 不自开 E51**

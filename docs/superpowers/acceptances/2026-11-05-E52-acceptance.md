# E52 Acceptance：Activity Feed 加厚 v2 · CLI 1.36.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E52-S1`  
基线：`abb96db`  
**tip：** _(pending)_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A watching 过滤 | ⏳ | Q1a 对齐 E19 |
| B 空 watcher / 跨租户 | ⏳ | |
| C 反应摘要 + FE chips | ⏳ | Q2a；复用 E27；无 entry 反应表 |
| D unread-count + mark-read + 铃铛 | ⏳ | Q3a 小表；Q4a 默认全量；Q5a 无 Push |
| E FE 仅关注开关 + vitest/build | ⏳ | |
| F CLI 1.36.0 + `--watching` + `unread` | ⏳ | Q6a |
| G 读路径 no-emit / formula | ⏳ | 不扩 E51 pack |

## ADR 确认
- D1–D7 待收口确认

## 门禁
| 面 | 结果 |
|----|------|
| BE | _(pending)_ |
| CLI | _(pending)_ |
| FE | _(pending)_ |

## Gaps / 非目标（未做）
- 节假日；webhook 仪表；Formula emit；Push/FCM/实时 WS；富媒体；entry 反应表；push/PR/E53

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`（收口时）
- **STOP**；**无 push / 无 PR / 不自开 E53**

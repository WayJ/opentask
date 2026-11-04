# E51 Acceptance：专用 webhook pack + 订阅事件过滤 FE · CLI 1.35.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E51-S1`  
基线：`38bd9c6`  
**tip：** _pending_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A WEBHOOK_EVENTS +5 | ⏳ | cycle/estimate/project/sla_paused/sla_resumed |
| B 写路径 fire + 并存 updated | ⏳ | issue_service + SlaService；Q2a |
| C 未订阅不投 | ⏳ | |
| D FE 勾选/标签/预设/投递过滤 | ⏳ | Q3a 集成常用 |
| E CLI 1.35.0 + webhook events | ⏳ | Q6a |
| F no-emit / 无回放 / 无 Activity | ⏳ | Q5a；D7 |

## ADR 确认
- D1 Epic=专用 webhook pack + 订阅过滤 FE · D2 并存 updated · D3 事件名对齐 timeline · D4 FE 薄预设+过滤 · D5 HMAC/重试沿用无回放 · D6 CLI **1.35.0** · D7 no-emit / 不 push / 不自开 E52

## 门禁
| 面 | 结果 |
|----|------|
| BE | _pending_ |
| CLI | _pending_ |
| FE | _pending_ |

## Gaps / 非目标（未做）
- 节假日/policy 覆盖；Activity 加厚；Formula emit；历史回放；订阅中心/多渠道路由；Redis/cron；push/PR/E52

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = _pending_`
- **STOP**；**无 push / 无 PR / 不自开 E52**

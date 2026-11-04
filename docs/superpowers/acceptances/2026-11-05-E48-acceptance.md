# E48 Acceptance：SLA first-response + pause timeline · CLI 1.32.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E48-S1`  
基线：`88ea4e8`  
**tip：** `1b8b5bd`（全文 `1b8b5bdb34df003ab6467bb4006b5558c32a4d36`）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A first_response metric | ✅ | `SLA_METRICS` += `first_response`；复用 `issue_sla_clocks`；启停同 start/stop/pause；非创建者首评 → met；创建者自评/assignee 不算；双 metric 并存；breach webhook/automation payload +`metric` |
| B pause timeline | ✅ | `TimelineAction` += `sla_paused`/`sla_resumed`；两 metric 均写；**不** fire webhook/automation；stop/met 不写 pause 类；**无** alembic migration（Q6a）；conftest `ADD VALUE IF NOT EXISTS` |
| C FE | ✅ | 设置 metric「首次响应」+ 帮助；徽标 `首响 SLA`；timeline/Activity 文案；automation 帮助注明含 first_response；vitest |
| D CLI 1.32.0 | ✅ | `--metric first_response\|time_in_status`；list/issue 输出 Metric；pyproject + `__init__` + setup + `VERSION` + `opentask_cli.VERSION` 全钉 **1.32.0**；历史 version 断言同步 |
| E 守住 | ✅ | 无 migration / 无营业日历 / 无策略优先级；paused 永不 tick；formula 路径未引入 emit |

## ADR 确认
- D1 Epic=first_response+pause timeline · D2 复用 clocks · D3 Q1a/Q2b · D4 pause 仅 timeline（Q3a）· D5 breach +`metric` · D6 同状态集 / 双 metric（Q4a/Q5a）· D7 无 migration（Q6a）· D8 CLI **1.32.0** · D9 no-emit / 不 push / 不自开 E49

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1053 passed**, 24 skipped；1 fail `test_user_search` = **已知 flake**；定向 E48+E45+E42 **36P**（E48 `test_e48_*` **8P**） |
| CLI | **506 passed**, 89 skipped；`test_e48_sla_first_response` **3P**；pins 全 **1.32.0** |
| FE | vitest **311 passed**（45 files）；`npm run build` OK |

## Gaps / 非目标（未做）
- 营业日历 / 时区 / 节假日 / 策略优先级；resolution 多阶段 metric；assignee 算首响；专用 `issue.cycle_changed`/`estimate_changed`/`sla_paused` webhook；Formula 色阶/emit；Activity 加厚；Redis/cron
- PG 生产：`timeline_action` 需 `ALTER TYPE … ADD VALUE IF NOT EXISTS 'sla_paused'|'sla_resumed'`（本轮无 alembic，测试靠 conftest）
- **无 push / 无 PR / 不自开 E49**

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**

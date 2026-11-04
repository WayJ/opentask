# E38 Acceptance：Automation delayed / scheduled actions

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E38-S1`  
基线：`9e8ce90`（E37 tip + E38 design）  
tip：`73cf387`（`git rev-parse HEAD` = `73cf387ffc9858c4ebfdb634d552ae1423ee2d75`）

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A 入队模型/校验/去重/disable→cancel | ✅ | `automation_pending_actions`；delay 0…10080；0/缺省即时；同 rule+issue 一条 pending；disable→cancelled |
| B run-due + pending list | ✅ | `POST /api/automations/run-due`；重评 condition；失败隔离；`GET /pending` limit 100；member+；跨租户不泄漏 |
| C FE delay 控件+摘要 | ✅ | delayMinutes 0…10080；withDelayMinutes；summarize `delay Nh/Nm →` |
| D CLI 1.22.0 | ✅ | `automation run-due` / `pending`；create help 含 delay_minutes；version 全仓 1.22.0 |

## ADR
| ID | 决定 |
|----|------|
| D1 | `automation_pending_actions`；delay 在 action_config |
| D2 | 无内置 cron；外部 run-due；UTC naive |
| D3 | delay 0…10080；0=即时；非法 400 |
| D4 | 同 rule+issue 一条 pending |
| D5 | tick 重评 condition + enabled |
| D6 | 快照执行（去 delay） |
| D7 | depth 防环不变；run-due depth=0 |
| D8 | 每条 due 每 tick 最多 1 次 |
| D9 | CLI 1.22.0 |
| D10 | 非目标；不 push；不自开 E39 |

## TDD
- 红：缺 model / 无 enqueue / 无 run-due（已跑）
- 绿：`tests/api/test_e38_automation_delayed_actions.py` **11P**；FE helpers 增测；`tests/test_e38_automation_delayed.py` **5P**

## 测试
- BE pytest：**945 passed** / 24 skipped（全量一次跑中 `test_tasks_jira_wire::test_user_search` 1 条偶发失败；单跑复测见下；与 E38 无关）
- CLI：**471 passed** / 89 skipped
- FE vitest：**275 passed**；`pnpm/vite build` 成功

## 非目标（未做）
- 多步流水线 / 内置 cron/RRULE / due digest / formula CF / webhook 扩展 / pending 改期·立即执行 UI / push·PR / E39

## tip
- SHA：`73cf387`（本 tip 提交后以 `git rev-parse HEAD` 为准）
- 未 push / 未开 PR
- **不自开 E39** · **STOP 待命**

`superpowers: design/plan/TDD/verify/acceptance = ok`

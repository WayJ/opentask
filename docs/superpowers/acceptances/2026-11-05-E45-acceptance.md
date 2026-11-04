# E45 Acceptance：SLA v2 thin — pause + breach→automation

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E45-S1`  
基线：`f6683d2`  
tip：`TIP_PLACEHOLDER`

## 范围（已交付）
- **A** `sla_policies.pause_statuses` JSON 默认 `[]`；CRUD/serialize `pauseStatuses`；非法 IssueStatus → 400；空=关闭暂停
- **B** `CLOCK_STATUSES+=paused`；时钟列 `elapsed_before_pause_minutes` / `paused_at` / **`segment_started_at`**；sync pause/resume；resume `deadline_at = now + max(0, target - elapsed)`；pause 保留旧 deadline（Q3）
- **C** 优先级 **stop > pause > start**；`run_due` 仅扫 `running`；breach → Inbox + webhook + **`fire_automations(issue.sla_breached)`**；`_match_trigger` 识别新 trigger；允许 set_status + FE/CLI 文档警告（Q6）；无 pause timeline（Q4b）
- **D** FE：settings SLA pause 多选；Issue 徽标「已暂停」+ formatSlaPaused；Automations 触发 `issue.sla_breached`；vitest
- **E** CLI **1.29.0**：`policy create|update --pause`；issue 输出 elapsed/pausedAt；TRIGGERS+；全仓 version 断言同步
- **F** Migration `l8a9b0c1d2e6` ← `k7f8a9b0c1d5`；running 回填 `segment_started_at=started_at`

## ADR（落地）
- D1 SLA v2 thin：pause + breach→automation  
- D2 仅 time_in_status；墙钟 UTC naive；无营业日历  
- D3 stop > pause > start  
- D4 活跃钟 = running|paused；每 (issue,policy) 一条  
- D5 run_due 只扫 running；paused 永不 breach  
- D6 resume：`deadline = now + max(0, target - elapsed)`  
- D7 trigger = `issue.sla_breached`；复用 ACTION_TYPES  
- D8 breached → Inbox → webhook → automations；后两者失败不回滚  
- D9 CLI **1.29.0**  
- D10 不 push；不自开 E46

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1025 passed**, 1 failed（已知 flake `test_user_search` / `TestMetadata::test_user_search`；solo 复跑绿）, 24 skipped |
| BE 定向 | E45+E42：**28 passed** |
| CLI | **499 passed**, 89 skipped（首轮曾 1 flake `test_config_multiple_updates_performance` 阈值阈值；solo/复跑绿） |
| FE vitest | **299 passed**（44 files） |
| FE build | **ok**（vite prod） |
| E45 专测 | BE `test_e45_sla_v2_pause` 12P；CLI `test_e45_sla_v2` 3P |

## Gaps / 非目标（刻意不做）
- 营业日历 / first-response / 策略优先级 / pause timeline（`sla_paused`/`sla_resumed`）
- Redis / 进程内 cron；formula emit；HMAC 改版
- push / PR / E46

## superpowers
`design/plan/TDD/verify/acceptance = ok`

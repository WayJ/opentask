# E6-S3 Acceptance — complete/rollover + capacity + generate-upcoming + Epic local-complete

**Verdict:** **pass**

**pass** — S3 范围交付：`POST /api/cycles/{id}/complete`（`into_next` 含无下一自动生成；`leave_unassigned`）；`GET /api/cycles/capacity-hint`（history / members）；`POST /api/cycles/generate-upcoming`；FE `/workspace/cycles` 结束确认、容量卡、无 upcoming/空列表 CTA。门禁：全量 pytest **646 passed, 27 skipped, 0 failed**（含新增 8 条 complete/capacity）；`npm run lint` **0 errors** / 253 warnings；`npm run build` 成功。Epic E6 标 **local-complete**。未推远程。

**Fingerprint (impl tip):** `4081ddfc093d9f2297cddd1de052843da86648f7`
**Branch:** `sprint/E6-S3`
**Worktree:** `/workspace/opentask-worktrees/E6-S3`
**Baseline:** `sprint/E6-S2` @ `9a59df0`
**Time (Asia/Shanghai):** 2026-11-04 ~10:18 CST

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"4081ddfc093d9f2297cddd1de052843da86648f7","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E6-S3；分支 sprint/E6-S3（基 E6-S2 tip 9a59df0）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite；Asia/Shanghai 2026-11-04 ~10:11–10:18 CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest test_complete_into_next_rolls_incomplete"],"expected":"未完成→下一；完成留原","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest test_complete_into_next_auto_generates_upcoming"],"expected":"自动生成再滚","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest test_complete_leave_unassigned"],"expected":"未完成 cycle_id null","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest test_capacity_hint_from_history"],"expected":"basis=history mean","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["pytest test_capacity_hint_members_fallback"],"expected":"basis=members","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S6","status":"passed","modality":"api","environment":"real","steps":["pytest test_generate_upcoming"],"expected":"新建 upcoming","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S7","status":"passed","modality":"code","environment":"real","steps":["cycles FE complete/capacity/empty CTA","lint","build"],"expected":"UI 可用；0 err；build ok","observed":"committed + gates","artifacts":[],"blockers":[]},{"id":"S8","status":"passed","modality":"cli","environment":"real","steps":["pytest -q","npm run lint","npm run build"],"expected":"全绿 / 0 errors / build ok","observed":"646 passed；0 errors；Build successful","artifacts":[],"blockers":[]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **646 passed, 27 skipped, 0 failed** |
| Complete API | `pytest tests/api/test_cycle_complete.py -v` | **8 passed** |
| Frontend lint | `cd frontend && npm run lint` | **0 errors** / 253 warnings |
| Frontend build | `cd frontend && npm run build` | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | into_next rollover | 未完成→下一 | PASSED | yes |
| S2 | into_next auto-generate | 自动生成再滚 | PASSED | yes |
| S3 | leave_unassigned | cycle_id null | PASSED | yes |
| S4 | capacity history | basis=history | PASSED | yes |
| S5 | capacity members | basis=members | PASSED | yes |
| S6 | generate-upcoming | 新 upcoming | PASSED | yes |
| S7 | FE polish | 结束/hint/CTA | PASSED (code) | yes |
| S8 | 门禁 | 绿 | PASSED | yes |

## Epic E6

- S1–S3 **closed**；roadmap **status: local-complete**；merged-commit **null**；**无 push**
- Leftover：**none** for E6 scope；optional browser E2E (R1–R8) not required for local-complete；Jira sprint / Initiatives / Slack / velocity charts → later epics

## Notes

- Mid-epic：未 ping Way/Yuri；整 Epic 收口后由 controller 回执。
- 无 push。

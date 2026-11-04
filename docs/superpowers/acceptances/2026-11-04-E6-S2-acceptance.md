# E6-S2 Acceptance — Issue.cycle_id + 筛选/指派 + ⌘K Cycles

**Verdict:** **pass**

**pass** — S2 范围交付：`issues.cycle_id` + optional `estimate_points`；Issue create/update/list 过滤；跨租户 Cycle 校验；FE 列表/看板 Cycle 筛选与详情指派；⌘K `kind=cycle`。门禁：全量 pytest **638 passed, 27 skipped, 0 failed**（含新增 6 条 issue cycle）；vitest palette/entities/apply-saved-view **24 passed**；`npm run lint` **0 errors** / 252 warnings；`npm run build` 成功。**无** complete/rollover/capacity/generate-upcoming。未推远程。Epic E6 仍 **active** → 接下 S3。

**Fingerprint (impl tip):** `b2e1f7ddf02388e12590a4d8a78ec674a46a2bc0`
**Branch:** `sprint/E6-S2`
**Worktree:** `/workspace/opentask-worktrees/E6-S2`
**Migration:** `a1b2c3d4e5f7` (revises `f0e1d2c3b4a5`)
**Time (Asia/Shanghai):** 2026-11-04 ~10:10 CST

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"b2e1f7ddf02388e12590a4d8a78ec674a46a2bc0","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E6-S2；分支 sprint/E6-S2（基 E6-S1 tip 15b95ea / impl bd22f89）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite；Asia/Shanghai 2026-11-04 ~10:03–10:10 CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest test_create_issue_with_cycle_id","test_update_issue_cycle_id_and_clear"],"expected":"cycle_id 持久化/可清","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest test_list_issues_filter_by_cycle_id"],"expected":"仅该 Cycle","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest test_list_issues_filter_none_cycle"],"expected":"__none__ 仅 null","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest test_reject_cross_workspace_cycle"],"expected":"400","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["clear via PUT null"],"expected":"null","observed":"PASSED (同 S1 update test)","artifacts":[],"blockers":[]},{"id":"S6","status":"passed","modality":"code","environment":"real","steps":["list NSelect Cycle + detail EditableField"],"expected":"筛选/指派入库","observed":"list/detail 改动 + build ok","artifacts":[],"blockers":[]},{"id":"S7","status":"passed","modality":"code","environment":"real","steps":["vitest cyclesToPaletteItems / buildPaletteGroups"],"expected":"kind=cycle → list?cycle_id=","observed":"24 vitest passed","artifacts":[],"blockers":[]},{"id":"S8","status":"passed","modality":"cli","environment":"real","steps":["pytest -q","npm run lint","npm run build"],"expected":"全绿 / 0 errors / build ok","observed":"638 passed；0 errors；Build successful","artifacts":[],"blockers":[]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **638 passed, 27 skipped, 0 failed** |
| Issue cycle API | `pytest tests/api/test_issue_cycle.py -v` | **6 passed** |
| FE vitest (palette+) | `npm test -- --run …palette…` | **24 passed** |
| Frontend lint | `cd frontend && npm run lint` | **0 errors** / 252 warnings |
| Frontend build | `cd frontend && npm run build` | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | 挂/改 Cycle | 持久化 | PASSED | yes |
| S2 | list cycle_id | 仅该 Cycle | PASSED | yes |
| S3 | __none__ | 仅 null | PASSED | yes |
| S4 | 跨租户 | 400 | PASSED | yes |
| S5 | 清 Cycle | null | PASSED | yes |
| S6 | FE 筛选/指派 | 可用 | PASSED (code) | yes |
| S7 | ⌘K cycle | 跳 list?cycle_id= | PASSED (vitest) | yes |
| S8 | 门禁 | 绿 | PASSED | yes |

## Leftover → S3

- complete/rollover（into_next / leave_unassigned）
- capacity-hint
- generate-upcoming 打磨 + 空状态
- Epic local-complete

## Notes

- Mid-epic：未 ping Way/Yuri；整 Epic 收口后再回执。
- 无 push。

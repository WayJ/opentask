# E6-S1 Acceptance — Cycle CRUD + Workspace Cycles 设置 UI

**Verdict:** **pass**

**pass** — S1 范围交付：`cycles` 表 + workspace `cycles_*` 设置列 + `/api/cycles` CRUD/activate + 设置页 `/workspace/cycles`（启用开关、列表、创建 upcoming）。门禁：全量 pytest **632 passed, 27 skipped, 0 failed**（含新增 11 条 cycles）；`npm run lint` **0 errors** / 252 warnings（存量+本页 style）；`npm run build` 成功（本地 `.env.prod` 拷贝，不入库）。**无** `Issue.cycle_id` / rollover / capacity / ⌘K Cycles。未推远程。Epic E6 仍 **active** → 接下 S2。

**Fingerprint (impl tip):** `bd22f895cb93277ce34c9d5fd456a35b301d5a0b`
**Branch:** `sprint/E6-S1`
**Worktree:** `/workspace/opentask-worktrees/E6-S1`
**Migration:** `f0e1d2c3b4a5` (revises `e1f2a3b4c5d6`)
**Time (Asia/Shanghai):** 2026-11-04 ~10:01 CST

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"bd22f895cb93277ce34c9d5fd456a35b301d5a0b","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E6-S1；分支 sprint/E6-S1（基 docs tip 634eff8 / E5-S3 da13c86）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite；Asia/Shanghai 2026-11-04 09:54–10:01 CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest test_create_and_list_cycles"],"expected":"POST upcoming + list 含 id","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest test_cycles_cross_workspace_isolation"],"expected":"跨租户 403/404","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest test_delete_upcoming_cycle"],"expected":"DELETE upcoming 成功","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest test_refuse_delete_active_cycle"],"expected":"active 删 4xx","observed":"PASSED 400","artifacts":[],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["pytest test_owner_patch_cycles_enabled"],"expected":"cyclesEnabled 持久化","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S6","status":"passed","modality":"code","environment":"real","steps":["views/workspace/cycles/index.vue + route /workspace/cycles"],"expected":"设置页列表可展示","observed":"页面入库；路由 workspace_cycles；lint/build 过","artifacts":[],"blockers":[]},{"id":"S7","status":"passed","modality":"code","environment":"real","steps":["空状态 CTA enableCycles"],"expected":"enabled=false 引导","observed":"NEmpty + 启用按钮（owner）","artifacts":[],"blockers":[]},{"id":"S8","status":"passed","modality":"cli","environment":"real","steps":["npm run lint","npm run build"],"expected":"0 errors；build ok","observed":"0 errors / 252 warnings；Build successful","artifacts":[],"blockers":[]},{"id":"R-browser","status":"blocked","modality":"browser","environment":"real","steps":["未跑完整前后端浏览器联调"],"expected":"设置页手感","observed":"API+静态门禁覆盖；浏览器可选不阻塞 S1 pass","artifacts":[],"blockers":["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **632 passed, 27 skipped, 0 failed** |
| Cycles API | `pytest tests/api/test_cycles.py -v` | **11 passed** |
| Frontend lint | `cd frontend && npm run lint` | **0 errors** / 252 warnings |
| Frontend build | `cd frontend && npm run build`（`.env.prod` 本地拷贝） | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | 创建 upcoming | 201/200 + list | PASSED | yes |
| S2 | 跨租户隔离 | 403/404 | PASSED | yes |
| S3 | 删除 upcoming | 成功消失 | PASSED | yes |
| S4 | 拒删 active | 4xx | PASSED | yes |
| S5 | cycles_enabled | 持久化 | PASSED | yes |
| S6 | 设置页列表 | 路由+组件 | PASSED (code) | yes |
| S7 | 未启用空状态 | CTA | PASSED (code) | yes |
| S8 | lint/build | 0 err / ok | PASSED | yes |

## Leftover → S2 / S3

- **S2:** `Issue.cycle_id` (+ optional `estimate_points`)；列表/看板筛选；指派 UI；⌘K `kind=cycle`
- **S3:** complete/rollover；capacity-hint；generate-upcoming 打磨；Epic local-complete

## Notes

- 2026-11-04 — worktree 缺 `.env.prod`（gitignore）；从 E5-S3 拷贝后 build 成功，未入库。
- Mid-epic：未 ping Way/Yuri 做 Sprint 验收；整 Epic 收口后再回执。

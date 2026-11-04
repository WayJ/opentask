# Acceptance record — sprint E4-S1（个人 Saved Views）, 2026-11-04

## Verdict

**pass** — 必需场景 S1–S6 由 API/pytest + 前端 lint/build 证据通过；可选 S7（浏览器 E2E）本轮未跑，诚实标为 blocked。门禁：后端全量 `612 passed, 27 skipped, 0 failed`；前端 `npm run lint` 0 errors / 244 warnings（存量+本轮轻微增量）；`npm run build` 成功。未推远程。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E4-S1-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E4-S1-acceptance.md","fingerprint":"c2b9df8e3cc3904d3b2ba520b97c3322d3cdec58"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"c2b9df8e3cc3904d3b2ba520b97c3322d3cdec58","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E4-S1；分支 sprint/E4-S1（基 E3-S3 tip 61d2f40）；PostgreSQL Docker opentask-pg-test；backend .venv python3.11；frontend npm/vite；Asia/Shanghai 2026-11-04 07:5x–08:0x CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_saved_views.py::test_create_and_list_saved_views"],"expected":"创建并列出个人视图","observed":"PASSED","artifacts":["/tmp/e4s1-pytest.txt"],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_saved_views.py::test_saved_views_isolation_between_users"],"expected":"同区成员不可见他人个人视图","observed":"PASSED","artifacts":["/tmp/e4s1-pytest.txt"],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_saved_views.py::test_update_and_favorite_saved_view"],"expected":"PATCH + favorite 生效","observed":"PASSED","artifacts":["/tmp/e4s1-pytest.txt"],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_saved_views.py::test_delete_saved_view"],"expected":"删除后 404 / 列表不含","observed":"PASSED","artifacts":["/tmp/e4s1-pytest.txt"],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_saved_views.py::test_saved_views_require_workspace_header"],"expected":"缺头 400；非成员 403","observed":"PASSED","artifacts":["/tmp/e4s1-pytest.txt"],"blockers":[]},{"id":"S6","status":"passed","modality":"ui","environment":"real","steps":["npm run lint","npm run build"],"expected":"0 errors；build successful；保存/我的视图入库","observed":"lint 0 errors / 244 warnings；Build successful；issue/list + saved-views.ts","artifacts":["/tmp/e4s1-lint2.txt","/tmp/e4s1-build.txt"],"blockers":[]},{"id":"S7","status":"blocked","modality":"browser","environment":"real","steps":["未启动完整前后端联调浏览器会话"],"expected":"保存并应用视图筛选恢复","observed":"未执行；API 证据覆盖 CRUD/隔离；前端静态控件入库","artifacts":[],"blockers":["本轮无浏览器 E2E 会话；可选场景，不阻塞 pass"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| S1 定向 | `cd backend && ./.venv/bin/python -m pytest tests/api/test_saved_views.py -v` | **5 passed** |
| 全量 pytest | `cd backend && ./.venv/bin/python -m pytest tests/ -q` | **612 passed, 27 skipped, 0 failed**（195.53s） |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 244 warnings**（存量为主） |
| 前端 build | `cd frontend && npm run build`（`.env.prod`） | **Build successful** |

相对 E3-S3：全量 607→612（+5 saved-views 用例）。

## Scenario Results

| id | command / 用例 | expected | actual | pass |
|---|---|---|---|---|
| S1 | `test_create_and_list_saved_views` | 创建+列表 | PASSED | yes |
| S2 | `test_saved_views_isolation_between_users` | 跨用户隔离 | PASSED | yes |
| S3 | `test_update_and_favorite_saved_view` | 更新/收藏 | PASSED | yes |
| S4 | `test_delete_saved_view` | 删除 | PASSED | yes |
| S5 | `test_saved_views_require_workspace_header` | 400/403 | PASSED | yes |
| S6 | lint + build + 控件入库 | 0 error / build ok | PASSED | yes |
| S7 | 浏览器 Saved Views | 可选 | **blocked** | n/a |

## DoD Checklist

- [x] Wave 1–3 Stories 完成（计划 / IssueSavedView+API / 前端保存·应用·收藏）
- [x] 定向 pytest 全绿（5/5）
- [x] 全量 pytest 无失败（612P/27S）
- [x] lint 0 errors + build 成功
- [x] acceptance 文档写入；sprint frontmatter `acceptance-record` 指向本文件
- [x] 提交在 `sprint/E4-S1`；**不推远程**

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E（S7）未跑；不阻塞 pass。
- 2026-11-04 — E4-S1 worktree 依赖符号链接到 E3-S1 的 `.venv`/`node_modules`（不入库）。
- 2026-11-04 — 未推远程；S2/S3 未开工。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| IssueSavedView + alembic | yes | synced | `models/issue_saved_view` + `d0e1f2a3b4c5` |
| SavedViewService + API | yes | synced | `/api/saved-views` |
| 前端保存/应用/收藏 | yes | synced | Naive UI / DESIGN.md 令牌 |
| IssueCollection 复用 | excluded | n/a | ADR D2 |
| 工作区共享视图 | excluded | n/a | ADR D1 |
| S2 分组 / S3 子 Issue | deferred | planned | 下一批 |

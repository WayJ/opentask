# E7-S1 Acceptance — Workspace Labels + groupBy label + L / ⌘K

**Verdict:** **pass**

**pass** — S1 范围交付：`tag_groups` + workspace-scoped `tags`（color/group）+ `/api/tags` & `/api/tag-groups` CRUD + Issue GET/POST/DELETE/PUT tags + list/detail `tags` enrich + FE `/workspace/labels` + detail 加减标 + `groupBy: label` + 热键 **L** picker + ⌘K「添加标签…」。Jira `get_or_create_tag(..., workspace_id=)` 工作区感知。门禁：全量 pytest **657 passed, 27 skipped, 0 failed**（含 11 条 tags）；vitest groupBy/hotkeys/palette **28 passed**；`npm run lint` **0 errors** / 259 warnings；`npm run build` 成功（本地 `.env.prod` 拷贝，不入库）。**无** `is_shared` / display prefs / board swimlanes。未推远程。Epic E7 仍 **active** → 接下 S2。

**Fingerprint (impl tip):** `a1b59bb05f1a8e29ec02107171f067be5bd6fc5f`
**Branch:** `sprint/E7-S1`
**Worktree:** `/workspace/opentask-worktrees/E7-S1`
**Migration:** `b2c3d4e5f6a8` (revises `a1b2c3d4e5f7`)
**Time (Asia/Shanghai):** 2026-11-04 ~10:37 CST

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"a1b59bb05f1a8e29ec02107171f067be5bd6fc5f","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E7-S1；分支 sprint/E7-S1（基 E6-S3 tip 7dd7c55 / docs a136a25）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite（node_modules→E6-S3→E3-S1）；Asia/Shanghai 2026-11-04 ~10:27–10:37 CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest test_create_and_list_tags","test_tags_cross_workspace_isolation"],"expected":"CRUD + 跨租户隔离","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest test_create_tag_group_and_assign","test_patch_tag_name_color_group"],"expected":"分组/颜色","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest test_issue_get_tags_not_empty_after_attach","test_issue_put_replace_tags"],"expected":"GET 非空；PUT replace","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest test_get_or_create_tag_scoped_to_workspace"],"expected":"workspace-aware get_or_create","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S5","status":"passed","modality":"code","environment":"real","steps":["views/workspace/labels","groupIssuesBy label","hotkey L","⌘K action.labels"],"expected":"FE 页+分组+热键+面板","observed":"入库；vitest 28 passed","artifacts":[],"blockers":[]},{"id":"S6","status":"passed","modality":"cli","environment":"real","steps":["pytest -q","npm run lint","npm run build"],"expected":"全绿 / 0 errors / build ok","observed":"657 passed；0 errors；Build successful","artifacts":[],"blockers":[]},{"id":"R-browser","status":"blocked","modality":"browser","environment":"real","steps":["未跑浏览器 E2E"],"expected":"手感","observed":"API+静态门禁覆盖；不阻塞 S1 pass","artifacts":[],"blockers":["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **657 passed, 27 skipped, 0 failed** |
| Tags API | `pytest tests/api/test_tags.py -v` | **11 passed** |
| Frontend vitest (E7 slice) | `vitest run groupIssuesBy/issue-hotkeys/command-palette` | **28 passed** |
| Frontend lint | `cd frontend && npm run lint` | **0 errors** / 259 warnings |
| Frontend build | `cd frontend && npm run build`（`.env.prod` 本地拷贝） | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | Tag CRUD + 隔离 | 200 / 403·404 | PASSED | yes |
| S2 | Group + color | 持久化 | PASSED | yes |
| S3 | Issue tags GET/PUT | 非空 / replace | PASSED | yes |
| S4 | get_or_create workspace | 同名不同 WS | PASSED | yes |
| S5 | FE labels/L/groupBy/⌘K | 入库+单测 | PASSED | yes |
| S6 | lint/build/pytest | 0 err / ok | PASSED | yes |

## APIs

- `GET/POST /api/tags`；`GET/PATCH/DELETE /api/tags/{id}`
- `GET/POST /api/tag-groups`；`PATCH/DELETE /api/tag-groups/{id}`
- `GET/PUT /api/issues/{id}/tags`；`POST/DELETE /api/issues/{id}/tags/{tag_id}`
- Header `X-Workspace-Id` required；member+ write / viewer+ read；camelCase JSON

## Leftover → S2 / S3

- **S2:** `is_shared` Saved Views + 权限 + Save As + 个人/共享列表隔离
- **S3:** Display prefs + Board swimlanes + fields visibility；Epic local-complete

## Notes

- 2026-11-04 — worktree 缺 `.env.prod`（gitignore）；从 E6-S3 拷贝后 build 成功，未入库。
- Mid-epic：未 ping Way/Yuri 做 Sprint 验收；整 Epic 收口后再回执。
- 全量 vitest 仍有存量 auth/`@pinia/testing` 失败（与 E5/E6 同）；本 Sprint 门禁以 E7 相关 28 条 + lint/build 为准。

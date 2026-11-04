# E7-S2 Acceptance — Workspace-shared Saved Views

**Verdict:** **pass**

**pass** — S2 范围交付：`issue_saved_views.is_shared` + list `{personal,shared,rows}` 隔离 + 权限（member+ 建；creator 或 WS owner 写共享；他人 personal 404；viewer 读共享不可建/Save As）+ `POST /saved-views/{id}/save-as` + favorite 仅 personal + FE 分区下拉 /「共享给工作区」/ 另存为。门禁：全量 pytest **666 passed, 27 skipped, 0 failed**（含 15 条 saved_views）；vitest sections **4 passed**；`npm run lint` **0 errors** / 259 warnings；`npm run build` 成功。**无** display prefs / board swimlanes。未推远程。Epic E7 仍 **active** → 接下 S3。

**Fingerprint (impl tip):** `8ca308aa00af87ddcad0875665edee04b0e196c1`
**Branch:** `sprint/E7-S2`
**Worktree:** `/workspace/opentask-worktrees/E7-S2`
**Migration:** `c3d4e5f6a7b9` (revises `b2c3d4e5f6a8`)
**Time (Asia/Shanghai):** 2026-11-04 ~10:45 CST

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"8ca308aa00af87ddcad0875665edee04b0e196c1","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E7-S2；分支 sprint/E7-S2（基 E7-S1 tip b024ba2 / impl a1b59bb）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite（node_modules→E6-S3）；Asia/Shanghai 2026-11-04 ~10:37–10:45 CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest test_create_shared_view_listed_for_other_member","test_list_personal_shared_isolation"],"expected":"共享可见；个人隔离","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["test_member_cannot_patch_others_personal","test_member_cannot_patch_shared_unless_creator","test_workspace_owner_can_patch_shared_created_by_member"],"expected":"404/403/owner 写","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["test_save_as_shared_creates_personal_copy","test_viewer_can_get_shared_cannot_create_or_save_as","test_favorite_rejected_on_shared_view","test_shared_cross_workspace_invisible"],"expected":"Save As / viewer / fav / 跨租户","observed":"PASSED","artifacts":[],"blockers":[]},{"id":"S4","status":"passed","modality":"code","environment":"real","steps":["FE sections/share/save-as","vitest saved-view-sections"],"expected":"分区 UI + 单测","observed":"入库；4 passed","artifacts":[],"blockers":[]},{"id":"S5","status":"passed","modality":"cli","environment":"real","steps":["pytest -q","npm run lint","npm run build"],"expected":"全绿 / 0 errors / build ok","observed":"666 passed；0 errors；Build successful","artifacts":[],"blockers":[]},{"id":"R-browser","status":"blocked","modality":"browser","environment":"real","steps":["未跑浏览器 E2E"],"expected":"手感","observed":"API+静态门禁覆盖；不阻塞 S2 pass","artifacts":[],"blockers":["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **666 passed, 27 skipped, 0 failed** |
| Saved Views API | `pytest tests/api/test_saved_views.py -v` | **15 passed** |
| Frontend vitest (S2 slice) | `vitest run saved-view-sections` | **4 passed** |
| Frontend lint | `cd frontend && npm run lint` | **0 errors** / 259 warnings |
| Frontend build | `cd frontend && npm run build`（`.env.prod` 本地拷贝） | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | Shared list isolation | personal/shared 分区 | PASSED | yes |
| S2 | Write ACL | 他人 personal 404；非 creator member 403；owner 可写 | PASSED | yes |
| S3 | Save As / viewer / fav / cross-WS | 副本 personal；viewer 403 写；共享禁收藏；跨租户不可见 | PASSED | yes |
| S4 | FE UI | 分区/共享开关/另存为 | PASSED | yes |
| S5 | lint/build/pytest | 0 err / ok | PASSED | yes |

## APIs

- `GET /api/saved-views` → `{ personal, shared, rows, total }`；每条含 `isShared`
- `POST /api/saved-views` body `is_shared?`（member+）
- `GET/PATCH/DELETE /api/saved-views/{id}` — accessible 读；写 = personal owner 或 (shared 且 creator|WS owner)
- `POST /api/saved-views/{id}/favorite` — personal only（共享 403）
- `POST /api/saved-views/{id}/save-as` — member+；深拷贝 → 新 personal
- Header `X-Workspace-Id` required

## Leftover → S3

- **S3:** Display prefs + Board swimlanes + fields visibility；Epic local-complete

## Notes

- Mid-epic：未 ping Way/Yuri 做 Sprint 验收；整 Epic 收口后再回执。
- Favorite 共享延后 E8 Favorites。

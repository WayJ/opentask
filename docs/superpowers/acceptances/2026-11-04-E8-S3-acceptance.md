# E8-S3 Acceptance — Sidebar Favorites + Epic local-complete

**Verdict:** **pass**

**pass** — S3 范围交付：`favorites` 多态表（Alembic `a7b8c9d0e1f3` revises `f6a7b8c9d0e2`）+ `/api/favorites` list/add/delete/reorder + pin Project upserts watcher（unpin **不** unwatch）+ 个人隔离/跨租户 404 + **不**改写 `issue_saved_views.is_favorite`。FE：`FavoritesNav` 插入 `global-sider`（Logo↔菜单）；项目详情 / Issue 详情 / 已保存视图「收藏到侧栏」（文案与星标分离）。门禁：全量 pytest **700 passed, 27 skipped, 0 failed**（含 8 条 favorites）；vitest favorites **6 passed**；`eslint --quiet` **0 errors**；`pnpm run build` 成功。Epic E8 **local-complete**（S1–S3 closed）。未推远程。`merged-commit: null`。**未**启动 E12。

**Fingerprint (impl tip):** `f9c3f731ea755eca07d93e58937a7f8821334615`
**Branch tip:** `f9c3f731ea755eca07d93e58937a7f8821334615`
**Branch:** `sprint/E8-S3`
**Worktree:** `/workspace/opentask-worktrees/E8-S3`
**Migration:** `a7b8c9d0e1f3` (revises `f6a7b8c9d0e2`)
**Time (Asia/Shanghai):** 2026-11-04 ~11:47 CST

```supervibe-acceptance-results
{"schema": 1, "scope": "sprint", "candidate": "f9c3f731ea755eca07d93e58937a7f8821334615", "environment": "共享 box Linux；worktree /workspace/opentask-worktrees/E8-S3；分支 sprint/E8-S3（基 E8-S2 tip 4325b15 + stub）；PostgreSQL portable；backend .venv；frontend pnpm/vite；Asia/Shanghai 2026-11-04 ~11:47 CST", "results": [{"id": "S1", "status": "passed", "modality": "api", "environment": "real", "steps": ["pytest tests/api/test_favorites.py"], "expected": "CRUD/ACL/pin→watcher/≠is_favorite", "observed": "8 PASSED", "artifacts": [], "blockers": []}, {"id": "S2", "status": "passed", "modality": "code", "environment": "real", "steps": ["FavoritesNav", "pin on project/issue/saved_view"], "expected": "FE 侧栏+钉选；文案区分星标", "observed": "入库 f9c3f73", "artifacts": [], "blockers": []}, {"id": "S3", "status": "passed", "modality": "cli", "environment": "real", "steps": ["pytest tests/ -q", "eslint --quiet", "pnpm run build", "vitest favorites"], "expected": "全绿 / 0 errors / build ok", "observed": "700 passed；0 errors；Build successful；6 vitest", "artifacts": [], "blockers": []}, {"id": "R-browser", "status": "blocked", "modality": "browser", "environment": "real", "steps": ["未跑浏览器 E2E"], "expected": "手感", "observed": "API+静态门禁覆盖；不阻塞 S3/Epic pass", "artifacts": [], "blockers": ["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **700 passed, 27 skipped, 0 failed** |
| Favorites API | `pytest tests/api/test_favorites.py -v` | **8 passed** |
| Favorites vitest | `pnpm exec vitest run src/utils/favorites.test.ts` | **6 passed** |
| Frontend lint | `cd frontend && pnpm exec eslint . --quiet` | **0 errors** |
| Frontend build | `cd frontend && pnpm run build` | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | favorites API + pin→watcher + ACL | CRUD/幂等/个人隔离/跨 WS 404；unpin 保留 watcher；不改 is_favorite | PASSED | yes |
| S2 | FavoritesNav + pin UI | 侧栏跳转；项目/Issue/视图可钉；≠星标 | PASSED | yes |
| S3 | lint/build/pytest/vitest | 0 err / ok / 700 / 6 | PASSED | yes |

## APIs

- `GET /api/favorites`
- `POST /api/favorites` `{target_type, target_id}`
- `PUT /api/favorites/reorder` `{ordered_ids}`
- `DELETE /api/favorites/{id}`
- Header `X-Workspace-Id` required

## Leftover

- 可选浏览器 E2E（不阻塞）
- **E12**（invites + KEY-N + de-PGE）由 controller 另开；**本 Sprint/agent 未启动**
- 无 Initiative / Slack / 远程 push

## Notes

- Epic E8 S1–S3 全部本地 closed；整包一次回执。
- `merged-commit: null`；**未推远程**。

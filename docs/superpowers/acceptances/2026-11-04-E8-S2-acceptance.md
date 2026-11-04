# E8-S2 Acceptance — Health updates · Watchers · Inbox fanout · Timeline MVP

**Verdict:** **pass**

**pass** — S2 范围交付：`project_health_updates` + `projects.health_*` 缓存 + `project_watchers` + POST/GET health + Watch/Unwatch（创建项目自动 watch）+ Inbox `type=project_health` fanout（跳过 actor）+ Timeline 聚合 API + project-detail header/历史/Timeline week-month + empty-state + Inbox 跳转项目。**无** Favorites（→ S3）。门禁：全量 pytest **692 passed, 27 skipped, 0 failed**（含 8 条 health）；vitest project-timeline **7 passed**；`eslint --quiet` **0 errors**；`pnpm run build` 成功。Epic E8 仍 **active**。未推远程。`merged-commit: null`。

**Fingerprint (impl tip):** `e7edb353e78e48a79f8fd8d77df99bdba5e91458`
**Branch tip:** `e7edb353e78e48a79f8fd8d77df99bdba5e91458`
**Branch:** `sprint/E8-S2`
**Worktree:** `/workspace/opentask-worktrees/E8-S2`
**Migration:** `f6a7b8c9d0e2` (revises `e5f6a7b8c9d1`)
**Time (Asia/Shanghai):** 2026-11-04 ~11:39 CST

```supervibe-acceptance-results
{"schema": 1, "scope": "sprint", "candidate": "e7edb353e78e48a79f8fd8d77df99bdba5e91458", "environment": "共享 box Linux；worktree /workspace/opentask-worktrees/E8-S2；分支 sprint/E8-S2（基 E8-S1 tip 97a53af）；PostgreSQL portable；backend .venv；frontend pnpm/vite；Asia/Shanghai 2026-11-04 ~11:39 CST", "results": [{"id": "S1", "status": "passed", "modality": "api", "environment": "real", "steps": ["pytest tests/api/test_project_health.py"], "expected": "health/watchers/inbox/timeline/ACL", "observed": "8 PASSED", "artifacts": [], "blockers": []}, {"id": "S2", "status": "passed", "modality": "code", "environment": "real", "steps": ["project-detail health+timeline", "inbox project_health nav"], "expected": "FE 交付", "observed": "入库 e7edb35", "artifacts": [], "blockers": []}, {"id": "S3", "status": "passed", "modality": "cli", "environment": "real", "steps": ["pytest tests/ -q", "eslint --quiet", "pnpm run build", "vitest project-timeline"], "expected": "全绿 / 0 errors / build ok", "observed": "692 passed；0 errors；Build successful；7 vitest", "artifacts": [], "blockers": []}, {"id": "R-browser", "status": "blocked", "modality": "browser", "environment": "real", "steps": ["未跑浏览器 E2E"], "expected": "手感", "observed": "API+静态门禁覆盖；不阻塞 S2 pass", "artifacts": [], "blockers": ["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **692 passed, 27 skipped, 0 failed** |
| Health API | `pytest tests/api/test_project_health.py -v` | **8 passed** |
| Timeline vitest | `pnpm exec vitest run src/utils/project-timeline.test.ts` | **7 passed** |
| Frontend lint | `cd frontend && pnpm exec eslint . --quiet` | **0 errors** |
| Frontend build | `cd frontend && pnpm run build` | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | Health + watchers + Inbox + timeline API | 写历史+缓存；fanout 跳过 actor；ACL/跨租户；Timeline DTO | PASSED | yes |
| S2 | FE header/history/Timeline/Inbox | 徽章+更新+关注；week/month；empty-state；Inbox 跳项目 | PASSED | yes |
| S3 | lint/build/pytest/vitest | 0 err / ok / 692 / 7 | PASSED | yes |

## APIs

- `POST/GET /api/projects/{id}/health`（`?history=1`）
- `GET/POST/DELETE /api/projects/{id}/watchers`
- `GET /api/projects/{id}/timeline`
- Project response 含 `health_status/note/updated_at/updated_by`
- Inbox `type=project_health`, `resourceType=project`
- Header `X-Workspace-Id` required（health/watchers/timeline）

## Leftover

- **S3**：Sidebar Favorites + 打磨；Epic local-complete
- 可选浏览器 E2E（不阻塞）
- 整 Epic E8 收口后 controller 接 **E12**（invites + KEY-N + de-PGE），**不**接 E9；本 agent **不**自行开 E12

## Notes

- Mid-epic：未 ping Way/Yuri。
- 无 Favorites 产品行为。

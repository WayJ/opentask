# E8-S1 Acceptance — Milestones · issue.milestone_id · project dates · project UI

**Verdict:** **pass**

**pass** — S1 范围交付：`milestones` 表 + nested `/api/projects/{id}/milestones` CRUD + `issues.milestone_id`（同项目校验、ON DELETE SET NULL）+ `projects.starts_at`/`target_date` + project-detail 日期编辑与里程碑面板 + Issue 详情 Milestone 选择器。**无** health / Timeline / Favorites（→ S2/S3）。门禁：全量 pytest **684 passed, 27 skipped, 0 failed**（含 12 条 milestones）；`eslint --quiet` **0 errors**；`pnpm run build` 成功。Epic E8 仍 **active**。未推远程。`merged-commit: null`。

**Fingerprint (impl tip):** `56c886e6d7c037eef5857d4af1acf617aa52dddf`
**Branch tip:** `14a27bf84bc8f63861cbd846a9eda489a16970d6`
**Branch:** `sprint/E8-S1`
**Worktree:** `/workspace/opentask-worktrees/E8-S1`
**Migration:** `e5f6a7b8c9d1` (revises `d4e5f6a7b8c0`)
**Time (Asia/Shanghai):** 2026-11-04 ~11:30 CST

```supervibe-acceptance-results
{"schema": 1, "scope": "sprint", "candidate": "56c886e6d7c037eef5857d4af1acf617aa52dddf", "environment": "共享 box Linux；worktree /workspace/opentask-worktrees/E8-S1；分支 sprint/E8-S1（基 E7-S3 tip 68740f7）；PostgreSQL portable PG16 /home/box/pgdata；backend .venv；frontend pnpm/vite；Asia/Shanghai 2026-11-04 ~11:30 CST", "results": [{"id": "S1", "status": "passed", "modality": "api", "environment": "real", "steps": ["pytest tests/api/test_milestones.py"], "expected": "CRUD/isolation/viewer/attach/SET NULL/dates", "observed": "12 PASSED", "artifacts": [], "blockers": []}, {"id": "S2", "status": "passed", "modality": "code", "environment": "real", "steps": ["project-detail milestones+dates", "issue detail Milestone picker"], "expected": "FE 交付", "observed": "入库 56c886e", "artifacts": [], "blockers": []}, {"id": "S3", "status": "passed", "modality": "cli", "environment": "real", "steps": ["pytest tests/ -q", "eslint --quiet", "pnpm run build"], "expected": "全绿 / 0 errors / build ok", "observed": "684 passed；0 errors；Build successful", "artifacts": [], "blockers": []}, {"id": "R-browser", "status": "blocked", "modality": "browser", "environment": "real", "steps": ["未跑浏览器 E2E"], "expected": "手感", "observed": "API+静态门禁覆盖；不阻塞 S1 pass", "artifacts": [], "blockers": ["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && .venv/bin/pytest tests/ -q` | **684 passed, 27 skipped, 0 failed** |
| Milestones API | `pytest tests/api/test_milestones.py -v` | **12 passed** |
| Frontend lint | `cd frontend && pnpm exec eslint . --quiet` | **0 errors** |
| Frontend build | `cd frontend && pnpm run build`（`.env.prod` 本地拷贝） | **Build successful** |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | Milestones API + dates + attach | CRUD；跨 WS/跨项目拒绝；viewer 只读；删里程碑 SET NULL | PASSED | yes |
| S2 | FE project-detail + issue attach | 日期+里程碑面板；Milestone picker | PASSED | yes |
| S3 | lint/build/pytest | 0 err / ok / 684 | PASSED | yes |

## APIs

- `GET/POST /api/projects/{project_id}/milestones`
- `GET/PATCH/DELETE /api/projects/{project_id}/milestones/{milestone_id}`
- Project `PUT` body 可选 `starts_at` / `target_date`
- Issue create/update/list：`milestone_id`（同项目校验）
- Header `X-Workspace-Id` required
- Milestone JSON snake_case：`id,workspace_id,project_id,name,description,target_date,status,position,created_at,updated_at`

## Leftover

- **S2**：Health updates + Inbox fanout + Timeline MVP（week/month + empty-state）
- **S3**：Sidebar Favorites + 打磨；Epic local-complete
- 可选浏览器 E2E 手感（不阻塞）
- 可选 Issue 列表 `milestone_id` 筛选（非门禁）
- 整 Epic E8 收口后 controller 接 **E12**（invites + KEY-N + de-PGE），**不**接 E9

## Notes

- Mid-epic：未 ping Way/Yuri；S1 关闭后开 E8-S2 worktree。
- 无 health / Timeline / Favorites 产品行为。

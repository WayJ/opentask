# E12-S2 Acceptance — Invites + members UI

**Verdict:** **pass**

**pass** — S2 范围交付：`workspace_invites`（token_hash sha256、email 可选、role、expiry、status、invited_by、workspace_id）+ Alembic `c9d0e1f2a3b5`（revises `b8c9d0e1f2a4`）；owner create/list/revoke；匿名 `GET /api/invites/{token}` 预览；登录 `POST …/accept` 幂等；register 可选 `inviteToken`（无 SMTP，copy-link 为主）；`PATCH …/members/{userId}` + `POST …/leave` + 最后 owner 守卫；保留 `add_member` **409**；FE `/workspace/members` + 常量路由 `/invite/:token`。**未**做 SMTP / SSO / S3 de-PGE。未推远程。

**Fingerprint (impl tip):** `0321d715cd63084f57b726f5b13f467248517639`
**Branch tip:** `0321d715cd63084f57b726f5b13f467248517639`
**Branch:** `sprint/E12-S2`
**Worktree:** `/workspace/opentask-worktrees/E12-S2`
**Plan:** `docs/superpowers/plans/2026-11-04-e12-s2-invites-members.md` @ `5e6ce353fb04b5d064a99781ad6718434e375fda`
**Migration:** `c9d0e1f2a3b5` (revises `b8c9d0e1f2a4`)
**Time (Asia/Shanghai):** 2026-11-04 ~12:25 CST

```supervibe-acceptance-results
{"schema": 1, "scope": "sprint", "candidate": "0321d715cd63084f57b726f5b13f467248517639", "environment": "共享 box Linux；worktree /workspace/opentask-worktrees/E12-S2；分支 sprint/E12-S2（基 E12-S1 tip 3f3c7ad）；PostgreSQL portable；backend .venv→E8-S1；frontend node_modules→E8-S1；Asia/Shanghai 2026-11-04 ~12:25 CST", "results": [{"id": "S1", "status": "passed", "modality": "api", "environment": "real", "steps": ["pytest tests/api/test_invites.py tests/api/test_workspace_members_s2.py"], "expected": "invites CRUD/accept/register + role/leave/409", "observed": "13 PASSED", "artifacts": [], "blockers": []}, {"id": "S2", "status": "passed", "modality": "code", "environment": "real", "steps": ["model+alembic+InviteService+routers+FE members/invite"], "expected": "copy-link + members UI", "observed": "入库", "artifacts": [], "blockers": []}, {"id": "S3", "status": "passed", "modality": "cli", "environment": "real", "steps": ["pytest tests/ -q", "eslint touched FE"], "expected": "≥708+new / 0 eslint", "observed": "721 passed, 27 skipped, 0 failed；eslint 0", "artifacts": [], "blockers": ["未跑 vitest（无新增纯函数单测）；pnpm build 跨 worktree unocss 环境限制同 S1"]}, {"id": "R-browser", "status": "blocked", "modality": "browser", "environment": "real", "steps": ["未跑浏览器 E2E"], "expected": "手感", "observed": "API+静态门禁覆盖；不阻塞 S2 pass", "artifacts": [], "blockers": ["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -q` | **721 passed, 27 skipped, 0 failed** |
| Invites + members API | `pytest tests/api/test_invites.py tests/api/test_workspace_members_s2.py -v` | **13 passed** |
| Frontend lint (touched) | `eslint workspace.ts auth.ts members/index.vue invite/[token].vue register.vue --quiet` | **0 errors** |
| Frontend vitest | — | **n/a**（无新增纯函数单测） |
| Frontend build | `pnpm run build` | **blocked (env symlink/unocss)** — 不阻塞 S2 |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | create/list/revoke/preview/accept/register+token + role/leave/409 | API 绿 | PASSED | yes |
| S2 | Alembic + FE members + invite landing + register inviteToken | 入库 | PASSED | yes |
| S3 | Full pytest ≥ prior 708 + new | 721 / 0 failed | PASSED | yes |

## APIs / UI routes

- `POST/GET /api/workspaces/{id}/invites`；`DELETE …/invites/{inviteId}`
- `GET /api/invites/{token}`（可匿名）；`POST /api/invites/{token}/accept`（需登录，幂等）
- `PATCH /api/workspaces/{id}/members/{userId}` `{ role }`
- `POST /api/workspaces/{id}/leave`
- `POST /api/auth/register` + optional `inviteToken`
- FE: `/workspace/members`；`/invite/:token`（constant）

## Leftover / gaps vs design S2 ACs

- **无 SMTP**（设计允许 copy-link 为主；email 字段仅备注）
- 成员列表仅 `userId`（后端未嵌用户名；UI 显示 userId）
- 浏览器 E2E 未跑；`pnpm build` 环境限制同 S1
- viewer 只读：API 层 owner 门禁已做；FE 非 owner 隐藏邀请区
- **未**开 S3 de-PGE；**未推远程**；`merged-commit: null`

## Notes

- Mid-epic：不单独找 Way/Yuri；Epic 收口后再回执。

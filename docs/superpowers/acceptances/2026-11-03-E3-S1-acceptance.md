# Acceptance record — sprint E3-S1（开放注册 + Workspace 租户边界）, 2026-11-03/04

## Verdict

**pass** — 必需场景 S1–S8 全部由 API/pytest 证据通过；可选 S9（浏览器注册页）本轮未跑，诚实标为 blocked（无本地前后端联调浏览器会话）。门禁：后端全量 `597 passed, 27 skipped, 0 failed`；前端 `npm run lint` 0 errors / 242 warnings（存量）；`npm run build` 成功。未推远程（Way SSH/GitHub 待配）。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-03-E3-S1-plan.md","record":"docs/superpowers/acceptances/2026-11-03-E3-S1-acceptance.md","fingerprint":"PENDING_AFTER_COMMIT"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"PENDING_AFTER_COMMIT","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E3-S1；分支 sprint/E3-S1；PostgreSQL Docker opentask-pg-test（DOCKER_HOST=tcp://127.0.0.1:2375）；backend .venv python3.11；frontend npm/vite；Asia/Shanghai 2026-11-04 00:0x CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_register.py::test_register_success"],"expected":"200；token + defaultWorkspaceId；user+workspace+owner","observed":"PASSED；POST /api/auth/register → 200","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_register.py::test_register_duplicate_username"],"expected":"409","observed":"PASSED","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_register.py::test_register_weak_password"],"expected":"422","observed":"PASSED；password=abc → 422","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_register.py::test_register_then_login_local"],"expected":"register 后 login-local 200","observed":"PASSED","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_workspace.py::test_list_workspaces_includes_default"],"expected":"GET /api/workspaces 含默认区","observed":"PASSED","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S6","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_workspace.py::test_create_workspace_and_project_isolation"],"expected":"新工作区下建 Project；头过滤隔离","observed":"PASSED","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S7","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_workspace.py::test_foreign_workspace_forbidden"],"expected":"非成员 X-Workspace-Id → 403","observed":"PASSED；GET /api/projects → 403","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S8","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_workspace.py::test_issue_cross_workspace_isolation"],"expected":"跨工作区 Issue list 不可见","observed":"PASSED","artifacts":["/tmp/e3s1-s1-targeted.txt"],"blockers":[]},{"id":"S9","status":"blocked","modality":"browser","environment":"real","steps":["未启动完整前后端联调浏览器会话"],"expected":"注册页可提交并进入登录态","observed":"未执行；前端 register.vue 已接线 fetchRegister；lint/build 绿作为静态证据","artifacts":[],"blockers":["本轮无浏览器 E2E 会话；可选场景，不阻塞 pass"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| S1 定向 | `cd backend && ./.venv/bin/python -m pytest tests/api/test_register.py tests/api/test_workspace.py -v` | **9 passed**（6.22s） |
| 全量 pytest | `cd backend && ./.venv/bin/python -m pytest tests/ -q` | **597 passed, 27 skipped, 0 failed**（193.53s） |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 242 warnings**（存量，无新增 error） |
| 前端 build | `cd frontend && npm run build`（需本地 gitignored `.env.prod`，由 `.env.example` 复制） | **Build successful** |

注：全量 pytest 原先 4 失败（`test_data_scope`×3、`test_dept_snapshot`×1）因 SQLite 旁路 fixture 的 `TABLES` 未含 `workspaces`/`workspace_members`，list Project 触发 `member_workspace_ids` 查询缺表。已补表清单后上述用例全绿。

## Scenario Results

| id | command / 用例 | expected | actual | pass |
|---|---|---|---|---|
| S1 | `test_register_success` | 200 + token + 默认 WS | PASSED | yes |
| S2 | `test_register_duplicate_username` | 409 | PASSED | yes |
| S3 | `test_register_weak_password` | 422 | PASSED | yes |
| S4 | `test_register_then_login_local` | login-local 200 | PASSED | yes |
| S5 | `test_list_workspaces_includes_default` | 含默认区 | PASSED | yes |
| S6 | `test_create_workspace_and_project_isolation` | 项目挂新区 + 隔离 | PASSED | yes |
| S7 | `test_foreign_workspace_forbidden` | 403 | PASSED | yes |
| S8 | `test_issue_cross_workspace_isolation` | 跨区不可见 | PASSED | yes |
| S9 | 浏览器 `/login/register` | 可提交 | **blocked**（未跑 E2E） | n/a（optional） |

附加：`test_owner_can_add_member` PASSED（成员邀请后可读项目）。

## DoD Checklist

- [x] Wave 1–4 Stories 完成（模型/迁移/注册/Workspace API/前端接线）
- [x] 定向 pytest 全绿（9/9）
- [x] 全量 pytest 无失败（597P/27S）
- [x] lint 0 errors + build 成功
- [x] acceptance 文档写入；sprint frontmatter `acceptance-record` 指向本文件
- [x] 提交在 `sprint/E3-S1`；**不推远程**

## Obstacles (verbatim)

- 2026-11-03 夜 — Cursor GitHub / Cloud Agent 不可用；按 Yuri/Way 指示改本地 HTTPS clone + worktree 推进，不推远程。
- 2026-11-03 — 宿主机无 docker CLI apt；改用 `DOCKER_HOST=tcp://127.0.0.1:2375` + 静态 docker 客户端拉起 `opentask-pg-test`。
- 2026-11-03 — tuna PyPI 短暂 403；临时切 pypi.org 装依赖后恢复。
- 2026-11-04 00:0x CST — 全量首跑 4 failed：`sqlite3.OperationalError: no such table: workspace_members`（`test_data_scope` / `test_dept_snapshot` 自建 TABLES 旁路）。修复：TABLES 增加 `workspaces`、`workspace_members`。重跑 597P/0F。
- 2026-11-03 — `npm run build` 缺 gitignored `.env.prod` → Unocss `VITE_ICON_LOCAL_PREFIX.replace` TypeError。处置：从 `.env.example` 复制本地 `.env.prod`（不入库）。其后 Build successful。
- 2026-11-04 — S9 浏览器 E2E 未跑；前端静态接线 + lint/build 作为非阻塞证据。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| 新 Workspace API | 本 sprint 计划/验收 + roadmap ADR | ok | `docs/superpowers/roadmaps/2026-11-03-opentask-linear-core.md` |
| Alembic 迁移 | 迁移文件入库 | ok | `backend/alembic/versions/2026_11_03_2355-a1b2c3d4e5f6_workspace_tenant_tables.py` |
| frontend `.env.prod` | 未改仓库内文件；仅本地复制 | n/a | 构建机惯例，与 Dockerfile 注释一致 |

## Delivered surface (S1)

- `POST /api/auth/register`（login crypto 同路径解密；同事务默认 Workspace + owner + tokens）
- Workspace CRUD + members；头 `X-Workspace-Id` 隔离 Project/Issue
- Alembic：workspaces / workspace_members；projects/issues.workspace_id + Default Workspace backfill
- 前端：真实注册表单；顶栏 Workspace 切换；请求注入 `X-Workspace-Id`

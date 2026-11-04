# Acceptance record — sprint E3-S3（Inbox 通知流）, 2026-11-04

## Verdict

**pass** — 必需场景 S1–S6 由 API/pytest + 前端 lint/build 证据通过；可选 S7（浏览器 E2E）本轮未跑，诚实标为 blocked。门禁：后端全量 `607 passed, 27 skipped, 0 failed`；前端 `npm run lint` 0 errors / 242 warnings（存量）；`npm run build` 成功。未推远程。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E3-S3-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E3-S3-acceptance.md","fingerprint":"d419c8e609b5341108b8b9584497f3ba8e98a7c8"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"d419c8e609b5341108b8b9584497f3ba8e98a7c8","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E3-S3；分支 sprint/E3-S3（基 S2 tip 4475f90）；PostgreSQL Docker opentask-pg-test；backend .venv python3.11；frontend npm/vite；Asia/Shanghai 2026-11-04 00:2x CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_inbox.py::test_assign_creates_notification"],"expected":"type=assigned 通知","observed":"PASSED","artifacts":["/tmp/e3s3-inbox-tests.txt"],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_inbox.py::test_comment_notifies_assignee_not_author"],"expected":"type=commented；作者无自通知","observed":"PASSED","artifacts":["/tmp/e3s3-inbox-tests.txt"],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_inbox.py::test_mention_notifies_workspace_member"],"expected":"type=mentioned","observed":"PASSED","artifacts":["/tmp/e3s3-inbox-tests.txt"],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_inbox.py::test_inbox_list_isolation"],"expected":"用户间通知 ID 不相交","observed":"PASSED","artifacts":["/tmp/e3s3-inbox-tests.txt"],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_inbox.py::test_mark_read_and_unread_filter"],"expected":"已读后 unread_only 不含该项","observed":"PASSED","artifacts":["/tmp/e3s3-inbox-tests.txt"],"blockers":[]},{"id":"S6","status":"passed","modality":"ui","environment":"real","steps":["npm run lint","npm run build"],"expected":"0 errors；build successful；铃铛+/inbox 入库","observed":"lint 0 errors / 242 warnings；Build successful；inbox-bell.vue + views/inbox/index.vue","artifacts":["/tmp/e3s3-lint.txt","/tmp/e3s3-build.txt"],"blockers":[]},{"id":"S7","status":"blocked","modality":"browser","environment":"real","steps":["未启动完整前后端联调浏览器会话"],"expected":"点铃铛可见列表并可进详情","observed":"未执行；API 证据覆盖通知流；前端静态组件入库","artifacts":[],"blockers":["本轮无浏览器 E2E 会话；可选场景，不阻塞 pass"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| S3 定向 | `cd backend && ./.venv/bin/python -m pytest tests/api/test_inbox.py -v` | **5 passed**（6.97s） |
| 全量 pytest | `cd backend && ./.venv/bin/python -m pytest tests/ -q` | **607 passed, 27 skipped, 0 failed**（203.13s） |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 242 warnings**（存量） |
| 前端 build | `cd frontend && npm run build`（`.env.prod`） | **Build successful** |

相对 S2：全量 602→607（+5 inbox 用例）。

## Scenario Results

| id | command / 用例 | expected | actual | pass |
|---|---|---|---|---|
| S1 | `test_assign_creates_notification` | assigned 通知 | PASSED | yes |
| S2 | `test_comment_notifies_assignee_not_author` | commented；无自通知 | PASSED | yes |
| S3 | `test_mention_notifies_workspace_member` | mentioned | PASSED | yes |
| S4 | `test_inbox_list_isolation` | 用户隔离 | PASSED | yes |
| S5 | `test_mark_read_and_unread_filter` | 已读过滤 | PASSED | yes |
| S6 | lint + build + 组件入库 | 0 error / build ok | PASSED | yes |
| S7 | 浏览器 Inbox | 可选 | **blocked** | n/a |

## DoD Checklist

- [x] Wave 1–3 Stories 完成（计划 / Notification 模型+挂钩+API / 前端 Inbox）
- [x] 定向 pytest 全绿（5/5）
- [x] 全量 pytest 无失败（607P/27S）
- [x] lint 0 errors + build 成功
- [x] acceptance 文档写入；sprint frontmatter `acceptance-record` 指向本文件
- [x] 提交在 `sprint/E3-S3`；**不推远程**

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E（S7）未跑；不阻塞 pass。
- 2026-11-04 — E3-S3 worktree 无独立 `.venv`/`node_modules`；符号链接到 E3-S1 的依赖树跑门禁（不入库）。
- 2026-11-04 — GitHub / Cloud Agent 仍未连；本轮仅本地 worktree，不推远程。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| Notification 模型 + alembic | yes | synced | `models/notification` + `c9d8e7f6a5b4` |
| IssueService 挂钩 | yes | synced | assign / comment+mention |
| Inbox API | yes | synced | `/api/inbox` |
| 前端铃铛 + `/inbox` | yes | synced | Naive UI / DESIGN.md |
| 邮件/IM | excluded | n/a | ADR D9 |

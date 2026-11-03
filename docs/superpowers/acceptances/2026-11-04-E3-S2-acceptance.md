# Acceptance record — sprint E3-S2（Issue 看板 + 列表双视图）, 2026-11-04

## Verdict

**pass** — 必需场景 S1–S6 由 API/pytest + 前端 lint/build 证据通过；可选 S7（浏览器拖拽 E2E）本轮未跑，诚实标为 blocked。门禁：后端全量 `602 passed, 27 skipped, 0 failed`；前端 `npm run lint` 0 errors / 242 warnings（存量）；`npm run build` 成功。未推远程。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E3-S2-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E3-S2-acceptance.md","fingerprint":"PENDING_IMPL_SHA"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"PENDING_IMPL_SHA","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E3-S2；分支 sprint/E3-S2（基 S1 tip 9659718）；PostgreSQL Docker opentask-pg-test；backend .venv python3.11；frontend npm/vite；Asia/Shanghai 2026-11-04 00:1x CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_issue_board.py::test_list_sort_by_position"],"expected":"按 position 升序","observed":"PASSED","artifacts":["/tmp/e3s2-board-tests.txt"],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_issue_board.py::test_board_move_updates_status_and_position"],"expected":"board/move 写 status+position","observed":"PASSED；POST /api/issues/board/move → 200","artifacts":["/tmp/e3s2-board-tests.txt"],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_issue_board.py::test_board_move_ordered_ids_rewrites_positions"],"expected":"ordered_ids 重写 position","observed":"PASSED","artifacts":["/tmp/e3s2-board-tests.txt"],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_issue_board.py::test_board_move_cross_workspace_forbidden"],"expected":"跨工作区 403 且不改写","observed":"PASSED","artifacts":["/tmp/e3s2-board-tests.txt"],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_issue_board.py::test_put_still_updates_status_and_position"],"expected":"PUT 兼容 status+position","observed":"PASSED","artifacts":["/tmp/e3s2-board-tests.txt"],"blockers":[]},{"id":"S6","status":"passed","modality":"ui","environment":"real","steps":["npm run lint","npm run build"],"expected":"0 errors；build successful；IssueBoard + list↔board 切换入库","observed":"lint 0 errors / 242 warnings；Build successful；组件 modules/IssueBoard.vue + list 双视图切换","artifacts":["/tmp/e3s2-lint2.txt","/tmp/e3s2-build.txt"],"blockers":[]},{"id":"S7","status":"blocked","modality":"browser","environment":"real","steps":["未启动完整前后端联调浏览器拖拽会话"],"expected":"看板拖拽后刷新一致","observed":"未执行；API 证据覆盖落盘；前端静态组件入库","artifacts":[],"blockers":["本轮无浏览器 E2E 会话；可选场景，不阻塞 pass"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| S2 定向 | `cd backend && ./.venv/bin/python -m pytest tests/api/test_issue_board.py -v` | **5 passed**（4.77s） |
| 全量 pytest | `cd backend && ./.venv/bin/python -m pytest tests/ -q` | **602 passed, 27 skipped, 0 failed**（202.71s） |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 242 warnings**（存量） |
| 前端 build | `cd frontend && npm run build`（本地 gitignored `.env.prod`） | **Build successful** |

相对 S1：全量 597→602（+5 board 用例）。

## Scenario Results

| id | command / 用例 | expected | actual | pass |
|---|---|---|---|---|
| S1 | `test_list_sort_by_position` | position 升序 | PASSED | yes |
| S2 | `test_board_move_updates_status_and_position` | status+position 持久化 | PASSED | yes |
| S3 | `test_board_move_ordered_ids_rewrites_positions` | 同列重排 | PASSED | yes |
| S4 | `test_board_move_cross_workspace_forbidden` | 403 | PASSED | yes |
| S5 | `test_put_still_updates_status_and_position` | PUT 兼容 | PASSED | yes |
| S6 | lint + build + 组件入库 | 0 error / build ok | PASSED | yes |
| S7 | 浏览器拖拽 | 可选 | **blocked** | n/a |

## DoD Checklist

- [x] Wave 1–3 Stories 完成（计划/后端 board/move + position 排序/前端双视图）
- [x] 定向 pytest 全绿（5/5）
- [x] 全量 pytest 无失败（602P/27S）
- [x] lint 0 errors + build 成功
- [x] acceptance 文档写入；sprint frontmatter `acceptance-record` 指向本文件
- [x] 提交在 `sprint/E3-S2`；**不推远程**

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E（S7）未跑；不阻塞 pass。
- 2026-11-04 — E3-S2 worktree 无独立 `.venv`/`node_modules`；符号链接到 E3-S1 的依赖树跑门禁（不入库）。
- 2026-11-04 — 首轮 lint 1 error：`IssueBoard` import 后模板未写入双视图分支；已补丁后 0 errors。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| 双视图呈现层 | 本 sprint 计划/验收 + roadmap D8 | ok | 未改 status 枚举 |
| board/move API | 测试 + router | ok | `POST /api/issues/board/move` |
| DESIGN.md | IssueBoard 用 Naive NCard/NTag + design-system 令牌 | ok | 无自创主题色 |

## Delivered surface (S2)

- `GET /api/issues?sort_by=position` 白名单排序（nulls last）
- `POST /api/issues/board/move`（status+position；可选 ordered_ids；工作区校验）
- 前端 `/issue/list`：列表 ↔ 看板切换；`IssueBoard.vue` 六列拖拽（vue-draggable-plus）
- PUT 更新 status+position 兼容保留

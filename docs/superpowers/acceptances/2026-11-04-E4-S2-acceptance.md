# Acceptance record — sprint E4-S2（Issue 列表分组泳道）, 2026-11-04

## Verdict

**pass** — 必需场景 S1–S6 由 vitest + saved-views API + 前端 lint/build + 全量 pytest 证据通过；可选 S7（浏览器 E2E）本轮未跑，诚实标为 blocked。门禁：后端全量 `613 passed, 27 skipped, 0 failed`；前端 vitest `7 passed`；`npm run lint` 0 errors / 245 warnings（存量）；`npm run build` 成功。未推远程。列表泳道为展示-only（跨泳道改字段 OUT）。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E4-S2-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E4-S2-acceptance.md","fingerprint":"021c25bc7965994f4b8e24aa6fc6cc4e40abf855"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"021c25bc7965994f4b8e24aa6fc6cc4e40abf855","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E4-S2；分支 sprint/E4-S2（基 E4-S1 tip cf748eb）；PostgreSQL Docker opentask-pg-test；backend .venv python3.11；frontend npm/vite/vitest；Asia/Shanghai 2026-11-04 08:0x–08:0x CST","results":[{"id":"S1","status":"passed","modality":"unit","environment":"real","steps":["vitest --run src/utils/groupIssuesBy.test.ts"],"expected":"priority/assignee/type/status 分桶与未分配正确","observed":"7 passed","artifacts":["/tmp/e4s2-vitest.txt"],"blockers":[]},{"id":"S2","status":"passed","modality":"unit","environment":"real","steps":["vitest none / empty 分支"],"expected":"none→[]；空输入→[]","observed":"PASSED","artifacts":["/tmp/e4s2-vitest.txt"],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["pytest tests/api/test_saved_views.py::test_saved_view_display_group_by"],"expected":"POST/PATCH display.group_by 往返","observed":"PASSED","artifacts":["/tmp/e4s2-sv-pytest.txt"],"blockers":[]},{"id":"S4","status":"passed","modality":"ui","environment":"real","steps":["index.vue 保存/应用/PATCH group_by；IssueListGrouped 入库","npm run lint","npm run build"],"expected":"控件与 payload 含 group_by；0 errors；build ok","observed":"lint 0 errors / 245 warnings；Build successful","artifacts":["/tmp/e4s2-lint2.txt","/tmp/e4s2-build.txt"],"blockers":[]},{"id":"S5","status":"passed","modality":"ui","environment":"real","steps":["npm run lint","npm run build"],"expected":"0 errors；build successful","observed":"0 errors；Build successful","artifacts":["/tmp/e4s2-lint2.txt","/tmp/e4s2-build.txt"],"blockers":[]},{"id":"S6","status":"passed","modality":"api","environment":"real","steps":["pytest tests/ -q"],"expected":"0 failed","observed":"613 passed, 27 skipped, 0 failed","artifacts":["/tmp/e4s2-pytest-full.txt"],"blockers":[]},{"id":"S7","status":"blocked","modality":"browser","environment":"real","steps":["未启动完整前后端联调浏览器会话"],"expected":"泳道可见可折叠","observed":"未执行；单元+静态门禁覆盖分组逻辑与控件入库","artifacts":[],"blockers":["本轮无浏览器 E2E 会话；可选场景，不阻塞 pass"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| vitest 定向 | `cd frontend && npm test -- --run src/utils/groupIssuesBy.test.ts` | **7 passed** |
| S3 定向 | `cd backend && ./.venv/bin/python -m pytest tests/api/test_saved_views.py -q` | **6 passed** |
| 全量 pytest | `cd backend && ./.venv/bin/python -m pytest tests/ -q` | **613 passed, 27 skipped, 0 failed**（210.10s） |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 245 warnings**（存量为主） |
| 前端 build | `cd frontend && npm run build`（`.env.prod`） | **Build successful** |

相对 E4-S1：全量 612→613（+1 display.group_by 用例）；vitest +7。

## Scenario Results

| id | command / 用例 | expected | actual | pass |
|---|---|---|---|---|
| S1 | `groupIssuesBy.test.ts` 分桶 | 键/计数/未分配 | 7 passed | yes |
| S2 | none / empty | 空桶约定 | PASSED | yes |
| S3 | `test_saved_view_display_group_by` | display 往返 | PASSED | yes |
| S4 | 列表分组 UI + Saved View 联动 | 入库 | PASSED | yes |
| S5 | lint + build | 0 error / build ok | PASSED | yes |
| S6 | 全量 pytest | 0 failed | 613P/27S | yes |
| S7 | 浏览器分组 | 可选 | **blocked** | n/a |

## DoD Checklist

- [x] Wave 1–3 Stories 完成（计划 / groupIssuesBy+vitest / IssueListGrouped + 工具栏 + display.group_by）
- [x] 可按 none/status/assignee/priority/type 分组且与筛选一致（客户端 filteredIssues）
- [x] 列表泳道展示-only（文档与 UI hint 写明无跨道 mutation）
- [x] 定向 vitest + saved-views pytest 全绿
- [x] 全量 pytest 无失败（613P/27S）
- [x] lint 0 errors + build 成功
- [x] acceptance 文档写入；sprint frontmatter 指向本文件
- [x] 提交在 `sprint/E4-S2`；**不推远程**
- [x] 未做 S3 parent_issue_id / ⌘K / 共享视图

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E（S7）未跑；不阻塞 pass。
- 2026-11-04 — E4-S2 worktree 依赖符号链接到 E3-S1 的 `.venv`/`node_modules`（不入库）。
- 2026-11-04 — 未推远程；S3 未开工。
- 2026-11-04 — 列表跨泳道拖拽改字段明确 OUT；看板 status 拖拽保持 IssueBoard 既有。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| groupIssuesBy + vitest | yes | synced | `frontend/src/utils/groupIssuesBy.ts` |
| IssueListGrouped 泳道 | yes | synced | Naive Collapse + DESIGN 令牌 |
| display.group_by 读写 | yes | synced | 保存/应用/PATCH；pytest 往返 |
| 客户端分组 ADR | yes | synced | Q3 closed；D5 |
| 跨泳道 mutation | excluded | n/a | 展示-only |
| S3 parent_issue_id | deferred | planned | 下一批 |
| 共享视图 / ⌘K | excluded | n/a | Epic exclusions |

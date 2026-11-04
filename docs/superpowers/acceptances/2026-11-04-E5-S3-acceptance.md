# Acceptance record — sprint E5-S3（焦点 + 热键 + ⌘B + 看板 URL / Epic 收口）, 2026-11-04

## Verdict

**pass** — S3 范围交付：`useIssueFocus`（list/board/detail）、C/A/S/P/I（ignoreWhenEditable；面板开时单键不抢）、Naive pickers + assign-to-me、⌘B/Ctrl+B Board↔List（`useIssueListViewMode` 与 UI 按钮同源）、看板详情 `buildIssueDetailLocation` → `?id=`（click=focus / dblclick=打开）。门禁：vitest 定向 **42 passed**；`npm run lint` **0 errors** / 249 warnings（存量）；`npm run build` 成功；全量 pytest **621 passed, 27 skipped, 0 failed**。未做 Cycles / Labels L / G-then-X / 模态创建 / 远程推送。Epic E5 标 **local-complete**（merged-commit null）。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E5-S3-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E5-S3-acceptance.md","fingerprint":"49486095b253f0368313444a3522efd83d453887"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"49486095b253f0368313444a3522efd83d453887","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E5-S3；分支 sprint/E5-S3（基 E5-S2 tip f5c70d1）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite/vitest；Asia/Shanghai 2026-11-04 09:43–09:50 CST","results":[{"id":"T1","status":"passed","modality":"unit","environment":"real","steps":["useIssueFocus set/clear/ensureDetail"],"expected":"焦点 id 正确","observed":"vitest use-issue-focus","artifacts":[],"blockers":[]},{"id":"T2","status":"passed","modality":"unit","environment":"real","steps":["resolveIssueHotkeyAction editable/palette"],"expected":"单键忽略","observed":"vitest issue-hotkeys","artifacts":[],"blockers":[]},{"id":"T3","status":"passed","modality":"unit","environment":"real","steps":["buildIssueDetailLocation"],"expected":"path+/query id","observed":"vitest issue-board-nav","artifacts":[],"blockers":[]},{"id":"T4","status":"passed","modality":"unit","environment":"real","steps":["toggleListBoardMode","useIssueListViewMode"],"expected":"list↔board","observed":"vitest","artifacts":[],"blockers":[]},{"id":"T5","status":"passed","modality":"unit","environment":"real","steps":["C → create"],"expected":"{type:create}","observed":"vitest resolveIssueHotkeyAction","artifacts":[],"blockers":[]},{"id":"T6","status":"passed","modality":"code","environment":"real","steps":["picker host + updateStatus/Assignee/Priority + assign-me"],"expected":"API 复用","observed":"issue-hotkey-picker-host + useAppHotkeys","artifacts":[],"blockers":[]},{"id":"T7","status":"passed","modality":"cli","environment":"real","steps":["vitest 42","lint 0 errors","build","pytest 621"],"expected":"门禁绿","observed":"全部通过","artifacts":["/tmp/e5s3-lint2.txt","/tmp/e5s3-build.txt","/tmp/e5s3-pytest.txt"],"blockers":[]},{"id":"R-browser","status":"blocked","modality":"browser","environment":"real","steps":["未跑浏览器联调 R6–R10"],"expected":"手感验收","observed":"单元+静态门禁；不阻塞 S3/Epic pass","artifacts":[],"blockers":["本轮无浏览器 E2E 会话"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| vitest 定向 | `cd frontend && npm test -- --run src/utils/issue-hotkeys.test.ts src/utils/issue-board-nav.test.ts src/composables/use-issue-focus.test.ts src/composables/use-issue-list-view-mode.test.ts src/utils/hotkeys.test.ts src/utils/command-palette.test.ts src/utils/command-palette-entities.test.ts src/composables/use-command-palette.test.ts` | **42 passed** |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 249 warnings** |
| 前端 build | `cd frontend && npm run build`（`.env.prod` 本地拷贝，不入库） | **Build successful** |
| 全量 pytest | `cd backend && .venv/bin/pytest tests/ -q` | **621 passed, 27 skipped, 0 failed**（186.89s） |

## Scenario Results

| id | expected | actual | pass |
|---|---|---|---|
| T1 focus | set/clear/detail | vitest | yes |
| T2 routing | editable/palette 忽略 | vitest | yes |
| T3 board URL | ?id= | vitest + IssueBoard | yes |
| T4 ⌘B | list↔board | vitest + singleton | yes |
| T5 C | create | vitest | yes |
| T6 A/S/P/I | pickers / assign-me | host + hotkeys | yes |
| T7 门禁 | 绿 | 通过 | yes |
| 浏览器 R6–R10 | 可选 | **blocked** | n/a |

## DoD Checklist

- [x] 计划 / sprint 台账 / focus / hotkeys / pickers / ⌘B / board URL / 门禁
- [x] list/board/detail 焦点可用；C/A/S/P/I；ignoreWhenEditable
- [x] ⌘B 与列表 UI 同源；看板详情 query id
- [x] 全量 pytest 无新增失败；lint 0 errors；build 成功
- [x] acceptance 写入；sprint state=closed；roadmap S3 closed；**Epic local-complete**；**merged-commit null**；**不推远程**
- [x] 未实现：Cycles、Labels L、G-then-X、模态创建

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E 未跑；不阻塞 S3/Epic pass。
- 2026-11-04 — `uv run pytest` 可能因镜像拉取失败；改用既有 `.venv/bin/pytest` 回归成功。
- 2026-11-04 — 未推远程；Epic local-complete 仅本地台账。

## Doc-Drift Audit

| map row | matched | detail |
|---|---|---|
| useIssueFocus | yes | composables/use-issue-focus.ts |
| useAppHotkeys C/A/S/P/I/⌘B | yes | composables/use-app-hotkeys.ts + utils/issue-hotkeys.ts |
| useIssueListViewMode | yes | composables/use-issue-list-view-mode.ts |
| pickers host | yes | issue-hotkey-picker-host.vue |
| board ?id= | yes | utils/issue-board-nav.ts + IssueBoard.vue |
| Cycles / Labels L / G-then-X | excluded | E6+ |

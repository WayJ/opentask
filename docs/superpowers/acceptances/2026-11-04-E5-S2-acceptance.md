# Acceptance record — sprint E5-S2（命令面板实体搜索）, 2026-11-04

## Verdict

**pass** — S2 范围交付：防抖实体搜索分组（Issues title/`by_code`、Projects 客户端过滤、Saved Views→`/issue/list?view=` apply）、`getIssue(..., { byCode })`、`deriveListStateFromSavedView` 共享 apply、跨组键盘仍走 flatten。门禁：vitest 定向 **31 passed**；`npm run lint` **0 errors** / 248 warnings（存量）；`npm run build` 成功；全量 pytest **621 passed, 27 skipped, 0 failed**。未做焦点/C/A/S/P/I/⌘B/看板 URL（S3）。未推远程。Epic E5 仍 **active**。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E5-S2-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E5-S2-acceptance.md","fingerprint":"96b2ffcbe0b850df45fe3e6ddafc5946ac7d8eb5"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"96b2ffcbe0b850df45fe3e6ddafc5946ac7d8eb5","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E5-S2；分支 sprint/E5-S2（基 E5-S1 tip 3075de2）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite/vitest；Asia/Shanghai 2026-11-04 09:34–09:42 CST","results":[{"id":"S1","status":"passed","modality":"unit","environment":"real","steps":["buildPaletteGroups empty query hides entities"],"expected":"仅 Actions","observed":"vitest entity sections","artifacts":[],"blockers":[]},{"id":"S2","status":"passed","modality":"unit","environment":"real","steps":["issuesToPaletteItems run → detail?id="],"expected":"/issue/detail?id=","observed":"vitest mappers","artifacts":[],"blockers":[]},{"id":"S3","status":"passed","modality":"unit","environment":"real","steps":["looksLikeIssueCode","resolveIssueSearchPlan","buildIssueDetailParams"],"expected":"by_code=true","observed":"vitest entities + issue-by-code","artifacts":[],"blockers":[]},{"id":"S4","status":"passed","modality":"unit","environment":"real","steps":["projectsToPaletteItems","filterByNameQuery"],"expected":"project-detail?id=","observed":"vitest","artifacts":[],"blockers":[]},{"id":"S5","status":"passed","modality":"unit","environment":"real","steps":["deriveListStateFromSavedView","list ?view= applySavedViewById"],"expected":"filters/tab/display 恢复","observed":"vitest + list wiring","artifacts":[],"blockers":[]},{"id":"S6","status":"passed","modality":"unit","environment":"real","steps":["composable setEntitySources flatten moveDown"],"expected":"跨组导航","observed":"vitest useCommandPalette entity sources","artifacts":[],"blockers":[]},{"id":"S7","status":"passed","modality":"cli","environment":"real","steps":["vitest 31","lint 0 errors","build","pytest 621"],"expected":"门禁绿","observed":"全部通过","artifacts":["/tmp/e5s2-lint2.txt","/tmp/e5s2-build.txt","/tmp/e5s2-pytest.txt"],"blockers":[]},{"id":"R-browser","status":"blocked","modality":"browser","environment":"real","steps":["未跑浏览器联调"],"expected":"R4–R5 手感","observed":"单元+静态门禁；不阻塞 S2 pass","artifacts":[],"blockers":["本轮无浏览器 E2E 会话"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| vitest 定向 | `cd frontend && npm test -- --run src/utils/command-palette-entities.test.ts src/utils/apply-saved-view.test.ts src/utils/command-palette.test.ts src/composables/use-command-palette.test.ts src/service/api/issue-by-code.test.ts src/utils/hotkeys.test.ts` | **31 passed** |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 248 warnings** |
| 前端 build | `cd frontend && npm run build`（`.env.prod` 本地拷贝，不入库） | **Build successful** |
| 全量 pytest | `cd backend && .venv/bin/pytest tests/ -q` | **621 passed, 27 skipped, 0 failed**（201.35s） |

## Scenario Results

| id | expected | actual | pass |
|---|---|---|---|
| S1 空 query | 仅 Actions | vitest | yes |
| S2 Issue 标题 | detail?id= | vitest mappers + host search | yes |
| S3 Issue code | by_code | vitest plan/params | yes |
| S4 Projects | project-detail | vitest | yes |
| S5 Saved View | list?view= apply | derive + list watch | yes |
| S6 跨组键盘 | flatten | vitest | yes |
| S7 门禁 | 绿 | 通过 | yes |
| 浏览器 R4–R5 | 可选 | **blocked** | n/a |

## DoD Checklist

- [x] 计划 / sprint 台账 / helpers / byCode / host 防抖 / list `?view=` / i18n / 门禁
- [x] 有 query 时 Issues / Projects / Views 分组；空 query 仅 Actions
- [x] Saved View 跳 list 并应用筛选（共享 derive）
- [x] 全量 pytest 无新增失败；lint 0 errors；build 成功
- [x] acceptance 写入；sprint state=closed；roadmap S2 closed；**Epic 仍 active**；**不推远程**
- [x] 未实现 S3：焦点、C/A/S/P/I、⌘B、看板 URL

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E 未跑；不阻塞 S2 pass。
- 2026-11-04 — `uv run pytest` 因镜像 403 不可用；改用既有 `.venv/bin/pytest` 回归成功。
- 2026-11-04 — 未推远程；Epic E5 仍 active（S3 待做）。

## Doc-Drift Audit

| map row | matched | detail |
|---|---|---|
| looksLikeIssueCode / resolveIssueSearchPlan | yes | utils/command-palette-entities.ts |
| getIssue byCode | yes | service/api/issue.ts + buildIssueDetailParams |
| buildPaletteGroups entity sections | yes | utils/command-palette.ts |
| deriveListStateFromSavedView | yes | utils/apply-saved-view.ts |
| host debounce 300ms | yes | command-palette-host.vue useDebounceFn |
| list ?view= | yes | issue/list/index.vue watch + onMounted |
| focus / C/A/S/P/I / ⌘B / board URL | excluded | S3 |

# Acceptance record — sprint E4-S3（一等公民子 Issue）, 2026-11-04

## Verdict

**pass** — 必需场景 S1–S8 由 `test_sub_issues.py` + vitest `nestIssuesDepth1` + 前端 lint/build + 全量 pytest 证据通过；可选 S9（浏览器 E2E）本轮未跑，诚实标为 blocked。门禁：后端全量 `621 passed, 27 skipped, 0 failed`；定向 sub-issues `8 passed`；vitest `4 passed`；`npm run lint` 0 errors / 247 warnings（存量）；`npm run build` 成功。未推远程。父子用 `parent_issue_id`，未改 IssueRelation。列表嵌套为客户端 **depth-1**（父不在当前筛选/分页结果则子作顶层）。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E4-S3-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E4-S3-acceptance.md","fingerprint":"1630c27b8d3ee5599c56834a75439869f5eec96a"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"1630c27b8d3ee5599c56834a75439869f5eec96a","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E4-S3；分支 sprint/E4-S3（基 E4-S2 tip 1e79a91）；PostgreSQL Docker opentask-pg-test；backend .venv python3.11；frontend npm/vite/vitest；Asia/Shanghai 2026-11-04 08:08–08:16 CST","results":[{"id":"S1","status":"passed","modality":"api","environment":"real","steps":["pytest test_create_child_issue_with_parent"],"expected":"200 + parent_issue_id","observed":"PASSED","artifacts":["/tmp/e4s3-pytest-full.txt"],"blockers":[]},{"id":"S2","status":"passed","modality":"api","environment":"real","steps":["test_get_and_list_expose_parent_and_children"],"expected":"parent_issue_id + children + GET /children","observed":"PASSED","artifacts":["/tmp/e4s3-pytest-full.txt"],"blockers":[]},{"id":"S3","status":"passed","modality":"api","environment":"real","steps":["test_reject_self_parent"],"expected":"400","observed":"PASSED","artifacts":["/tmp/e4s3-pytest-full.txt"],"blockers":[]},{"id":"S4","status":"passed","modality":"api","environment":"real","steps":["test_reject_cross_workspace_parent","test_reject_missing_parent"],"expected":"400","observed":"PASSED","artifacts":["/tmp/e4s3-pytest-full.txt"],"blockers":[]},{"id":"S5","status":"passed","modality":"api","environment":"real","steps":["test_child_not_listed_in_other_workspace"],"expected":"他工作区 list 不含父子","observed":"PASSED","artifacts":["/tmp/e4s3-pytest-full.txt"],"blockers":[]},{"id":"S6","status":"passed","modality":"unit","environment":"real","steps":["vitest nestIssuesDepth1.test.ts"],"expected":"depth-1 顺序/孤儿顶层","observed":"4 passed","artifacts":[],"blockers":[]},{"id":"S7","status":"passed","modality":"ui","environment":"real","steps":["npm run lint","npm run build"],"expected":"0 errors；build ok","observed":"0 errors / 247 warnings；Build successful","artifacts":[],"blockers":[]},{"id":"S8","status":"passed","modality":"api","environment":"real","steps":["pytest tests/ -q"],"expected":"0 failed","observed":"621 passed, 27 skipped, 0 failed","artifacts":["/tmp/e4s3-pytest-full.txt"],"blockers":[]},{"id":"S9","status":"blocked","modality":"browser","environment":"real","steps":["未启动完整前后端联调浏览器会话"],"expected":"详情/列表可见嵌套","observed":"未执行；API+单元+静态门禁覆盖","artifacts":[],"blockers":["本轮无浏览器 E2E 会话；可选场景，不阻塞 pass"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| 定向 sub-issues | `cd backend && ./.venv/bin/python -m pytest tests/api/test_sub_issues.py -q` | **8 passed** |
| vitest 定向 | `cd frontend && npm test -- --run src/utils/nestIssuesDepth1.test.ts` | **4 passed** |
| 全量 pytest | `cd backend && ./.venv/bin/python -m pytest tests/ -q` | **621 passed, 27 skipped, 0 failed**（206.93s） |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 247 warnings**（存量为主） |
| 前端 build | `cd frontend && npm run build`（`.env.prod`） | **Build successful** |

相对 E4-S2：全量 613→621（+8 sub-issues）；vitest +4。

## Scenario Results

| id | command / 用例 | expected | actual | pass |
|---|---|---|---|---|
| S1 | create child | parent_issue_id | PASSED | yes |
| S2 | get/list/children | 父子字段 | PASSED | yes |
| S3 | self-parent | 400 | PASSED | yes |
| S4 | cross-ws / missing | 400 | PASSED | yes |
| S5 | workspace isolation | 不可见 | PASSED | yes |
| S6 | nestIssuesDepth1 | 4 passed | PASSED | yes |
| S7 | lint + build | 0 error / build ok | PASSED | yes |
| S8 | 全量 pytest | 0 failed | 621P/27S | yes |
| S9 | 浏览器 | 可选 | **blocked** | n/a |

另：`test_reject_cycle_parent`、`test_clear_parent_with_null` 一并绿（环检测 + null 清空）。

## DoD Checklist

- [x] Wave 1–3 完成（计划 / model+API+校验 / 列表嵌套+详情父子）
- [x] 可建父子；list/get 暴露 `parent_issue_id`；详情 children + 添加子 Issue
- [x] 拒自指、缺父、跨工作区、环
- [x] 列表 depth-1 客户端嵌套（文档写明）
- [x] 定向 + 全量 pytest 全绿
- [x] lint 0 errors + build 成功
- [x] acceptance 文档写入；sprint frontmatter 指向本文件
- [x] 提交在 `sprint/E4-S3`；**不推远程**
- [x] 未用 IssueRelation 表达父子；未做 ⌘K / Cycles / Labels / 共享视图

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E（S9）未跑；不阻塞 pass。
- 2026-11-04 — E4-S3 worktree 依赖符号链接到 E3-S1 的 `.venv`/`node_modules`（不入库）。
- 2026-11-04 — 未推远程；Epic E4 S1–S3 本地齐，status→`local-complete`（merged-commit 仍 null）。
- 2026-11-04 — 列表嵌套仅 depth-1；更深层级仍以 depth=1 展示约定。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| parent_issue_id FK + migration | yes | synced | `e1f2a3b4c5d6` after saved_views |
| API create/update/get/children | yes | synced | ValueError→400 |
| nestIssuesDepth1 + vitest | yes | synced | depth-1 |
| 详情父链接 / 子列表 / 添加 | yes | synced | Naive UI |
| IssueRelation 父子 | excluded | n/a | 未改 enums |
| 共享视图 / ⌘K | excluded | n/a | Epic exclusions |

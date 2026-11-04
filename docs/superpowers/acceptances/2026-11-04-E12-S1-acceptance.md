# E12-S1 Acceptance — Workspace.issue_key + KEY-N + dual-parse

**Verdict:** **pass**

**pass** — S1 范围交付：`workspaces.issue_key`/`issue_counter`（平台 UNIQUE）+ Alembic `b8c9d0e1f2a4`（revises `a7b8c9d0e1f3`）存量回填 + `issues.legacy_issue_code`；新建 Issue 分配 `KEY-N`；改 `issueKey` 仅影响新单；`get_issue(by_code)` 双解析（code∨legacy）并在带 `X-Workspace-Id` 时按 workspace 过滤；列表 search 含 code/legacy；Workspace API/FE 设置读写 `issueKey`；CLI/`looksLikeIssueCode` 认 KEY-N；Jira key 编解码在 **不改写** legacy 年号公式前提下增加 KEY-N 独立号段双读（避免全量门禁被污染 KEY-N 行打爆）。**未**做 invites / 成员 UI / SMTP / 去 PGE。未推远程。

**Fingerprint (impl tip):** `bad406b53512d1509ad812d1b846125dcb5d206f`
**Branch tip:** `77ab2d53b88a711075e30e91ff668acec086807b`
**Branch:** `sprint/E12-S1`
**Worktree:** `/workspace/opentask-worktrees/E12-S1`
**Plan:** `docs/superpowers/plans/2026-11-04-e12-s1-issue-key.md` @ `c46e9ba86972b9a6a10ac7d4e30ce1902c699ea4`
**Migration:** `b8c9d0e1f2a4` (revises `a7b8c9d0e1f3`)
**Time (Asia/Shanghai):** 2026-11-04 ~12:08 CST

```supervibe-acceptance-results
{"schema": 1, "scope": "sprint", "candidate": "bad406b53512d1509ad812d1b846125dcb5d206f", "environment": "共享 box Linux；worktree /workspace/opentask-worktrees/E12-S1；分支 sprint/E12-S1（基 E8-S3 tip 9fef926）；PostgreSQL portable；backend .venv→E8-S1；frontend node_modules→E8-S1；Asia/Shanghai 2026-11-04 ~12:08 CST", "results": [{"id": "S1", "status": "passed", "modality": "api", "environment": "real", "steps": ["pytest tests/api/test_issue_key.py"], "expected": "issueKey/KEY-N/dual-parse/cross-WS 404", "observed": "8 PASSED", "artifacts": [], "blockers": []}, {"id": "S2", "status": "passed", "modality": "code", "environment": "real", "steps": ["models+alembic+services+FE issueKey+CLI"], "expected": "分配/回填/设置/CLI", "observed": "入库", "artifacts": [], "blockers": []}, {"id": "S3", "status": "passed", "modality": "cli", "environment": "real", "steps": ["pytest tests/ -q", "vitest command-palette-entities", "eslint touched FE"], "expected": "≥700+new / ⌘K KEY-N / 0 eslint", "observed": "708 passed, 27 skipped, 0 failed；vitest 8 passed；eslint 0", "artifacts": [], "blockers": ["pnpm run build 因跨 worktree node_modules/unocss 配置读取失败（环境）；非本 Sprint 逻辑回归"]}, {"id": "R-browser", "status": "blocked", "modality": "browser", "environment": "real", "steps": ["未跑浏览器 E2E"], "expected": "手感", "observed": "API+静态门禁覆盖；不阻塞 S1 pass", "artifacts": [], "blockers": ["本轮无浏览器 E2E 会话"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -q` | **708 passed, 27 skipped, 0 failed** |
| Issue key API | `pytest tests/api/test_issue_key.py -v` | **8 passed** |
| ⌘K vitest | `vitest run src/utils/command-palette-entities.test.ts` | **8 passed** |
| CLI auto-detect | `pytest agent-harness/.../test_issue_auto_detect.py` | **4 passed** |
| Frontend lint (touched) | `eslint workspace.ts cycles/index.vue --quiet` | **0 errors** |
| Frontend build | `pnpm run build` | **blocked (env symlink/unocss)** — 不阻塞 S1 |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | KEY-N create + issueKey patch + by_code + legacy + cross-WS | API 绿 | PASSED | yes |
| S2 | Alembic backfill + FE settings + CLI | 入库 | PASSED | yes |
| S3 | Full pytest ≥ prior 700 + new | 708 / 0 failed | PASSED | yes |

## APIs / schema

- `WorkspaceOut.issueKey`；`PATCH /api/workspaces/{id}` `{ issueKey }`
- `POST /api/issues` → `issue_code` = `{issueKey}-{n}`（需 `X-Workspace-Id`）
- `GET /api/issues/{code}?by_code=true` + `X-Workspace-Id`：code ∨ `legacy_issue_code`，租户过滤
- Alembic `b8c9d0e1f2a4`

## Leftover / gaps vs design S1 ACs

- 全量 `pnpm run build` 本环境因 `node_modules` 指向 E8-S1 触发 unocss `replace` 失败（非产品逻辑）；eslint + vitest 已绿
- 未做浏览器 E2E
- Jira：仅 KEY-N **双读投影**（独立号段），**未**重做 legacy 年号公式（符合 exclusion）
- orphan 无 `workspace_id` 创建仍走 `ISSUE{year}-N`（设计允许）
- **未**开 S2 invites / S3 de-PGE；**未推远程**；`merged-commit: null`

## Notes

- Mid-epic：不单独找 Way/Yuri；Epic 收口后再回执。

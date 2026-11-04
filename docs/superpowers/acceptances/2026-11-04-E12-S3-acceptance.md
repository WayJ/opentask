# E12-S3 Acceptance — de-PGE + Epic local-complete

**Verdict:** **pass**

**pass** — S3 范围交付：主菜单隐藏 `workflow_requirements`（深链保留）；CreatePGE 入口 tertiary「创建任务（遗留·已弃用）」；`.env.example` `VITE_ROUTE_HOME=issue_list`；i18n「需求（遗留）」；PGE `/api/tasks`（create/preview/prompt）`deprecated=True` + 响应头 `Deprecation: true`；`CodingWorker.md` 重写为 Issue/KEY-N 驱动（PGE 指南仅可选遗留）。**未** DROP `requirements`/PGE 相关表；事件溯源/CLI/Agent 能力保留。全量 pytest **726**；vitest de-pge-nav **3**。Epic E12 **local-complete**（S1–S3）。未推远程。`merged-commit: null`。**未**启动 E9。

**Fingerprint (impl tip):** `998382035a9063ee57cdb2880f5de69f6a95b471`
**Branch tip:** `e0b0d92c94ec7c6f8a11f785f59cc49e858ef670`
**Branch:** `sprint/E12-S3`
**Worktree:** `/workspace/opentask-worktrees/E12-S3`
**Plan:** `docs/superpowers/plans/2026-11-04-e12-s3-de-pge.md` @ `5f2daa7f5054f673716e55a3ccfc32a7a22f1ce1`
**Epic tip (handoff for E9 / Yuri receipt):** `e0b0d92c94ec7c6f8a11f785f59cc49e858ef670`
**Time (Asia/Shanghai):** 2026-11-04 ~12:25 CST

```supervibe-acceptance-results
{"schema": 1, "scope": "sprint", "candidate": "998382035a9063ee57cdb2880f5de69f6a95b471", "environment": "共享 box Linux；worktree /workspace/opentask-worktrees/E12-S3；分支 sprint/E12-S3（基 E12-S2 tip 0b4a225）；PostgreSQL portable；backend .venv→E8-S1；frontend node_modules→E8-S1；Asia/Shanghai 2026-11-04 ~12:25 CST", "results": [{"id": "S1", "status": "passed", "modality": "api", "environment": "real", "steps": ["pytest tests/api/test_pge_deprecation.py", "pytest tests/test_codingworker_de_pge.py"], "expected": "Deprecation header + CodingWorker Issue-first", "observed": "5 PASSED", "artifacts": [], "blockers": []}, {"id": "S2", "status": "passed", "modality": "code", "environment": "real", "steps": ["hideInMenu requirements", "demote CreatePGE", "CodingWorker rewrite", "VITE_ROUTE_HOME"], "expected": "主路径去 PGE 强制；表/API 保留", "observed": "入库", "artifacts": [], "blockers": []}, {"id": "S3", "status": "passed", "modality": "cli", "environment": "real", "steps": ["pytest tests/ -q", "vitest de-pge-nav", "eslint touched"], "expected": "≥721+new / vitest / 0 eslint", "observed": "726 passed, 27 skipped；vitest 3 passed；eslint 0", "artifacts": [], "blockers": ["pnpm build 跨 worktree unocss 环境限制同前；无浏览器 E2E"]}, {"id": "R-browser", "status": "blocked", "modality": "browser", "environment": "real", "steps": ["未跑浏览器 E2E"], "expected": "手感", "observed": "API+静态门禁；不阻塞 Epic pass", "artifacts": [], "blockers": ["本轮无浏览器 E2E"]}]}
```

## Gates

| Gate | Command | Result |
|---|---|---|
| Backend pytest | `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -q` | **726 passed, 27 skipped, 0 failed** |
| de-PGE smoke | `pytest tests/api/test_pge_deprecation.py tests/test_codingworker_de_pge.py -v` | **5 passed** |
| FE vitest | `vitest run src/router/__tests__/de-pge-nav.test.ts` | **3 passed** |
| FE eslint (touched) | `eslint … --quiet` | **0 errors** |
| Frontend build | `pnpm run build` | **blocked (env symlink/unocss)** — 不阻塞 S3/Epic |

## Scenario matrix

| id | scenario | expected | result | blocking |
|---|---|---|---|---|
| S1 | Deprecation header + CodingWorker assertions | API/文档绿 | PASSED | yes |
| S2 | hideInMenu + demote PGE UI + Issue-first worker | 入库 | PASSED | yes |
| S3 | Full pytest ≥ 721 + new | 726 / 0 failed | PASSED | yes |

## Hidden / deprecated vs retained

| Surface | Action |
|---|---|
| 侧栏 `workflow_requirements` | **hideInMenu**；路径 `/workflow/requirements` 深链保留 |
| CreatePGE 按钮 | **demote** tertiary +「遗留·已弃用」；modal 代码保留 |
| `VITE_ROUTE_HOME` | **issue_list**（example） |
| `POST/GET /api/tasks*` PGE | **deprecated** OpenAPI + `Deprecation: true`；仍 2xx |
| `CodingWorker.md` | **rewrite** Issue-first；PGE 指南可选 |
| DB tables / event-sourcing / CLI | **retained**（无 DROP） |

## Leftover / gaps

- 未改权限 seed（设计：FE 静态隐藏即可）
- AgentPromptModal 本已 Issue 向，未大改
- `docs/PGE_TASK_USER_GUIDE.md` 保留为遗留文档，未删
- 浏览器 E2E / 全量 `pnpm build` 环境限制
- **未**开 E9；**未推远程**

## Notes

- Epic 收口 tip 供 parent 回执 Yuri；本 Sprint 不单独打扰。

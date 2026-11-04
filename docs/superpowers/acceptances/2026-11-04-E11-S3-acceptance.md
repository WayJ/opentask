# E11-S3 Acceptance — Status hooks + polish + Epic local-complete

**Date:** 2026-11-04 (Asia/Shanghai)  
**Worktree:** `/workspace/opentask-worktrees/E11-S3` · `sprint/E11-S3`  
**Plan SHA:** `999fc6d29eab349b2f58e72dae58f98f09efbcf5`  
**Impl tip (pre-docs):** `e81076e78e4475852fe46a16312b6aaf66b5cdfb`  
**Baseline:** E11-S2 `da6b140` (794 pytest)

## Scope delivered

- [x] Workspace `git_status_hooks_enabled` (default **false**) + `git_hook_on_pr_open` / `git_hook_on_pr_merged`
- [x] Alembic `e5f6a7b8c9d0` ← `d4e5f6a7b8c9`
- [x] Webhook applies Issue status **only when enabled**: open/draft→`in_progress` (from `open` only); merged→`resolved`; closed-unmerged no-op
- [x] FE Workspace settings Toggle「从 PR 自动更新 Issue 状态」
- [x] CLI/Agent contract doc + CodingWorker.md VCS section (same HTTP)
- [x] Full `pytest tests/` green
- [x] Epic E11 local-complete; **no** live GitHub App; **no** push; **no** next epic started

## Evidence

| Check | Result |
|---|---|
| `cd backend && pytest tests/` | **803 passed**, 27 skipped |
| Unit hook helpers | 2 passed |
| WS settings API | 2 passed (default false; PATCH enable) |
| Webhook hook matrix | 5 passed (off/on/open/merged/in_progress/closed) |
| Contract | `docs/superpowers/contracts/2026-11-04-e11-vcs-http-contract.md` |

## Hook behavior

| WS hooks | PR event | Issue before | Issue after |
|---|---|---|---|
| off | open | open | open |
| on | open/draft | open | in_progress |
| on | open | in_progress | in_progress (unchanged) |
| on | merged | * | resolved (unless closed/rejected) |
| on | closed (unmerged) | * | unchanged |

## Gaps (non-blocking)

- Live GitHub App / OAuth / remote create PR — out of E11 DoD (Approach A)
- Remote push of sprint branches
- Configurable target statuses exposed in FE beyond defaults (API fields exist; UI is enable toggle)

## Yuri four ACs

1. Branch naming — S1  
2. PR↔Issue — S2  
3. Optional status hooks — **S3**  
4. CLI/Agent same HTTP — S1–S3 + contract doc  

# E11-S1 Acceptance — Branch naming + issue_vcs_links

**Date:** 2026-11-04 (Asia/Shanghai)  
**Worktree:** `/workspace/opentask-worktrees/E11-S1` · `sprint/E11-S1`  
**Plan SHA:** `26619ac`  
**HEAD at acceptance:** `d8328cc7ac6f24ddeb60ddba905ee67d34f51de4`  
**Baseline:** E10-S3 `55ed5b7` · docs tip `d9bdf4c`

## Scope delivered

- [x] Branch template `{issue_code}-{slug}` helpers + unit tests
- [x] `issue_vcs_links` table/model (Alembic `d4e5f6a7b8c9` ← `c3d4e5f6a7b8`) — **not** `requirement_repos`
- [x] API: `GET .../vcs/branch-name`; `GET/POST/DELETE .../vcs/links`
- [x] FE Issue detail「复制分支名」
- [x] CLI `issue branch-name` / `issue link-branch` / `issue vcs-links` → same HTTP
- [x] Full pytest green
- [x] No push; no S2 webhook; no S3 status hooks product

## Evidence

| Check | Result |
|---|---|
| `pytest tests/` | **783 passed**, 27 skipped |
| Unit branch naming | 9 passed |
| API VCS | 5 passed (suggest, CRUD, viewer 403, cross-WS 404) |
| CLI tests | help + client path assertions |
| FE eslint (touched) | 0 errors on issue-vcs + detail after button wire |

## Out of sprint (deferred)

- S2: GitHub-compatible webhook ingest + PR panel polish
- S3: optional status hooks toggle
- Live GitHub App / OAuth / remote create PR
- Remote push of this branch

## Notes

- PR `kind=pull_request` create allowed via API for skeleton; webhook upsert is S2.
- `parse_issue_code_from_branch` ready for S2 webhook matching.

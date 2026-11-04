# E11-S2 Acceptance — PR links + mockable GitHub webhook + Issue PR panel

**Date:** 2026-11-04 (Asia/Shanghai)  
**Worktree:** `/workspace/opentask-worktrees/E11-S2` · `sprint/E11-S2`  
**Plan SHA:** `b638f96452e6caaeb23f87799abff318750a4d76`  
**HEAD at acceptance:** `87516cbf8930a884a818d1f77836e08e3d2834c8` (docs tip; impl `fe50a90`)
**Baseline:** E11-S1 `c2823c7` (783 pytest)

## Scope delivered

- [x] PR link CRUD on `issue_vcs_links` — PATCH status/title/url fields; POST kind=`pull_request` (S1)
- [x] Mockable GitHub webhook `POST /api/webhooks/github/pull-request` (fixture; optional HMAC via `WEBHOOK_GITHUB_SECRET`; empty ⇒ skip verify)
- [x] Match: `head.ref` parse → issue_code; else existing `pr_url` / `external_id` (refuse cross-URL id collision)
- [x] Status map: merged / open / draft / closed
- [x] FE Issue detail `IssuePrPanel` — list / open URL / unlink / add prUrl
- [x] CLI `issue link-pr CODE URL` → same HTTP POST
- [x] Full `pytest tests/` green
- [x] No `requirement_repos` / PGE; no live GitHub App; no S3 status hooks; no push

## Evidence

| Check | Result |
|---|---|
| `cd backend && pytest tests/` | **794 passed**, 27 skipped |
| Unit `test_github_webhook_helpers` | 6 passed |
| API `test_issue_vcs_webhook` | 5 passed (PATCH, create, update/merged, unmatched 404, bad sig 401) |
| CLI | `link-pr` help + client payload assertions |
| FE | `IssuePrPanel.vue` mounted on Issue detail |

## APIs / webhook / UI

| Surface | Notes |
|---|---|
| `PATCH /api/issues/{id}/vcs/links/{linkId}` | writer+; camelCase body |
| `POST /api/webhooks/github/pull-request` | no workspace auth; optional `X-Hub-Signature-256` |
| Issue detail | 「关联的 PR」卡片 |
| CLI | `issue link-pr` |

## Out of sprint (deferred → S3)

- Workspace `git_status_hooks_enabled` + open→in_progress / merged→resolved
- Live GitHub App / OAuth / remote create PR
- Remote push of this branch
- CodingWorker VCS contract polish

## Gaps / notes

- `external_id` alone is ambiguous across repos; lookup refuses when stored `pr_url` differs from inbound URL.
- Alembic tip unchanged: `d4e5f6a7b8c9`.
- Approach A fixture webhook only — live App **not** DoD.

# E9-S1 Acceptance — Triage 队列

日期：2026-11-04（Asia/Shanghai）  
Epic：E9 · Sprint：S1  
Worktree：`/workspace/opentask-worktrees/E9-S1` · 分支 `sprint/E9-S1`  
基线：E12-S3 `77990b4` → docs Phase1 `2923802` → plan `ddb9fd5`  
**未推远程** · **未开 S2/S3**

## Gates

| gate | result |
|---|---|
| `pytest tests/ -q` | **736 passed**, 27 skipped |
| triage file | `tests/api/test_triage.py` 10 passed |
| FE eslint (touched) | 0 errors |
| FE vitest `command-palette.test.ts` | 11 passed |
| FE `npm run build` | successful（需 worktree `.env`/`.env.prod` symlink → E8-S1） |

## Delivered vs design §S1

| item | status |
|---|---|
| `issues.triage_status` + Alembic `d0e1f2a3b4c6` ← `c9d0e1f2a3b5` | done |
| `GET/POST /api/triage` | done |
| accept / decline / duplicate | done |
| `IssueRelation(duplicates)` on duplicate | done |
| viewer GET / write 403；跨 WS 404 | done |
| FE `/triage` + sider `TriageNav` + ⌘K `nav.triage` | done |
| 与个人 Inbox 分离（文案 + 独立 API） | done |
| Templates / snooze | **out of scope**（S2/S3） |

## Key APIs

- `GET /api/triage` — pending 列表
- `POST /api/triage` — `{ issueId }` 入队或 `{ title,… }` 创建并入队
- `POST /api/triage/{id}/accept|decline`
- `POST /api/triage/{id}/duplicate` body `{ duplicateOfIssueId }`

## Key UI

- `/triage` 队列页：接受 / 拒绝 / 标记重复（目标 Issue ID）
- 侧栏 Logo 下「分诊」入口；⌘K 「分诊」

## Gaps / notes

- Duplicate UI 目前手填目标 Issue ID（未做搜索选择器；S3 打磨可增强）
- `IssueResponse.triage_status` 已暴露；列表默认不过滤 triage（队列专页负责）
- 无邮件/集成自动入队（设计排除）

## Decision

**Accept S1 local-complete.** `merged-commit: null`. Do not start S2/S3 in this acceptance.

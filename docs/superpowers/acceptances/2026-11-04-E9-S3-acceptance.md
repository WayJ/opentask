# E9-S3 Acceptance — Inbox snooze + Epic local-complete

日期：2026-11-04（Asia/Shanghai）  
Epic：E9 · Sprint：S3（收口）  
Worktree：`/workspace/opentask-worktrees/E9-S3` · 分支 `sprint/E9-S3`  
基线：E9-S2 `223b264` → plan `0b4c932`  
**未推远程** · **未开 E10**

## Verdict

**pass** — S3 交付：`notifications.snoozed_until`；`POST /api/inbox/{id}/snooze|unsnooze`；默认列表隐藏未到期 snooze；`include_snoozed`；90d 上限；FE 预设延后 + 取消延后 + Inbox≠Triage 文案。Epic E9 **S1–S3 local-complete**。`merged-commit: null`。

**Epic tip (handoff / Yuri receipt):** `8764d094893fa8ebeb3b1bef6ff785b8f3d3f656`

## Gates

| gate | result |
|---|---|
| `pytest` (backend cwd) | **751 passed**, 27 skipped；3 failed 预存 `opentask/api/test/test_task_protocol_rules.py`（UserModel/AccessToken mapper，与 E9 无关） |
| snooze file | `tests/api/test_inbox_snooze.py` **7 passed** |
| FE eslint (touched inbox) | 0 errors |
| FE `pnpm run build` | successful |

## Delivered vs design §S3

| item | status |
|---|---|
| `notifications.snoozed_until` + Alembic `f2a3b4c5d6e8` ← `e1f2a3b4c5d7` | done |
| list 默认 `(NULL OR <= now)`；`include_snoozed` | done |
| snooze / unsnooze；非本人 404；>90d / past 400 | done |
| FE 1h/3h/明天/下周一 + 显示已延后 + unsnooze | done |
| 已读与 snooze 并存 | done |
| Triage 独立 | done |
| E10 | **not started** |

## Key APIs

- `POST /api/inbox/{id}/snooze` `{ until }`
- `POST /api/inbox/{id}/unsnooze`
- `GET /api/inbox?include_snoozed=`

## Key UI

- Inbox 行「延后」菜单；角标「已延后」；副标题区分分诊

## Epic S1–S3 tip chain (local)

| Sprint | tip (approx) | note |
|---|---|---|
| S1 | `e0aad93` | Triage |
| S2 | `223b264` | Templates |
| S3 / **Epic** | `8764d094893fa8ebeb3b1bef6ff785b8f3d3f656` | Snooze + DoD |

## Gaps / notes

- 无浏览器 E2E；无独立 snooze worker（懒过滤）
- protocol_rules 3 fails 预存
- Settings/菜单未加「已延后」全局入口（Inbox 页内勾选即可）

## Decision

**Accept S3 + Epic E9 local-complete.** No push. Do not start E10.

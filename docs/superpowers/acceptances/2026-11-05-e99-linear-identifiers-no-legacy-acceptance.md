# E99 Acceptance：Linear Issue Identifiers — 无历史环境，删除 legacy

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E99-S1`  
基线：`f4bd973`（全文 `f4bd973e9d3ba006676511c526efb4168e02fa9c`；含 E99 design；E98 tip `02af930` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e99-linear-identifiers-no-legacy-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e99-linear-identifiers-no-legacy-plan.md`  
Migrations：
- E98 no-op：`backend/alembic/versions/2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py`（rev `f9a0b1c2d3e4`）
- E99 drop：`backend/alembic/versions/2026_11_05_5900-g0a1b2c3d4e5_e99_drop_legacy_issue_code.py`（rev `g0a1b2c3d4e5`，down `f9a0b1c2d3e4`）

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | Scheme A / Q1a–Q6a |
| B FE | ⏳ | |
| C CLI | ⏳ | VERSION 保持 1.81.0 |
| D 安全/邻面/no-emit | ⏳ | |
| E 门禁 | ⏳ | |

## Tip

- 分支：`sprint/E99-S1`
- tip short：_tbd_
- tip full：_tbd_
- **未 push / 未开 PR / 未开下一 Epic**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E99 | ⏳ |
| Directed E98 create/WS bind | ⏳ |
| Directed Jira keys / search FTS / issue_key | ⏳ |
| Full BE `pytest tests` | ⏳ |
| CLI suite | ⏳ |
| FE vitest | ⏳ |
| FE production build + f+r | ⏳ |
| `rg legacy_issue_code` 业务路径为零 | ⏳ |

## Q1a–Q6a 落地

- **Q1a** drop `legacy_issue_code` + 索引；ORM 删除；API 不暴露
- **Q2a** `f9a0b1c2d3e4` 保留 id，upgrade/backfill → no-op；E99 `g0a1b2c3d4e5` 接其后 drop
- **Q3a** Jira 仅 KEY-N ↔ OPENTASK；`< KEY_N_BASE` → ValueError
- **Q4a** CLI/FE 前缀 2–6；`ISSUE2026-*` false；help KEY-N
- **Q5a** 不改写 E12/E60 历史 revision；不改历史 sprint 证据 md
- **Q6a** Requirement 年号不动

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = _tbd_`

## 禁区

未触碰：Team / Requirement 年号 / 真 Git / OAuth2 / E79–E97 邻面；未改写 E12/E60 历史 revision；E98 WS 绑定保留；formula no-emit；未停 7377/9527；未 push/PR；未自开下一 Epic。

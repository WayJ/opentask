# E10-S2 Acceptance — Health rollup + nav/⌘K

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E10-S2`  
Worktree：`/workspace/opentask-worktrees/E10-S2`  
Plan：`docs/superpowers/plans/2026-11-04-e10-s2-health-nav.md` @ `db5e8cf`  
基线：E10-S1 tip `4dd86fa`

## Scope delivered

- [x] `healthSummary` on Initiative list/create/get/update/M2M responses  
  - formula：off_track > at_risk > on_track；全 unknown / 无 project → overall null  
  - counts：onTrack / atRisk / offTrack / unknown + projectCount  
  - detail includes `projects[{id,name,healthStatus}]`
- [x] ⌘K `nav.initiatives` → `/initiatives`（i18n + vitest）
- [x] Favorites `target_type=initiative`（BE TARGET_TYPES + resolve；FE nav/icon/pin）
- [x] FE list 健康列；详情健康卡 + 侧栏钉
- [x] 侧栏路由 `/initiatives` 保持可见（S1）
- [x] **无** PGE 双轴；**无** S3 Docs；**无** Alembic；**无** push

## Tests

| 项 | 结果 |
|---|---|
| `test_initiative_health.py` | 5 passed |
| `test_pin_initiative` | passed |
| Full `pytest tests/` | **764 passed**, 27 skipped |
| `command-palette.test.ts` | 13 passed |

## APIs / UI

- Same `/api/initiatives*` payloads now include `healthSummary`（detail + `projects`）
- Favorites POST `{ target_type: "initiative", target_id }`
- ⌘K action id `nav.initiatives`

## Gaps / deferred

- S3 Docs / entity_documents or KB deep-link
- Initiative entity search in ⌘K (nav only this sprint)
- No remote push

## Yuri check

- [x] Initiatives remain Issue/Project axis only；无 requirements/PGE 入口

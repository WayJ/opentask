# E10-S1 Acceptance — Initiative CRUD

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E10-S1`  
Worktree：`/workspace/opentask-worktrees/E10-S1`  
Plan：`docs/superpowers/plans/2026-11-04-e10-s1-initiatives.md` @ `3367143`  
HEAD（本验收时）：见 git tip

## Scope delivered

- [x] `initiatives` + `initiative_projects`（Alembic `b2c3d4e5f6a7` ← `f2a3b4c5d6e8`）
- [x] API CRUD + M2M：list/create/get/patch/delete；PUT projects；POST/DELETE attach/detach
- [x] ACL：viewer GET；member+ write；跨 WS 404；异 WS project 400；同名 409
- [x] FE：`/initiatives` 列表、`/initiatives/detail?id=` 详情+Project 多选
- [x] **无** PGE / `requirements` 导航或路由；**无** S2 health；**无** S3 Docs；**无** push

## Tests

| 项 | 结果 |
|---|---|
| `tests/api/test_initiatives.py` | 7 passed |
| Full `pytest tests/` | **758 passed**, 27 skipped |
| FE eslint（新文件） | clean |

## APIs

| Method | Path |
|---|---|
| GET/POST | `/api/initiatives` |
| GET/PATCH/DELETE | `/api/initiatives/{id}` |
| PUT | `/api/initiatives/{id}/projects` |
| POST/DELETE | `/api/initiatives/{id}/projects/{projectId}` |

## UI

- Menu route `initiatives`（Issue/Project 轴文案）
- Detail 关联 Project via `fetchProjectList`；不链 knowledge PGE / requirements

## Gaps / deferred

- S2：health rollup、侧栏/⌘K、Favorites `initiative`
- S3：Docs / entity_documents 或 KB 深链
- 无远程 push

## Yuri check

- [x] 产品入口 = Initiatives on Issue/Project；**无** PGE 双轴

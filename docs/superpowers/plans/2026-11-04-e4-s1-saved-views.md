# E4-S1 实施计划（精简 TDD）

## 目标

个人 Saved Views CRUD + Issue 列表保存/应用/收藏。本地 `sprint/E4-S1`，不推远程。

## API 形状

```
GET    /api/saved-views
POST   /api/saved-views          { name, filter, sort?, is_favorite?, display? }
GET    /api/saved-views/{id}
PATCH  /api/saved-views/{id}     部分更新
DELETE /api/saved-views/{id}
POST   /api/saved-views/{id}/favorite  { is_favorite: bool }
```

Header：`Authorization` + **必填** `X-Workspace-Id`。

## 文件

- `backend/opentask/models/issue_saved_view/model.py`
- `backend/opentask/models/issue_saved_view/__init__.py`
- `backend/opentask/models/__init__.py`（注册）
- `backend/alembic/versions/2026_11_04_0100-d0e1f2a3b4c5_issue_saved_views.py`
- `backend/opentask/services/saved_view/service.py`
- `backend/opentask/api/saved_views/router.py` + `__init__.py`
- `backend/opentask/app.py`（include_router）
- `backend/tests/api/test_saved_views.py`
- `frontend/src/service/api/saved-views.ts` + `index.ts` export
- `frontend/src/views/issue/list/index.vue`

## TDD 顺序

1. 写 `test_saved_views.py`（create/list/isolation/update/delete/workspace/favorite）→ 红
2. Model + migration 注册 → 仍红（无路由）
3. Service + Router → 绿
4. 前端 API + 列表 UI
5. 全量 pytest + lint + build
6. acceptance + 关 sprint

## 非目标

S2 分组、S3 子 Issue、共享视图、远程 push。

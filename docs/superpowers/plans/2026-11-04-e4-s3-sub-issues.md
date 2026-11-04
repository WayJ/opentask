# E4-S3 实施计划（精简 TDD）

> **For agentic workers:** 本会话内联执行（executing-plans）。本地 `sprint/E4-S3`，不推远程。

**Goal:** 一等公民子 Issue：`parent_issue_id` FK + API 校验 + 详情/列表 depth-1 嵌套。

**Architecture:** Issue 自引用 FK；服务层校验同工作区/自指/环；响应 additive 字段；列表嵌套在前端对当前筛选结果做 depth-1。

**Tech Stack:** FastAPI / SQLAlchemy / Alembic / pytest / Vue3 / Naive UI / vitest

## Global Constraints

- 不用 IssueRelation 表达父子
- 不推远程；不做 ⌘K / Cycles / Labels / 共享视图
- 中文 SuperVibe 文档
- 门禁：定向 + 全量 pytest；lint 0 errors；build

## 文件

- Modify: `backend/opentask/models/issue/model.py`（parent_issue_id + 可选 relationships）
- Modify: `backend/opentask/models/issue/schema.py`
- Create: `backend/alembic/versions/2026_11_04_0200-e1f2a3b4c5d6_issue_parent_issue_id.py`
- Modify: `backend/opentask/services/issue_service.py`
- Modify: `backend/opentask/api/issue/router.py`
- Create: `backend/tests/api/test_sub_issues.py`
- Modify: `frontend/src/typings/api/issue.d.ts`
- Modify: `frontend/src/service/api/issue.ts`
- Create: `frontend/src/utils/nestIssuesDepth1.ts` + `.test.ts`
- Modify: `frontend/src/views/issue/list/index.vue`
- Modify: `frontend/src/views/issue/detail/index.vue`

## TDD 顺序

1. 写 `test_sub_issues.py` → 红
2. Model + migration → 仍红/部分红
3. Schema + Service 校验 + Router → 绿
4. 前端 nest 工具 + vitest → UI
5. 全量门禁 + acceptance + 关 sprint / epic local-complete

## API 形状

```
POST /api/issues              { ..., parent_issue_id? }
PUT  /api/issues/{id}         { ..., parent_issue_id? }  # null 清空
GET  /api/issues/{id}         含 parent_issue_id + children[{id,title,status,issue_code}]
GET  /api/issues/{id}/children  同上摘要列表
GET  /api/issues              每项含 parent_issue_id（无强制 children）
```

校验错误 → HTTP 400，detail 中文。

## 非目标

S1/S2 重写、共享视图、远程 push、IssueRelation 父子、深度>1 服务端树。

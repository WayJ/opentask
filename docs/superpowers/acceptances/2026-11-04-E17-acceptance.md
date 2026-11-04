# E17 Acceptance

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E17-S1`  
基线：`b4ec445`  
tip：`d49c538a8375935d000dc046bbcee9752ee2e4e1`

## A. E16 收口
- [x] `alembic upgrade head` → `a1b2c3d4e5f9`；孤儿 Default WS 行已删
- [x] `GET /api/workspaces` 无 `00000000-0000-4000-8000-000000000001`（:7377 smoke）
- [x] CLI `issue create/update --estimate-points`；show/list 展示 Pts
- [x] CLI `cycle capacity` + `cycle show` 附带 capacity-hint（unit/suggested/samples/currentLoad）
- [x] CLI **1.2.0**；README 更新

## B. Global Search
- [x] `GET /api/search?q=&limit=` + `X-Workspace-Id`；缺头 400；跨租户 403
- [x] 分组：issues / projects / docs / members
- [x] FE `/search`（hideInMenu）+ ⌘K「搜索…」
- [x] 键盘 ↑↓/Enter；vitest helpers

## 测试
| 套件 | 结果 |
|---|---|
| backend pytest | **828 passed**, 24 skipped |
| CLI pytest | **410 passed**, 89 skipped |
| FE vitest（相关） | global-search + e17-search-route + command-palette：**17 passed**；全量 184 passed（2 既有 `@pinia/testing` 解析失败无关 E17） |

## 冒烟
笔记：`/workspace/opentask-smoke/e17/SMOKE.json`  
- login smoke_way OK；orphanInList=false；search no-header=400；search ok；capacity-hint 200

## 未做 / 缺口
- Knowledge-base 全文未进聚合（仅 entity_documents）
- Doc 结果跳转目前落到 project-detail（按 parentId）；Issue/Initiative parent 未做专用深链
- 未 push / 未开 PR / 未开 E18

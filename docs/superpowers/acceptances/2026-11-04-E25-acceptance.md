# E25 Acceptance：Issue Custom Fields

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E25-S1`  
基线：`29ecfe5`

## 状态
✅ 本地齐套（未 push）

## tip
`b193e69`

## 测试数
- BE pytest：869 passed / 1 flake（`test_tasks_jira_wire::test_user_search` 单测复跑绿；全量偶发）/ 24 skipped；本 Epic 新增 `tests/api/test_custom_fields.py` 7P
- CLI pytest：430 passed / 89 skipped（含 E25 4P）；version **1.9.0**
- FE vitest：235 passed（+2 helpers）；`npm run build` 成功；lint 未新增 error（仅既有 + 新页 inline-style warning，与 labels 同风格）

## 范围核对
- [x] A 字段定义 CRUD + 归档优于有值硬删 + viewer 403 + 跨租户
- [x] B Issue 取值类型校验；详情默认 `customFields`；列表默认不带 / `?include=custom_fields`；`PATCH .../custom-fields`
- [x] C FE `/workspace/custom-fields` + Issue 详情编辑 + 创建可选填；**列表列不做**（ADR D8）
- [x] D CLI `custom-field list|create` + `issue set-field`；**1.9.0**
- [x] 未 push / 未开 PR / 未自开 E26

## ADR 摘要
- D1–D5：slug / options / 类型校验 / 有值归档 / 归档字段不可写
- D6：详情默认带、列表 opt-in
- D7：路由 Workspace 菜单
- D8：列表列本期不做
- D9：创建后 PATCH
- D10：CLI 1.9.0
- D11：非目标 + 不 push + 不自开 E26

## 缺口
- SmartSearch `field:value`、公式/关联实体/字段级权限、列表 Display 列：明确非目标
- 全量 BE 中 `test_user_search` 偶发失败，与 E25 无关；单文件 40P 全绿

# E28 Acceptance：Issue CSV Import / Export

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E28-S1`  
基线：`be27e7d`

## 状态
✅ 本地齐套（未 push）

## tip
`TIP_PLACEHOLDER`

## 测试数
- BE pytest：886 passed / 1 flake（`test_user_search` 隔离复跑确认）/ 24 skipped；本 Epic `tests/api/test_issue_csv.py` **3P**
- CLI pytest：439 passed / 89 skipped（含 E28 3P）；version **1.12.0**
- FE vitest：242 passed（+2 issue-csv helpers）；`pnpm run build` 成功

## 范围核对
- [x] A Export `GET /api/issues/export.csv` + 过滤 + viewer+ + X-Workspace-Id + 10k 上限
- [x] B Import `POST /api/issues/import` upsert + 行级错误 + member+ + 模板
- [x] C FE 列表 Export/Import + 模板下载
- [x] D CLI `issue export|import`；**1.12.0**
- [x] 未 push / 未开 PR / 未自开 E29

## ADR 摘要
- D1：export.csv / import/template.csv / import multipart
- D2：email 列 = username
- D3：estimate↔points；labels find-or-create；cycle 按名
- D4：code 命中更新；未命中/空 → 新建 KEY-N（忽略未知外部码）
- D5：EXPORT_MAX_ROWS=10000；截断头 X-Export-Truncated
- D6–D10：权限 / 过滤 / FE / CLI / 非目标

## 缺口
- 自定义字段列、附件、Jira/Linear 同步：明确非目标
- `test_user_search` 偶发失败与 E28 无关（既往 Epic 同款 flake）

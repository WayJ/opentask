# E26 Acceptance：Automations lite

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E26-S1`  
基线：`dfae2ae`

## 状态
✅ 本地齐套（未 push）

## tip
`dad8018`（`dad8018d1afdd595ed391d27b20cca862d7a3cad`）

## 测试数
- BE pytest：873 passed / 4 flake（`test_auth`×3 + `test_user_search` 隔离复跑全绿；与 E26 无关）/ 24 skipped；本 Epic `tests/api/test_automations.py` **7P**
- CLI pytest：433 passed / 89 skipped（含 E26 3P）；version **1.10.0**
- FE vitest：238 passed（+3 automations helpers）；`npm run build` 成功

## 范围核对
- [x] A 规则 CRUD + enable/disable + after-commit 执行器 + 防环（depth≤1）+ viewer 403 + 跨租户
- [x] B 条件 AND（statusIn / priorityIs / hasLabel）；无条件=总匹配
- [x] C FE `/workspace/automations` 列表/开关/创建 + 空状态 + Workspace 菜单
- [x] D CLI `automation list|create|enable|disable`；**1.10.0**
- [x] 未 push / 未开 PR / 未自开 E27

## ADR 摘要
- D1：单表 automation_rules；固定 trigger/action 枚举
- D2：contextvars `automation_depth` 防环（深度≤1）
- D3：执行器 best-effort；失败只 log
- D4：label_added ≡ Tags attach/replace
- D5：add_comment 为 system + `[automation]` 前缀 + meta
- D6–D8：trigger/action/condition config 形状
- D9：FE Workspace 菜单路由
- D10：CLI 1.10.0
- D11：非目标 + 不 push + 不自开 E27

## 缺口
- 多步流水线 / 延迟 cron / 出站 Webhook / Slack / 自定义脚本 / AI 派单：明确非目标
- 全量 BE 中 auth 与 user_search 偶发失败，与 E26 无关；隔离复跑绿

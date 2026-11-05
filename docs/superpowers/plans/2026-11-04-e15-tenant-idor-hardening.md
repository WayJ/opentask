# E15 Plan：租户 IDOR 硬化

分支：`sprint/E15-S1` · 基线 `0f64111`

## Task 1 — 文档落地
- [ ] commit design + plan（本文件 + specs）

## Task 2 — RED：失败用例
- [ ] `backend/tests/api/test_tenant_idor.py`
  - 注册 A/B 两用户（各默认 WS）
  - B 建 project + issue
  - A：`GET/PUT/DELETE` B 的 project → 403
  - A：`GET/PUT` B 的 issue UUID → 403；A 对本租户 → 200
  - A：`GET` B issue 的 comments/relations/attachments → 403
  - A：`GET /api/projects` + B 的 `X-Workspace-Id` → 403（回归）
  - by_code：B 的 KEY 在 A 的 WS 头下找不到/拒绝（不回退）

## Task 3 — GREEN：共享守卫 + 路由
- [ ] `opentask/api/workspace/deps.py`：`ensure_entity_workspace_access`
- [ ] project router：get/update/delete
- [ ] issue router：get/update/delete + comments/relations/attachments（含 comment 按 id）

## Task 4 — 验证
- [ ] `uv run pytest` 全绿（或至少 IDOR + 相关）
- [ ] 对本地 `:7377` 关键 IDOR 断言（若服务在）
- [ ] acceptance 文档
- [ ] 可选：CLI 7 坏测快修

## Task 5 — 回执待命
- tip SHA、硬化路由清单、pytest 数、IDOR 复跑、明确未 push；停，不开下一 Epic

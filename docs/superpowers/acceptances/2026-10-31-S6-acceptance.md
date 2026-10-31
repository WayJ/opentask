# Acceptance record — sprint S6, 2026-10-31

## Verdict

pass — 五个场景现场复跑通过（S4 按计划 D4 以 blocked+替代证据形态满足）；97 用例含错误路径与 code review 七项回归；spec 随代码提交且受 12 项对账测试守护；无未偿 doc-sync 欠账。code review（e2e6ade..HEAD，独立评审）七项发现全部修复并配回归用例。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-10-31-S6-plan.md","record":"docs/superpowers/acceptances/2026-10-31-S6-acceptance.md","fingerprint":"327ac71ad8475cfc7e2a663db39610e187bd8b4dc029869dea0297a4f3c6ceb9"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"327ac71ad8475cfc7e2a663db39610e187bd8b4dc029869dea0297a4f3c6ceb9","environment":"本机 Windows 11；载体 D:/orca/workspaces/opentask/E2-S6（Orca 原生工作区，分支 sprint/E2-S6，基于 main@fbe15f8）；DB 为 Docker opentask-pg（localhost:5432，测试库 opentask_test）；执行身份 run_1c0f1c692b5a/task_ba16d5d45c53/ctx_91cc9c711add（worker-lifecycle 已 settle+cleanup）；运行时间 2026-10-31T2x:xxZ UTC","results":[{"id":"S1","status":"passed","modality":"cli","environment":"real","steps":["运行 spec 导出","spec 字段与路由 schema 对账"],"expected":"spec 随代码提交；字段与实现一致","observed":"backend/openapi_contract.json（31,326 字节，4 端点+ContractErrorResponse+HTTPBearer 安全方案）；12 项 spec↔实现对账测试含于 97 passed","artifacts":["backend/openapi_contract.json","tests/tasks/test_tasks_openapi.py"],"blockers":[]},{"id":"S2","status":"passed","modality":"cli","environment":"real","steps":["运行错误路径测试（无凭证/错凭证/禁操作/不可达）"],"expected":"CONTRACT_AUTH_MISSING/INVALID、CONTRACT_FORBIDDEN、CONTRACT_UNAVAILABLE 独立错误码 + 可读消息","observed":"错误语义定稿 400/401/403/404/422/503 统一 CONTRACT_* 族（优先级 503>401>403）；四类错误路径用例 + capabilities 禁操作表实时下发，含于 97 passed","artifacts":["backend/opentask/api/tasks/errors.py","tests/tasks/test_tasks_errors.py"],"blockers":[]},{"id":"S3","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run pytest tests/tasks/ -v"],"expected":"全部通过（含错误路径新用例）","observed":"97 passed（1 warning）37.51s：S4/S5 存量 53 + 错误路径/spec 对账/code review 七项回归 44","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S4","status":"passed","modality":"other","environment":"real","steps":["探测 Orca 自定义任务源注册能力","可得则注册并跑五操作留证；不可得则记录 blocked + 契约套件与 capabilities 替代证据"],"expected":"联调证据（列出/读取/创建/更新/状态流转）或 blocked 记录 + 替代证据","observed":"本机 Orca 构建无自定义任务源注册面（CLI 全量核查：外部集成固定 Jira/Linear/GitHub/GitLab，无 taskSource 配置）——按 D4 透明降级：活体 uvicorn:8000 五操作 E2E 转录 + updated_since 游标零重复 + psql 落库核验 + GET /capabilities 输出，全部留证于 docs/superpowers/sprints/2026-10-31-S6-orca-e2e-evidence.md；epic DoD 1 的 Orca 侧注册列为 E2 关闭时遗留","artifacts":["docs/superpowers/sprints/2026-10-31-S6-orca-e2e-evidence.md"],"blockers":[]},{"id":"S5","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run python -c \"import opentask.api\""],"expected":"无 ImportError","observed":"import OK","artifacts":["Scenario Results 表"],"blockers":[]}]}
```

## Gate Evidence

载体分支 tip（评审时）：未提交工作区（记录随载荷同提交）。宿主门禁以 main 为权威面；S6 落地后 complete 按 gate 缓存规则核对。

## Scenario Results

| id | command | expected | actual | pass |
|---|---|---|---|---|
| S1 | spec 导出+对账 | 一致 | 31KB + 12 对账测试 | yes |
| S2 | 错误路径测试 | CONTRACT_* 独立 | 六状态码统一族 | yes |
| S3 | `uv run pytest tests/tasks/ -v` | 全绿 | 97 passed | yes |
| S4 | Orca 联调/降级 | 留证 | blocked+替代证据留档 | yes |
| S5 | `import opentask.api` | 无错 | OK | yes |

## DoD Checklist

- [x] OpenAPI spec 生成随代码发布、字段一致（DoD 7）— openapi_contract.json + 对账测试
- [x] 三类错误独立错误码（DoD 8）— CONTRACT_* 族 + 可读消息 + capabilities 下发
- [x] 单元测试覆盖（DoD 9 部分）— 97 用例（CRUD 全路径 + 游标边界 + 错误路径 + 回归）
- [ ] Orca 注册后五操作（DoD 1）— **环境不可得**（本机 Orca 无自定义任务源注册面），D4 降级证据在档；E2 关闭时列遗留
- [x] 游标/落库/timeline/软删除/状态映射（DoD 2-6）— S4/S5 交付，S6 树 97 用例复验含

## Obstacles (verbatim)

- 2026-10-31 2x:xxZ — Orca 侧注册探测结论：本机构建外部集成固定为 Jira/Linear/GitHub/GitLab（Jira 仅桌面 Settings UI 且需 Jira REST 线格式），无自定义任务源配置面 → D4 降级执行（活体 E2E 五操作 + 游标 + psql + capabilities 替代证据留档）。
- 2026-10-31 2x:xxZ — 协调者将独立 code review 七项发现（4 中 3 低）经 orca send 推送给在跑 worker，全部修复并各配回归用例：状态过滤集合化、默认状态配置推导、issue_type 词表校验、client_credentials 的 scp 修复、孤儿 refresh 行、labels 原子化、并发撞号重试；验收复跑 97 passed 含全部回归。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| `backend/config/*.yaml` → backend/README.md | 无（S6 未改 yaml；README 错误码表更新与代码同批） | current | README 与 spec 同批落盘 |
| `docs/superpowers/roadmaps/*.md` → roadmaps/ | 无 | n/a | 未触发 |
| `frontend/.env.prod` → frontend/README.md | 无 | n/a | 未触发 |

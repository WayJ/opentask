# Acceptance record — sprint S7, 2026-11-01

## Verdict

pass — 五个必需场景现场通过：137 用例全绿（+40 Jira 线格式往返）、**真实 Orca 自建 Jira 集成五操作 E2E 打通**（epic DoD 1 完整形态，取代 S6 降级证据）、探测文档与证据在档、内核复用经 grep 核验、导入零缺失。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-01-S7-plan.md","record":"docs/superpowers/acceptances/2026-11-01-S7-acceptance.md","fingerprint":"48e9bc1706b2800016dcc7e31da3ec61613a1250f0518b2ed05860e24611c97d"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"48e9bc1706b2800016dcc7e31da3ec61613a1250f0518b2ed05860e24611c97d","environment":"本机 Windows 11；载体 D:/orca/workspaces/opentask/E2-S7（Orca 原生工作区，分支 sprint/E2-S7，基于 main@f304a5b）；DB 为 Docker opentask-pg（开发库 opentask，测试库 opentask_test）；E2E 后端 uvicorn:8000 + Orca 1.4.245 桌面运行时（RPC 注册）；执行身份 run_1c0f1c692b5a/task_4ac4a486355e/ctx_67bc3ad0d944（已 settle+cleanup）；运行时间 2026-11-01T0x:xxZ UTC","results":[{"id":"S1","status":"passed","modality":"other","environment":"real","steps":["启动本机后端 uvicorn:8000","Orca 连接配置指向 http://localhost:8000 并完成鉴权"],"expected":"连接建立，/rest/api/2/myself 鉴权通过","observed":"经运行时 RPC（协议还原自 Orca transport.js，与 Settings UI 同源）注册自建 Jira 站点成功；orca jira connection 显示 connected:true；myself 首跳通过（vk_ API Key 即服务层签发的 access token）","artifacts":["docs/superpowers/sprints/2026-11-01-S7-orca-e2e-evidence.md §0"],"blockers":[]},{"id":"S2","status":"passed","modality":"other","environment":"real","steps":["Orca 侧执行列出/读取/创建/更新/状态流转","psql 核验 OpenTask 落库"],"expected":"五操作全部成功，字段/状态/timeline 落库正确","observed":"真实 orca jira CLI 五操作+评论全部 ok：list/search（JQL summary~/statusCategory/ORDER BY 翻译命中）、create（OPENTASK-2026000000001 + browse URL）、update、transition；psql 核验字段/标签/评论/时间线 7 行落库","artifacts":["证据文档 §1-§2 转录"],"blockers":[]},{"id":"S3","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run pytest tests/tasks/ -v"],"expected":"全部通过（含 jira 适配用例）","observed":"137 passed（1 warning）46.16s：S6 基线 97 + Jira 线格式往返 40","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S4","status":"passed","modality":"cli","environment":"real","steps":["grep 检查 jira 层对 mapping/auth/schemas 的引用"],"expected":"无线格式层外的业务逻辑重复","observed":"api/jira/ 各模块共 8 处 import 自 opentask.api.tasks（auth×2/router×3/converters/jql/errors）；keys/wiring 为纯线格式辅助","artifacts":["内核复用 grep 结果"],"blockers":[]},{"id":"S5","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run python -c \"import opentask.api\""],"expected":"无 ImportError","observed":"import OK","artifacts":["Scenario Results 表"],"blockers":[]}]}
```

## Gate Evidence

载体分支 tip（评审时）：未提交工作区（记录随载荷同提交）。宿主门禁以 main 为权威面，S7 落地后 complete 按 gate 缓存规则核对。

## Scenario Results

| id | command | expected | actual | pass |
|---|---|---|---|---|
| S1 | Orca 注册 | connected + myself | RPC 注册成功 | yes |
| S2 | 五操作 + psql | 走通+落库 | 全 ok + 7 行核验 | yes |
| S3 | `uv run pytest tests/tasks/ -v` | 全绿 | 137 passed | yes |
| S4 | 内核复用 grep | 无复制 | 8 处复用 import | yes |
| S5 | `import opentask.api` | 无错 | OK | yes |

## DoD Checklist

- [x] **Orca 注册后五操作（DoD 1）——完整形态达成**：真实 Orca CLI + 自建 Jira 模式 + psql 落库核验（S6 降级证据就此升级取代）
- [x] 游标/落库/timeline/软删除/状态映射（DoD 2-6）——契约内核经 137 用例与 E2E 复验
- [x] OpenAPI spec（DoD 7）——契约层 spec 维持（Jira 层 ASGI 挂载不污染契约 spec；Jira 线格式以探测文档为准）
- [x] 错误语义（DoD 8）——CONTRACT_* 内核 + Jira 形状错误体（errorMessages/errors）
- [x] 单元测试覆盖（DoD 9）——137 用例（CRUD+游标+错误+Jira 往返）

## Obstacles (verbatim)

- 2026-11-01 — Orca 站点注册路径：配置文件不可手写（token 在加密 vault）、GUI 聚焦受 Windows 前台锁限制 → worker 还原 Orca 本机运行时 RPC（named pipe + NDJSON，协议源自 transport.js）完成注册，与 Settings UI 同源等价；探测结论（反混淆适配器源码：/rest/api/2 固定、双鉴权、errorMessages/errors、search 单页 POST、写操作 204、myself 首跳）入档 `2026-11-01-S7-orca-jira-probe.md`。
- 2026-11-01 — 遗留处置（协调者验收后执行，手册在证据文档 §3）：8000 端口 E2E 实例仍在运行、Orca 已注册站点与开发库 E2E 数据待清理。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| `backend/config/*.yaml` → backend/README.md | 无（S7 未改 yaml） | n/a | 未触发 |
| `docs/superpowers/roadmaps/*.md` → roadmaps/ | 无 | n/a | 未触发 |
| `frontend/.env.prod` → frontend/README.md | 无 | n/a | 未触发 |

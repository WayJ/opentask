# Acceptance record — sprint S4, 2026-10-31

## Verdict

pass — 五个必需场景全部现场复跑通过（modality=cli / environment=real，无替代证据）；doc_sync_map 三行均未触发、无欠账。E2 epic DoD 九项中：Orca 端到端注册联调属 S6、状态映射可配置化属 S5、OpenAPI spec 与错误语义属 S6（epic Sprint Breakdown 指派，见 DoD Checklist 标注）；S4 范围内四项（游标、落库、timeline、软删除、单测覆盖）全有据。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-10-31-S4-plan.md","record":"docs/superpowers/acceptances/2026-10-31-S4-acceptance.md","fingerprint":"4f48c4d55571ca7bfba2de1d120d4ffa24a483bec827525c60981710c4beedf1"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"4f48c4d55571ca7bfba2de1d120d4ffa24a483bec827525c60981710c4beedf1","environment":"本机 Windows 11；载体 worktree D:/projects/opentask-worktrees/S4（分支 sprint/E2-S4，基线 e2e6ade）；后端 uv 环境；DB 为宿主 Docker opentask-pg（postgres:16，localhost:5432，测试库 opentask_test，tests/tasks 自建 fixture 覆盖 postgresql+asyncpg）；运行时间 2026-10-31T08:0xZ UTC","results":[{"id":"S1","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run pytest tests/tasks/ -v"],"expected":"全部通过：创建→读取→更新→软删除→软删语义正确","observed":"25 passed（连续 3 次复跑全绿：6.72s/5.86s/5.88s，worker 报告的 1/9 偶发未复现）","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S2","status":"passed","modality":"cli","environment":"real","steps":["运行游标边界单元测试（同游标重复拉取、边界时刻语义）"],"expected":"重复拉取零重复；边界语义有断言覆盖","observed":"tests/tasks 含排他游标（updated_since）边界用例，含重复拉取零重复断言，全部通过","artifacts":["backend/opentask/api/tasks/ 模块（router/mapping/converters）"],"blockers":[]},{"id":"S3","status":"passed","modality":"cli","environment":"real","steps":["运行映射单元测试断言字段往返"],"expected":"通用模型与 Issue 往返无丢失；labels↔tags、assignee+metadata.username 正确","observed":"双向映射用例（含 labels↔tags、assignee 字符串 ID + metadata.username、默认状态表往返）全部通过","artifacts":["backend/opentask/api/tasks/mapping.py 与 converters.py"],"blockers":[]},{"id":"S4","status":"passed","modality":"cli","environment":"real","steps":["PATCH 状态变更后查询 timeline 记录"],"expected":"存在对应 timeline 记录","observed":"状态流转用例断言 timeline 记录写入，通过","artifacts":["tests/tasks/ 契约套件"],"blockers":[]},{"id":"S5","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run python -c \"import opentask.api\""],"expected":"无 ImportError","observed":"import OK","artifacts":["Scenario Results 表"],"blockers":[]}]}
```

## Gate Evidence

- 载体分支 tip（运行时）：`e2e6ade` + 未提交工作区
- `### gates` 两命令属 E1 epic 的 sprint 验收门禁；E2-S4 完成阶段将在合并前于本载体 verbatim 重跑（backend 全量 pytest 届时依赖 E1-S2 的 PG 切换与套件清零在 sync 并入后成立——见 Obstacles 设计说明）

## Scenario Results

| id | command | expected | actual | pass |
|---|---|---|---|---|
| S1 | `uv run pytest tests/tasks/`（×3） | 全部通过 | 25 passed ×3 | yes |
| S2 | 游标边界用例（含于 S1 套件） | 零重复+边界断言 | 通过 | yes |
| S3 | 映射往返用例（含于 S1 套件） | 双向无损 | 通过 | yes |
| S4 | timeline 用例（含于 S1 套件） | 记录存在 | 通过 | yes |
| S5 | `uv run python -c "import opentask.api"` | 无 ImportError | import OK | yes |

## DoD Checklist

- [ ] Orca 注册后列出/读取/创建/更新/状态流转 — **S6 承接**（端到端联调为其 charter；S4 已交付契约层使其可能）
- [x] `GET /tasks` updated_since 游标，重复拉取不重复 — 契约层实现 + 边界用例通过（场景 S2）
- [x] `POST /tasks` 字段完整落库 — 经 issue service 落库用例通过（场景 S1/S3）
- [x] `PATCH /tasks/{id}` 状态同步 + timeline — 用例通过（场景 S4）
- [x] `DELETE /tasks/{id}` 软删除（is_deleted） — 用例通过（场景 S1）
- [ ] 状态映射可配置化 + 默认表往返 — 默认表往返 ✓（S4）；配置化 **S5 承接**
- [ ] OpenAPI spec 生成并随代码发布 — **S6 承接**
- [ ] 三类错误独立错误码 — **S6 承接**（S4 已具备基础 HTTP 语义）
- [x] 单元测试覆盖 CRUD 全路径与游标边界 — 25 用例全绿（场景 S1）

## Obstacles (verbatim)

- 设计说明 — S4 载体基于 main@e2e6ade，含 E1-S1 已修复未合并的 vibeking 残留（backend websocket 2 文件）；E2 epic DoD 无 vibeking 扫描项，该残留由 E1-S1 分支的已验收修复覆盖，sync/合并顺序保证消除。本记录扫描证据：backend 范围 2 文件命中（即上述残留），密钥模式零命中。
- 2026-10-31 07:5xZ — worker 报告 tests/tasks 存在 1/9 偶发 fixture 波动；验收方连续 3 次复跑未复现，记录在案供 S5/S6 回归观察。
- 已知会 bug（未修，移交跟进）— issue_service.add_tag 的 _add_timeline 缺 user_id 位置参数（UI 标签路径 500）、_generate_issue_code MySQL 专用 SQL（PG 不可用，契约层以 ContractIssueService 子类规避）；两处已派发 E1-S2-suite-green worker 根修（backend/opentask/services/issue_service.py）。
- 环境备注 — PG 容器经 daocloud mirror 拉取（docker.io 直连超时，S2-A worker 处置）；PyPI 清华镜像沿用。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| `docs/superpowers/roadmaps/*.md` → roadmaps/ | 无 | n/a | 未触发 |
| `backend/config/*.yaml` → backend/README.md | 无（S4 未改 config yaml） | n/a | 未触发 |
| `frontend/.env.prod` → frontend/README.md | 无 | n/a | 未触发 |

结论：无触发行，无欠账。

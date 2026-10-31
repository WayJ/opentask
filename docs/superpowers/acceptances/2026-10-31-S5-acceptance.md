# Acceptance record — sprint S5, 2026-10-31

## Verdict

pass — 五个必需场景在 sync 后树（b5925e6，含 E1/E2 全部已落地内容）上现场复跑通过；53 用例全绿覆盖映射配置化、401 独立语义、capabilities；yaml 与 README 同批（doc_sync_map 触发行已满足）；无未偿欠账。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-10-31-S5-plan.md","record":"docs/superpowers/acceptances/2026-10-31-S5-acceptance.md","fingerprint":"9fdbda3fec35bdb1bf8d7d4a488797d5b5aa60ae63181ddec89edca0371d25cc"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"9fdbda3fec35bdb1bf8d7d4a488797d5b5aa60ae63181ddec89edca0371d25cc","environment":"本机 Windows 11；载体 worktree D:/projects/opentask-worktrees/S5（分支 sprint/E2-S5，HEAD b5925e6：载荷提交 + main@f6c64be 干净合并）；DB 为宿主 Docker opentask-pg（localhost:5432，测试库 opentask_test，tests/tasks 自带 PG fixture）；运行时间 2026-10-31T20:2xZ UTC","results":[{"id":"S1","status":"passed","modality":"cli","environment":"real","steps":["修改 config yaml 的 contract.status_mapping 后运行往返用例","移除配置运行默认表用例"],"expected":"配置生效且 Orca→OpenTask→Orca 往返正确；未配置走默认表","observed":"default.yaml 含 contract.status_mapping（6 条）与 default_issue_type；配置化与默认表回退用例含于 53 passed","artifacts":["backend/config/default.yaml","tests/tasks/test_tasks_mapping_config.py"],"blockers":[]},{"id":"S2","status":"passed","modality":"cli","environment":"real","steps":["无 token 与错误 token 调用 /tasks","合法 access_token 调用 /tasks"],"expected":"无效凭证 401 且错误体可辨识；合法凭证 200","observed":"401 用例（detail.code=CONTRACT_AUTH_MISSING/CONTRACT_AUTH_INVALID）与合法 200 用例含于 53 passed；app.py 契约路由已脱离 common_dependencies（协调者批准的一行变更）","artifacts":["backend/opentask/api/tasks/auth.py","tests/tasks/test_tasks_auth_capabilities.py"],"blockers":[]},{"id":"S3","status":"passed","modality":"cli","environment":"real","steps":["GET /capabilities"],"expected":"返回端点支持情况与契约版本","observed":"capabilities 用例含于 53 passed（契约版本 1.0、鉴权模式、配置驱动状态词表）","artifacts":["backend/opentask/api/tasks/router.py"],"blockers":[]},{"id":"S4","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run pytest tests/tasks/ -v"],"expected":"全部通过（含映射/鉴权/capabilities 新用例）","observed":"53 passed（1 warning）12.27s：S4 存量 21 + 映射配置化 16 + 鉴权/capabilities 16","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S5","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run python -c \"import opentask.api\""],"expected":"无 ImportError","observed":"import OK","artifacts":["Scenario Results 表"],"blockers":[]}]}
```

## Gate Evidence

载体分支 tip（评审时）：`b5925e6`。宿主门禁以 main 为权威面（E1-S2 载体实测 395P/0F/0E + lint/build 双绿；本 sprint 落地后 complete 按 gate 缓存规则核对）。

## Scenario Results

| id | command | expected | actual | pass |
|---|---|---|---|---|
| S1 | 映射配置化用例 | 配置生效+默认回退 | 53 内含 | yes |
| S2 | 401 语义用例 | 独立可辨识 | CONTRACT_AUTH_* | yes |
| S3 | capabilities 用例 | 支持与版本 | 契约 1.0 | yes |
| S4 | `uv run pytest tests/tasks/ -v` | 全绿 | 53 passed | yes |
| S5 | `import opentask.api` | 无 ImportError | OK | yes |

## DoD Checklist

- [x] 状态映射可配置 + 未配置默认表往返（epic DoD 6）— 配置化用例 + 6 条默认映射 ✓
- [x] 鉴权失败 401 独立错误码（epic DoD 8 之鉴权面）— CONTRACT_AUTH_MISSING/INVALID ✓
- [ ] Orca 端到端注册联调（DoD 1）/ OpenAPI spec（DoD 7）/ 503 错误语义（DoD 8 其余）— **S6 承接**（HC1 绑定：错误码命名沿用 CONTRACT_AUTH_*）
- [x] 游标/落库/timeline/软删除/单测覆盖 — S4 交付，S5 树复验含于 53 passed

## Obstacles (verbatim)

- 2026-10-31 19:2xZ — worker 问询：共享 authenticate 依赖链使 401 语义不可达 → 协调者批准 app.py:122 一行变更（契约路由脱离 common_dependencies，自带 authenticate_contract）；vk_ 前缀确认为既有 AccessTokenService.TOKEN_PREFIX 约定（非新引入）。
- 2026-10-31 20:1xZ — 载体基于 sprint/E2-S4 tip（非 main）的基线分叉按 D1 决策以 sync 收敛：载荷提交后并入 main 干净合并零冲突（app.py 单行变更与 yaml 增段均自动合并）。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| `backend/config/*.yaml` → backend/README.md | **是** — default.yaml 增 contract 段 | current | README 契约层鉴权与配置说明与 yaml 同批（worker 同任务落盘，协调者同提交）；验收核对内容与实际配置一致 |
| `docs/superpowers/roadmaps/*.md` → roadmaps/ | 无 | n/a | 未触发 |
| `frontend/.env.prod` → frontend/README.md | 无 | n/a | 未触发 |

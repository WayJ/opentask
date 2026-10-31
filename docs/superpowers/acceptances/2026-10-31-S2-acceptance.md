# Acceptance record — sprint S2, 2026-10-31

## Verdict

pass — 五个必需场景全部现场复跑通过（含两条 verbatim 门禁命令在载体本环境全绿：backend pytest 395P/0F/0E、frontend lint 0 error + build 成功）；TD1 关闭有据；PG 切换（D11）落地且 README 同批；doc_sync_map 触发行（backend/config/*.yaml → backend/README.md）已在同批变更中满足；无未偿欠账。DoD 中首提交/ls-remote 两项属 S3 承接；websocket 两文件 vibeking 残留属 E1-S1 分支已验收修复（88cef1d），本树自基线继承、S1 合并后消除（见 Obstacles）。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-10-31-S2-plan.md","record":"docs/superpowers/acceptances/2026-10-31-S2-acceptance.md","fingerprint":"71b68f5d2c6f5d305b16c9a2b044fca9f0cb4716616d3d1f8686a5a521d10ebc"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"71b68f5d2c6f5d305b16c9a2b044fca9f0cb4716616d3d1f8686a5a521d10ebc","environment":"本机 Windows 11；载体 worktree D:/projects/opentask-worktrees/S2（分支 sprint/E1-S2，基线 e2e6ade）；DB 为 Docker opentask-pg（postgres:16，localhost:5432，dev 库 opentask / test 库 opentask_test，基线迁移 003ccd38d5cd 已 upgrade，volume opentask-pgdata）；前端 node_modules 经 pnpm 12.16.1 安装、门禁命令 verbatim npm run；运行时间 2026-10-31T09:0xZ UTC","results":[{"id":"S1","status":"passed","modality":"cli","environment":"real","steps":["运行 grep 检查 config.py 与 config/*.yaml 无 mysql 代码残留","uv run python 打印解析后的数据库配置"],"expected":"连接串为 postgresql+asyncpg，无 mysql 残留","observed":"grep -i mysql 于 config.py+四份 yaml 零命中；解析输出 host: localhost db: opentask driver: asyncpg","artifacts":["Scenario Results 表","backend/README.md 数据库节"],"blockers":[]},{"id":"S2","status":"passed","modality":"gate","environment":"real","steps":["docker PG 容器运行中","cd backend","uv run pytest tests/ -v"],"expected":"0 failed（通过或合法跳过）","observed":"395 passed, 27 skipped, 0 failed, 0 error（89.27s；27 skip 均合法：18 个已下线架构/已移除端点的文档化跳过 + 9 个原有模板/环境 skip）","artifacts":["Scenario Results 表（verbatim 门禁输出）"],"blockers":[]},{"id":"S3","status":"passed","modality":"gate","environment":"real","steps":["cd frontend","npm run lint","npm run build"],"expected":"lint 0 error；build 成功产出 dist","observed":"lint 退出 0（0 errors / 272 存量 warnings）；build 退出 0，Build successful，dist 产出（6.6 MB）","artifacts":["Scenario Results 表（verbatim 门禁输出）"],"blockers":[]},{"id":"S4","status":"passed","modality":"cli","environment":"real","steps":["grep TD1 清单路径验证 agent_task/file_storage/agent_v3 死引用零命中","查看 docs/tech-debt-tracker.md TD1 行状态"],"expected":"死引用零命中；TD1 移入已关闭区附证据","observed":"源码 grep 零命中（仅 main.py:25 注释行与已清理的陈旧 .pyc，TD1 关闭证据已载明）；TD1 行已关闭，删除路线全清单附证据","artifacts":["docs/tech-debt-tracker.md TD1 行"],"blockers":[]},{"id":"S5","status":"passed","modality":"cli","environment":"real","steps":["cd backend","uv run python -c \"import opentask.api\""],"expected":"无 ImportError","observed":"import OK","artifacts":["Scenario Results 表"],"blockers":[]}]}
```

## Gate Evidence

- 载体分支 tip（评审时）：`e2e6ade` + 未提交工作区（本记录随载荷一并提交）
- `cd backend && uv run pytest tests/ -v`：**395 passed, 27 skipped, 0 failed, 0 error**（2026-10-31T09:0xZ，载体本环境，Docker opentask-pg 运行中）
- `cd frontend && npm run lint && npm run build`：lint **0 errors**（272 warnings 存量非阻塞）+ build **Build successful**（dist 6.6 MB）
- 两命令均 verbatim 取自宿主 `### gates`，完整输出如上；本块供 complete 阶段门禁短路核对（tip+清单一致时）

## Scenario Results

| id | command | expected | actual | pass |
|---|---|---|---|---|
| S1 | grep + 配置解析 | PG 无 mysql 残留 | 0 命中；postgres/asyncpg | yes |
| S2 | `uv run pytest tests/ -v`（门禁 verbatim） | 0 failed | 395P/27S/0F/0E | yes |
| S3 | `npm run lint && npm run build`（门禁 verbatim） | 0 error + build 成功 | lint 0 err；build OK | yes |
| S4 | TD1 grep + tracker | 零死引用 + 已关闭 | 源码零命中；TD1 closed | yes |
| S5 | `import opentask.api` | 无 ImportError | OK | yes |

## DoD Checklist

- [ ] `git log` 首次提交 + ls-files 无凭据文件 — **S3 承接**（推送 sprint）；先行证据：git ls-files 无 local.yaml/.env.prod.local/chatapp/.env.prod（均 ignored）
- [x] vibeking 全仓扫描仅命中 backend/openapi*.json — 代码/配置层：S2 改动域零命中；全仓剩余 = openapi*.json（允许）+ websocket auth/config 2 文件（基线继承，E1-S1 分支 88cef1d 已修复，S1 合并紧随其后消除）+ 文档自引用 3 处（S1 记录同款解释）
- [x] 高危密钥模式零命中 — backend/frontend 源码扫描零命中（本轮实测）
- [x] `cd backend && uv run pytest tests/ -v` 通过 — 395P/0F/0E/27S（场景 S2，verbatim）
- [x] `cd frontend && npm run lint && npm run build` 通过 — 双退出 0（场景 S3，verbatim）
- [ ] CLI 可安装运行输出版本号 — **S1 已验收覆盖**（opentask v1.0.6，S1 记录）；S2 载体未含 S1 的 CLI 改动，合并后随 S1 记录成立
- [x] 导入图零缺失维持 — import opentask.api OK；TD1 死引用清除后导入图更净
- [ ] 推送后 ls-remote 一致 — **S3 承接**

## Obstacles (verbatim)

- 2026-10-31 07:25Z — S2-A 问询：mysql_* 属性改名波及允许路径外引用点（alembic/env.py、fix_uuid 脚本、utils、repositories/base.py；另迁移链为 MySQL 方言）→ 协调者授权扩围修复 + 迁移链重建为单一 PG 基线（45 表+20 枚举，up/down 往返验证）。
- 2026-10-31 07:4xZ — S2-B 问询：14 个非 DB 失败根因在 3 个越界源文件（auth.py 401 语义、hub_service 迭代变异集合/内存注册不 upsert、task_service DocumentSummary 缺必填）→ 授权修复（均真实缺陷）。
- 2026-10-31 08:5xZ — worker D 问询：最后 14 项卡在 5 个越界源文件（INSERT 缺 NOT NULL 列、str 上调 .value、RETURNING 读 .rowcount、TaskResponse 缺 link_data、settings NameError）→ 授权最小修复；备选「skip+blocked」被否。
- 2026-10-31 全程 — 前端 npm ci 不可用（workspace 协议）→ pnpm 安装 + 门禁 verbatim npm run（D3 裁定）；PyPI 清华镜像、Docker 镜像 daocloud mirror（docker.io 直连超时）。
- 2026-10-31 09:1xZ — TD1 复核遇陈旧 .pyc 命中（已删模块的编译缓存，gitignored）→ rm 清除，源码零命中；指纹不受影响（忽略文件不入快照）。
- 套件修复总账：基线 78F/196P/178E → 终态 395P/0F/0E/27S；conftest 模块级引擎重绑测试库 NullPool（根治 ~121 个 asyncpg InterfaceError）、幂等播种用户修复登录链、陈旧测试修正（路径前缀/信封断言/失效枚举/时间戳唯一化）、10 处真实源码缺陷修复（add_tag user_id、_generate_issue_code 方言无关化、issue 路由遮蔽、requirement 双重转换、project PUT query 误用、auth datetime naive/aware + 授权 5 文件）。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| `backend/config/*.yaml` → backend/README.md | **是** — 四份 yaml database 段切换 | current | README 数据库节（容器启动/连接/初始化）与 yaml 同批变更（worker 同任务落盘，协调者同提交提交）；验收核对 README 内容与实际凭据/端口一致 |
| `docs/superpowers/roadmaps/*.md` → roadmaps/ | 无 | n/a | 未触发 |
| `frontend/.env.prod` → frontend/README.md | 无（仅新增 .env 与 pnpm-lock.yaml，模式为 .env.prod） | n/a | 未触发 |

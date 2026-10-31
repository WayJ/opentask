# 技术债追踪

## 未关闭

| id | severity | item | repayment criteria | owner | date | evidence |
|---|---|---|---|---|---|---|
| TD3 | low | 根目录 `Dockerfile`（Node+Prisma）与 `docker-compose.yml`（postgres/redis 模板）与实际 Python+MySQL 技术栈不符 | 重写为 Python 版镜像与 MySQL 编排，或删除并移入 docs 说明 | — | 2026-10-31 | Dockerfile 内容 |
| TD5 | low | `backend/openapi.json` / `openapi_current.json` 是含改名前字符串的历史生成产物 | 重新生成后提交，或加入 .gitignore 改为构建期产物 | — | 2026-10-31 | 文件内容含 vibeking 字符串 |

## 已关闭（Closed）

| id | severity | item | resolution | closed | evidence |
|---|---|---|---|---|---|
| TD1 | medium | 后端存在改名前遗留的死导入：`opentask.services.file_storage`（api/git/router.py、services/git_service.py）、`opentask.services.agent_v3.integration`（services/conversation.py）、`opentask.models.agent_task` / `opentask.repositories.agent_task` / `opentask.services.agent_task.service`（tests/agent_task/*）——对应源模块目录均不存在 | 采取删除路线：删除 `opentask/api/git/`（未挂载的 router，__init__.py+router.py）、`tests/api/test_git.py`、`tests/knowledge_base/test_git_integration.py`（测试从未挂载的 /git/* 端点）、`tests/agent_task/{conftest_standalone,run_service_tests,test_agent_task_service,test_repository,test_service_async}.py`；`services/git_service.py` 改为持有 `knowledge_root` 路径（原 FileStorageService 依赖移除，内部 `_kb_dir`/`_doc_file_path`）；`services/conversation.py` 删除无调用方的死方法 `query()`（agent_v3 唯一引用点）及 4 个随之失效的导入；`tests/run_all_tests.py`、`run_quick_tests.py` 移除指向已删文件的条目 | 2026-10-31（E1-S2 worker task_29e9f8e538e5） | `grep -rn "from opentask.services.file_storage\|from opentask.services.agent_v3\|opentask\.models\.agent_task\|opentask\.repositories\.agent_task\|opentask\.services\.agent_task" backend/opentask backend/tests --include=*.py` 零命中（唯一残留 `main.py:25` 为注释行，非导入）；`opentask.app`、`opentask.services.git_service`、`opentask.services.conversation`、`opentask.services.auto_commit_service` 导入验证通过；`tests/conftest.py` 的 collect_ignore 遗留条目与 `agent_task_id` 字段/`agent_tasks` 表名等命中均为合法标识符，非死引用 |
| TD2 | low | `backend/opentask/api/oauth.py` 是断链符号链接（→ `oauth/router.py`，目标不存在；S1 勘察时已退化为 15 字节残留文件） | S1 删除该残留文件；全仓无 `api.oauth` 代码引用（仅存 `/api/oauth/` 均为 JNPF 外部 URL）；导入图静态校验无该断链 | 2026-10-31 | `git status` D backend/opentask/api/oauth.py（sprint/E1-S1 工作区）；grep 全仓 api.oauth 零代码命中 |
| TD4 | low | CLI 内 `cli_anything.opentask.*` 导入路径不存在（`opentask_cli.py:353` 的 subprocess 自调用、`tests/test_core.py` 的 5 处导入） | 记录中的死导入已在改名提交 e2e6ade 改为实际包路径 `opentask.*`（本次核查 `opentask_cli.py` 与 `tests/test_core.py` 均无 `cli_anything` 命中）；S1 进一步清除品牌残留：`repl_skin.py` docstring/banner/`CLI_ANYTHING_NO_COLOR`→`OPENTASK_NO_COLOR`/历史目录 `~/.cli-anything-*`→`~/.opentask-*`、`opentask/tests/TEST.md` 覆盖率目标、`tests/test_repl_skin.py` 测试名与历史目录断言、`test_commands.py`/`test_cli_edge_cases.py` 残留的 `vibe` 断言 | 2026-10-31 | `grep -rn "cli_anything\|cli-anything\|CLI_ANYTHING" agent-harness/` 零命中（S1 工作区）；`pip install -e . && opentask --version` → `opentask v1.0.6`，退出码 0；repl_skin 两个测试文件全部通过 |

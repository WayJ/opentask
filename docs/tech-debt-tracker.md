# 技术债追踪

| id | severity | item | repayment criteria | owner | date | evidence |
|---|---|---|---|---|---|---|
| TD1 | medium | 后端存在改名前遗留的死导入：`opentask.services.file_storage`（api/git/router.py、services/git_service.py）、`opentask.services.agent_v3.integration`（services/conversation.py）、`opentask.models.agent_task` / `opentask.repositories.agent_task` / `opentask.services.agent_task.service`（tests/agent_task/*）——对应源模块目录均不存在 | 每个缺失模块二选一：补齐实现，或删除引用它的调用点与测试文件；导入图静态校验零缺失 | — | 2026-10-31 | 导入图静态校验（AST）结果 |
| TD3 | low | 根目录 `Dockerfile`（Node+Prisma）与 `docker-compose.yml`（postgres/redis 模板）与实际 Python+MySQL 技术栈不符 | 重写为 Python 版镜像与 MySQL 编排，或删除并移入 docs 说明 | — | 2026-10-31 | Dockerfile 内容 |
| TD5 | low | `backend/openapi.json` / `openapi_current.json` 是含改名前字符串的历史生成产物 | 重新生成后提交，或加入 .gitignore 改为构建期产物 | — | 2026-10-31 | 文件内容含 vibeking 字符串 |

## 已关闭（Closed）

| id | severity | item | resolution | closed | evidence |
|---|---|---|---|---|---|
| TD2 | low | `backend/opentask/api/oauth.py` 是断链符号链接（→ `oauth/router.py`，目标不存在；S1 勘察时已退化为 15 字节残留文件） | S1 删除该残留文件；全仓无 `api.oauth` 代码引用（仅存 `/api/oauth/` 均为 JNPF 外部 URL）；导入图静态校验无该断链 | 2026-10-31 | `git status` D backend/opentask/api/oauth.py（sprint/E1-S1 工作区）；grep 全仓 api.oauth 零代码命中 |
| TD4 | low | CLI 内 `cli_anything.opentask.*` 导入路径不存在（`opentask_cli.py:353` 的 subprocess 自调用、`tests/test_core.py` 的 5 处导入） | 记录中的死导入已在改名提交 e2e6ade 改为实际包路径 `opentask.*`（本次核查 `opentask_cli.py` 与 `tests/test_core.py` 均无 `cli_anything` 命中）；S1 进一步清除品牌残留：`repl_skin.py` docstring/banner/`CLI_ANYTHING_NO_COLOR`→`OPENTASK_NO_COLOR`/历史目录 `~/.cli-anything-*`→`~/.opentask-*`、`opentask/tests/TEST.md` 覆盖率目标、`tests/test_repl_skin.py` 测试名与历史目录断言、`test_commands.py`/`test_cli_edge_cases.py` 残留的 `vibe` 断言 | 2026-10-31 | `grep -rn "cli_anything\|cli-anything\|CLI_ANYTHING" agent-harness/` 零命中（S1 工作区）；`pip install -e . && opentask --version` → `opentask v1.0.6`，退出码 0；repl_skin 两个测试文件全部通过 |

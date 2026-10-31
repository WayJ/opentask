# 技术债追踪

| id | severity | item | repayment criteria | owner | date | evidence |
|---|---|---|---|---|---|---|
| TD1 | medium | 后端存在改名前遗留的死导入：`opentask.services.file_storage`（api/git/router.py、services/git_service.py）、`opentask.services.agent_v3.integration`（services/conversation.py）、`opentask.models.agent_task` / `opentask.repositories.agent_task` / `opentask.services.agent_task.service`（tests/agent_task/*）——对应源模块目录均不存在 | 每个缺失模块二选一：补齐实现，或删除引用它的调用点与测试文件；导入图静态校验零缺失 | — | 2026-10-31 | 导入图静态校验（AST）结果 |
| TD2 | low | `backend/opentask/api/oauth.py` 是断链符号链接（→ `oauth/router.py`，目标不存在） | 删除该符号链接，或恢复目标文件 | — | 2026-10-31 | `find . -type l` 检查 |
| TD3 | low | 根目录 `Dockerfile`（Node+Prisma）与 `docker-compose.yml`（postgres/redis 模板）与实际 Python+MySQL 技术栈不符 | 重写为 Python 版镜像与 MySQL 编排，或删除并移入 docs 说明 | — | 2026-10-31 | Dockerfile 内容 |
| TD4 | low | CLI 内 `cli_anything.opentask.*` 导入路径不存在（`opentask_cli.py:353` 的 subprocess 自调用、`tests/test_core.py` 的 5 处导入） | 改为实际包路径 `opentask.*`，使 CLI 可在无额外安装前缀下运行 | — | 2026-10-31 | grep cli_anything |
| TD5 | low | `backend/openapi.json` / `openapi_current.json` 是含改名前字符串的历史生成产物 | 重新生成后提交，或加入 .gitignore 改为构建期产物 | — | 2026-10-31 | 文件内容含 vibeking 字符串 |

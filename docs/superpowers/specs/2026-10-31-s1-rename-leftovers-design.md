# S1 改名遗留修复 — 设计（2026-10-31）

epic: E1 · sprint: S1 · 状态：待批准

## 意图

公开发布前的改名收尾：清除 `vibe_king→opentask` 改名后遗留的断链与品牌残留，使后端与 CLI 的导入图零缺失、CLI 可安装运行。对应 epic DoD「导入图静态校验零缺失」「CLI 可安装运行」两项。

## 目标

1. 删除 `backend/opentask/api/oauth.py`（15 字节降级符号链接，指向已不存在的 `oauth/router.py`；全后端无本地引用）
2. CLI 内 `cli_anything` 品牌残留彻底清除（方案 A）：
   - docstring 示例路径与用法（`repl_skin.py:1-19`）改为 `opentask` 语境
   - 环境变量 `CLI_ANYTHING_NO_COLOR` → `OPENTASK_NO_COLOR`（`repl_skin.py:144`，测试同步改）
   - 历史目录 `~/.cli-anything-<软件>` → `~/.opentask-<软件>`（`repl_skin.py:131`）
   - `opentask/tests/TEST.md:155` 覆盖率命令、测试名 `test_cli_anything_no_color_env` 同步改名
3. `.claude/settings.json` 引用核查：全仓已零命中，记录证据关闭该任务
4. CLI 元数据诚实化：`pyproject.toml` `requires-python >=3.8` → `>=3.10`（代码用 `str | None` 语法，3.8/3.9 实际装不上）
5. （规划期补充）前端 `frontend/src/components/AgentPromptModal.vue` 8 处用户可见命令示例前缀 `cli-anything-opentask ` → `opentask `（仅前缀 token，命令体不动）—— 方案 A 彻底去品牌的同一品牌残留
6. （规划期补充）关闭技术债 TD4：其记录的 `cli_anything.opentask.*` 死引用在当前代码已零命中，补证据后关闭台账条目

## 非目标

- PostgreSQL 切换（epic D11，S2 范围）
- 死引用修复与 pytest/lint/build 门禁（S2）
- 首次提交/推送（S3）
- cli-anything 上游项目的任何改动（本仓库只是 vendored 副本）

## 约束

- sprint 文档五段结构与逐字 DoD 不可变（`docs/superpowers/sprints/2026-10-31-S1-plan.md`）
- 在 worktree `../opentask-worktrees/S1`（分支 `sprint/E1-S1`）执行，main 保持干净
- `str | None` 等语法不动 —— 只改元数据声明，不降级代码写法

## 方案取舍

- **A. 彻底去品牌（用户选定）**：docstring/env var/目录/测试名全改。仓库今日才首次公开、包未发 PyPI，无外部兼容负担；与 D2（统一改名）精神一致。
- B. 最小修复（否决）：只改文档性文本 —— 行为零变化，但 `cli_anything` 品牌永久留在公开代码里，违背改名收尾的意图。

## 留给执行者的细节

- 导入图静态校验的具体命令（walk_packages 逐模块导入或等价手段）在计划阶段定义并写入验收场景
- env var 改名后 `test_repl_skin*.py` 相关断言的同步修改清单
- `.claude` 零命中的证据（grep 输出）记入验收记录

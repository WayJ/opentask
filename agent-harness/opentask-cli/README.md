# OpenTask CLI

面向人类与 AI Agent 的 OpenTask 命令行客户端。

**Version**: **v1.1.0** · Python 3.8+ · 默认 API `http://localhost:7377`

## 主轴（E14）

1. `login` → 2. `workspace use`（请求头带 `X-Workspace-Id`）→ 3. `project` / `issue` → 4. `cycle` / `label` / `triage` 等 Linear 常用面。

遗留：`requirement` / `task` / `collection` 仍可用（后端保留），但不再作为默认主路径（E12 去 PGE）。

## 安装

```bash
cd agent-harness/opentask-cli
pip install -e .
# 或
uv sync && uv run opentask --version
```

## 快速开始

```bash
opentask config set-api http://localhost:7377
opentask login -U smoke_way -P 'SmokeTest123!'
opentask workspace list
opentask workspace use <workspace-id>
opentask project list
opentask issue create -t "CLI smoke" --json
opentask issue show KEY-1 --json
opentask cycle list --json
opentask label list --json
opentask triage list --json
```

所有命令支持 `--json`；错误形如：

```json
{"success": false, "error": "HTTP 400", "message": "...", "status_code": 400, "details": {}}
```

配置文件：`~/.opentask/config.json`（含 `active_workspace_id` / `active_project_id`）。

## 命令一览

| 组 | 子命令 |
|---|---|
| `workspace` | list / use / current / show |
| `project` | list / show / create / update / use / current / delete |
| `issue` | list / show / create / update / assign / status 工作流 / children / relation / branch-name / link-branch / link-pr / vcs-links / comment / document |
| `cycle` | list / show / create / activate / complete |
| `label` | list / create / delete / attach / detach |
| `triage` | list / enqueue / accept / decline / duplicate |
| `inbox` | list / read / read-all / snooze / unsnooze |
| `favorite` | list / add / remove |
| `view` | list / show / use |
| `member` | list / add / remove / role |
| `invite` | list / create / revoke / preview / accept |
| `initiative` | list / show / create / update / delete |
| `doc` | list / show / create / update / delete |
| `requirement` / `task` / `collection` | 遗留 PGE 面（仍可用） |

## 测试

```bash
uv run pytest -q
bash scripts/e14_cli_smoke.sh   # 需本地 BE :7377
```

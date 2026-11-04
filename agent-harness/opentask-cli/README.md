# OpenTask CLI

面向人类与 AI Agent 的 OpenTask 命令行客户端。

**Version**: **v1.4.0** · Python 3.8+ · 默认 API `http://localhost:7377`

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
opentask issue list --mine --json
opentask issue list --watching --json
opentask issue list --due-soon --json
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
| `issue` | list / show / create / update（含 `--estimate-points`）/ watch / unwatch / watchers / assign / status 工作流 / children / relation / branch-name / link-branch / link-pr / vcs-links / comment / document |
| `cycle` | list / show（附容量）/ capacity / create / activate / complete |
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


## E17 估点与容量

```bash
# 创建/更新故事点
opentask issue create -t "Ship search" --estimate-points 5 --json
opentask issue update KEY-12 --estimate-points 8 --json
opentask issue show KEY-12   # 展示 EstimatePoints
opentask issue list          # Pts 列

# Cycle 点容量 / velocity hint（对齐 GET /api/cycles/capacity-hint）
opentask cycle capacity --json
opentask cycle capacity --cycle-id <id> --json
opentask cycle show <id>     # 人类可读时附带 SuggestedCapacity / LoadPoints
```


## E18 Issue Watch

```bash
opentask issue watch KEY-1 --json
opentask issue watchers KEY-1 --json
opentask issue show KEY-1          # Watching 字段
opentask issue unwatch KEY-1 --json
```

关注后，他人对该 Issue 的评论 / 状态 / 指派会进入你的 Inbox。

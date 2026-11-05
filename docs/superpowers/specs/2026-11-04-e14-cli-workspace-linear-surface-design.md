# E14 设计：OpenTask CLI 做完整（Workspace + Linear 常用面）

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E14-S1` @ 基线 `sprint/E13-S1` `eb76295`  
worktree：`/workspace/opentask-worktrees/E11-S4`  
包：`agent-harness/opentask-cli`（v1.0.6 → **1.1.0**）  
约束：**本地提交，禁止 push / 禁止 PR**；不改 E13 FE 视觉；少问多做。

## 问题

CLI v1.0.6 能 login / project / issue（含 KEY-N、VCS）/ requirement / task / collection，但：

1. **无 Workspace 上下文**：请求不带 `X-Workspace-Id`，而 cycles/tags/triage/favorites/saved-views/initiatives/entity-docs 等均 `require_workspace_context` → 400「缺少 X-Workspace-Id」。
2. **Linear 常用面缺失**：cycle / label(tags) / triage / inbox / favorite / view / member+invite / initiative / doc。
3. **主轴仍偏 PGE**：README/help 仍把 requirement/task 当主路径；E12 去 PGE 后应以 **Issue + Workspace** 为轴。
4. Project list 未强调 workspace；部分命令 JSON 错误形态不统一。

## 决策

| # | 决策 |
|---|---|
| C1 | Config 增加 `active_workspace_id` / `active_workspace_name`（`~/.opentask/config.json`）；语义对齐 FE `localStg.workspaceId` |
| C2 | `OpenTaskClient._get_headers()`：若 config 有 active workspace → 所有请求附加 `X-Workspace-Id`；可用 env `OPENTASK_WORKSPACE_ID` 临时覆盖（可选，YAGNI 可后加） |
| C3 | 新命令组 `opentask workspace list\|use\|current\|show`；`use` 持久化；list 走 `GET /api/workspaces` |
| C4 | Issue 保持一等公民：list/show/create/update/assign/status 已有；补 `children` / `relations`（API 已有）；VCS 已有 branch-name/link-*，补 `vcs` 子组或保留现名并在 help 挂齐 |
| C5 | 新命令组（有后端才做）：`cycle`、`label`（映射 `/api/tags`）、`triage`、`inbox`、`favorite`、`view`（saved-views 只读 list/show/use）、`member`+`invite`（挂 workspace 下或顶层最小）、`initiative`、`doc`（entity-documents） |
| C6 | Project CRUD+use 保留；list/create 依赖当前 WS header，与 FE 一致 |
| C7 | requirement/task/collection **保留**（后端仍在），但 README / `--help` 文案以 Issue/Workspace 为默认主轴，PGE 降为「遗留/进阶」 |
| C8 | 版本 bump **1.1.0**；错误 `--json` 统一 `APIError.to_dict()` 形态 |
| C9 | 单测：workspace header、KEY-N、新命令 help + client path；冒烟脚本打本地 `:7377` |

## 非目标

- 不实现后端没有的面；不改 FE；不 push；不开 E15；不重写 click 架构；不做交互式 TUI。
- Saved views：list/show/use（把 filter 印出/存本地提示）即可，不做完整 CRUD UI。
- Invite accept 公开 token 流可最小：`invite preview|accept` 走 `/api/invites/{token}`。

## 命令清单（目标）

```
opentask workspace list|use <id>|current|show [id]
opentask project …（现有；list 尊重 WS）
opentask issue …（现有 + children|relations；vcs 已有）
opentask cycle list|show|create|activate|complete
opentask label list|create|delete|attach|detach   # tags
opentask triage list|enqueue|accept|decline|duplicate
opentask inbox list|read|read-all|snooze|unsnooze
opentask favorite list|add|remove
opentask view list|show|use
opentask member list|add|remove|role
opentask invite list|create|revoke|preview|accept
opentask initiative list|show|create|update|delete
opentask doc list|show|create|update|delete
opentask issue branch-name|link-branch|link-pr|vcs-links  # E11 已有
```

## 缺口（后端无则 CLI 跳过）

无（上表均有对应 HTTP）。Webhook 属服务端，CLI 不暴露。

## 验收条

人类/agent 仅用 CLI：`login → workspace use → project create/list → issue create/list/update(KEY-N) → cycle/label/triage 常用`；`--json` 错误可解析；CLI pytest 全绿。

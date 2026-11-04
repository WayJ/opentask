# E14 验收：OpenTask CLI 做完整（Workspace + Linear 面）

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E14-S1`  
包版本：**1.1.0**  
约束：**未 push / 未开 PR**

## 交付摘要

| 项 | 状态 |
|---|---|
| `X-Workspace-Id` 全请求注入 | ✅ Config `active_workspace_*` + Client headers |
| `workspace list\|use\|current\|show` | ✅ |
| Issue 一等（含 KEY-N、children、relations、VCS） | ✅ VCS 已有；补 children/relation |
| cycle / label / triage / inbox / favorite / view / member / invite / initiative / doc | ✅ |
| Project list 解包 rows + 尊重 WS header | ✅ |
| README / `--help` 主轴 Issue+WS | ✅ |
| 单测 workspace header + KEY-N | ✅ |
| 冒烟脚本 | ✅ `agent-harness/opentask-cli/scripts/e14_cli_smoke.sh` |
| 版本 1.1.0 | ✅ |

## 命令清单（新增 / 变更）

**新增顶层组：** `workspace` `cycle` `label` `triage` `inbox` `favorite` `view` `member` `invite` `initiative` `doc`  
**Issue 新增：** `issue children` `issue relation list|add|remove`  
**变更：** Client 全请求可带 `X-Workspace-Id`；`project list` 正确读 `rows`；help/README 去 PGE 主轴

## 测试

```text
uv run pytest -q
# 本机记录：400 passed / 89 skipped / 7 failed
# 7 failed 均为既有坏测（非 E14 回归）：
#   - test_create_collection（status draft vs planning）
#   - test_config_load_existing_file / test_config_default_values（污染真实 ~/.opentask）
#   - test_color_support_when_tty
#   - test_comments_group_exists / test_requirement_update_*（requirement 组名/mock）
# E14 新增全绿：test_workspace_header(3) / test_workspace_commands(7) / test_e14_key_n(2) / issue_vcs(5)
# 冒烟：bash scripts/e14_cli_smoke.sh → E14 smoke OK（BE :7377，账号 smoke_way）
```

## 冒烟（本地 BE :7377）

```bash
cd agent-harness/opentask-cli
bash scripts/e14_cli_smoke.sh
# 账号默认 smoke_way / SmokeTest123!
```

## 顺带修复

- `issue create` 默认 `type=feature`（后端枚举无 `task`）；Choice 对齐 `bug|feature|question|feedback|incident|improvement`
- `project create` 尊重全局 `--json`

## 缺口

- 无（规格所列后端面均已挂 CLI）。Webhook 不暴露。
- 既有 CLI 坏测未在本 Epic 全量修复（与 E14 无关）。

## 非目标确认

未改 E13 FE；未 push；未开下一 Epic。

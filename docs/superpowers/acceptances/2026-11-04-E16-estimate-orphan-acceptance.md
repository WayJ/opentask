# E16 验收：故事点 · Cycle 点容量 · 孤儿 Default WS · 坏测清零 · PGE 快扫

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E16-S1` · tip `03d8b0c`  
基线：`sprint/E15-S1` @ `386fc9b`  
worktree：`/workspace/opentask-worktrees/E11-S4`  
约束：**未 push / 未开 PR**；齐套后待命，**不自开 E17**。

## 交付摘要

| 项 | 结果 |
|----|------|
| Issue `estimate_points` 读写 | 详情右栏 Fibonacci 可编辑；列表「估点」列；看板默认显示；⌘K「设置估点…」+ 热键 picker |
| Cycle 容量默认按点 | `capacity-hint`：`unit=points\|issues\|members`；样本含 `completedPoints`/`completedIssueCount`/`completedHours`；有点历史优先均值点；全 0 回退 Issue 数；无历史回退成员数；可选 `currentLoad` |
| 孤儿 Default WS | Alembic `a1b2c3d4e5f9` 删除 0 成员种子；`WorkspaceService.cleanup_orphan_default_workspace`；list 懒清理 + 硬排除 id；3 测 |
| 原 3 坏测 | 遗留脚本移出采集（`testpaths=tests`）；`AccessToken` 注册修 mapper；新 `tests/services/test_task_protocol_rules.py` 3 绿 |
| PGE 快扫 | `workflow_requirements` / `agents` / `home` 均 `hideInMenu`；`VITE_ROUTE_HOME=issue_list` — 无需改码 |
| E15 IDOR | `test_tenant_idor` 5 绿，未回退 |

## 测试

### 后端 pytest
```text
PYTHONPATH=. .venv/bin/pytest -q
# 824 passed / 24 skipped / 0 failed
```

### 前端 vitest（闸门）
```text
display-prefs + command-palette + de-pge-nav + e13-linear-nav
# 4 files / 23 passed
```

### 容量默认说明（产品）
- **默认单位：故事点（points）**
- 次要：完成 Issue 个数、预估工时总和（样本字段并存，不驱动默认 suggestedCapacity，除非点全为 0）
- 成员回退：尚无 completed Cycle 历史时

## 未做 / 非目标
- velocity 图 / burndown
- CLI 估点子命令
- 物理删 PGE 表
- **未 push**

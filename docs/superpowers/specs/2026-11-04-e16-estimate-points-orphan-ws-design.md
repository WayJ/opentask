# E16 设计：故事点估算 · Cycle 点容量 · 孤儿 Default WS · 坏测清零 · PGE 快扫

日期：2026-11-04（Asia/Shanghai）  
Epic：E16  
基线：`sprint/E15-S1` @ `386fc9b`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E16-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E17**。

## 1. 目标

1. **Estimate 点（Linear 式）**：Issue 故事点可读写（与 `estimated_hours` 并存）；列表/看板/详情可见可改；Cycle **容量默认按点汇总**（小时为次要并存信息）。
2. **Default Workspace 孤儿**：`00000000-0000-4000-8000-000000000001` 无成员种子 → 迁移清理，永不进 list；补测。
3. **后端 3 既有坏测**：`opentask/api/test/test_task_protocol_rules.py` → 修到绿（根因：`AccessToken` 未注册进 metadata）。
4. **PGE 快扫**：主导航/默认首页/Agent 路径若仍逼 PGE → 清或隐藏（不删表）。

## 2. 探索事实

| 项 | 现状 |
|---|---|
| `issues.estimate_points` | E6-S2 已加列 + schema Create/Update；API 可写 |
| 详情右栏 | 仅展示 `estimated_hours`，**无估点编辑** |
| 列表列 | **无**估点列；看板有 `estimate_points` 字段开关（默认 false） |
| Cycle `capacity-hint` | 按 **完成 Issue 个数** 均值；FE 文案「个 Issue」；类型已预留 `completedPoints?` |
| Default WS | 迁移种子存在、0 成员；`list_for_user` 按 membership 已不泄漏（A9 PASS）；仍应物理清理 |
| 3 坏测 | 脚本式测落在 `opentask/api/test/`；`UserModel.access_tokens → AccessToken` 未 import → mapper 炸 |
| PGE | `workflow_requirements` / `agents` / `home` 均 `hideInMenu`；`VITE_ROUTE_HOME=issue_list` |

## 3. 决策

| ID | 决策 |
|----|------|
| D1 | 估点存 `Numeric`，UI 提供 Fibonacci 枚举 `1/2/3/5/8/13/21` + 清空；仍允许 API 任意 `>=0` |
| D2 | **容量默认单位 = points**：历史样本 `completedPoints = Σ estimate_points(done)`（null→0）；`suggestedCapacity = mean(points)`；若全部点为 0 则回退 `unit=issues` 用个数均值；无历史则 `unit=members` |
| D3 | 样本同时返回 `completedIssueCount` + `completedPoints` + 可选 `completedHours`（次要）；响应加 `unit: "points"|"issues"|"members"` |
| D4 | 孤儿 Default WS：Alembic 删除（先将指向它的 project/issue `workspace_id` 置 NULL）；服务层 `cleanup_orphan_default_workspace` + list 硬过滤该 id |
| D5 | 3 坏测：在 `opentask.models` 注册 `AccessToken`；保留文件位置 |
| D6 | PGE：确认隐藏即可，不扩 scope；验收记录快扫结果 |
| D7 | 不 push；不改全局主题；不自开 E17 |

## 4. 非目标

- 精修 velocity 图 / burndown
- 物理删除 PGE/requirement 表
- 改 IDOR 逻辑（保持 E15）
- CLI 估点命令（可后续）

## 5. 验收摘要

- Issue 详情可改估点；列表/看板能看见；Cycle 容量文案按点
- 孤儿 WS 迁移后不存在或不可列；测试覆盖
- `pytest` 0 fail（含原 3 条）
- 跨租户负例仍绿

# E15 验收：租户 IDOR 硬化

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E15-S1`  
基线：`sprint/E14-S1` @ `0f64111`  
worktree：`/workspace/opentask-worktrees/E11-S4`  
约束：**未 push / 未开 PR**；齐套后待命，不自开更远 Epic。

## 根因

列表/创建已用 `X-Workspace-Id` + 成员校验；**按 UUID 直读/直写**（`GET/PUT/DELETE /api/projects/{id}`、`GET/PUT/DELETE /api/issues/{id}` 及 comments/relations/attachments 等子资源）只叠全局 `authenticate`，未校验实体 `workspace_id` 成员资格 → 跨租户可读可改。

## 修复

| 层 | 变更 |
|----|------|
| `api/workspace/deps.py` | 新增 `ensure_entity_workspace_access`（非空 WS → `require_member`；NULL 遗留行放行） |
| `api/project/router.py` | `GET/PUT/DELETE /{id}` 加载后验成员 |
| `api/issue/router.py` | `_require_issue_access` / `_require_comment_issue_access`；覆盖 get/update/delete、comments、relations、attachments、children、timeline、reactions、status/assignee/priority/reporter；`by_code` header 精确滤不回退 |

## 测试

### 后端 pytest
```text
.venv/bin/pytest -q
# 817 passed / 3 failed / 24 skipped
# 新增 tests/api/test_tenant_idor.py → 5 passed
# 3 failed = opentask/api/test/test_task_protocol_rules.py（既有/采集环境问题，与 E15 无关）
```

### 线上 IDOR 复跑（BE :7377，账号 smoke_*）
| 断言 | 结果 |
|------|------|
| e13 GET Demo Project（own_ws / wrong_ws / no_header） | 403 无权访问该工作区 |
| e13 PUT Demo Project | 403 |
| e13 GET First smoke issue UUID | 403 |
| e13 GET 本租户 project | 200 |
| e13 list + Smoke WS header | 403 |

### CLI（顺带快修原 7 坏测）
```text
407 passed / 89 skipped / 0 failed
# Config 不再污染 ~/.opentask；collection status=draft；NO_COLOR；requirement update mock get；comments 组允许缺失
```

## 未做 / 非目标

- 公开 `/api/attachments/{id}/download|preview`（无认证）另票
- 遗留 `workspace_id IS NULL` 行强制迁移
- viewer 写权限细粒度
- **未 push**

## 回执要点

- tip：见 git log HEAD
- 路由硬化清单见上表
- 停，不开 E16+

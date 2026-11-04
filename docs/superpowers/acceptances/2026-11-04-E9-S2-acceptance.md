# E9-S2 Acceptance — Issue Templates

日期：2026-11-04（Asia/Shanghai）  
Epic：E9 · Sprint：S2  
Worktree：`/workspace/opentask-worktrees/E9-S2` · 分支 `sprint/E9-S2`  
基线：E9-S1 `e0aad93` → plan `ccceed7`  
**未推远程** · **未开 S3**

## Gates

| gate | result |
|---|---|
| `pytest` (backend cwd) | **744 passed**, 27 skipped；3 failed 预存 `opentask/api/test/test_task_protocol_rules.py`（UserModel/AccessToken mapper，与 E9-S2 无关） |
| templates file | `tests/api/test_issue_templates.py` **8 passed** |
| FE eslint (touched) | 0 errors |
| FE vitest `command-palette.test.ts` | **12 passed** |
| FE `pnpm run build` | successful（`.env`/`.env.prod` → E8-S1） |

## Delivered vs design §S2

| item | status |
|---|---|
| `issue_templates` + Alembic `e1f2a3b4c5d7` ← `d0e1f2a3b4c6` | done |
| `GET/POST/PATCH/DELETE /api/issue-templates`（workspace 作用域） | done |
| GET 空表自动 seed 5 builtins（`seed_key` 幂等） | done |
| `POST /api/issues` 可选 `template_id` 合并 payload | done |
| FE client `issue-templates.ts` | done |
| `IssueTemplateSelector` API 优先 + 常量 fallback | done |
| Create `?pickTemplate=1` / `?templateId=` + 提交带 `template_id` | done |
| Settings `/workspace/issue-templates` CRUD | done |
| ⌘K「从模板创建」+「Issue 模板」设置 | done |
| 不与 PGE `prompt_generator` 混用 | done（文案/路由独立） |
| Snooze / Inbox S3 | **out of scope** |

## Key APIs

- `GET /api/issue-templates` — 列表；空则 seed
- `POST /api/issue-templates` — 创建（member+）
- `PATCH /api/issue-templates/{id}` / `DELETE …`
- `POST /api/issues` + `template_id` — 合并 title/description/type/priority 等

## Key UI

- Create Issue：选模板 / `?pickTemplate=1`
- ⌘K：`nav.create_from_template` → `/issue/create?pickTemplate=1`
- `/workspace/issue-templates` 管理页

## Gaps / notes

- Settings 页未挂侧栏静态菜单项（可通过 ⌘K / 直链进入；与 Labels 同属 workspace 路由树）
- `labelIds` / `projectId` payload 字段后端可存，FE 设置页 MVP 未做标签/项目选择器
- 3 个 protocol_rules 失败为预存 mapper 问题，非本 sprint 引入
- 常量 `ISSUE_TEMPLATES` 仍作 fallback / seed 镜像

## Decision

**Accept S2 local-complete.** `merged-commit: null`. Do not start S3 in this acceptance. No push.

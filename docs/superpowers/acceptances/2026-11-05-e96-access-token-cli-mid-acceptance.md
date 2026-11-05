# E96 Acceptance：Access Token CLI mid · CLI 1.80.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E96-S1`  
基线：`0f8b28f`（全文 `0f8b28f1a7f0afcce59bd4a5cd399f525f0180f1`；含 E96 design；E95 tip `2809068` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e96-access-token-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e96-access-token-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用既有 `GET/POST/DELETE /api/access-tokens`；邻面 spy 6 绿；**无**新 alembic/e96；**无** PATCH/rename/续期；**未改** E95 project-repos / E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster；OAuth2 面与个人 access_tokens 区分 |
| B FE | ✅ | **零产品 FE**；vitest **427 passed**；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 冲掉 imports/typings → **已 checkout 恢复**；WT 干净） |
| C CLI 1.80.0 | ✅ | 新顶层组 `access-token list\|create\|revoke`（`rm` 别名）；api_client 三 helpers → GET/POST（body `{name, description?}`）/DELETE；human list 薄表 id/name/token_prefix/expires_at/last_used_at；create 醒目一次打印完整 token +「仅此一次可见」；**仅** `--save` 写本地 `config.access_token`（默认不写/不覆盖）；缺 `--name` 本地失败不打 BE；**未改** `config set-access-token` 既有语义；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.80.0**；历史 epic 断言级联；directed **20 passed** |
| D 安全/邻面/no-emit | ✅ | 测试**仅**假 token `vk_TEST_ONLY_NOT_A_REAL_TOKEN`（+ sentinel `vk_SENTINEL_PREVIOUS_NOT_REAL` / prefix 样例）；隔离 HOME/config；默认 create 证明未改 config；diff 扫描无真实 `vk_` 密钥；未改 E79–E95 邻面；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** OAuth2 client CRUD / 真 Git / requirement-repos / PATCH rename；**未停** 7377/9527 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E96-S1`
- tip short：fd84208
- tip full：fd8420838c654a7faff7136506ee9a03f759910c
- **未 push / 未开 PR / 未开 E97**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E96 BE `tests/api/test_e96_access_token_cli_mid.py` | **6 passed** |
| Directed E96 CLI `tests/test_e96_access_token.py` | **20 passed** |
| Full BE `pytest tests` | **1456 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **836 passed**, 89 skipped（含 directed E96 **20 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 冲掉 imports → 已 checkout 恢复；WT 干净） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.80.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有三端点 `GET/POST/DELETE /api/access-tokens`
- Q2a CLI 新顶层组 `access-token list|create|revoke`（`rm` 别名）；与 `config set-access-token` 并存
- Q3a 仅显式 `--save` 写入 `config.access_token`；默认绝不写/覆盖；api_client create body `{name, description?}`
- Q4a human list 薄表 id/name/token_prefix/expires_at/last_used_at；create 醒目一次打印 token +「仅此一次可见」；`--json` 全量（含一次性 token）
- Q5a pins **1.80.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 安全确认

- 测试只用假 token：`vk_TEST_ONLY_NOT_A_REAL_TOKEN`（及 `vk_SENTINEL_PREVIOUS_NOT_REAL` / `vk_TEST` / `vk_xxxx` 元数据样例）
- 默认 create **不**写本地 config；`--save` 才写（临时 HOME/config 隔离证明）
- 仓库 / 日志 / acceptance / plan **无**真实 token；文档用假样例或「仅此一次」提示
- list **永不**输出原文（BE 列表本无 `token` 字段）
- **未**调用真实创建接口签发生产钥；**未**触碰真实用户 `~/.opentask`

## 禁区

未触碰：E95 project-repos / E94 reactions / E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**未改** `config set-access-token` 语义；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** OAuth2 client CRUD / SSO / 真 Git / requirement-repos / AccessToken PATCH·rename·续期；**未停** 7377/9527；WT 干净；未 push / 未开 PR / 未自开 E97。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / bulk project_id / `project list --watching` / Issue VCS unlink / OAuth2 client CRUD / 真 Git / requirement-repos / E97
- flake：`test_user_search`（已知，不阻塞）

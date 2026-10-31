# S6 联调证据：契约层 OpenAPI spec + 错误语义 + Orca 侧端到端（2026-10-31）

worker: task_ba16d5d45c53（dispatch ctx_91cc9c711add），worktree `sprint/E2-S6`。
本文档为 sprint 台账 `2026-10-31-S6-plan.md` 的 S1–S5 验收留证。

## 结论速览

| 项 | 结果 | 证据 |
|---|---|---|
| S1 契约 spec 生成且一致 | ✅ | `backend/openapi_contract.json` + `tests/tasks/test_tasks_openapi.py` 对账测试 |
| S2 三类错误独立语义 | ✅ | `tests/tasks/test_tasks_errors.py`（401/403/503/404/422 全错误码） |
| S3 契约测试全绿 | ✅ | `cd backend && uv run pytest tests/tasks/ -v` → **97 passed** |
| S4 Orca 侧注册联调 | ⛔ **blocked**（本机 Orca 无自定义任务源注册面）| 见下「Orca 侧探测」；替代证据 = 活体服务器五操作 E2E + 契约套件 + capabilities |
| S5 导入图维持 | ✅ | `uv run python -c "import opentask.api"` 无 ImportError |

## Orca 侧探测（S4：blocked 及依据）

按任务要求探测本机 Orca 的自定义任务源注册能力，结论：**本机 Orca 构建不提供自定义任务源注册面，注册 `http://localhost:8000` 契约端点不可行**。

探测过程（2026-10-31，本机 `orca` CLI）：

1. `orca --help` 全量命令清单（约 40 组命令）——无任何 task source / 任务源设置命令；
   与"任务"相关的仅有 `orchestration task-*`（Orca 内部编排任务 DAG，非外部任务源）。
2. 外部任务集成均为**固定 provider**：Jira（`orca jira *`）、Linear（`orca linear *`）、
   GitHub/GitLab（`worktree create/set --issue/--pr/--linear-issue/--gitlab-issue`）。
3. `orca jira connection --json` → `{"connected": false, "sites": [], ...}`；
   其技能指南（`orca skills get orca-jira`）明确 *"Configure credentials in Orca Settings"*——
   Jira 站点连接只能经桌面端 Settings UI 配置，无 CLI/配置文件入口
   （`orca.yaml`、`~/.orca`、安装目录均无 `taskSource`/`task_source`/`customTask` 配置面）。
4. 即便经 Settings UI 添加"Jira 站点"，Orca 以 Jira REST 线格式（JQL、transitions、
   `rest/api/2`）访问；OpenTask 契约 API（`/tasks`、`/capabilities`）非 Jira 线格式，
   冒充 Jira 站点无法工作。epic 所述"模拟 Jira 模式"指集成模式（外部任务源），
   而非 Orca 侧可配置的通用任务源。

**遗留（epic 关闭时列入）**：Orca 侧真实注册联调待 Orca 提供自定义任务源配置面
（或 OpenTask 侧实现 Jira 线格式兼容层）后补做；本 sprint 以替代证据透明降级。

## 替代证据：活体服务器五操作 E2E（S4 降级路径）

真实 uvicorn 实例（`uv run uvicorn opentask.main:app --port 8000`，测试库
`opentask_test`，Docker `opentask-pg`），用户 `orca_e2e_user` + `vk_` API Key
经 access_token 体系签发。以下为实跑转录（响应体经截断标注）。

### 0. 能力协商（公开端点）

```json
GET /capabilities → 200
{"contract_version":"1.0",
 "endpoints":{"list_tasks":"GET /tasks","create_task":"POST /tasks","get_task":"GET /tasks/{task_id}",
              "update_task":"PATCH /tasks/{task_id}","delete_task":"DELETE /tasks/{task_id}",
              "issue_token":"POST /tasks/token","capabilities":"GET /capabilities"},
 "features":{"pagination":"limit_offset","incremental_cursor":"updated_since",
             "cursor_semantics":"exclusive","delete_semantics":"soft",
             "status_mapping_source":"config","forbidden_operations":"none"},
 "auth":{"modes":["bearer_api_key","oauth2_client_credentials"],"scheme":"Bearer",
         "token_endpoint":"/tasks/token","grant_type":"client_credentials","api_key_prefix":"vk_"},
 "status_vocabulary":["cancelled","done","in_progress","in_review","todo"]}
```

### 1. 鉴权与 token 交换

```
GET  /tasks                        → 401 {"detail":{"code":"CONTRACT_AUTH_MISSING","message":"缺少 Bearer 凭证…"}}
GET  /tasks  (Bearer vk_bogus)     → 401 {"detail":{"code":"CONTRACT_AUTH_INVALID","message":"API Key 无效、已过期或用户被禁用"}}
POST /tasks/token (client_credentials, client_id+client_secret=vk_ Key)
                                   → 200 {"access_token":"eyJhbGciOiJIUzI1NiIs…","token_type":"Bearer","expires_in":7200}
                                      （无 refresh_token 字段；库中无新增 refresh_tokens 行）
```

### 2. 五操作（Bearer API Key）

```
GET /tasks?limit=3                 → 200 {"items":[],"total":0,"limit":3,"offset":0}
POST /tasks {title/description/assignee/status=todo/labels=[orca-e2e,contract]}
                                   → 201 {"id":"4b2a725d-…","status":"todo",
                                           "labels":["contract","orca-e2e"],
                                           "metadata":{"issue_code":"ISSUE2026-1","type":"feature",
                                                       "username":"orca_e2e_user",…},
                                           "url":"/issue/detail?id=4b2a725d-…"}
GET /tasks/{id}                    → 200（同上形状）
PATCH /tasks/{id} {status:"in_progress", description:…}
                                   → 200 {"status":"in_progress","updated_at":"2026-10-31T12:03:01.228449"}
DELETE /tasks/{id}                 → 204
GET /tasks/{id}（软删后）           → 404 {"detail":{"code":"CONTRACT_TASK_NOT_FOUND","message":"任务不存在: 4b2a725d-…"}}
```

### 3. 增量游标（排他语义）

```
GET /tasks?updated_since=2026-10-31T12:03:01.228449（= 该任务 updated_at）
                                   → 200 {"items":[],"total":0}   # 同游标重拉零重复
```

### 4. 落库核验（psql，测试库）

```
issues:      ISSUE2026-1 | ORCA-E2E 契约联调任务 | status=in_progress | is_deleted=t   # 软删除，行保留
issue_timeline（按时间序）:
  created         {"title":"ORCA-E2E 契约联调任务","type":"feature","issue_code":"ISSUE2026-1"}
  label_added     {"tag_id":62,"label":"orca-e2e"}
  label_added     {"tag_id":63,"label":"contract"}
  status_changed  {"from":"open","to":"in_progress"}                              # PATCH 写入既有 timeline
```

联调数据已清理（user/issues/tags/access_tokens 归零核验）。

## 契约套件与 spec（S1–S3）

- `cd backend && uv run pytest tests/tasks/ -v` → **97 passed**（53 项 S4/S5 既有 + 22 项
  S6 错误路径/错误码 + 12 项 spec 对账 + 10 项 code review 回归）。
- `backend/openapi_contract.json`：FastAPI 既有机制导出，仅含
  `/tasks`、`/tasks/{task_id}`、`/tasks/token`、`/capabilities`；含
  `ContractErrorResponse`（401/403/404/503/422 声明）、`HTTPBearer` 安全方案、
  全部契约模型（字段与 pydantic `model_fields` 逐一相等，见对账测试）。
  重新导出：`cd backend && AUTH_SECRET_KEY=<密钥> uv run python -m opentask.api.tasks.openapi_export`。
- 错误码表（与 `backend/README.md` 同批定稿）：
  400 `CONTRACT_AUTH_UNSUPPORTED_GRANT` / 401 `CONTRACT_AUTH_MISSING`·`CONTRACT_AUTH_INVALID` /
  403 `CONTRACT_FORBIDDEN` / 404 `CONTRACT_TASK_NOT_FOUND` / 422 `CONTRACT_STATUS_UNKNOWN` /
  503 `CONTRACT_UNAVAILABLE`；优先级 503 > 401 > 403。

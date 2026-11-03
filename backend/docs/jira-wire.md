# Jira 线格式兼容层（`/rest/api/2/*`）— 契约说明

本文件是 OpenTask **Jira 线格式兼容层**的仓内权威契约。它面向两类读者：

- **外部适配方**（如 Orca 的自建 Jira 集成）：照此实现客户端，或核对兼容性；
- **本仓维护者**：新增/变更 Jira 线端点时，**必须同步更新本文件**——漂移由
  `backend/tests/tasks/test_jira_wire_doc.py` 拦截（每个已实现路由都必须在本文件中出现）。

> 历史背景：Jira 线格式的**实现依据**是 S7 探测报告
> `docs/superpowers/sprints/2026-11-01-S7-orca-jira-probe.md`（对 Orca Jira 适配器的
> 源码级探测结论）。本文件是那份报告的**长期落点**——探测报告是 sprint 台账，会随归档失联；
> 本文件是接口契约，不随 sprint 生命周期消失。

---

## 1. 定位与挂载

| 项 | 说明 |
|---|---|
| 前缀 | `/rest/api/2`（Jira Server/Data Center 的 v2 线；Orca 的 `authType: "server"` 站点**永远**走 v2） |
| 挂载方式 | ASGI catch-all：`/rest/api/2/{jira_path:path}` 转发到内层 `opentask.api.jira.router` |
| 为何不是 FastAPI 路由 | 转发层不建模，故 **Jira 线不出现在 `backend/openapi*.json`**——这是有意为之：契约层 `/tasks` 的 spec 保持干净。副作用是 Jira 线的形状契约**只以本文件为准**（即 TD8 的由来） |
| 与 `/tasks` 契约层的关系 | 两层**共用**映射内核（`api/tasks/mapping.py`）、鉴权内核（`api/tasks/auth.py` 的 `resolve_contract_token`）、错误码族（`CONTRACT_*`）。Jira 线**不复制业务逻辑**，读写一律经 `ContractIssueService` / `IssueService`（与 UI 侧同权限路径） |
| 读写语义 | 成功写操作返回 **204 无 body**（Jira/Orca 期望 `204 → null`） |

## 2. 鉴权

Orca 的 server 模式站点每请求带：

```
Authorization: Basic base64(username:token)     # 连接表单里的 email 即 username 位
Authorization: Bearer <PAT>                     # username 留空的 PAT 模式
```

- 两种头都只取其中的 **token** 交给契约凭证内核 `resolve_contract_token`（`vk_` API Key 或 JWT → 用户）；
  Basic 的 username 位**不参与校验**（仅作展示提示）。
- 依赖不可达（503）**先于** 401 判定——与 `/tasks` 契约层同序。
- 被禁用的操作（`contract.forbidden_operations`）→ **403**，Jira 形状错误体。

## 3. 错误体（Jira 形状）

所有语义错误统一为：

```json
{"errorMessages": ["CONTRACT_XXX: 可读消息"], "errors": {}}
```

字段级错误放 `errors.{field}`（此时 `errorMessages` 为空数组）。错误码沿用契约层
`CONTRACT_*` 命名族（唯一定义处 `api/tasks/errors.py`，此处直接复用不复制）。

| 语义 | HTTP | 错误码 |
|---|---|---|
| 鉴权缺失/无效 | 401 | `CONTRACT_AUTH_CODE_MISSING` / `CONTRACT_AUTH_CODE_INVALID` |
| 禁用操作 | 403 | `CONTRACT_FORBIDDEN_OP` |
| 资源不存在 | 404 | `CONTRACT_TASK_NOT_FOUND` |
| 状态未知 | 400/422 | `CONTRACT_STATUS_UNKNOWN` |
| JQL 越界 | 400 | `CONTRACT_BAD_REQUEST` |
| 依赖不可达 | 503 | `CONTRACT_UNAVAILABLE` |

Orca 侧读 `errorMessages[]` + `errors{}` 的 values + `message`，分号拼接；缺省回退 HTTP statusText。

## 4. 端点清单（18 条，全部已实现）

| Method | Path | 用途 | Orca 侧对应 |
|---|---|---|---|
| GET | `/myself` | 连接验证 + viewer | 连接时自动调用（`jira:connect`） |
| POST | `/search` | 列表 + JQL 搜索（单页语义） | `jira list` / `jira search` |
| GET | `/project` | 项目列表 | `jira project list` |
| GET | `/issue/createmeta/{project_key}/issuetypes` | 项目下 issue 类型 | `jira project types` |
| GET | `/issue/createmeta/{project_key}/issuetypes/{type_id}` | 建单可用字段 | `jira project fields` |
| GET | `/priority` | 优先级词表 | `jira priority list` |
| GET | `/field` | 字段发现（缓存，失败非致命） | 内部字段发现 |
| GET | `/filter/favourite` | 收藏过滤器（渲染器用，失败优雅降级） | 渲染器 |
| GET | `/issue/{key}` | 读取单个 issue | `jira issue <key>` |
| POST | `/issue` | 建单（201） | `jira create` |
| PUT | `/issue/{key}` | 更新字段（204） | `jira priority set` / `jira label set` |
| PUT | `/issue/{key}/assignee` | 指派/清除（204） | `jira assignee set/clear` |
| GET | `/issue/{key}/transitions` | 可用状态流转 | `jira status list` |
| POST | `/issue/{key}/transitions` | 状态流转（204） | `jira status set` |
| GET | `/issue/{key}/comment` | 评论列表 | `jira comment list` |
| POST | `/issue/{key}/comment` | 新增评论（201） | `jira comment add` |
| GET | `/user/assignable/search` | 可指派用户检索 | `jira assignee list` |
| GET | `/user/search` | 用户检索 | 内部 |

路径前缀均为 `/rest/api/2`（表中省略）。

## 5. 形状要点

### 5.1 issue 对象

顶层 `id` / `key` / `fields` / `renderedFields`（可选，缺省安全）。`fields` 关键字段：

- `summary` / `description`：server 线为**纯文本字符串**（非 ADF）
- `status`：`{id, name, statusCategory: {key, name}, colorName}`——**`statusCategory` 必须存在**
  （Orca 的 `list --filter done` 依赖 `statusCategory = Done` 的 JQL，终态判定亦然）
- `assignee` / `reporter`：`{name, displayName, emailAddress?, avatarUrls?}` 或 `null`
- `project` / `issuetype` / `priority` / `labels` / `created` / `updated` 等见 `api/jira/converters.py`

### 5.2 搜索响应

```json
{"issues": [...], "total": 0, "startAt": 0, "maxResults": 30}
```

server 模式**单页语义**（Orca 不做 `startAt` 翻页）；`maxResults` 由客户端钳制在 `1..100`，
服务端 50 兜底（`SEARCH_MAX_LIMIT = 100`）。

### 5.3 JQL 支持子集

```
field := assignee | reporter | status | statusCategory | key | issueKey
        | project | summary | text | description
op    := = | != | ~ | in
值    := "引号串" | currentUser() | 裸词
排序  := ORDER BY updated [ASC|DESC]   （缺省 DESC）
```

- 子句间 **AND**；同一 `in (...)` 内 **OR**。
- `sprint` 筛选恒为空集（语义合法但必然无结果）；`project = 别的项目` 等同理返回空页。
- **子集外语法（OR / was / 日期比较 / NOT 等）显式 400**，不静默吞子句——静默丢弃会让
  「没搜到」与「不支持」不可区分。

## 6. 状态映射

Jira 线与 `/tasks` 契约层共用 `api/tasks/mapping.py` 的映射内核（可经 `contract.status_mapping`
配置调整；未配置时用下表兜底）：

| OpenTask `IssueStatus` | 通用状态（契约层） | Jira `statusCategory` |
|---|---|---|
| `open` | `todo` | To Do |
| `in_progress` | `in_progress` | In Progress |
| `feedback` | `in_review` | In Review |
| `resolved` | `done` | Done |
| `closed` | `done` | Done |
| `rejected` | `cancelled` | Done |

## 7. 已知边界（有意不做）

- **Cloud 线 `/rest/api/3/*`**：Orca 自建站点走 server 线，v3 不实现。
- **Agile 看板 `GET /rest/agile/1.0/board`**：Orca 渲染器会调，失败**优雅降级**为空列序，
  OpenTask 侧不实现该端点。
- **PKCE / 动态注册 / introspection**：与 OAuth2 Provider 口径一致，YAGNI 不做。
- **Jira Webhook / 附件上传**：Orca Jira 适配器未使用，不实现。

## 8. 维护约定

1. 新增/删除 Jira 线端点 → 同步改本文件 §4 表格 + §5 形状要点。
2. 改错误码或鉴权语义 → 同步改 §2 / §3。
3. `backend/tests/tasks/test_jira_wire_doc.py` 会断言「已实现路由 ⊆ 本文件表格」，
   漏改文档 → 测试红。
4. 形状层面的回归由 `backend/tests/tasks/test_tasks_jira_wire.py`（40 例）覆盖。

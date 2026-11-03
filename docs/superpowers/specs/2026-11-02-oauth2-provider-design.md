# OpenTask OAuth2 Provider 设计规格

- 日期：2026-11-02
- 仓库：`wayj/opentask`（worktree `opentask/tunicate`，分支 `WayJ/oauth2-provider`）
- 状态：已评审（协调者裁决 A/B/C/D/E/F/G 已固化，见文末「裁决记录」）
- 契约权威性：本文件是**跨仓契约权威**——端点路径、claim 语义、scope 语义、错误形状以本文件为准；dsh-saas 侧实现（`ds/superpowers/specs/2026-11-02-opentask-oauth-binding-design.md`）必须与本文件一致。

---

## 1. 目标与非目标

### 1.1 目标

OpenTask 增 OAuth 2.0 **Provider（授权服务器）**能力，使外部应用（首个消费者：dsh-saas admin 工作台「应用」菜单）能以标准 OAuth 2.0 授权码流程与 OpenTask 用户建立绑定，并以**只读**权限代表该用户读取其任务 / 项目 / 需求。

形态是 **GitHub-in-Orca 式「应用连接 + 代表用户调 API」**，不是页面嵌入（iframe）。

### 1.2 非目标（本期明确不做）

| 项 | 理由 |
|---|---|
| PKCE（RFC 7636） | 消费者是服务端 confidential client，client secret 保存在 dsh-saas 服务端密文存储，PKCE 边际收益低 |
| 动态客户端注册（RFC 7591） | client 由管理员在 OpenTask 后台显式注册，无自助注册需求 |
| Token 内省端点（RFC 7662） | 资源服务器与授权服务器同进程，直接本地校验签名即可 |
| OAuth token 黑名单 | 吊销走 `oauth_access_tokens.revoked_at` 与 refresh token 表 |
| 写权限（scope） | 本期只读；写操作不开放给第三方 |
| 改动既有 `/tasks` 契约层、`/api/*` 通用端点鉴权链、`user` 表结构、JNPF/钉钉同步链 | 边界约束 |

---

## 2. 架构

```
┌──────────────────── OpenTask（授权服务器）────────────────────┐
│  /oauth2/authorize      授权端点（未登录→登录页回跳；已登录→同意页）│
│  /oauth2/token          令牌端点（authorization_code / refresh_token）│
│  /oauth2/userinfo       用户信息端点（绑定对齐用）                    │
│  /oauth2/revoke         吊销端点（RFC 7009）                        │
│  /oauth2/clients        client 注册管理 API（管理员）                 │
│  /oauth2/api/*          只读数据面（任务 / 项目 / 需求）              │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 模块划分

| 单元 | 职责 | 依赖 |
|---|---|---|
| `models/oauth2/` | 3 张表的 SQLAlchemy 模型 | `models/base.py` |
| `services/oauth2/client_service.py` | client 注册/校验、secret 生成与校验 | models、config |
| `services/oauth2/authorization_service.py` | 授权码签发与消费、TTL、重放检测 | models、user_center/utils |
| `services/oauth2/token_service.py` | access/refresh token 签发、轮换、吊销 | models、jwt_utils |
| `services/oauth2/identity_service.py` | email → OpenTask 用户定位/建号 | models、user_center/utils |
| `api/oauth2/schemas.py` | 请求/响应模型 | pydantic |
| `api/oauth2/router.py` | 端点装配 | services |
| `api/oauth2/dependencies.py` | `require_oauth_client` / `require_oauth_scope` | jwt_utils、services |
| `api/oauth2/read_api.py` | 只读数据面（薄封装既有 service 层） | 既有 service 层 |

---

## 3. 数据模型

三张新表，挂在既有单一 alembic 基线（revision `003ccd38d5cd`）**之后**的新 revision 上（不改基线，ADR D11 约束）。

### 3.1 `oauth_clients`

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | CHAR(36) PK | UUIDMixin |
| `client_id` | VARCHAR(64) UNIQUE | 公开标识，如 `dsh-saas` |
| `client_secret_hash` | VARCHAR(64) | SHA-256(client_secret)，**不存明文** |
| `name` | VARCHAR(255) | 应用名，同意页展示 |
| `description` | TEXT NULL | 同意页展示 |
| `redirect_uris` | TEXT | 逗号分隔白名单，`authorize` 时精确匹配 |
| `scopes` | VARCHAR(512) | 允许的 scope 集合，空格分隔 |
| `grant_types` | VARCHAR(128) | 默认 `authorization_code refresh_token` |
| `status` | VARCHAR(16) | `ACTIVE` / `DISABLED` |
| `created_by` | VARCHAR(36) FK user.id | |
| `created_at` / `updated_at` | TIMESTAMP | |

### 3.2 `oauth_authorization_codes`

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | CHAR(36) PK | |
| `code_hash` | VARCHAR(64) UNIQUE | 授权码 SHA-256 |
| `client_id` | VARCHAR(64) FK oauth_clients.client_id | |
| `user_id` | VARCHAR(36) FK user.id | |
| `redirect_uri` | VARCHAR(2048) | |
| `scope` | VARCHAR(512) | |
| `expires_at` | TIMESTAMP | 默认签发后 10 分钟 |
| `used_at` | TIMESTAMP NULL | 一次性消费标记 |
| `created_at` | TIMESTAMP | |

### 3.3 `oauth_access_tokens`

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | CHAR(36) PK | |
| `token_hash` | VARCHAR(64) UNIQUE | JWT `jti` 的 SHA-256 |
| `client_id` | VARCHAR(64) FK oauth_clients.client_id | |
| `user_id` | VARCHAR(36) FK user.id | |
| `scope` | VARCHAR(512) | |
| `expires_at` | TIMESTAMP | |
| `revoked_at` | TIMESTAMP NULL | |
| `created_at` | TIMESTAMP | |

**refresh token 不建表**：复用既有 `refresh_tokens` 表（`models/user_center/model.py`）承载？—— **不**。既有 `refresh_tokens` 表按 `user_id` 归属，用于 Web 会话刷新，与 OAuth 的 client 归属语义不同，且其轮换逻辑会吊销用户全部 refresh（疑似泄漏语义）。故 OAuth refresh token **另建 `oauth_refresh_tokens` 表**，字段同 §3.3 加 `token_hash` / `client_id` / `user_id` / `scope` / `expires_at` / `revoked_at` / `rotated_to_hash`。

> 说明：最终落地为 **4 张新表**（clients / authorization_codes / access_tokens / refresh_tokens）。OAuth refresh 与会话 refresh 生命周期独立：Web 会话改密不应吊销第三方应用授权，反之亦然。

---

## 4. 令牌语义

### 4.1 Access token（JWT）

复用既有 `opentask.jwt_utils.create_access_token`（HS256，`AUTH_SECRET_KEY`）。

**claims 定稿**：

| claim | 值 | 说明 |
|---|---|---|
| `sub` | `str(user.id)` | 用户 ID |
| `tv` | `user.token_version` | 与既有会话 token 同语义：改密/批量吊销后旧 token 失效 |
| `aud` | `client_id` | 资源服务器标识 |
| `scope` | 空格分隔的 scope 串 | **不是 `scp`** |
| `jti` | UUID4 | 用于 `oauth_access_tokens.token_hash` 关联与吊销 |
| `exp` | 签发后过期 | 有效期默认 2h，同 `AUTH_ACCESS_EXPIRE_MINUTES` |

**为什么不用 `scp`**：`scp` 已被 OpenTask 内部受限令牌占用——`backend/opentask/auth.py:122` 精确等值比较 `payload.get("scp") == "pwd_change"` 决定是否只放行改密端点。同一 claim 承载两套互斥语义会埋雷。OAuth scope 走 RFC 9068 的 `scope` claim。

### 4.2 scope 强制方式（零改动既有鉴权链）

**实测事实**（backend `uv run`，python-jose **3.5.0**）：

| 情形 | 结果 |
|---|---|
| token 带 `aud`，`jwt.decode` **不传** `audience=` | `JWTError: Invalid audience` |
| token 带 `aud`，`audience=` 传匹配值 | OK |
| token 带 `aud`，`audience=` 传错值 | `JWTError: Invalid audience` |
| token 不带 `aud`，不传 `audience=` | OK |

`jwt_utils.verify_token` 调 `jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])` **不传 audience** → 任何带 `aud` 的 token 在既有全局链（`app.py:80` `common_dependencies` → `authenticate` → `get_current_user`）与契约层 `resolve_contract_token` 中被 `except JWTError` 转成 **401 Invalid token**。

**结论**：OAuth access token（带 `aud`）**天然无法进入** `/api/*` 通用端点与 `/tasks` 契约层——只读 scope 形同虚设的风险为零，**既有 `auth.py` / `jwt_utils.py` 零改动**。

**必须新增回归测试**把该库行为钉死（见 §8），防止将来 python-jose 升级改变该行为时静默失守。

### 4.3 OAuth 侧校验内核

```python
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_aud": False})
```

随后显式校验：
1. `aud` 存在且等于某个 `status=ACTIVE` 的已注册 client_id
2. `scope` 包含端点要求的 scope，否则 **403 `insufficient_scope`**
3. `sub` 对应用户存在且 `status == 1`（禁用用户失效）
4. `tv == user.token_version`（改密/批量吊销失效）
5. `jti` 未被吊销（`oauth_access_tokens.revoked_at IS NULL`）且未过期

> `options={"verify_aud": False}` + 签名验证的组合：签名验证通过即 `aud` 被认证（篡改签名的 token 实测被拒）。等价替代方案是先用 `jwt.get_unverified_claims` 取 `aud` 再以 `audience=<aud>` 解码。

### 4.4 Refresh token

- 明文 `secrets.token_hex(32)`，**仅在 `/oauth2/token` 响应里下发一次**，库中只存 SHA-256 哈希（与既有 `refresh_tokens` 表纪律一致）
- 轮换：每次刷新签发新 refresh 并吊销旧行
- **重放检测**：已吊销的 refresh 被再次使用 → 视为泄漏，**吊销该用户全部活跃 OAuth token**（同既有会话 refresh 的泄漏处置语义）
- 有效期默认 30 天（`AUTH_OAUTH_REFRESH_EXPIRE_DAYS` 可配）

---

## 5. 端点

### 5.1 `GET /oauth2/authorize`

**请求**：`client_id`、`redirect_uri`、`response_type=code`、`scope`、`state`

**校验顺序**（任一失败均不泄露内部信息）：
1. `client_id` 存在且 `status=ACTIVE` → 否则 400 `invalid_client`
2. `redirect_uri` 与该 client 白名单**精确匹配** → 否则 400 `invalid_redirect_uri`（**不回显任何信息，防开放重定向**）
3. `response_type=code` → 否则 400 `unsupported_response_type`
4. 请求 scope ⊆ client 允许 scope → 否则 400 `invalid_scope`

**分支**：
- **未登录** → 302 到前端登录页，带 `redirect` 回跳参数（复用既有 `frontend/src/router/guard/route.ts:66` 的 `?redirect=` 机制），登录后回到本页继续
- **已登录** → 302 到前端同意页 `/oauth2/consent?...`（携带原始参数）

### 5.2 `POST /oauth2/authorize/approve`

同意页调用（需 OpenTask 会话）。body：`client_id`、`redirect_uri`、`scope`、`state`、`decision`（`approve` / `deny`）。

- `approve` → 签发授权码（存哈希，10 分钟 TTL）→ 302 `redirect_uri?code=...&state=...`
- `deny` → 302 `redirect_uri?error=access_denied&state=...`

### 5.3 `POST /oauth2/token`

`application/x-www-form-urlencoded`，支持 `grant_type=authorization_code` / `refresh_token`。

**`authorization_code`**：
1. `code` 存在 → 否则 400 `invalid_request`
2. 哈希查授权码 → 未命中 400 `invalid_grant`
3. `client_id` + `client_secret` 校验 → 失败 401 `invalid_client`
4. 授权码所属 client 与请求 client 一致 → 否则 400 `invalid_grant`
5. `expires_at` 未过期 → 否则 400 `invalid_grant`
6. `used_at IS NULL` → 否则 400 `invalid_grant` **且触发重放处置**（吊销该用户全部活跃 OAuth token）
7. 消费授权码（写 `used_at`）→ 签发 access token + refresh token

**`refresh_token`**：
1. 哈希查 refresh 行 → 未命中 400 `invalid_grant`
2. `client_id` + `client_secret` 校验 → 失败 401 `invalid_client`
3. 已吊销（`revoked_at` 非空）→ 400 `invalid_grant` **且触发重放处置**
4. 轮换：签发新 refresh，吊销旧行

**成功响应**（RFC 6749 §5.1）：
```json
{"access_token": "...", "token_type": "Bearer", "expires_in": 7200, "refresh_token": "...", "scope": "read:tasks read:projects read:requirements profile"}
```

**错误响应**（RFC 6749 §5.2）：`{"error": "invalid_grant", "error_description": "..."}`，HTTP 400 / 401。

### 5.4 `GET /oauth2/userinfo`

`Authorization: Bearer <access_token>`。返回：
```json
{"sub": "<opentask user.id>", "username": "...", "name": "...", "email": "..."}
```
> `email` 为**外部传入并落 username 种子**的原始 email（OpenTask `user` 表无 email 列，见 §6）。

### 5.5 `POST /oauth2/revoke`

RFC 7009。`token` + `client_id` + `client_secret`。吊销该 token 对应的 access token 与 refresh token。始终返回 200（不泄露 token 是否存在）。

### 5.6 `GET/POST/PATCH/DELETE /oauth2/clients`

管理员（既有管理员权限判定）维护 client 注册。
- `POST` 返回 `client_id` 与 **`client_secret` 明文（仅此一次）**
- `GET` 列表**不返回** secret 明文，只返回前缀
- `PATCH` 可改 name/description/redirect_uris/scopes/status；secret 轮换用独立动作

### 5.7 只读数据面 `GET /oauth2/api/*`

| 端点 | 所需 scope | 取数路径 |
|---|---|---|
| `GET /oauth2/api/tasks` | `read:tasks` | **通用 issue service**：`IssueService.get_issues(params, visible_dept_ids=…, user_id=…)`——与通用 `GET /api/issues` 同源同口径 |
| `GET /oauth2/api/projects` | `read:projects` | 既有 project service 层 + `RbacService.get_visible_dept_ids` 收窄 |
| `GET /oauth2/api/requirements` | `read:requirements` | 既有 requirement service 层 + `RbacService.get_visible_dept_ids` 收窄 |
| `GET /oauth2/api/me` | `profile` | 当前用户 |

**取数口径（数据范围）**：三个数据端点一律按**代表成员的部门可见集**收窄——`visible_dept_ids = await RbacService(session).get_visible_dept_ids(user)`，再配合「或本人创建」（`user_id`），与通用 `/api/issues`、`/api/projects`、`/api/requirements` 完全一致。

> **任务端点为何不走契约层取数**：契约层 `ContractIssueService.list_issues_for_contract` **不带部门可见性过滤**——直接复用会把**整个工作区**的任务集暴露给只读 scope。故任务端点改走通用 issue service 的取数路径；**契约层 service 与 `/tasks` 路由一概未改**（不污染 Orca 对接面，也不需要给契约层加参数）。

**参数**：

| 参数 | 语义 |
|---|---|
| `status`（仅任务端点） | **OpenTask 原生任务状态词表**（`IssueStatus`：open / in_progress / feedback / resolved / closed / rejected）——**不是**契约层的通用状态词表（通用词表是集合语义，单值过滤会漏数据，故不采用）；未知值 → 400 `invalid_status` |
| `limit` / `offset` | 分页窗口（`limit` 上限 50）。通用 service 以 page/page_size 分页，其 offset 是 `(page-1)*page_size`。窗口换算：`page_size=limit`，`page=offset//limit+1`，取本页后切 `[offset%limit:]`；切完不足 `limit` 条且本页已满，再取下一页拼上。最多两次查询，窗口精确 |

**响应形状**沿用既有契约层 DTO（`ContractTaskListResponse`：`items` / `total` / `limit` / `offset`，item 为 `ContractTask`），便于消费者复用解析。

---

## 6. 身份对齐（email → OpenTask 用户）

**事实**：OpenTask `user` 表**全列无 email**（`backend/opentask/models/user/model.py`：name / username / password_hash / role / status / token_version / must_change_password / failed_attempts / locked_until / last_login_time / sync_time / jnpf_* / organize_* / position_* / dingtalk_user_id / jwt_expires_at / openai_* / langsmith_* / sentry_*）；JNPF 与钉钉同步链也无 email 字段。**本期不改 `user` 表结构**。

**流程**（dsh-saas 回调时带 `email` + `display_name`）：
1. 按 `username` 精确查（lower 归一化）→ 命中即复用该用户
2. 未命中 → 建号：
   - `username = unique_username(existing_names, email)`（`services/user_center/utils.py`，冲突自动 `_2` / `_3`）
   - `name = display_name`
   - `role = "viewer"`、`password_hash = None`
   - 风格照 `services/user_center/dingtalk/oauth_service.py:87` `_create_user`
3. 返回 `external_user_id`（= OpenTask `user.id`）与 `external_email` 给 dsh-saas 落绑定关系

**已知副作用**：若该用户此前经 JNPF/钉钉同步建过账号且 `username != email`，会另建新账号——OAuth「首次连接自动建号」的常规语义。

**实施状态（2026-11-02）**：`OAuthIdentityService.resolve_or_create` 已实现，但**未被授权流程调用**。`/oauth2/token` 走 `find_by_id(record.user_id)`——谁在同意页点了同意，就代表谁。标准 OAuth2 下身份由授权服务器的登录会话决定；dsh-saas 成员若没有 OpenTask 账号，无法完成同意。另外前端用户名正则 `^[一-龥a-zA-Z0-9_-]{4,16}$` 不允许 `@`、最长 16，与「email 作 username 种子」冲突。本期不改核心 `user` 表、不放宽该正则，登记为待裁定技术债。

**裁定结论（2026-11-03，用户拍板）**：**走「维持标准 OAuth2 语义」路线**——成员须**先有 OpenTask 账号**才能完成授权同意，授权流不接入自动建号。

- 产品口径：资源所有者身份由**授权服务器的登录会话**决定（谁在同意页点同意就代表谁）。dsh-saas 侧成员若无 OpenTask 账号，需先注册/登录 OpenTask，再发起连接。
- 因此 `OAuthIdentityService.resolve_or_create` **保留在仓内但不接线**（含其单测），作为未来若改口径时的现成实现；本期不改核心 `user` 表、不放宽前端正则。
- 需求侧动作（非本仓）：dsh-saas 的「连接 OpenTask」入口需在引导文案中说明「需先有 OpenTask 账号」，并给出注册入口。
- 技术债 TD6 据此销账，证据见 `docs/tech-debt-tracker.md` 与 `.agents/notes/2026-11-03-debt-fixes.md`。
- 顺带**订正本节前述的一个误解**（2026-11-03 复核）：前端 `REG_USER_NAME` 正则只约束**前端表单**，后端 `user.username` 是 `String(50)` 唯一索引且**无格式校验**——该正则**不构成**服务端自动建号的障碍。真正的待裁定项从来是**身份来源与信任模型**（email 从哪来、客户端可否代断言 email），而非正则。

---

## 7. 前端同意页

| 项 | 内容 |
|---|---|
| 文件 | `frontend/src/views/oauth2/index.vue`（**实际落地路径**，与本节初稿写的 `consent.vue` 不同——2026-11-03 订正） |
| 路由 | 由 elegant-router 从 views 目录生成（`pnpm gen-route`），路由名 `oauth2`，路径 `/oauth2/authorize`（初稿写 `/oauth2/consent`，以实现为准） |
| 展示 | 应用名、应用描述、申请的 scope 清单（中文映射）、目标 redirect_uri 主机名 |
| 交互 | 「同意授权」/「拒绝」按钮；同意走 `POST /api/oauth2/authorize/approve`，拒绝走 `decision=deny`（初稿写 `/oauth2/authorize/approve`，**实际后端路径带 `/api` 前缀**） |
| 未登录 | 复用既有路由守卫 `?redirect=` 机制，登录后自动回到同意页 |
| API | 新增 `frontend/src/service/api/oauth2.ts`，沿用既有 `request` 封装 |

---

## 8. 测试策略

`backend/tests/oauth2/`：

| 文件 | 覆盖 |
|---|---|
| `test_client_crud.py` | client 注册 API；secret 仅一次下发；列表不返回明文；禁用 client 拒绝授权 |
| `test_authorization_flow.py` | 授权码全链路；redirect_uri 不匹配拒绝；scope 越权拒绝；授权码 10min TTL；**一次性消费**；**重放 → 吊销该用户全部 token** |
| `test_token_endpoint.py` | RFC 6749 §5.2 错误形状；refresh 轮换；refresh 重放 → 吊销 |
| `test_scope_enforcement.py` | scope claim 校验；`insufficient_scope` 403；**带 aud 的 token 进不了 `/api/*` 与 `/tasks`**（F2 库行为回归钉死） |
| `test_userinfo.py` | userinfo 形状；email → 用户定位/建号；已存在用户复用 |

前端：`npm run lint` + `npm run build`；浏览器证据用 MCP Playwright 录同意页、登录回跳、只读数据面。

---

## 9. 配置

| 配置项 | 默认 | 说明 |
|---|---|---|
| `AUTH_SECRET_KEY` | 无（必配） | 复用既有 JWT 密钥，不新增第二把密钥 |
| `AUTH_OAUTH_CODE_EXPIRE_SECONDS` | 600 | 授权码 TTL |
| `AUTH_OAUTH_REFRESH_EXPIRE_DAYS` | 30 | refresh token 有效期 |
| `AUTH_OAUTH_CLIENT_SECRET_BYTES` | 32 | client secret 随机字节数 |

---

## 10. 裁决记录（协调者 2026-11-02）

| id | 裁决 | 依据 |
|---|---|---|
| A | 采纳整体设计：OpenTask 独立 `oauth2` 模块，不污染 `/tasks` 契约层 | Orca 集成契约不应被第三方生态绑架 |
| B1 | 两仓都做，先 OpenTask 侧 | 授权服务器是消费方前提 |
| B2 | 跨仓契约文档写两份各归其仓；**本文件为契约权威** | — |
| B3 | 新表挂基线之后的新 revision，不改基线 | ADR D11 |
| C1 | 与 link-check worktree 零交集，无需分工 | 实测 17 个改动文件均在 examples/deploy/notes |
| D1 | OpenTask 侧沿用本 worktree，分支可改名 `WayJ/oauth2-provider` | 原名 `check-oauth2-support` 语义已偏离 |
| E | 采纳 E(a) 且零成本：python-jose 对带 `aud` 的 token 不传 `audience=` 即拒 | 实测 4 情形；既有 auth.py/jwt_utils.py 零改动 |
| F | 采纳 F：新增 `/oauth2/api/{tasks,projects,requirements}` 薄封装既有 service 层 | 不改通用端点 |
| G | 采纳 G1：email 作 username 种子，零 schema 变更 | `user` 表无 email 列；不改核心用户表 |
| — | 不做 PKCE / RFC7591 / introspection | YAGNI |

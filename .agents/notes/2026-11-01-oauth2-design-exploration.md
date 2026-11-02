# OAuth2 对接设计探索笔记（2026-11-01，设计期）
# 实施状态（2026-11-02 收口）：OpenTask 侧已交付（7 commit，568 pytest 绿 / lint 0 error / build 成功 / 迁移往返 / 浏览器证据）；dsh-saas 侧已交付（服务端 + 契约 + 前端 + 16 Java 用例 + 1861 admin 用例绿）。
# 本文件保留设计期核实结论，供后续追溯。

worktree: opentask/tunicate · 分支: WayJ/check-oauth2-support · 终端: term_394e881d-4030-489e-ac5f-b7bcc045b02e

## 场景（用户澄清后的定论）

**不是页面嵌入**，而是 GitHub-in-Orca 式「应用连接 + 代表用户调 API」：

- OpenTask = OAuth2 **Provider**（授权服务器）；dsh-saas = OAuth2 **Client**
- dsh-saas admin 工作台「应用」菜单 → 点「连接 OpenTask」→ 跳转 OpenTask 授权 → 回调建立绑定 → 之后代表该成员读自己的 OpenTask 数据
- 用户原话：「类似于在 orca 中集成了 github 一样，允许绑定关系后，可以调用接口做一些操作」

## 用户已拍板的决策（勿再讨论）

1. OpenTask 扮演 Provider，dsh-saas 扮演 Client
2. 形态 = 应用连接 + 代表用户调 API（非 iframe 嵌入）
3. 接入范围 = **只读**：read:tasks / read:projects / read:requirements（+ profile）
4. OpenTask 侧 client 注册 = **数据库表 + 管理 API**（非配置文件静态注册）
5. OpenTask 侧**需要授权同意页**（非静默授权）
6. 身份对齐 = **email 自动匹配 / 自动建号**
7. 架构 = **方案 A**：OpenTask 新增独立 oauth2 模块，不污染 Orca 契约层 /tasks
8. access token = **复用现有 JWT 机制**（sub/tv + aud=client_id + scp）；refresh token 存哈希

## 两侧现状（核实结论）

### OpenTask（backend/opentask）
- 现有认证：JWT 会话（`jwt_utils.create_access_token` HS256 + `user.token_version`）、`vk_` PAT（`access_tokens` 表，存 SHA-256 哈希）、钉钉免登（`services/user_center/dingtalk/oauth_service.py`）、JNPF 中间件
- 契约层半套 OAuth：`api/tasks/auth.py` 的 `POST /tasks/token` 只做 client_credentials「API Key 换 OAuth2 形状」，无 client 注册、无授权码、无 scope
- `app.py:85` 有 `# self.include_router(oauth_router)` —— **被注释的占位，oauth_router 文件不存在**，Provider 需从零建
- 全局鉴权链：`app.py:80` `common_dependencies = [Depends(authenticate)]` → `auth.py:authenticate` → `get_current_user`（JWT / vk_ 双路）
- `create_access_token(data: dict)` 透传任意 claims → aud/scp/jti 可直接带
- 迁移：**单一 PG 基线** `alembic/versions/2026_10_31_1529-003ccd38d5cd_pg_initial_baseline.py`（ADR D11，覆盖 45 表）→ 新表应**新增 revision**，不改已应用的基线
- 前端登录回跳：路由守卫 `frontend/src/router/guard/route.ts:66` 已支持 `?redirect=` → 同意页未登录可走标准守卫回跳，无需特判
- 通用读端点：任务 = `/api/issues`（`api/issue/router.py`，前缀 `/api/issues`）、`/api/projects`、`/api/requirements`；契约层另有 `/tasks`

### dsh-saas（server/owndsh-modules/owndsh-enterprise）
- 应用目录 `ent_app`：`credential_type` 两型 `STATIC` / `OAUTH_CLIENT_CREDENTIALS`（V159），**库 CHECK 约束钉死**：
  - `ck_ent_app_credential_type`（in 两型）+ `ck_ent_app_oauth_fields`（字段组合）
  - V159 已加 `oauth_token_url` / `oauth_client_id` / client secret 密文三列（ciphertext/nonce/key_version，`SecretPurpose.APP_OAUTH_SECRET`）
- V156 已加 `system_key`（绑定受信目录 `BusinessSystemCatalog`）+ `entry_url`
- `AppRegistryService.requireCredentialType` / `requireOAuthConsistency` 做应用层校验 → 扩第三型需同步改
- 成员级凭据 `ent_member_business_connection`（V142）：每 (tenant, member, system_key) 一条不透明密文，服务 OA-system 的 `/v1/browser-entry` + `submitOperation` 协议（成员手填 token）
- `OAuthTokenSupplier`（`app/application/`）只做 **client_credentials**，注释明说「**授权码流不在本期**」→ 正是本次要补的一格
- `SecretPurpose` 枚举已有 `APP_OAUTH_SECRET` / `MEMBER_BUSINESS_CREDENTIAL`；新成员 OAuth token 存储需**新增用途槽**（防密文跨用途复用）
- 迁移编号：最新 **V163** → 新迁移为 **V164/V165**（不是 V143/V144）
- 契约优先：`contracts/` 是 OpenAPI 3.1 真源（`contracts/paths/*.yaml` 分片 + `contracts/components/`），`generated/` 为派生物**禁手改**，改完跑 `pnpm generate`（`admin/package.json`）；`check:generated` 门禁漂移；新 zod schema 须登记 `plugin/packages/contracts/src/index.ts`
- 门禁：`sh scripts/check-all.sh`

## 设计要点（待协调者最终裁决）

### OpenTask 侧
- 新增 3 表：`oauth_clients` / `oauth_authorization_codes` / `oauth_access_tokens`
- 端点：`/oauth2/authorize`、`/oauth2/token`、`/oauth2/userinfo`、`/oauth2/revoke`、`/oauth2/clients`
- 同意页：`frontend/src/views/oauth2/consent.vue`
- 授权码一次性消费 + 10min TTL；**重放即吊销该用户全部活跃 token**（疑似泄漏）
- access token claims 定稿：`sub`(user.id) + `tv`(token_version) + `aud`(client_id) + `scope`(空格分隔) + `jti` + `exp`
- **`scope` 而非 `scp`**：`scp` 已被 OpenTask 内部受限令牌占用（`auth.py:122` 精确等值判 `scp == "pwd_change"` → 403 请先改初始密码），语义互斥不可混用；OAuth scope 走 RFC 9068 的 `scope` claim
- scope 不足 → 403 `insufficient_scope`；请求 scope ⊄ client 允许集 → `invalid_scope`
- 自动建号：email 无匹配则建号（role=viewer，password_hash=None，复用 `sync_service` 建号风格）—— **身份源在 OpenTask 侧**

### dsh-saas 侧
- `ent_app.credential_type` 扩第三型 `OAUTH_AUTHORIZATION_CODE`（改两条库 CHECK + 应用层校验）
- 新增列 `oauth_authorize_url` / `oauth_userinfo_url` / `redirect_uri`
- 成员绑定：拟新建 `ent_member_oauth_binding`（V165：access/refresh 密文 + expires_at + scopes + external_user_id/email）
- 新增包 `appoauth/`：AppOAuthController / Service / TokenSupplier / Store / IdentityClient
- admin SPA：工作台应用页「连接」按钮 → 调 authorize-url → `window.location.href` 跳转；回调落库

## 不做（YAGNI）
PKCE · RFC 7591 动态注册 · RFC 7662 introspection 端点 · OAuth token 黑名单

## 待协调者裁决（2026-11-01 发出的消息）
- `msg_fdd6a36cc06e` — 4 项：A 设计认可 / B 范围与文档落点 / C 与 link-check 重叠 / D 分支提交策略
- `msg_e46e093b026b` — 3 处事实修正 + 新增 E(scope 强制方式) / F(只读面落点) + 成员绑定表权衡
- `msg_038b6aa2b45d` — AGENTS.md 改动系用户明确指示的澄清

## 关键未决问题（自记，防遗忘）

**E. scope 强制方式** —— ✅ **已由库行为免费解决，实测确认**（backend `uv run`，python-jose **3.5.0**）：
- token 带 `aud` + 解码**不传** `audience=` → `JWTError: Invalid audience` → `jwt_utils.verify_token` 捕获后转 **401 Invalid token**
- 既有全局鉴权链（`app.py:80` → `authenticate` → `get_current_user`）与契约层 `resolve_contract_token` 均走 `verify_token` → **OAuth token（带 aud=client_id）天然进不了 `/api/*` 与 `/tasks`**，只读 scope 形同虚设的风险为零
- **既有 `auth.py` / `jwt_utils.py` 零改动**
- OAuth 侧独立校验两条均实测可用（篡改签名均被拒）：
  - S1 `jwt.decode(tok, KEY, algorithms=[ALG], options={'verify_aud': False})` + 显式比对 aud 是否已注册 client_id
  - S2 `jwt.get_unverified_claims(tok)['aud']` → `jwt.decode(..., audience=该aud)`
  - 两者等价（签名验证通过即 aud 被认证）；S1 更直白

**F. 只读面落点** —— 倾向新开 `/oauth2/api/{tasks,projects,requirements}` 薄封装既有 service 层，不改通用端点

**G. 身份对齐落到哪个字段** —— ⚠️ **OpenTask 全库无 email 字段**。`user` 表列：name / username(unique, lower 归一, 长 50) / password_hash / role / status / token_version / must_change_password / failed_attempts / locked_until / last_login_time / sync_time / jnpf_* / organize_* / position_* / dingtalk_user_id / jwt_expires_at / openai_* / langsmith_* / sentry_*。JNPF 集成侧亦无 email（`JnpfUserInfo` 只有 userId/userAccount/userName/headIcon/organize*/position*）。→ 用户拍板的「email 自动匹配/建号」必须在 username 上落地：
- **G1（倾向）**：email 作 username 种子，`unique_username(existing, email)`（`services/user_center/utils.py`，冲突自动 _2/_3）+ name=display name + role=viewer + password_hash=None（沿钉钉 `_create_user` 风格）；匹配=username 精确查（lower 归一）→ 命中复用，未命中建号；零 schema 变更。副作用：若该用户已有 JNPF/钉钉同步账号且 username≠email，会另建新号
- G2：给 `user` 加 `email` 列（迁移 + `unique (lower(email)) where email is not null` + 存量回填 null），改核心用户表需回归
- G3：G1 最小形态，userinfo 仍返回 email 供展示

## 附：dsh-saas 部署侧
业务系统目录由 `enterprise.business-connections.catalog` 属性指向 JSON 文件（`BusinessConnectionConfiguration`），`BusinessSystemCatalog.load` 解析；OpenTask 以 `key=opentask` 登记（origin + workspaces）。

## 附带改动（未提交）
`AGENTS.md`：移除 MANDATORY workflow-guide 段（用户明确指示删除「先读 Workflow Guide 和检查 Constitution」的要求）。删除范围限于该段与 Legacy 段的 "The OpenTask Workflow Guide takes precedence." 一句；其余各节保留。

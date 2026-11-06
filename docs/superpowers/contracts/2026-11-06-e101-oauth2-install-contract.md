# 契约：OpenTask ↔ 小蓝 CoWork OAuth 自动接入（Install Flow）**v2**

- 版本：**v2**（2026-11-06）— 取代 v1（v1 引入的长期 `installer_token` 前置**已废弃**）
- 状态：**拟议待联调**（OpenTask 侧实现同步进行；小蓝侧由同一对话开发）
- 参照流程：GitHub App **manifest registration**（管理员确认页 + 一次性 code + 服务端兑换）+ OAuth **PKCE（S256）**
- 关联：`docs/superpowers/specs/2026-11-06-e101-oauth2-install-flow-design.md`、
  `docs/superpowers/plans/2026-11-06-e101-oauth2-install-flow.md`

## 变更记录（v1 → v2）

| v1 | v2 | 原因 |
|---|---|---|
| 接入方长期 `installer_token`（线下交付）作为**必需前置** | **删除**；改为小蓝发起时生成**一次性高熵 verifier**，OpenTask 只绑定 `challenge` | 违反「两系统之间免复制长期凭据」的要求 |
| 兑换靠 `installer_token` 鉴权 | 兑换靠 **verifier**（PKCE S256 绑定）+ 一次性 code | 同上 |
| `exchange` 返回 `already_consumed` 时语义含糊 | **明确：`consumed` ≠ 成功**；给出**恢复窗口**（verifier 重试 → 返回新密钥）与窗口外的**强制重装**路径 | 响应丢失时小蓝拿不到密钥，不能假报成功 |
| 未提及开放重定向 | 单列 §6 评估 + 硬缓解 | `callback_url` 由来方提供 → 回跳即开放重定向面 |
| 未定义未认证发起的滥用上限 | §5 单列限流/去重/存活期 | 发起方不再有身份，必须有资源与诱导面约束 |

---

## 0. 一句话协议

> 小蓝生成**一次性 verifier**（只留自己手里）→ 把 `challenge = BASE64URL(SHA256(verifier))` 连同应用清单
> 推给 OpenTask → 管理员登录 OpenTask **确认安装** → OpenTask 生成**短期一次性 code** 并把管理员浏览器
> 回跳到小蓝 → 小蓝**服务端**用 `verifier` 兑换，得到 `client_id` + `client_secret` → 之后小蓝按标准 OAuth
> 授权码流程访问用户数据（**成员单独授权**）。

**核心不变量**

1. `client_secret` **只在小蓝后端的兑换响应体里出现一次**；不进 URL、不进日志、不进浏览器、不落库明文。
2. OpenTask **只存 challenge**（`S256(verifier)`），从不接触 verifier。
3. **任何 2xx 响应体必含 `client_secret`**；不含 `client_secret` 的响应**一律不得**被小蓝视为成功。
4. 成员授权与安装流**完全独立**：安装不签发任何 token，不代成员授权。

---

## 1. 角色与信任边界

| 角色 | 是什么 | 持有什么 | 信任边界 |
|---|---|---|---|
| **小蓝后端** | 发起安装 + 兑换密钥的服务端 | `verifier`（高熵、一次性）、兑换后拿到 `client_secret` | **verifier 即能力凭证**：无它则 code 换不出密钥 |
| **管理员** | OpenTask `role == "admin"` | 登录会话 | **唯一能把申请变成 client 的角色**；批准即授权该应用被请求这些 scope |
| **成员** | OpenTask 普通用户 | — | 仍在同意页 `/oauth2/authorize` **单独**同意 |
| **任意第三方** | 任何人 | — | **无法认证发起**（§5 有上限），无法兑换（无 verifier），无法批准（无 admin） |

> **与 v1 的关键差别**：发起方**没有身份**。因此本协议的安全由三层构成：
> ① **资源与诱导面上限**（§5）② **管理员确认门**（人工闸门）③ **verifier 绑定**（兑换环节）。

---

## 2. 端点总览

| # | 方法 | 路径 | 调用方 | 鉴权 | 用途 |
|---|---|---|---|---|---|
| A | POST | `/api/oauth2/install/requests` | 小蓝后端 | **无**（未认证发起，§5 限流） | 发起安装申请 |
| B | POST | `/api/oauth2/install/status` | 小蓝后端 | **verifier**（body） | 查询申请状态（**不含任何密钥**） |
| C | GET | `/oauth2/install/{install_id}` | 管理员浏览器 | 登录会话 | 安装确认页（SPA） |
| D | POST | `/api/oauth2/install/requests/{install_id}/approve` | 管理员浏览器 | 登录 + `role == admin` | 批准 → 生成一次性 code |
| E | POST | `/api/oauth2/install/requests/{install_id}/reject` | 管理员浏览器 | 同上 | 拒绝 |
| F | POST | `/api/oauth2/install/exchange` | 小蓝后端 | **verifier**（body） | 兑换 `client_id` + `client_secret` |
| G | GET | `/api/oauth2/install/requests` | 管理员浏览器 | 登录 + admin | 审计列表（最近 N 条） |

> A/B/F 必须是**服务端到服务端**调用；B/F 的 `verifier` 走 **request body**，**不得**放 query string（防落日志/Referer）。

---

## 3. 端点详解

### A. 发起安装申请（未认证）

```http
POST {opentask_origin}/api/oauth2/install/requests
Content-Type: application/json
```

```jsonc
{
  "client_id": "xl-cowork-prod",          // ≤64，[A-Za-z0-9._-]
  "name": "小蓝 CoWork",                   // ≤255，同意页/确认页展示
  "description": "小蓝 CoWork 管理后台",   // 可选，≤1000
  "redirect_uris": [                      // 1–20 条，绝对 http(s)，去重
    "https://xiaolan.example.com/enterprise/api/v1/app-oauth/opentask/callback"
  ],
  "scopes": ["read:tasks", "read:projects", "read:requirements", "profile"], // ≤32
  "grant_types": ["authorization_code", "refresh_token"],  // 可选，默认这两项
  "callback_url": "https://xiaolan.example.com/enterprise/install/done", // 安装完成回跳
  "state": "b7f1c2d9e4a6",                // 小蓝的 CSRF 随机串，原样回传
  "code_challenge": "6VUZHh8vJ0nU5x1r2sT3kQ9pL4mN7oW8cX1yZ0aB2c", // BASE64URL(SHA256(verifier))
  "code_challenge_method": "S256"         // **只接受 S256**，拒绝 plain
}
```

**响应 `201`（新建）/ `200`（幂等复用）**

```jsonc
{
  "code": 200,
  "message": "ok",
  "data": {
    "install_id": "9f3c1d2e-4b5a-6c7d-8e9f-0a1b2c3d4e5f",
    "status": "pending",                  // pending | approved | rejected | expired | consumed
    "approval_url": "https://opentask.example.com/oauth2/install/9f3c1d2e-...",
    "expires_at": "2026-11-06T12:15:00",
    "reused": false                       // true = 命中同 (client_id, code_challenge) 的既有 pending 申请
  }
}
```

**校验规则**

| 字段 | 规则 |
|---|---|
| `code_challenge_method` | 必须 `"S256"`；**拒绝 `plain`**（防止降级为明文比对） |
| `code_challenge` | 必须 43 字符 BASE64URL（`[A-Za-z0-9_-]`），即 `BASE64URL(SHA256(verifier))` 的标准长度 |
| `client_id` | 1–64，`[A-Za-z0-9._-]`；**不得**与既有正式 client 冲突（→ 409 `client_id_conflict`） |
| `name` | 1–255 |
| `redirect_uris` | 1–20 条；每条 ≤2048 字符；**绝对** `http(s)` URL；去重；不接受通配/路径参数 |
| `scopes` | ≤32；每条匹配 `[a-zA-Z0-9:._-]{1,64}` |
| `callback_url` | **绝对** URL；scheme `https`（loopback 主机例外允许 `http`）；禁 userinfo / fragment / 控制字符；主机必须是某个 `redirect_uris` 主机**或其子域**（见 §6.2） |
| `state` | 可选，≤256 |

**错误**

| HTTP | 业务码 | 含义 |
|---|---|---|
| 409 | `client_id_conflict` | `client_id` 已是既有正式 client |
| 422 | `invalid_request` | 字段校验失败（`detail` 给出原因） |
| 429 | `too_many_pending_requests` / `rate_limited` | 触发 §5 上限 |

---

### B. 查询状态（verifier 鉴权）

```http
POST {opentask_origin}/api/oauth2/install/status
Content-Type: application/json

{ "install_id": "9f3c1d2e-...", "verifier": "<小蓝持有的 verifier 明文>" }
```

**响应 `200`**

```jsonc
{
  "code": 200, "message": "ok",
  "data": {
    "install_id": "9f3c1d2e-...",
    "status": "approved",       // pending | approved | rejected | expired | consumed
    "client_id": "xl-cowork-prod",
    "created_at": "2026-11-06T12:00:00",
    "expires_at": "2026-11-06T12:15:00",
    "approved_at": "2026-11-06T12:03:00",
    "consumed_at": null,
    "recoverable": false        // consumed 且仍在恢复窗口内 → true（可重试兑换拿密钥）
  }
}
```

- **不含** `client_secret`、code、verifier；
- verifier 不匹配 → `404 install_request_not_found`（不泄露申请是否存在）；
- **`status == "consumed"` 不等于小蓝成功**：它只说明"发生过一次兑换"。小蓝仍需拿到含 `client_secret` 的 2xx 响应。

---

### C. 安装确认页（管理员）

`GET {opentask_origin}/oauth2/install/{install_id}` —— SPA 路由；未登录走既有 `?redirect=` 回跳。

页面**必须**展示（且**不可编辑**，要改只能驳回后重新申请）：

| 展示项 | 说明 |
|---|---|
| 应用名 / 描述 / `client_id` | 与申请一致 |
| **回调地址白名单** | 逐条列出 + "精确匹配"提示 |
| **请求的 scopes** | 中文说明 + 对应只读数据面端点（附录 §7.1） |
| **安装回跳地址（callback_url）** | 主机名高亮 |
| **请求来源** | 源 IP + User-Agent |
| **风险提示** | 「本接入方**未提供长期凭据**，OpenTask 无法验证其身份；请核对回调域名是否为可信方」 |
| **成员授权独立提示** | 「安装仅登记应用；成员仍需在授权同意页单独同意，OpenTask 不会代成员授予数据权限」 |

---

### D. 批准安装

```http
POST {opentask_origin}/api/oauth2/install/requests/{install_id}/approve
Authorization: Bearer {admin_session_token}
Content-Type: application/json

{ "approved": true }
```

**响应 `200`**

```jsonc
{
  "code": 200, "message": "ok",
  "data": {
    "install_id": "9f3c1d2e-...",
    "status": "approved",
    "redirect_to": "https://xiaolan.example.com/enterprise/install/done?code=ins_9a8b7c...&state=b7f1c2d9e4a6"
  }
}
```

- `code` 是**安装码**：不透明、**10 分钟**有效、**单次**消费、库内只存 SHA-256 哈希；
- `redirect_to` = `callback_url` + `code` + `state`（**原样**回传）；
- 响应头必须带：`Referrer-Policy: no-referrer`、`Cache-Control: no-store`、`X-Content-Type-Options: nosniff`；
- **安装码明文只在此响应里出现一次**；**不进日志**。

**错误**

| HTTP | 业务码 | 含义 |
|---|---|---|
| 403 | `admin_required` | 非管理员 |
| 404 | `install_request_not_found` | 申请不存在 |
| 409 | `install_request_not_pending` | 已批准 / 已拒绝 / 已过期（**幂等保护**：不重复签发安装码） |

---

### E. 拒绝安装

`POST /api/oauth2/install/requests/{install_id}/reject` → `{ "install_id": "...", "status": "rejected" }`。错误口径同 D。

---

### F. 兑换密钥（服务端到服务端）

```http
POST {opentask_origin}/api/oauth2/install/exchange
Content-Type: application/json

{ "install_id": "9f3c1d2e-...", "code": "ins_9a8b7c...", "verifier": "<verifier 明文>" }
```

**响应 `200`（首次兑换）**

```jsonc
{
  "code": 200, "message": "ok",
  "data": {
    "client_id": "xl-cowork-prod",
    "client_secret": "ocs_5f2a...",     // 明文仅此一次；库内只存哈希
    "name": "小蓝 CoWork",
    "description": "小蓝 CoWork 管理后台",
    "redirect_uris": ["https://xiaolan.example.com/enterprise/api/v1/app-oauth/opentask/callback"],
    "scopes": ["read:tasks", "read:projects", "read:requirements", "profile"],
    "grant_types": ["authorization_code", "refresh_token"],
    "recovered": false                    // true = 走的是恢复路径（见 §4）
  }
}
```

**响应 `200`（恢复路径）**：形状完全相同，`client_secret` 是**新密钥**（旧密钥立即失效），`recovered: true`。

**错误（全部是失败）**

| HTTP | 业务码 | 含义 | 小蓝应做什么 |
|---|---|---|---|
| 400 | `invalid_verifier` | verifier 与 challenge 不匹配 | 停止；查是否拿错 verifier |
| 400 | `invalid_install_code` | 安装码不存在/不匹配 | 停止；重新发起安装 |
| 400 | `install_code_expired` | 安装码超 10 分钟 | 重新发起安装 |
| 409 | `install_not_approved` | 申请尚未批准 / 已拒绝 / 已过期 | 等批准或重新发起 |
| 409 | `install_already_consumed` | 已兑换过且**恢复窗口已过** | **重新发起安装**（新 verifier + 管理员再次确认） |
| 404 | `install_request_not_found` | 申请不存在或 verifier 不匹配 | 停止 |

> ⚠️ **「已消费」不是成功**：只有 **2xx 且响应体含 `client_secret`** 才算接入成功。
> `409 install_already_consumed` / `400 invalid_install_code` 等**一律是失败**，小蓝不得记为成功。

---

## 4. 失败恢复语义（重点）

### 4.1 状态机

```
PENDING ──approve──▶ APPROVED ──exchange(首次)──▶ CONSUMED
   │                     │                            │
   │                     │                            └── exchange(verifier 重试, 窗口内) ──▶ CONSUMED(密钥已轮换)
   ├──reject──▶ REJECTED │                            └── 窗口过后再试 ──▶ 409 install_already_consumed
   └──超时───▶ EXPIRED
```

### 4.2 恢复窗口

- 定义：自**首次成功兑换**起 `oauth_install_recovery_window_seconds`（默认 **600 秒 = 10 分钟**）；
- 窗口内，小蓝用**同一 verifier** 重试兑换（code 可仍用原值，也可省略）→ OpenTask **轮换出新密钥**并返回 200；
- 窗口外 → `409 install_already_consumed` → **必须重新走安装**（新 verifier + 管理员再次确认）；
- 每次恢复兑换都记 `recovery_count` / `recovery_used_at`（审计）。

### 4.3 为什么恢复路径是「轮换」而不是「取回同一把」

- 库内**从不存密钥明文/可逆密文**（批准时创建的是**占位密钥**，明文立即丢弃；兑换时才轮换出真密钥）。
- 「取回同一把」要求服务端保存密钥的**可逆副本**（需引入主密钥 + 轮换/备份运维面），代价高于收益；
- 轮换的副作用（旧密钥立即失效）由 §4.4 的实现约束兜住。

### 4.4 小蓝侧实现约束（契约强制）

1. 兑换请求**串行化**：同一 `install_id` 同时只允许一个在途兑换请求；收到 2xx 立即停止重试；
2. 收到 2xx 后**先持久化 `client_secret` 再做别的事**；持久化失败 → 走恢复路径重试（会拿到新密钥）；
3. **不得**把"拿到 2xx"与"拿到 `client_secret`"分开判断——本契约中二者同时发生（§0 不变量 3）；
4. 任何 4xx/5xx → 记失败，按错误表处置；**不得**记为成功。

---

## 5. 未认证发起的滥用上限

发起方无身份（§1），故必须有资源与诱导面约束：

| 滥用场景 | 上限（配置项） | 超限响应 |
|---|---|---|
| pending 申请**总数**堆积（DB 膨胀） | `oauth_install_max_pending_global` = **100** | `429 too_many_pending_requests` |
| 单源 IP 的 pending 申请数（诱导刷屏） | `oauth_install_max_pending_per_ip` = **5** | `429 too_many_pending_requests` |
| 单源 IP 的**创建速率** | `oauth_install_rate_limit_per_minute` = **10** | `429 rate_limited` |
| 重复发起（同 `client_id` + 同 `code_challenge`） | 复用同一 `install_id` | `200` + `reused: true`（不新建） |
| 请求体规模 | ≤ 16KB（ASGI 层）；`redirect_uris` ≤20 条/≤2048 字符；`scopes` ≤32 | `422 invalid_request` |
| 申请存活期 | `oauth_install_request_ttl_seconds` = **900**（15 分钟） | 过期 → `EXPIRED`，自动释放配额 |

**配套**

- **无"批准队列"洪水**：批准只能通过**直达链接**（`install_id` 为 UUID4，不可枚举）打开；管理员若不点，垃圾申请不会打扰任何人；
- 审计列表（端点 G）**只展示最近 50 条**，且**不含** `code` / `challenge` / `state`；
- **批准前内容复核**（§6.3）由管理员完成，这是唯一的质量闸门。

---

## 6. 安全约束

### 6.1 密钥 / 凭据

| 约束 | 落地 |
|---|---|
| `client_secret` 永不进浏览器 | 只在 F 的服务端响应体出现一次；不进 URL、不进日志、不进前端存储 |
| OpenTask 从不接触 verifier | 只存 `challenge = S256(verifier)`；校验时 `compare_digest` 恒定时间比较 |
| 安装码可进 URL | 但**不透明、10 分钟、单次**，且**必须配 verifier** 才能兑换 → 单独泄漏 code 无用 |
| 库内无密钥明文 | 占位密钥 + 兑换时轮换（§4.3）；`client_secret` / `code` 只存哈希 + 展示前缀 |
| 日志脱敏 | 新端点**不打印** `code` / `verifier` / `challenge` / `client_secret` / `state`；错误响应不回显 |

### 6.2 开放重定向评估与缓解（`callback_url` 由来方提供）

**风险**：D 的 `redirect_to` 是 302 到**来方提供**的 `callback_url` → ①可借 OpenTask 域做钓鱼跳转；②`code`/`state` 泄漏给该地址。

**缓解（全部必须落地）**

| # | 缓解 | 说明 |
|---|---|---|
| M1 | **严格 URL 校验**（入参时 + **回跳前再校验一次**） | 绝对 URL；scheme ∈ {`https`}（loopback 主机例外允许 `http`）；禁 userinfo / fragment / 控制字符 / 空白；禁 IP 字面量（loopback 除外）；禁 `javascript:` / `data:` |
| M2 | **主机绑定**：`callback_url` 主机 ∈ {某条 `redirect_uris` 的主机} ∪ {其子域} | 攻击者只能把 code 送回自己本来就有权的域；也防止"申请用小蓝域名、回跳指向攻击者域名"的分裂 |
| M3 | **回跳响应头** | `Referrer-Policy: no-referrer`、`Cache-Control: no-store`、`X-Content-Type-Options: nosniff` |
| M4 | **code 非秘密** | 单次 + 10 分钟 + 需 verifier 配对 → 泄漏 code 换不出密钥 |
| M5 | **`state` 由小蓝生成并校验** | 契约强制项（§8.3） |
| M6 | 确认页显式展示 **callback 主机** 与"接入方未验证身份"风险提示 | 管理员在批准前能肉眼核对 |

**残余风险（明确接受）**：管理员浏览器可能被重定向到**申请方自选域名**（外观仍是 OpenTask 的安装页 → 有钓鱼观感）。
缓解其危害的是 M4（code 无用）+ M6（人工核对域名）+ 无长期凭据（换不到密钥也拿不到数据，因为成员授权独立）。
**不引入**白名单配置（YAGNI）；若未来出现多接入方场景，再加"管理员维护的可信回调主机列表"。

**SSRF**：本协议 OpenTask **不对来方提供的任何 URL 发起服务端请求**（安装申请是 push，不是 pull），故**无 SSRF 面**。
> GitHub 采用 pull 模式（GitHub 抓 `manifest_url`）因而必须做 7 条加固（仅 https、域名白名单、解析后禁私网/回环、禁跟随重定向、DNS 固定、超时/体积上限、字段逐条校验）。
> **在那些落地前，禁止新增任何"按来方 URL 抓取"的入口。**

### 6.3 绑定与批准内容校验

| 约束 | 落地 |
|---|---|
| 精确绑定 | 兑换返回的 `redirect_uris` / `scopes` / `grant_types` / `client_id` **从 DB 读**（批准时写入的值），**不接受请求体改写** |
| 按原样批准 | 确认页只读展示；管理员不能当场改 scopes/回调 → 要改只能驳回后重新申请 |
| 批准时复核 | 批准动作**再次**校验 `redirect_uris`（绝对 http(s)、去重、≤20）与 scopes 形态（防存储期篡改） |
| scope 上界 | client 的 scopes 是**上界**；小蓝请求超出即 `invalid_scope`（既有实现，不隐式收敛） |
| 最小权限 | 确认页对每个 scope 标注"读取你的…"中文说明，便于管理员判断 |

### 6.4 CSRF / 重放 / 过期

| 威胁 | 防护 |
|---|---|
| CSRF（管理员侧） | OpenTask 管理 API 用 `Authorization: Bearer`（非 Cookie 自动附带）→ 跨站页面无法代发；确认页走既有登录守卫 |
| CSRF（小蓝侧回跳） | 回跳必须带 `state`；**小蓝必须校验 `state` 与发起时一致**（§8.3 强制项） |
| 重放（安装码） | 单次消费（条件更新 `WHERE consumed_at IS NULL`）；重复兑换 → 走恢复路径或 409 |
| 重放（成员授权码） | 沿用既有实现：授权码一次性，重放即吊销该用户全部 OAuth token |
| 过期 | 申请 15 分钟 / 安装码 10 分钟 / 恢复窗口 10 分钟 |
| 回跳泄漏 | M3 响应头 |

### 6.5 权限确认

| 面 | 要求 |
|---|---|
| 安装批准 | 仅 `role == "admin"`；确认页显式列出回调白名单与 scopes；按原样批准 |
| 成员授权 | **独立流程**：成员在 `/oauth2/authorize` 同意页单独同意；未同意则小蓝拿不到任何用户数据 |
| 安装不签发 token | 安装流只创建 client 与安装码，不签发 access/refresh token |

---

## 7. 附录

### 7.1 provider 支持的 scope（真源：`backend/opentask/api/oauth2/read_api.py`）

| scope | 含义 | 只读数据面端点 |
|---|---|---|
| `read:tasks` | 读取任务列表与详情 | `GET /oauth2/api/tasks` |
| `read:projects` | 读取项目列表与详情 | `GET /oauth2/api/projects` |
| `read:requirements` | 读取需求列表与详情 | `GET /oauth2/api/requirements` |
| `profile` | 读取基本资料（用户名、姓名） | `GET /oauth2/api/me`、`GET /oauth2/userinfo` |

### 7.2 既有协议端点（安装完成后小蓝使用，**本次不改**）

| 用途 | 端点 |
|---|---|
| 授权入口（浏览器跳转） | `{frontend_origin}/oauth2/authorize?client_id=…&redirect_uri=…&response_type=code&scope=…&state=…` |
| 换取令牌 | `POST {backend_origin}/oauth2/token`（`grant_type=authorization_code` / `refresh_token`） |
| 用户信息 | `GET {backend_origin}/oauth2/userinfo` |
| 吊销令牌 | `POST {backend_origin}/oauth2/revoke` |

### 7.3 小蓝侧实现清单（契约强制项）

1. `verifier` 用 `secrets.token_urlsafe(32)`（≥256 位熵）生成，**只存在小蓝后端**；
2. `code_challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()`；
3. `state` ≥16 字节随机，**保存**并在回跳时**校验**（不一致即丢弃）；
4. `verifier` **不得**进 URL / 日志 / 前端代码包；
5. 兑换请求**只发服务端**，**串行化**，收到 2xx 立即停止重试；
6. `client_secret` 落小蓝侧密钥管理，**不得**进浏览器可读存储；
7. 兑换失败**不重放**旧 code：先查状态（B）；`consumed` 且 `recoverable=false` → **重新发起安装**；
8. 发起授权时 `redirect_uri` **逐字符**使用 OpenTask 下发的白名单值（精确匹配，不做尾斜杠/大小写归一）；
9. `scope` 请求值必须是下发集合的**子集**；
10. `callback_url` 主机必须与 `redirect_uris` 主机相同或是其子域（否则 OpenTask 拒绝创建申请）。

### 7.4 参考实现（Python，小蓝侧可直接取用）

```python
import base64
import hashlib
import secrets
import httpx

OPENTASK = "https://opentask.example.com"
REDIRECT_URI = "https://xiaolan.example.com/enterprise/api/v1/app-oauth/opentask/callback"
CALLBACK_URL = "https://xiaolan.example.com/enterprise/install/done"

def _s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

def start_install() -> tuple[str, str, str]:
    """返回 (approval_url, install_id, verifier)——verifier 必须持久化到服务端密钥管理"""
    verifier = secrets.token_urlsafe(32)          # 一次性高熵
    state = secrets.token_urlsafe(16)
    save_state(state)                               # 回跳时校验
    save_verifier_pending(verifier)                 # 兑换时取用（按 install_id 索引）
    r = httpx.post(
        f"{OPENTASK}/api/oauth2/install/requests",
        json={
            "client_id": "xl-cowork-prod",
            "name": "小蓝 CoWork",
            "description": "小蓝 CoWork 管理后台",
            "redirect_uris": [REDIRECT_URI],
            "scopes": ["read:tasks", "read:projects", "read:requirements", "profile"],
            "callback_url": CALLBACK_URL,
            "state": state,
            "code_challenge": _s256(verifier),
            "code_challenge_method": "S256",
        },
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()["data"]
    return data["approval_url"], data["install_id"], verifier

def exchange(install_id: str, code: str, verifier: str) -> dict:
    """服务端兑换；返回体含 client_secret —— 缺失即视为失败"""
    r = httpx.post(
        f"{OPENTASK}/api/oauth2/install/exchange",
        json={"install_id": install_id, "code": code, "verifier": verifier},
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"兑换失败: {r.status_code} {r.text}")   # 不得当成功
    data = r.json()["data"]
    if not data.get("client_secret"):
        raise RuntimeError("兑换响应缺少 client_secret，视为失败")
    return data                                     # 立即持久化 client_secret
```

---

## 8. 端到端时序

```
小蓝后端                        OpenTask API                  管理员浏览器                 OpenTask DB
    │                               │                             │                          │
    │─A POST /install/requests ─────▶│  (challenge=S256(verifier))│                          │
    │   {client_id,name,redirects,   │── 写 PENDING 申请 ───────────────────────────────▶│
    │    scopes,callback_url,state,  │                             │                          │
    │    code_challenge}             │                             │                          │
    │◀─ 201 {install_id, approval_url}                             │                          │
    │                               │                             │                          │
    │── 把 approval_url 给管理员（跳转/二维码）────────────────────▶│                          │
    │                               │◀── C GET /oauth2/install/{id}（未登录→登录）───│         │
    │                               │── 渲染确认页（名称/回调白名单/scopes/来源IP）──▶│         │
    │                               │◀── D POST /approve (admin) ────────────────────│         │
    │                               │── 建 client(占位密钥) + 生成 code(哈希落库) ─▶│         │
    │                               │   302 → callback_url?code=…&state=…  (no-referrer)          │
    │◀── 小蓝 callback 收到 code ────│                             │                          │
    │                               │                             │                          │
    │─F POST /install/exchange ─────▶│  校验 verifier↔challenge、code、有效期         │
    │   {install_id, code, verifier} │── 原子消费 code + 轮换密钥 ──────────────────▶│
    │◀─ 200 {client_id, client_secret, scopes…} ───│               │                          │
    │   (若响应丢失：同 verifier 重试 → 200 新密钥；窗口外 → 409 必须重装)             │
    │                               │                             │                          │
    │  之后：成员在小蓝侧点「连接 OpenTask」→ 浏览器跳 {frontend}/oauth2/authorize?…
    │        → 成员在同意页单独同意 → 小蓝后端 POST /oauth2/token 换 token
```

---

## 9. v1 → v2 迁移提示（若已有 v1 实现）

- 删除 `installer_token` 相关端点与字段（`/api/oauth2/installers` 整组取消）；
- 安装申请增加 `code_challenge` / `code_challenge_method`（**必填**）；
- 兑换改为 `{install_id, code, verifier}`，并新增**恢复路径**语义；
- 新增端点 B（status）与 G（审计列表）；
- 新增 §5 限流与 §6.2 回跳校验（M1/M2）。

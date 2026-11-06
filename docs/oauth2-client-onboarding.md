# OAuth 客户端接入指南（管理员 / 接入方）

面向两方：**OpenTask 管理员**（在后台登记与确认应用）与**接入方**（如小蓝 CoWork，按本文档协议调用 OpenTask）。

> 协议契约（权威，含完整错误码与安全约束）：
> `docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md`

---

## 0. 一分钟概览

| 想做的事 | 走哪条路 |
|---|---|
| 接入方能自助发起、管理员点一次「确认安装」 | **方式一：自动接入**（推荐，无需复制长期凭据） |
| 管理员直接手工建 client，把密钥交给接入方 | **方式二：手工登记** |
| 让某个成员授权 OpenTask 数据给应用 | 成员在 `/oauth2/authorize` 同意页**单独同意**（与上面两条都独立） |

OpenTask 侧管理入口：**系统管理 → OAuth 客户端**（`/manage/oauth2`）。

---

## 1. 方式一：自动接入（小蓝发起，推荐）

### 1.1 时序

```
小蓝后端                        OpenTask API                    管理员浏览器
  │ ①生成 verifier（高熵随机，只留小蓝侧）                            │
  │ ②POST /api/oauth2/install/requests（带 challenge）────────────────▶│
  │ ③◀── install_id + approval_url ──────────────────────────────────┤
  │ ④把 approval_url 给管理员 ──────────────────────────────────────▶│
  │ ⑤                                    管理员登录 → 核对 → 确认安装 │
  │ ⑥◀── 302 到小蓝回调地址：?code=<一次性安装码>&state=<原样回传> ────┤
  │ ⑦POST /api/oauth2/install/exchange（code + verifier）────────────▶│
  │ ⑧◀── client_id + client_secret（明文仅此一次）─────────────────────┤
```

### 1.2 小蓝侧要做的四件事

1. **生成 verifier**：`secrets.token_urlsafe(32)`（≥256 位熵），**只存小蓝后端**；
   `challenge = base64url(sha256(verifier))`（PKCE S256，不带 `=` 补位）。
2. **发起安装申请**（服务端到服务端）：

   ```http
   POST {opentask}/api/oauth2/install/requests
   Content-Type: application/json

   {
     "client_id": "xl-cowork-prod",
     "name": "小蓝 CoWork",
     "description": "小蓝 CoWork 管理后台",
     "redirect_uris": ["https://xiaolan.example.com/enterprise/api/v1/app-oauth/opentask/callback"],
     "scopes": ["read:tasks", "read:projects", "read:requirements", "profile"],
     "callback_url": "https://xiaolan.example.com/enterprise/install/done",
     "state": "<小蓝生成的 CSRF 随机串>",
     "code_challenge": "<BASE64URL(SHA256(verifier))>",
     "code_challenge_method": "S256"
   }
   ```

   响应：`{install_id, status:"pending", approval_url, approval_path, expires_at, reused}`。
   `approval_url` 交给管理员（跳转或二维码均可）；`approval_path` 是相对路径，
   若贵方已知 OpenTask 前端域名，可自行拼接。

3. **接住回调**：管理员批准后浏览器跳到 `callback_url?code=ins_…&state=…`。
   **必须校验 `state`** 与发起时一致（不一致即丢弃）——这是小蓝侧的 CSRF 防线。
4. **服务端兑换密钥**：

   ```http
   POST {opentask}/api/oauth2/install/exchange
   Content-Type: application/json

   { "install_id": "...", "code": "ins_...", "verifier": "<verifier 明文>" }
   ```

   成功（HTTP 200，**响应体必须含 `client_secret`**）：

   ```json
   { "client_id": "xl-cowork-prod", "client_secret": "ocs_…",
     "redirect_uris": [...], "scopes": [...], "grant_types": [...], "recovered": false }
   ```

   **立即持久化 `client_secret`**（明文只出现这一次，服务端只存哈希）。

### 1.3 失败恢复（务必按此实现）

| 情况 | 服务端行为 | 小蓝侧正确做法 |
|---|---|---|
| 兑换响应**丢失**（网络中断/超时） | 状态变为 `CONSUMED` | **用同一 verifier 在恢复窗口（10 分钟）内重试** → 返回**新密钥**（`recovered: true`），旧密钥失效 |
| 恢复窗口已过 | `409 install_already_consumed` | **重新发起安装**（新 verifier + 管理员再次确认）。**不得**把该响应当成功 |
| code 过期（>10 分钟） | `400 install_code_expired` | 重新发起安装 |
| 申请未批准 | `409 install_not_approved` | 等管理员批准，或重新发起 |
| verifier 不匹配 | `400 invalid_verifier` | 停止，检查是否拿错 verifier |

**铁律**：只有 **HTTP 2xx 且响应体含 `client_secret`** 才算接入成功；
「状态是 consumed」**不等于**成功。小蓝侧兑换请求要**串行化**，收到 2xx 立即停止重试。

### 1.4 未认证发起的上限（管理员视角）

安装申请无需凭据即可发起（信任锚是 verifier + 管理员确认），因此服务端设了上限：

| 上限 | 默认 | 超限 |
|---|---|---|
| 全局 pending 申请数 | 100 | `429 too_many_pending_requests` |
| 单来源 IP 的 pending 申请数 | 5 | `429 too_many_pending_requests` |
| 单来源 IP 每分钟创建次数 | 10 | `429 rate_limited` |
| 申请有效期 | 15 分钟 | 过期自动作废 |

同 `(client_id, code_challenge)` 重复发起会**复用**同一申请（幂等，`reused: true`）。

---

## 2. 方式二：手工登记

1. 管理端「系统管理 → OAuth 客户端 → 新建客户端」；
2. 填 `client_id`（唯一，创建后不可改）、应用名称、**回调地址白名单**、勾选 scopes；
3. 创建成功后**立即复制 client_secret**（**仅显示一次**，服务端只存哈希）；
4. 把 `client_id` / `client_secret` 交给小蓝侧（走贵方既有的密钥分发渠道）。

**回调地址依赖小蓝 appKey 的情形**（appKey 在小蓝侧创建后才确定）：
先建 client 用**占位地址**，等小蓝侧拿到实际回调地址后，回到列表「编辑」**回填**——
授权时按**逐字符精确匹配**校验，不支持通配/前缀/尾斜杠容错。

密钥丢失只能「轮换密钥」（旧密钥立即失效）。

---

## 3. 安装完成后：成员授权与数据访问

安装只登记应用，**不授予任何用户数据权限**。成员侧流程（与安装流完全独立）：

| 用途 | 端点 |
|---|---|
| 授权入口（浏览器跳转） | `{frontend}/oauth2/authorize?client_id=…&redirect_uri=…&response_type=code&scope=…&state=…` |
| 换取令牌 | `POST {backend}/oauth2/token`（`grant_type=authorization_code` / `refresh_token`） |
| 用户信息 | `GET {backend}/oauth2/userinfo`（scope `profile`） |
| 吊销令牌 | `POST {backend}/oauth2/revoke` |
| 只读数据面 | `GET {backend}/oauth2/api/tasks` \| `/projects` \| `/requirements` \| `/me` |

成员未在同意页同意前，接入方拿不到任何用户数据。

---

## 4. 常见问题

| 问题 | 回答 |
|---|---|
| 密钥丢了怎么办 | 客户端管理页「轮换密钥」（旧密钥立即失效）；安装流场景则重新发起安装 |
| 停用客户端会立刻踢掉已登录用户吗 | 不会。停用只挡**新的**授权请求与换 token；已签发的 access token 在有效期内仍可用。要立即失效请轮换密钥或删除客户端 |
| 小蓝 appKey 后拿到回调地址，还要重装吗 | 不用。用「编辑」回填 redirect_uris 即可（精确匹配） |
| 安装码泄漏了有危险吗 | 安装码本身换不出密钥——还必须配 verifier（只有小蓝侧有）。且 10 分钟过期、单次消费 |
| 管理员误批了一个陌生应用 | 客户端管理页「删除」即可；其授权码与令牌会级联吊销 |
| 为什么发起安装不需要长期凭据 | 信任由三层构成：管理员确认门 + verifier 绑定 + 滥用上限。**两系统之间无需复制任何长期凭据** |

---

## 5. 边界（不可承诺）

- OpenTask **不承诺跨仓一键对接**：小蓝侧应用创建、appKey 生成、回调地址登记仍需在小蓝 CoWork 后台完成；
- OpenTask **不对接入方提供的任何 URL 发起服务端请求**（无 SSRF 面）；
- 安装流**不签发任何 token**，**不代成员授权**；
- 接入方若未在本地校验 `state`，OpenTask 无法替其兜底 CSRF。

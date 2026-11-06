# E101 · OAuth 自动接入（Install Flow）设计 **v2**

- 日期：2026-11-06
- 范围：OpenTask 侧「小蓝发起安装 → 管理员确认 → 一次性 code → 服务端兑换密钥」全链路
- 状态：设计定稿（v2，取代 v1 的 installer_token 方案）
- **协议契约（权威）**：`docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md`
- 前置：E100（客户端管理界面）——共用 client 表与页面外壳

## 变更（v1 → v2）

| v1 | v2 | 原因 |
|---|---|---|
| 接入方长期 `installer_token`（线下交付）+ `oauth_installers` 表 | **删除**；改为小蓝发起时生成**一次性高熵 verifier**，OpenTask 只存 `challenge = S256(verifier)` | 「两系统免复制长期凭据」的硬要求 |
| 兑换靠 installer token | 兑换靠 **verifier（PKCE S256 绑定）** + 一次性 code | 同上 |
| `already_consumed` 语义含糊 | **consumed ≠ 成功**；新增**恢复窗口**（verifier 重试 → 换发新密钥）与窗口外**强制重装** | 响应丢失时不得假报成功 |
| 无开放重定向评估 | 新增 §4.3 | `callback_url` 由来方提供 |
| 无未认证发起滥用上限 | 新增 §4.4 | 发起方无身份 |

---

## 1. 背景与目标

E100 把「管理员手工调接口建 client」搬进了界面，但**跨系统首次接入仍是人工串流程**。
小蓝 CoWork 希望**自己发起**接入，管理员在 OpenTask 点一次「确认安装」即完成登记与密钥交付。

### 1.1 目标

- 小蓝侧**自助发起**安装申请（无需管理员先建 client、无需跨系统复制长期凭据）；
- 管理员在 OpenTask **登录后确认**（显式看到回调白名单与 scopes，且不可就地修改）；
- 密钥交付**只经服务端**：一次性 code → 服务端用 verifier 兑换 → `client_secret` 只在小蓝后端出现一次；
- **成员授权仍独立**：安装不授予任何用户数据权限；
- 满足 CSRF / 重放 / 过期 / SSRF / 开放重定向 / 权限确认 / 幂等失败处理（§5）。

### 1.2 非目标

- ❌ RFC 7591 自助注册（本流程的核心恰是**管理员确认**）；
- ❌ "拉取 manifest URL"模式（GitHub 式 pull）——见 §4.3；
- ❌ 任何**跨系统长期凭据**（不引入 installer token / 共享密钥）；
- ❌ 跨仓一键对接：小蓝侧应用侧逻辑不在本仓，按契约另行开发；
- ❌ 改线上环境、不推送、不部署。

---

## 2. 现状盘点（已核实）

- 后端 OAuth2 Provider 能力完备（client CRUD + 授权码流 + 只读数据面 + scope 强制）；
- **缺**：安装流的数据模型、服务、端点、迁移、界面；
- 权限体系：`permission_defs.py` → `seed_user_center()`（启动播种）→ `admin` 权限集 = 字典全集；
  前端 `MENU_PERMISSION_ROUTE_KEYS` ↔ `route_key` 一一对应；
- 既有 secret 口径：**只存 SHA-256 哈希 + 展示前缀**，明文一次性下发；
- 可用原语：`hashlib.sha256` + `secrets.compare_digest`（恒定时间比较）；IP 明文记录（登录审计既有惯例）。

---

## 3. 方案选择

| 方案 | 做法 | 评价 |
|---|---|---|
| **A. push + PKCE**（**选定**） | 小蓝 push manifest（含 `challenge`）；OpenTask 批准后回跳一次性 code；小蓝用 verifier 兑换 | 无长期凭据、无 SSRF 面；信任由「管理员确认」+「verifier 绑定」+「滥用上限」三层构成 |
| B. pull（GitHub 式 manifest URL 抓取） | OpenTask 抓来方 URL | 需 7 条 SSRF 加固，且引入对来方可用性依赖 |
| C. 长期 installer token | v1 方案 | **违反免复制凭据要求，已废弃** |

**选 A。** 与 GitHub 的差异是刻意的：GitHub 必须拉取（因为它要先知道 app 身份），
本场景小蓝是**已知的一方**，push 即可换取"无 SSRF 面"的收益。

---

## 4. 详细设计

### 4.1 数据模型（新增 1 张表）

`oauth_install_requests`（安装申请）——**不引入 installer 表**（无长期凭据即无接入方身份）：

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | UUID PK | `install_id`（UUID4，不可枚举） |
| `client_id` | String(64) | 小蓝申请的客户端标识 |
| `name` / `description` | String(255) / Text | 应用元信息 |
| `redirect_uris` | Text | 逗号分隔白名单（精确匹配，沿用既有存储口径） |
| `scopes` | String(512) | 空格分隔 |
| `grant_types` | String(128) | 空格分隔 |
| `callback_url` | Text | 安装完成回跳地址（带 code & state） |
| `state` | String(256) | 小蓝的 CSRF 串，原样回传 |
| `code_challenge` | String(128) | **S256(verifier)**（BASE64URL，43 字符） |
| `code_challenge_method` | String(16) | 固定 `S256` |
| `status` | String(16) | `PENDING` / `APPROVED` / `REJECTED` / `EXPIRED` / `CONSUMED` |
| `code_hash` | String(64) | 安装码 SHA-256 哈希（**不存明文**） |
| `code_expires_at` | DateTime | 安装码有效期（默认 10 分钟） |
| `expires_at` | DateTime | 申请有效期（默认 15 分钟） |
| `approved_by` / `approved_at` / `rejected_at` | FK / DateTime | 生命周期留痕 |
| `consumed_at` / `first_exchange_at` | DateTime | 首次兑换时间（恢复窗口起算点） |
| `recovery_count` / `recovery_used_at` | Int / DateTime | 恢复路径审计 |
| `request_ip` / `user_agent` | String(64) / Text | 来源留痕（供管理员判断可信度 + 限流） |
| `created_at` / `updated_at` | DateTime | |

索引：`(status, expires_at)`、`(client_id, status)`、`code_hash`。

### 4.2 密钥处理：**占位密钥 + 兑换时轮换**

批准时创建 client，其 `client_secret` 用**随机占位值**（明文立即丢弃，只留哈希）。
兑换时**轮换**出新密钥，明文放进响应。

**为什么不用"加密存库、兑换时解密"**：加密需要服务端主密钥（轮换/备份/灾备都是新运维面），
且密文泄漏即等于密钥泄漏。占位方案让**库内任何时刻都没有密钥明文或可逆密文**，只有哈希——
与仓内 client / user PAT 口径一致。

代价：「已批准未兑换」窗口内 client 持有一枚谁都不知道的密钥（无法通过校验，无害），
兑换时旧密钥立即失效。

### 4.3 SSRF 与开放重定向

**SSRF**：OpenTask **不对来方提供的任何 URL 发起服务端请求**（push 而非 pull）→ **无 SSRF 面**。
> 若将来要支持 manifest URL 拉取，必须先落地 GitHub 式 7 条加固（仅 https、域名白名单、解析后禁私网/回环、
> 禁跟随重定向、DNS 固定、超时/体积上限、字段逐条校验）。在此之前**禁止**新增按来方 URL 抓取的入口。

**开放重定向**（`callback_url` 由来方提供 → D 端点 302 过去）：

| # | 缓解 | 落地位置 |
|---|---|---|
| M1 | 严格 URL 校验（入参 + **回跳前二次校验**）：绝对 URL；scheme https（loopback 允许 http）；禁 userinfo/fragment/控制字符/IP 字面量（loopback 除外） | `install_service._validate_callback_url()` |
| M2 | 主机绑定：`callback_url` 主机 ∈ redirect_uris 主机 ∪ 其子域 | 同上（M2 与 M1 一起做） |
| M3 | 回跳响应头 `Referrer-Policy: no-referrer` + `Cache-Control: no-store` + `X-Content-Type-Options: nosniff` | approve 端点 |
| M4 | code 非秘密：单次 + 10 分钟 + 必须配 verifier | exchange 端点 |
| M5 | `state` 由小蓝生成并校验 | 契约强制项 |
| M6 | 确认页展示 callback 主机 + "接入方未验证身份"风险提示 + 来源 IP/UA | 前端安装确认页 |

**残余风险（明确接受）**：管理员浏览器可能被重定向到申请方自选域名（钓鱼观感）。
危害被 M4（code 无用）+ M6（人工核对）+ 成员授权独立 三重限制住。
**不引入**可信主机白名单（YAGNI；多接入方场景再评估）。

### 4.4 未认证发起的滥用上限

发起方无身份 → 必须有资源与诱导面约束（配置项见 §4.8）：

| 滥用 | 上限 | 超限 |
|---|---|---|
| pending 申请**总数** | 100 | `429 too_many_pending_requests` |
| 单源 IP 的 pending 数 | 5 | `429 too_many_pending_requests` |
| 单源 IP 创建速率 | 10 次/分钟 | `429 rate_limited` |
| 重复发起（同 client_id + 同 challenge） | 复用同一 install_id | `200` + `reused: true` |
| 请求体/字段规模 | body ≤16KB；redirect_uris ≤20/≤2048；scopes ≤32 | `422` |
| 申请存活期 | 15 分钟 | `EXPIRED`，惰性释放配额 |

配套：**无"批准队列"洪水**（批准只走 UUID4 直达链接，不可枚举）；
审计列表只展示最近 50 条且不含 code/challenge/state。

### 4.5 端点与绑定

| 方法 | 路径 | 鉴权 | 语义 |
|---|---|---|---|
| POST | `/api/oauth2/install/requests` | 无 | 发起；幂等复用；校验 challenge/redirect/callback/scopes |
| POST | `/api/oauth2/install/status` | verifier（body） | 查状态；**不含密钥**；verifier 不匹配 → 404 |
| POST | `/api/oauth2/install/requests/{id}/approve` | 登录 + admin | 条件更新 `PENDING→APPROVED`；建 client（占位密钥）；生成 code（只存哈希）；返回 `redirect_to` |
| POST | `/api/oauth2/install/requests/{id}/reject` | 登录 + admin | `PENDING→REJECTED` |
| POST | `/api/oauth2/install/exchange` | verifier（body） | 见 §4.6 |
| GET | `/api/oauth2/install/requests` | 登录 + admin | 审计列表（最近 50 条） |

**绑定**：兑换返回的 `redirect_uris` / `scopes` / `grant_types` / `client_id` **从 DB 读**（批准时写入值），
不接受请求体改写；批准**按原样**（确认页只读），要改只能驳回后重新申请。

### 4.6 失败恢复（重点）

```
PENDING ─approve→ APPROVED ─exchange(首次)→ CONSUMED
                     │                          │
                     │                          ├─ 同 verifier 重试（恢复窗口内）→ 200 新密钥（旧的立即失效）
                     │                          └─ 窗口过后再试 → 409 install_already_consumed（必须重装）
```

- 恢复窗口 = 首次兑换起 `oauth_install_recovery_window_seconds`（默认 600s）；
- **恢复 = 轮换**（不存可逆副本，见 §4.2）；
- **「已消费」不是成功**：只有 **2xx 且响应体含 `client_secret`** 才算成功；所有 4xx/5xx 都是失败；
- 小蓝侧约束：**串行化**兑换请求、收到 2xx 立即停止重试、先持久化再继续（契约 §4.4）。

### 4.7 幂等与并发

- 兑换消费 code 用条件更新：`UPDATE ... SET status='CONSUMED', consumed_at=now() WHERE id=:id AND status='APPROVED' AND consumed_at IS NULL`
  → 影响行数 0 → 并发已消费 → 走恢复分支或 409；
- 批准同理：`WHERE status='PENDING'`；
- 创建申请幂等：同 `(client_id, code_challenge)` 且未过期 → 复用。

### 4.8 配置项（`backend/opentask/config.py`，`auth` 段）

| 配置 | 默认 | env |
|---|---|---|
| `oauth_install_request_ttl_seconds` | 900 | `AUTH_OAUTH_INSTALL_REQUEST_TTL_SECONDS` |
| `oauth_install_code_ttl_seconds` | 600 | `AUTH_OAUTH_INSTALL_CODE_TTL_SECONDS` |
| `oauth_install_recovery_window_seconds` | 600 | `AUTH_OAUTH_INSTALL_RECOVERY_WINDOW_SECONDS` |
| `oauth_install_max_pending_global` | 100 | `AUTH_OAUTH_INSTALL_MAX_PENDING_GLOBAL` |
| `oauth_install_max_pending_per_ip` | 5 | `AUTH_OAUTH_INSTALL_MAX_PENDING_PER_IP` |
| `oauth_install_rate_limit_per_minute` | 10 | `AUTH_OAUTH_INSTALL_RATE_LIMIT_PER_MINUTE` |

### 4.9 界面

| 界面 | 位置 | 内容 |
|---|---|---|
| 客户端管理 | `views/manage/oauth2/index.vue`（E100） | client 列表、创建/编辑/停用、一次性密钥 |
| 安装申请审计 | 同页「安装申请」页签 | 最近 50 条：状态、来源 IP/UA、client_id、时间；不展示 code/challenge |
| 安装确认页 | `views/oauth2/install/[installId].vue` | §4.3 M6 全量展示 + 批准/拒绝；批准后整页跳 `redirect_to` |
| 接入说明 | E100「接入说明」面板 | 更新为自动接入流程（含契约链接） |

路由：`oauth2_install`（`/oauth2/install/:installId`），走既有登录守卫。

---

## 5. 测试计划

| 层 | 用例 |
|---|---|
| 后端 pytest（`tests/oauth2/test_install_flow.py`） | ①发起→批准→回跳带 code&state；②批准后 client 存在且库内只有哈希；③兑换成功返回明文密钥，库内仍只有哈希；④**二次兑换 → 恢复窗口内返回新密钥、窗口外 409**；⑤verifier 不匹配 → 400；⑥code 错误 → 400；⑦code 过期 → 400；⑧非 admin 批准 → 403；⑨重复批准 → 409；⑩同 client_id+challenge 重复发起 → 复用同一 install_id；⑪client_id 与既有 client 冲突 → 409；⑫pending 超限 → 429；⑬兑换返回的 scopes/redirect_uris 与批准内容精确一致；⑭callback_url 主机不在 redirect_uris 主机集合 → 422；⑮状态端点 verifier 不匹配 → 404；⑯日志不含 code/verifier/secret |
| 前端 vitest | 确认页数据映射、状态枚举文案、scope 文案映射（复用 E100 utils） |
| 门禁 | `uv run pytest tests/ -v`；`pnpm lint` / `pnpm build` / `pnpm test` / `pnpm typecheck`；浏览器实测 |

---

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 诱导批准（钓鱼） | 确认页展示 callback 主机 + 接入方未验证身份提示 + 来源 IP/UA；批准按原样；限流 |
| 开放重定向 | §4.3 M1–M6；code 无用；残余风险明确接受 |
| code 从浏览器历史/Referer 泄漏 | 单次 + 10 分钟 + 必须配 verifier；no-referrer/no-store |
| 兑换响应丢失 | §4.6 恢复窗口（换发新密钥）；窗口外明确失败并要求重装；**不得假报成功** |
| verifier 泄漏 | 一次性高熵、只在服务端、OpenTask 只存 challenge |
| 乱序/并发兑换导致密钥反复失效 | 小蓝侧串行化约束（契约 §4.4）+ 恢复次数审计 |
| 与 E100 重复 | 安装流创建的 client 同样出现在 E100 列表，可编辑/停用/轮换 |

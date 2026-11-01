# OAuth2 Provider 验收证据（2026-11-02）

- 范围：OpenTask 侧 OAuth2 Provider（授权码流 + 只读数据面 + scope 隔离）
- 规格：`docs/superpowers/specs/2026-11-02-oauth2-provider-design.md`
- 环境：后端 `uvicorn opentask.main:app` :3000；前端 `vite dev` :9527；PostgreSQL 16（容器 `opentask-postgres`）
- 工具：Orca 内置浏览器（`orca tab/snapshot/screenshot/eval`）+ curl

---

## 1. 门禁

| 门禁 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `cd backend && uv run pytest tests/ -q` | **567 passed, 27 skipped, 0 failed**（退出码 0） |
| OAuth2 专项 | `cd backend && uv run pytest tests/oauth2/ -q` | **36 passed, 0 failed** |
| 前端 lint | `cd frontend && npm run lint` | **0 errors**（272 warnings 全为仓内存量，新增文件 0 告警） |
| 前端 build | `cd frontend && npm run build` | **Build successful** |
| 迁移往返 | `alembic upgrade head` → `downgrade 003ccd38d5cd` → `upgrade head` | 4 表 → 0 表 → 4 表（PG 16 实测） |

---

## 2. 浏览器证据

### 2.1 未登录访问授权入口 → 守卫跳登录页并带完整回跳参数

访问 `/oauth2/authorize?client_id=dsh-saas-demo&redirect_uri=...&response_type=code&scope=...&state=demo-state-123`：

```
ORIGIN: http://localhost:9527/login?redirect=/oauth2/authorize?client_id=dsh-saas-demo%26redirect_uri=http://localhost:9527/oauth2-demo-callback%26response_type=code%26scope=read:tasks%2Bread:projects%2Bread:requirements%2Bprofile%26state=demo-state-123
```

### 2.2 登录后回跳到同意页（授权请求未丢失）

清空浏览器存储（模拟首次登录）→ 重新进入授权入口 → 账号密码登录：

```
ORIGIN: http://localhost:9527/oauth2/authorize?client_id=dsh-saas-demo&redirect_uri=http://localhost:9527/oauth2-demo-callback&response_type=code&scope=read:tasks+read:projects+read:requirements+profile&state=demo-state-123
```

截图：[`assets/2026-11-02-oauth2-consent-after-login-redirect.png`](assets/2026-11-02-oauth2-consent-after-login-redirect.png)

> 修复记录：登录后曾停在 `/home`——`auth/index.ts` 的 `checkTabClear()` 在**首次登录**（本地无 `lastLoginUserId`）时也返回 true，把 `?redirect=` 回跳一并抑制，导致授权请求丢失。已改为只在**确实换了用户**时才抑制回跳（清标签页语义不变）。

### 2.3 同意页渲染正确

截图：[`assets/2026-11-02-oauth2-consent-page.png`](assets/2026-11-02-oauth2-consent-page.png)

页面要素逐项核对：

| 要素 | 实测值 |
|---|---|
| 标题 | 授权确认 |
| 引导语 | 「小蓝 CoWork 管理后台」请求访问你的 OpenTask 数据。 |
| 权限标题 | 该应用将获得以下权限 |
| 权限清单 | 读取你的基本资料（用户名、姓名）／读取你的项目列表与详情／读取你的需求列表与详情／读取你的任务列表与详情 |
| 回调提示 | 授权后将返回 → `localhost:9527` |
| 应用描述 | 小蓝 CoWork admin 工作台的「应用」菜单，用于读取成员的 OpenTask 任务/项目/需求 |
| 操作 | 拒绝／同意授权 |

### 2.4 点击「同意授权」→ 302 回回调地址并带 code 与 state

```
ORIGIN: http://localhost:9527/oauth2-demo-callback?state=demo-state-123&code=4eb2d0c5da1bbe54946aed86ade7ced0130c397f0bf28e32588c00db80b8d72c
```

---

## 3. 真栈接口证据

### 3.1 授权码换令牌（真实 code）

`POST /oauth2/token`（grant_type=authorization_code）：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 7200,
  "refresh_token": "94c5c06f5dc001453eefaeb558e030a3f22025dd353b4f4596f8ca1a3e4cb0f7",
  "scope": "profile read:projects read:requirements read:tasks"
}
```

JWT payload 解出：

```json
{"sub":"09894c0b-...","tv":0,"aud":"dsh-saas-demo","scope":"profile read:projects read:requirements read:tasks","jti":"97575f13-...","exp":1793558373}
```

claims 与规格 §4.1 定稿一致（`sub`+`tv`+`aud`+`scope`+`jti`+`exp`；**用 `scope` 不用 `scp`**）。

### 3.2 只读数据面

| 端点 | 状态码 |
|---|---|
| `GET /oauth2/api/me` | 200 |
| `GET /oauth2/api/tasks` | 200 |
| `GET /oauth2/api/projects` | 200 |
| `GET /oauth2/api/requirements` | 200 |
| `GET /oauth2/userinfo` | 200 |

### 3.3 scope 隔离（同一 token 打不该打的端点）

| 端点 | 凭据 | 状态码 |
|---|---|---|
| `/api/issues` | OAuth token（带 aud） | **401** |
| `/tasks`（契约层） | OAuth token（带 aud） | **401** |
| `/api/issues` | 会话 token（不带 aud） | **200** |

即：OAuth token 进不了通用 API 面与 Orca 契约层；既有会话 token 不受影响。

---

## 4. 已知限制

- `POST /oauth2/token` 等**标准协议端点**按 RFC 6749 §5 返回 `{access_token, token_type, expires_in, refresh_token, scope}`，**不走**本仓 `{code,message,data}` 包装（包装会破坏 OAuth2 互操作性）；SPA 面向的 `/api/oauth2/*` 端点则走仓内包装，与其余 `/api/*` 一致。
- 同意页当前挂在 base 布局下（侧边栏可见），非独立空白页；不影响流程正确性。

# E100 · OAuth 客户端管理体验（管理员界面）设计

- 日期：2026-11-06
- 范围：OpenTask 管理端「OAuth 客户端」界面 + 小蓝 CoWork 接入说明
- 状态：设计定稿（实现前评审通过）

---

## 1. 背景与目标

### 1.1 现状痛点

小蓝 CoWork 是 OAuth 2.0 **授权码客户端**（消费方）。今天要让一个小蓝应用连上 OpenTask，
管理员必须手工完成：

1. 手工 `POST /api/oauth2/clients` 注册 client；
2. 从响应里**一次性**取出 `client_secret` 明文（库里只存 SHA-256 哈希，**没有任何接口能再取回**）；
3. 手工拼 `redirect_uris` 白名单；
4. 回调地址变更时手工 `PATCH`（**精确匹配**，不容错）。

任何一步出错都要重发 HTTP 请求，且密钥一旦丢失只能轮换——现场配置门槛高、风险大。

### 1.2 目标

在 OpenTask 后台提供一个**管理员界面**，让管理员（而非脚本）完成：

- 创建 / 查看 / 编辑 / 停用 OAuth 客户端；
- 清晰管理**回调地址**（白名单）与 **scopes**（授权范围）；
- **一次性**安全展示并复制新密钥（此后不可再取回，与后端口径一致）；
- 直接在页面上拿到**小蓝 CoWork 接入所需的端点与操作说明**（含 appKey 先建、回调后定的两步流程）。

### 1.3 成功判据

| 判据 | 验证方式 |
|---|---|
| 管理员不用碰 curl 就能建好 client 并拿到密钥 | 浏览器实测：建 → 复制密钥 → 列表只见前缀 |
| 回调地址/scopes 的填写规则在界面上说清楚 | 表单内联提示 + 校验 |
| 非管理员拿不到页面、也拿不到接口 | 路由菜单权限 + 后端 403 双保险 |
| 密钥不落盘、不二次展示 | 代码审查 + 列表接口不含明文（后端既有测试已钉死） |
| 小蓝侧接入步骤可照做 | 页面内「接入说明」面板 + `docs/oauth2-client-onboarding.md` |

---

## 2. 现状盘点（已核实，非推测）

> 下述结论均来自本仓代码实读，行号会随改动漂移，以文件名为准。

### 2.1 后端能力（**已完备，本设计基本不改**）

| 能力 | 位置 | 口径 |
|---|---|---|
| client 列表 | `backend/opentask/api/oauth2/router.py` `GET /api/oauth2/clients` | admin；**不含 secret 明文**，只回 `secret_prefix` |
| 注册 client | 同上 `POST /api/oauth2/clients` | admin；**secret 明文仅此一次**返回 |
| 更新 client | 同上 `PATCH /api/oauth2/clients/{client_id}` | admin；可改 name/description/redirect_uris/scopes/status |
| 删除 client | 同上 `DELETE /api/oauth2/clients/{client_id}` | admin；级联清理授权码与令牌 |
| 轮换密钥 | 同上 `POST /api/oauth2/clients/{client_id}/rotate-secret` | admin；**新明文仅此一次**返回 |
| 权限门禁 | 同上 `_require_admin()` | `current_user.role != "admin"` → **403** |
| secret 存储 | `services/oauth2/client_service.py` `hash_secret()` | 库内存 SHA-256 哈希 + 8 位前缀，明文不落库 |
| redirect_uri 校验 | 同上 `verify_redirect_uri()` | **白名单精确匹配**，不做前缀/通配 |
| scope 校验 | 同上 `verify_scope()` | 允许集是**上界**，超出即 `invalid_scope`，不隐式收敛 |
| grant_type | 同上 `verify_grant_type()` | `authorization_code` / `refresh_token`（默认两者） |
| provider 实际支持的 scope | `api/oauth2/read_api.py` | `read:tasks` / `read:projects` / `read:requirements` / `profile`（共 4 个） |

**结论：后端管理 API 已经能支撑完整的管理界面，本设计不新增、不改写任何 OAuth2 端点。**

### 2.2 前端能力（**缺口在这里**）

| 项 | 现状 |
|---|---|
| 同意页 | `frontend/src/views/oauth2/index.vue`（路由 `/oauth2/authorize`）——**有** |
| 管理界面 | **无**（`src/views/manage/` 下只有 user/dept/role/perm） |
| API 客户端 | `frontend/src/service/api/oauth2.ts` —— 只有同意页用的两个函数 |
| 类型 | `frontend/src/typings/api/oauth2.d.ts` —— 只有同意页用的类型 |

### 2.3 权限模型（**复用，不另起炉灶**）

- 后端权限点字典：`backend/opentask/services/user_center/permission_defs.py`
  （`type=menu` 时 `route_key` 对应前端静态路由 name；`type=button` 为操作码）。
- 幂等播种：`services/user_center/seed.py` `seed_user_center()`，**后端启动时**由 `opentask/main.py` 调用。
  - 系统角色 `admin` 的目标权限集 = **字典全集** → 新增一条菜单权限，admin 自动获得；
  - `maintainer` / `developer` / `viewer` 的权限集是**白名单枚举** → 默认**不会**拿到新菜单权限。
- 前端菜单门禁：`frontend/src/store/modules/route/shared.ts`
  - `MENU_PERMISSION_ROUTE_KEYS` 与字典里 `type=menu` 的 `route_key` **一一对应**；
  - 未登记的业务路由默认放行，**登记后**才受 `menus` 过滤。
- 按钮级门禁：`useAuth().hasAuth(code)`（`buttons` 权限码）。

### 2.4 导航现状（本次要动的一处）

`manage` 父路由 `hideInMenu: true` → **用户/部门/角色/权限点四个管理页在侧边栏不可见，只能 URL 直达**
（全仓无任何跳转入口，见 `grep -rn "manage_user" src/` 仅命中类型/路由/测试）。
本次新增的管理页若沿用该父路由，将继续「建好却找不到」——与"易用"目标直接冲突。

---

## 3. 方案选择

| 方案 | 做法 | 评价 |
|---|---|---|
| **A. 纯前端** | 只做页面，复用现有 API，菜单可见性用前端 `roles` 判断 | 权限口径分裂（前端按 role、后端按字典），与仓内既有 `manage_*` 页不一致 |
| **B. 复用菜单权限模型**（**选定**） | 后端字典加 1 条菜单权限；前端登记 route_key + 页面 | 与 user/dept/role/perm 完全同构；admin 自动获得、其他角色默认拿不到；不新增 API |
| C. 后端新造带 scope 目录的管理 API | 新增 scope 目录端点与 DTO | 范围膨胀；provider 支持的 scope 只有 4 个且已在前端同意页镜像；漂移可用「自定义 scope」兜底 |

**选 B。** 理由：①后端 OAuth2 管理 API 已完备，B 方案零新增端点；②权限沿用仓内唯一真源
（字典 + 播种 + route_key 三处登记），不发明第二套鉴权；③`admin` 角色权限 = 字典全集，
新权限点随下一次后端启动自动落库，**存量 admin 不需要任何手工授权**。

### 3.1 明确的非目标

- ❌ 不做 RFC 7591 动态客户端注册（自助注册）——设计原案已明确「client 由管理员显式注册」。
- ❌ 不做密钥找回 / 二次查看——后端不存明文，前端不得凭空造出。
- ❌ 不做「跨仓一键对接」：小蓝侧应用创建、appKey 生成、回调地址登记**仍需在小蓝 CoWork 后台完成**。
  本仓只负责 OpenTask 侧 client 登记与密钥发放，两侧各自操作、各自可回滚。
- ❌ 不改线上环境、不推送、不部署；不使用真实用户凭据。

---

## 4. 详细设计

### 4.1 后端改动（最小：1 行权限字典 + 测试）

**改动 1：`backend/opentask/services/user_center/permission_defs.py`**

```python
{"code": "menu:manage_oauth2", "name": "OAuth 客户端", "type": "menu", "route_key": "manage_oauth2"},
```

**不改动 OAuth2 端点的鉴权口径**（继续用 `_require_admin()`，即 `user.role == "admin"`）：

- 理由一（不削弱）：`_require_admin` 是**现有边界**，换成 `require_permission("menu:manage_oauth2")`
  会引入「字典播种前存量 admin（`user.role='admin'` 但未挂 `user_role` 关联行）被挡在门外」的**回归风险**——
  存量库未必播种过，且本仓不做线上变更，无法验证。宁可保留更宽松的既有校验。
- 理由二（不削弱）：前端菜单门禁只是**可见性**；真正的边界在后端 403，绕过页面直连 API 依然被拒。
- 页面层再做一层：admin 之外的角色 `menus` 里没有 `manage_oauth2` → 路由被过滤 → 403 页。

**改动 2：测试**（`backend/tests/unit/test_seed.py` 或新增用例）
断言新菜单权限已入字典、`route_key` 正确、且 **admin 之外的三个系统角色都没有它**（默认最小权限）。

### 4.2 前端改动

#### 4.2.1 路由与菜单

| 项 | 值 |
|---|---|
| 视图目录 | `frontend/src/views/manage/oauth2/`（`index.vue` + `modules/`） |
| 路由名 | `manage_oauth2`（elegant-router 由目录生成） |
| 路径 | `/manage/oauth2` |
| 父级 | 复用 `manage` 分组（与用户/角色管理同级） |
| 菜单登记 | `src/store/modules/route/shared.ts` 的 `MENU_PERMISSION_ROUTE_KEYS` 追加 `'manage_oauth2'` |
| i18n | `route.manage_oauth2`（zh-cn / en-us） |

**导航可见性**：`manage` 父路由当前 `hideInMenu: true`（管理页在侧边栏不可见）。本次把 `manage`
父路由**改为可见**（去掉 `hideInMenu`），使「系统管理」分组连同其子项出现在侧边栏：

- 管理员：可见「系统管理 → 部门/角色/权限点/用户/OAuth 客户端」；
- 非管理员：其 `menus` 不含任何 `manage_*` → 子项全被过滤 → 父分组被剪枝（既有 `filterAuthRouteByMenus` 逻辑），
  **侧边栏与今天一致**，不会多出空分组。
- 该父路由自带图标 `carbon:cloud-service-management` 与 `order: 9`，无需新增资源。

#### 4.2.2 组件拆分（各自单一职责）

| 文件 | 职责 |
|---|---|
| `views/manage/oauth2/index.vue` | 列表页：表格、状态筛选、行操作编排、数据加载 |
| `views/manage/oauth2/modules/client-form-drawer.vue` | 创建/编辑抽屉：名称、client_id、描述、回调地址、scopes、grant_types |
| `views/manage/oauth2/modules/secret-modal.vue` | **一次性密钥**弹窗：明文 + 复制 + 不可找回提示 |
| `views/manage/oauth2/modules/guide-panel.vue` | 小蓝 CoWork 接入说明面板（端点表 + 两步流程 + 边界声明） |
| `utils/oauth2-client.ts` | 纯函数：回调地址解析/校验、scope 归一、文案映射（**可单测**） |
| `utils/oauth2-client.test.ts` | 上者的 vitest 单测 |

#### 4.2.3 API 层与类型

`src/service/api/oauth2.ts` 追加（沿用现有 `request` 封装与 `{error, data}` 返回约定）：

| 函数 | 方法 | 路径 |
|---|---|---|
| `fetchGetOAuthClients` | GET | `/api/oauth2/clients` |
| `fetchCreateOAuthClient` | POST | `/api/oauth2/clients` |
| `fetchUpdateOAuthClient` | PATCH | `/api/oauth2/clients/{client_id}` |
| `fetchDeleteOAuthClient` | DELETE | `/api/oauth2/clients/{client_id}` |
| `fetchRotateOAuthClientSecret` | POST | `/api/oauth2/clients/{client_id}/rotate-secret` |

`src/typings/api/oauth2.d.ts` 追加 `OAuthClient` / `OAuthClientCreate` / `OAuthClientUpdate` /
`OAuthClientCreated` 类型（字段与后端 `OAuthClientView` / `OAuthClientCreate` / `OAuthClientUpdate` 一一对应）。

#### 4.2.4 一次性密钥 UX（安全要点）

1. 创建成功 / 轮换成功 → 后端返回 `client_secret` 明文 → **只进内存 `ref`**，弹窗展示；
2. 弹窗内提供「复制」按钮（`navigator.clipboard.writeText`）；
3. 弹窗顶部醒目告警：**「明文仅此一次，关闭后不可再取回；库中只存哈希」**；
4. 关闭弹窗即**清空内存中的明文**（`secret.value = ''`），此后只能「轮换密钥」换新的；
5. **不写** localStorage / sessionStorage / URL / 控制台日志 / 埋点；
6. 列表与详情**只展示 `secret_prefix`**（如 `ocs_1a2b…`），与后端口径一致。

#### 4.2.5 回调地址管理

- 输入方式：动态列表，一行一个 URI（便于逐条校验与删除）；
- 客户端校验（提交前，提示级）：
  - 必须是**绝对 URL**（`http`/`https`）；
  - **去重**（相同 URI 重复登记无意义）；
  - 提示「**精确匹配**，不支持通配 / 前缀 / 尾斜杠容错」；
  - 提示「必须与小蓝 CoWork 应用后台登记的回调地址**逐字符一致**」；
- 后端仍会再做一次精确匹配校验（`verify_redirect_uri`），前端校验只是提前拦截，不是安全边界。

#### 4.2.6 scopes 管理

- 以**已知 scope 复选**为主：`read:tasks` / `read:projects` / `read:requirements` / `profile`（附中文说明与对应数据面端点），
  取值真源为 `backend/opentask/api/oauth2/read_api.py`；
- 另留「自定义 scope」输入（逗号/空格分隔），供未来 provider 新增 scope 时先行登记（**不阻断**）；
- 提示文案：scopes 是**上界**，客户端请求超出即 `invalid_scope`——宁少勿多，按需授权。

#### 4.2.7 状态与危险操作

| 操作 | 交互 |
|---|---|
| 停用 / 启用 | 列表行内切换 `status`（`ACTIVE` / `DISABLED`）；停用后该 client 的授权请求与换 token 一律被拒 |
| 轮换密钥 | 二次确认 → 弹一次性密钥弹窗（旧密钥立即失效） |
| 删除 | 二次确认（明确告知：级联吊销其授权码与令牌） |

### 4.3 小蓝 CoWork 接入说明（页面面板 + 文档）

**内容大纲**（面板与 `docs/oauth2-client-onboarding.md` 同源同文）：

1. **端点清单**

   | 用途 | 端点 |
   |---|---|
   | 授权入口（浏览器跳转） | `{前端地址}/oauth2/authorize?client_id=…&redirect_uri=…&response_type=code&scope=…&state=…` |
   | 换取令牌 | `POST {后端地址}/oauth2/token`（`grant_type=authorization_code` / `refresh_token`） |
   | 用户信息 | `GET {后端地址}/oauth2/userinfo`（scope `profile`） |
   | 吊销令牌 | `POST {后端地址}/oauth2/revoke` |
   | 只读数据面 | `GET {后端地址}/oauth2/api/tasks` \| `/projects` \| `/requirements` \| `/me` |

   地址取自当前部署：前端地址用 `window.location.origin`，后端地址用 API base URL。

2. **两步接入流程（appKey 先建 → 回调后定）**

   小蓝 CoWork 的应用在**小蓝侧**创建后才拿得到 `appKey`，而回调地址往往带 `appKey`
   → OpenTask 侧登记时**还不知道最终回调地址**。因此：

   - **第 1 步**：在本页创建 OpenTask client，`redirect_uris` 先填**占位地址**
     （如 `https://placeholder.invalid/callback`），scopes 按最小必要勾选，**立即复制并保存密钥**（仅此一次）；
   - **第 2 步**：到小蓝 CoWork 后台创建应用，拿到 `appKey` 与其后台登记的回调地址；
   - **第 3 步**：回到本页「编辑」，把占位地址替换为**小蓝侧实际登记的回调地址**（精确匹配，逐字符一致）；
   - **第 4 步**：在小蓝侧填入本页给出的 `client_id` / `client_secret` 与授权入口地址（前端地址），
     由小蓝侧发起浏览器跳转，走标准授权码流程。

3. **边界声明**（避免误以为跨仓一键打通）

   - 本页**只**管理 OpenTask 侧的 client 登记与密钥发放；
   - 小蓝侧的应用创建、`appKey` 生成、回调地址登记**在小蓝 CoWork 后台完成**，本仓不代劳、也不承诺一键完成；
   - 两步之间存在**人工窗口期**：第 1 步到第 3 步之间，该 client 的回调地址是不正确的，授权请求会被
     `invalid_redirect_uri` 拒绝（这是**预期且安全**的失败，不是故障）。

4. **常见问题**：密钥丢了怎么办（轮换）、停用会不会踢掉已登录用户（停用只挡新的授权与换 token，
   已签发的 access token 仍在其有效期内可用；如需立即失效请轮换密钥或删除 client）。

### 4.4 权限与安全边界（自检清单）

| 项 | 结论 |
|---|---|
| 页面可见性 | 菜单权限 `menu:manage_oauth2`；admin 自动获得，其余系统角色默认无 |
| 接口鉴权 | 沿用 `_require_admin`（`role == "admin"`），**未放宽** |
| 密钥存储 | 后端只存哈希；前端只在内存弹窗短暂持有，关闭即清空 |
| 密钥传输 | 仅在注册/轮换的那一次响应里出现，列表接口永不含明文 |
| 越权面 | 非 admin 直连 API → 403（既有测试 `test_register_client_requires_admin` 已钉死） |
| 前端校验定位 | 提示/防呆，**不是**安全边界（后端仍精确校验 redirect_uri 与 scope） |

### 4.5 测试与验证计划

| 层 | 内容 |
|---|---|
| 后端 pytest | ①新菜单权限入字典且 `route_key` 正确；②admin 角色自动获得；③maintainer/developer/viewer **不**获得；④（回归）oauth2 既有套件全绿 |
| 前端 vitest | `utils/oauth2-client.ts` 纯函数：URI 解析/去重/合法性（http(s)/绝对 URL/相对路径拒绝）、scope 归一与去重、已知 scope 文案映射兜底 |
| 前端门禁 | `pnpm lint`（0 error）、`pnpm build`（成功）、`pnpm test`（全绿）、`pnpm typecheck` |
| 浏览器实测 | 新建页面属"大幅度页面修改" → AGENTS.md 要求浏览器验证：列表加载 / 建 client / 一次性密钥弹窗与复制 / 编辑回调地址 / 停用 / 删除 / 接入说明面板，并截图 |

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 存量 admin 未挂 `user_role` → 拿不到新菜单权限 → 侧边栏看不到新页 | 管理员找不到页面 | ①后端接口鉴权仍是 `role == admin`，功能不受影响；②页面路径 `/manage/oauth2` 可直达；③验收文档写明"如未播种，重启后端即自动同步"（播种幂等） |
| 前端 scope 清单与后端 read_api 漂移 | 管理员看不到新 scope | 已知 scope 清单在代码注释中标注真源；提供自定义 scope 输入兜底 |
| 侧边栏新增「系统管理」分组影响现有用户 | 导航变化 | 非管理员该分组被剪枝，侧边栏与今天一致；浏览器实测两类角色 |
| 一次性密钥误关弹窗 | 密钥丢失 | 弹窗强提示 + 提供「轮换密钥」补偿路径（弹窗内提供"我已保存"复选，未勾选时关闭再提示一次） |

---

## 6. 交付物清单

| 类别 | 文件 |
|---|---|
| 后端 | `services/user_center/permission_defs.py`（+1 条菜单权限）、`tests/unit/test_seed.py`（+用例） |
| 前端 | `service/api/oauth2.ts`、`typings/api/oauth2.d.ts`、`utils/oauth2-client.ts(+test)`、`views/manage/oauth2/**`、`router/elegant/routes.ts`、`store/modules/route/shared.ts`、`locales/langs/{zh-cn,en-us}.ts` |
| 文档 | 本设计、`docs/superpowers/plans/2026-11-06-e100-oauth2-client-admin.md`、`docs/oauth2-client-onboarding.md`（管理员/接入方手册）、`docs/superpowers/acceptances/2026-11-06-e100-oauth2-client-admin-acceptance.md` |
| 进度 | `progress.txt` |

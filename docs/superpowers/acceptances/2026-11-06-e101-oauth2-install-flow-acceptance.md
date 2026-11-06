# E101 · OAuth 自动接入（Install Flow）+ E100 客户端管理界面 验收证据

- 日期：2026-11-06
- 范围：OpenTask 侧 OAuth 客户端管理界面 + 跨系统自动接入（安装流）全链路
- 规格：`docs/superpowers/specs/2026-11-06-e101-oauth2-install-flow-design.md`、
  `docs/superpowers/specs/2026-11-06-e100-oauth2-client-admin-design.md`
- 契约（权威）：`docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md`
- 手册：`docs/oauth2-client-onboarding.md`

---

## 1. 门禁

| 门禁 | 命令 | 结果 |
|---|---|---|
| 后端全量（**干净库** `opentask_e101`） | `POSTGRES_TEST_DATABASE=opentask_e101 uv run pytest tests/ -q --tb=line` | **1523 passed，27 skipped，0 failed**（610.64s） |
| 后端全量（共享库 `opentask_test`） | `uv run pytest tests/ -q` | 3 failed（`tests/tasks/test_tasks_jira_wire.py`）/ 1520 passed —— **非回归**：与 `docs/superpowers/acceptances/2026-11-06-pending-fixes-acceptance.md` 记录的同名 3 条一致，为共享库污染；干净库全绿已证 |
| 安装流专项 | `uv run pytest tests/oauth2/test_install_flow.py -q` | **25 passed，0 failed** |
| 既有 OAuth2 专项（回归） | `uv run pytest tests/oauth2/ -q` | **56 passed**（安装流前）/ 含新增后 81 passed |
| 播种权限专项 | `uv run pytest tests/unit/test_seed.py -q` | **4 passed** |
| 迁移往返 | `alembic upgrade head` → `downgrade -1` → `upgrade head` | 通过（新增 `oauth_install_requests` 表） |
| 前端 lint（**本次改动文件**） | `npx eslint <本次改动文件>` | **0 error**，9 warning（inline-style，与仓内存量一致） |
| 前端 lint（全仓） | `pnpm lint` | 153 errors / 428 warnings —— **全部为存量**（改动前 156 errors，本次消掉自身 3 个） |
| 前端 build | `pnpm build` | **Build successful** |
| 前端测试 | `pnpm vitest run` | **69 files，465 passed**（新增 `src/utils/oauth2-client.test.ts` 19 例；改写 e13 导航断言与 shared 菜单门禁断言） |
| 前端 typecheck | `pnpm typecheck` | 仅剩**存量**错误：`src/typings/components.d.ts`（生成文件语法）与 `src/typings/api/issue.d.ts`（枚举语法），二者 HEAD 即如此、**本次改动文件零错误** |

---

## 2. 浏览器证据（无头 Chrome + CDP，本机真实后端 :7377 / 前端 :9527）

管理员账号为**本地新建**（`scripts/create_admin_user.py` 生成 `e2e_admin`），未使用任何既有用户凭据。

| # | 场景 | 实测 | 截图 |
|---|---|---|---|
| 1 | 打开「系统管理 → OAuth 客户端」 | 标题 `OAuth 客户端 - OpenTask`，URL `/manage/oauth2`；三个页签（客户端 / 安装申请 / 接入说明）齐全；侧边栏出现「系统管理」分组 | [`2026-11-06-e101-oauth2-clients-page.png`](assets/2026-11-06-e101-oauth2-clients-page.png) |
| 2 | 新建客户端（抽屉 → 表单 → 一次性密钥） | 抽屉打开；填 client_id / 名称 / 回调地址、勾选 `read:tasks`；点「创建」后**一次性密钥弹窗出现**，明文前缀 `ocs_…` | [`…-oauth2-client-form.png`](assets/2026-11-06-e101-oauth2-client-form.png)、[`…-oauth2-secret-modal.png`](assets/2026-11-06-e101-oauth2-secret-modal.png) |
| 3 | 列表核对 | 列表含新建 client；**列表正文不含密钥明文**（只显 `secret_prefix`） | [`…-oauth2-clients-list.png`](assets/2026-11-06-e101-oauth2-clients-list.png) |
| 4 | 安装确认页（管理员） | 展示 client_id / 描述 / 回跳地址与主机 / 来源 IP·UA / 有效期 / **回调白名单** / **scopes 中文说明** / 「接入方未提供长期凭据」风险提示 / 「成员授权独立」提示；「拒绝」「确认安装」可点 | [`…-oauth2-install-confirm.png`](assets/2026-11-06-e101-oauth2-install-confirm.png) |
| 5 | 批准 → 回跳 | 点「确认安装」后浏览器跳到 `http://127.0.0.1:9527/e2e-opentask/install-done?code=ins_f876820afc6cf922f341cdb925ad787d&state=e2e-state-123` —— **带一次性安装码与原样 state** | [`…-oauth2-install-redirect.png`](assets/2026-11-06-e101-oauth2-install-redirect.png) |
| 6 | 安装申请审计页签 | 含本次申请（应用名 / 状态 / 回跳主机 / 来源 IP / 时间）；**列表不含安装码、不含 challenge、不含 state** | [`…-oauth2-install-audit.png`](assets/2026-11-06-e101-oauth2-install-audit.png) |

### 2.1 浏览器测试抓出并修掉的真实缺陷

- **回调地址表单不生效**：`NDynamicInput` 的默认插槽给出的是**字符串**，不是 `{value}` 对象，
  原写法 `v-model:value="value.value"` 绑定到 `undefined` → 表单永远报「至少一条回调地址」，无法创建。
  已改为自绘行列表（`v-model:value="form.redirect_uris[index]"` + 增删按钮）。**这是浏览器实测才发现的问题**，
  纯 lint/build/单测都不会暴露。
- **安装确认页底色异常**：原用 `var(--n-color)`（组件内变量，页面外无定义）导致卡片变紫、对比度不足；
  已改为与同意页一致的 `NCard` + `--bg-color` 页面底色。

---

## 3. 小蓝侧全链路实测（服务端到服务端，真实后端）

```
1) 发起安装: 95917393-… | approval_path: /oauth2/install/95917393-…
2) 管理员批准 → 回跳带一次性安装码: ins_51b58432… | state: demo-state
3) 小蓝服务端兑换 → client_id: demo-xiaolan-mw4n6x0x | client_secret: ocs_c30524f7… | recovered: false
   下发的 scopes: profile read:tasks | redirect_uris: https://xiaolan.example.com/…/callback
4) 窗口内重放（模拟响应丢失后重试）→ HTTP 200 | recovered: true | 新密钥不同: true
5) 错误 verifier → HTTP 400 {"error":"invalid_verifier","error_description":"verifier 与申请不匹配"}
```

要点：**4 证明「响应丢失 → 同 verifier 重试 → 换发新密钥」的恢复路径可用**；
**5 证明 verifier↔challenge 绑定生效**（仅拿到 code 换不出密钥）。

---

## 4. 安全约束自检（对应契约 §6）

| 约束 | 落地证据 |
|---|---|
| 无长期凭据 | 未新增任何接入方凭据表/端点；OpenTask 只存 `code_challenge`（S256） |
| 密钥零落库明文 | client **在兑换时才创建**，只写哈希；批准阶段不建 client（浏览器步骤 2 已验证列表无 client） |
| `client_secret` 不进浏览器 | 只在兑换响应体（服务端到服务端）；列表/审计接口均不含 |
| 安装码不进日志 | `tests/oauth2/test_install_flow.py::test_logs_do_not_leak_code_or_secret` 断言 caplog 不含 code/secret/verifier |
| consumed ≠ 成功 | `install_already_consumed` 为 409 失败；窗口内恢复返回**新密钥**（`recovered: true`）；响应体不含 `client_secret` 的失败响应被测试断言 |
| verifier↔challenge 绑定 | S256 + `secrets.compare_digest` 恒定时间比较；错 verifier → 400 |
| 单次消费 | 安装码条件更新消费（`WHERE consumed_at IS NULL`），并发双兑被挡 |
| 过期 | 申请 15 分钟 / 安装码 10 分钟 / 恢复窗口 10 分钟（可配） |
| CSRF | 管理 API 用 Bearer 头（非 Cookie 自动附带）→ 跨站不可代发；小蓝侧必须校验 `state`（契约 §7.3 强制项） |
| 开放重定向 | `callback_url` 严格校验（绝对 URL、https、无 userinfo/fragment/控制字符、禁 IP 字面量）+ **主机绑定**（须为某条 redirect_uris 主机或其子域）+ **回跳前二次校验**；回跳响应头 `no-referrer` / `no-store` / `nosniff` |
| SSRF | OpenTask 不对来方任何 URL 发起服务端请求（push 而非 pull）→ 无 SSRF 面 |
| 未认证发起滥用上限 | 全局 pending 100 / 单 IP pending 5 / 单 IP 速率 10 每分钟 / 幂等复用 / 15 分钟存活（均有测试） |
| 权限边界 | 安装批准与审计列表要求 `role == admin`；页面受菜单权限 `menu:manage_oauth2` 门禁（admin 专属，其余系统角色默认无） |
| 成员授权独立 | 安装流不签发任何 token；同意页与 `/oauth2/token` 未改动 |

---

## 5. 已知限制 / 遗留

1. **共享测试库 `opentask_test` 上的 3 条 jira-wire 失败**：与本次改动无关（干净库全绿已证），
   详见 `docs/superpowers/acceptances/2026-11-06-pending-fixes-acceptance.md` 的同类记录。
2. **`pnpm typecheck` 存量错误**：`src/typings/components.d.ts`（生成文件语法）与 `src/typings/api/issue.d.ts`
   在 HEAD 即报错，本次未触碰；本次新增/改动文件 **0 类型错误**。
3. **全仓 lint 存量 153 errors**：未在本次范围内清理（仓内既有）。
4. **未做小蓝侧真实联调**：小蓝侧代码不在本仓，本次只交付协议契约 + OpenTask 侧实现 + 参考实现片段；
   契约 §7.3 列出小蓝侧强制实现清单，联调需双方就绪后再跑。
5. **scope 清单在前端**：`KNOWN_OAUTH_SCOPES`（4 个）镜像自后端 `read_api.py`，前后端各存一份；
   未来 provider 新增 scope 时需同步（前端另有「自定义 scope」输入兜底）。
6. **未部署线上**：本仓只写代码、迁移、测试与文档；未迁移线上库、未推送、未部署。
7. **本地环境副作用**：为浏览器实测在**本地开发库** `opentask` 建了 `e2e_admin` 账号并产生若干测试 client；
   线上环境未做任何变更。

# 待修批次 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 E99 已合并的 `main`（`c1d2424`）上隐藏 Requirement 界面、删除问题集专属代码、统一 OpenTask 品牌、把生产前端从 `/opentask` 改到站点根，并按 Yuri 选定的方式补上零成员用户的第一个工作区。

**Architecture:** Requirement 只做路由守卫和废弃标记，API 与表不动。问题集删除专属路由、服务、ORM、CLI，保留 `issue_collections` 表和历史迁移。品牌只换活跃表面，logo 用现有 PNG。生产 `VITE_BASE_URL=/`，容器与宿主 nginx 按根提供 SPA，后端路径（`/api`、`/ws`、OAuth 协议、`/tasks`）单独反代且不注入 `X-Workspace-Id`。工作区在任务 0 确认方案 C 后，由 `create_admin_user.py` 与前端引导页共同覆盖零成员用户。

**Tech Stack:** Vue 3 + Vite + Vue Router history；FastAPI；nginx；pytest；vitest；`pnpm`。

**Spec:** `docs/superpowers/specs/2026-11-06-pending-fixes-design.md`

## Global Constraints

- 基线 `c1d2424`。不合并、不部署、不 SSH 到 `112.126.60.109`、不 reload 其 nginx。
- 不写入口令，不重置已有管理员口令，不 drop 表，不删业务数据，不新增 Alembic drop revision。
- 不在代理或 nginx 里写死 workspace id，不选其他租户的工作区，不关闭 `require_workspace_context`。
- 保留 `/f/:token`、`/r/:token`。客户与客户需求按钮保留。
- 登录路由保持现有名字 `login` 与路径 `/login/:module(...)?`。生产浏览器地址不得再进入 `/opentask`。
- 本地 Vite 开发代理前缀 `/opentask` 可以留下。生产产物不可以。
- README 放在对应行为落地之后。不编造测试通过数字。
- 本计划入库时不执行下面的业务步骤。任务 0 未通过不得开始任务 1。
- 不做下一 Epic。

---

### Task 0: 停在检查点

**Files:**
- 只读：`docs/superpowers/specs/2026-11-06-pending-fixes-design.md`
- 只读：本文件

- [ ] **Step 1:** 把设计和本计划交给 Yuri。不改 `frontend/`、`backend/`、`deploy/`、`agent-harness/`。
- [ ] **Step 2:** 工作区必须得到 A、B 或 C 的回复。未回复时跳过任务 5。推荐是 C。
- [ ] **Step 3:** 根路径已在用户范围里。Yuri 若否决 notegit 的 `location /` 让位，停在任务 4，不要私自改回 `/opentask`。

### Task 1: 隐藏 Requirement 表面并标记废弃

**Files:**
- Modify: `frontend/src/router/guard/route.ts`
- Modify: `frontend/src/router/__tests__/de-pge-nav.test.ts`
- Modify: `backend/opentask/api/requirement/router.py`（文件顶部 docstring 与 `APIRouter(..., deprecated=True)`）
- Modify: `agent-harness/opentask-cli` 里 requirement 命令的 help 文案（行为不改）
- Test: `frontend/src/router/__tests__/de-pge-nav.test.ts`

**Interfaces:**
- Consumes: 路由名 `workflow_requirements`、`workflow_requirement-detail`、`issue_list`
- Produces: 访问这两个路由名时 `next({ name: 'issue_list' })`，页面组件不挂载

- [ ] **Step 1: 写失败测试**

在 `de-pge-nav.test.ts` 旁新增断言，或在同文件加一个纯函数测试。把重定向收成守卫可单测的函数，避免拉起整站：

```ts
export const REQUIREMENT_ROUTE_NAMES = new Set([
  'workflow_requirements',
  'workflow_requirement-detail'
]);

export function requirementSurfaceRedirect(name: string | symbol | null | undefined) {
  if (typeof name === 'string' && REQUIREMENT_ROUTE_NAMES.has(name)) {
    return { name: 'issue_list' as const };
  }
  return null;
}
```

测试：

```ts
it('redirects legacy requirement routes to the issue list', () => {
  expect(requirementSurfaceRedirect('workflow_requirements')).toEqual({ name: 'issue_list' });
  expect(requirementSurfaceRedirect('workflow_requirement-detail')).toEqual({ name: 'issue_list' });
  expect(requirementSurfaceRedirect('customers')).toBeNull();
  expect(requirementSurfaceRedirect('public-form')).toBeNull();
});
```

- [ ] **Step 2:** `cd frontend && pnpm exec vitest run src/router/__tests__/de-pge-nav.test.ts`  
  Expected: FAIL，函数未定义。
- [ ] **Step 3:** 把函数放进 `route.ts`，在 `beforeEach` 里于鉴权判断之前：若返回值非空则 `next(返回值)`。不要删 Vue 文件，不要改 `/api/requirements` 的处理函数。`APIRouter` 增加 `deprecated=True`。CLI help 加一行「已废弃，API 仍可用」。
- [ ] **Step 4:** 同一 vitest 命令 Expected: PASS。既有「菜单 hideInMenu」断言保持。
- [ ] **Step 5:** Commit `fix: hide legacy requirement screens behind the issue list`

### Task 2: 删除问题集专属代码，保留表

**Files:**
- Delete 页面：`frontend/src/views/issue/collection/`、`frontend/src/views/issue/collection-list/`、`frontend/src/views/issue/collection-create/`
- Delete：`frontend/src/service/api/issue-collection.ts`、`frontend/src/typings/api/issue-collection.d.ts`、`frontend/src/constants/issue-collection.ts`、`frontend/src/components/AgentPromptModal.vue`
- Modify：`frontend/src/service/api/index.ts`、`frontend/src/typings/api/index.d.ts`、`frontend/src/locales/langs/zh-cn.ts`、`en-us.ts`、`frontend/src/router/routes/index.ts`（只删 custom `issue` 下三个 collection 子路由）、`frontend/src/typings/components.d.ts` 里 AgentPromptModal 两项
- Delete 后端：`backend/opentask/services/issue_collection_service.py`、`backend/opentask/models/issue_collection/`、`backend/tests/issue_collection/`
- Modify：`backend/opentask/models/__init__.py`、`backend/opentask/api/issue/router.py`（约 940–1193 行 collection 块）、`backend/tests/api/test_e98_linear_issue_identifiers.py`（文件列表去掉 collection service）
- Delete CLI：`agent-harness/opentask-cli/opentask/core/collection.py`、`tests/test_collection_commands.py`
- Modify CLI：`opentask/opentask_cli.py` 去掉 `collection_cli`；`opentask/utils/api_client.py` 去掉 collection 方法；共享测试里只删 collection 用例
- 不改：`backend/alembic/versions/2026_10_31_1529-003ccd38d5cd_pg_initial_baseline.py`、`backend/migrations/fix_uuid_32_to_36.py`、`generic_status_to_issue_set`、`issue_saved_views`、Issue 列表/详情

**Interfaces:**
- Consumes: 无
- Produces: `GET /api/issues/collections` 为 404；`GET /api/issues` 与 `GET /api/saved-views` 仍按原语义

- [ ] **Step 1: 写失败的 API 测试** `backend/tests/api/test_issue_collection_removed.py`

```python
import pytest

@pytest.mark.asyncio
async def test_collection_routes_gone(test_client, auth_headers):
    response = await test_client.get("/api/issues/collections", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_issue_list_still_listed(test_client, auth_headers):
    response = await test_client.get("/api/issues", headers=auth_headers)
    assert response.status_code == 200
```

`auth_headers` 用仓库里现有注册夹具的名字（打开 `backend/tests/api/test_saved_views.py` 抄它的 header 构造）。不要新写一套登录。

- [ ] **Step 2:** `cd backend && uv run pytest tests/api/test_issue_collection_removed.py -v`  
  Expected: FAIL，collections 仍是 200。
- [ ] **Step 3:** 删除上面的专属文件与 router 块。`models/__init__.py` 去掉 `IssueCollection` 导入，并留下注释：表 `issue_collections` 由 baseline `003ccd38d5cd` 创建，本批不 drop、不删行。跑 `cd frontend && pnpm gen-route`。从 e98 测试的文件列表去掉 `services/issue_collection_service.py`，其余三个文件的 `resolve_workspace_for_issue_create` 断言保留。
- [ ] **Step 4:** 重跑该 pytest Expected: PASS。再跑 `uv run pytest tests/api/test_e98_linear_issue_identifiers.py tests/api/test_saved_views.py -v` Expected: PASS。
- [ ] **Step 5:** `cd backend && uv run python scripts/export_openapi.py`。确认 `openapi.json` 不再含 `/api/issues/collections`。
- [ ] **Step 6:** Commit `fix: remove issue collection UI API and CLI`

### Task 3: 活跃表面改用现有 OpenTask 标

**Files:**
- Modify: `frontend/index.html`（只留 `favicon.png`）
- Delete: `frontend/public/favicon.svg`（笑脸，不是现有 logo）
- Modify: `frontend/src/router/guard/title.ts`、`frontend/src/store/modules/app/index.ts`
- Modify: `frontend/src/plugins/loading.ts`（启动屏改为 `<img src="/opentask-logo.png" alt="OpenTask">`，删掉 `getLogoSvg`）
- Modify: `frontend/src/theme/preset/default.json`、`dark.json` 的 watermark `text`；`watermark-settings.vue` 的 placeholder
- Modify: `frontend/src/views/home/modules/header-banner.vue`、`project-news.vue`、`frontend/src/layouts/modules/global-footer/index.vue`、对应 soybean 文案的 locale
- 不改：`package.json` 的包名、`presetSoybeanAdmin`、`SystemLogo` 已引用的 `src/assets/imgs/opentask-logo.png`

- [ ] **Step 1: 写失败测试** `frontend/src/router/guard/title.test.ts`

```ts
import { formatDocumentTitle } from './title';

it('keeps OpenTask in the document title', () => {
  expect(formatDocumentTitle('问题', 'OpenTask')).toBe('问题 - OpenTask');
  expect(formatDocumentTitle('OpenTask', 'OpenTask')).toBe('OpenTask');
});
```

- [ ] **Step 2:** vitest 该文件 Expected: FAIL。
- [ ] **Step 3:** 抽出 `formatDocumentTitle`，两处 `useTitle` 改为 `useTitle(formatDocumentTitle(页面标题, $t('system.title')))`。其余品牌文件按列表改，不新画图。
- [ ] **Step 4:** vitest Expected: PASS。
- [ ] **Step 5:** Commit `fix: use the existing OpenTask mark on active surfaces`

### Task 4: 生产改到站点根，登录仍是 `/login`

**Files:**
- Modify: `frontend/Dockerfile`、`frontend/Dockerfile.dist`、`frontend/nginx.conf`
- Modify: `frontend/src/utils/attachmentUrls.ts`、`frontend/src/utils/attachmentUrls.test.ts`
- Modify: `deploy/nginx/opentask-locations.conf`、`deploy/deploy.sh`（只改检查与注释；本任务不执行该脚本）
- Modify: `frontend/src/router/__tests__/login-path.test.ts`（新建）
- 不改：`frontend/src/router/elegant/routes.ts` 的 login 路径；`createProxyPattern()` 的开发前缀；后端路由前缀

**Interfaces:**
- Consumes: 路由名 `login`、`root`；`VITE_ROUTE_HOME=issue_list`
- Produces: 生产 history base `/`；容器对 `/login` 回 index.html；宿主 `/api/`、`/ws/` 原样到 7377；`/oauth2/authorize` 到前端 8080

- [ ] **Step 1: 写失败测试**

`frontend/src/utils/attachmentUrls.test.ts` 增加：当 `apiBase` 为 `/` 时，`/api/attachments/signed/tok` 保持该路径，不以 `/opentask` 开头。把函数改成 `toBrowserAttachmentUrl(apiPath, apiBase)`，第二个参数默认取当前服务基址，测试显式传入。

`frontend/src/router/__tests__/login-path.test.ts`：

```ts
import { generatedRoutes } from '../elegant/routes';

function findRoute(routes: any[], name: string): any | undefined {
  for (const r of routes) {
    if (r.name === name) return r;
    if (r.children) {
      const hit = findRoute(r.children, name);
      if (hit) return hit;
    }
  }
  return undefined;
}

it('matches /login with an optional module', () => {
  const login = findRoute(generatedRoutes as any[], 'login');
  expect(login.path.startsWith('/login')).toBe(true);
  expect(login.meta?.constant).toBe(true);
  expect(login.path).not.toContain('opentask');
});
```

- [ ] **Step 2:** vitest 这两个文件 Expected: 附件用例 FAIL（现实现总是加 `/opentask`）；登录用例 PASS（路由已经是 `/login`，用来锁住回归）。
- [ ] **Step 3: 改构建与容器 nginx**

`Dockerfile` 与 `Dockerfile.dist`：

```dockerfile
ARG VITE_BASE_URL=/
ARG VITE_SERVICE_BASE_URL=/
# dist 拷到 /usr/share/nginx/html/ 而不是 .../opentask
HEALTHCHECK CMD wget -qO- http://127.0.0.1/login >/dev/null || exit 1
```

`frontend/nginx.conf` 的 server 改为根：

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    client_max_body_size 64m;
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $backend_host backend;

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
        access_log off;
    }

    location /api/ {
        proxy_pass http://$backend_host:7377;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }

    location /ws/ {
        proxy_pass http://$backend_host:7377;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }
}
```

不要加 `return 301 /opentask`。不要设置 `X-Workspace-Id`。

- [ ] **Step 4: 宿主片段**

删除 `location = /opentask` 与 `location /opentask/`。保留 `/tasks/`、`/capabilities`、`/healthcheck`。增加：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:7377;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 300s;
}

location /ws/ {
    proxy_pass http://127.0.0.1:7377;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 300s;
}

location = /oauth2/authorize {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
}

location /oauth2/ {
    proxy_pass http://127.0.0.1:7377;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_read_timeout 300s;
}
```

片段头部写明：`sites-available/notegit` 里现有 `location /` 若仍 `proxy_pass` 到 `127.0.0.1:3000`，则 `/` 与 `/login` 仍是 notegit。要让 OpenTask 占据根，把该 `proxy_pass` 改为 `http://127.0.0.1:8080`。本文件不包含第二个 `location /`。回滚是指回 `3000` 并恢复旧片段。

`deploy/deploy.sh` 的检查改为：

```bash
for kv in "VITE_BASE_URL=/" "VITE_SERVICE_BASE_URL=/"; do
```

产物自检：`index.html` 含 `/assets/`，且 `grep` 不到 `/opentask/assets/`。不要在本任务运行 `deploy.sh`。

- [ ] **Step 5: 本地冒烟**  
  用含新 `nginx.conf` 与一份最小 `index.html` 的 nginx 容器（不必等完整前端构建）请求 `/`、`/login`、`/issue/list`、`/f/sample-token`。Expected: 200，正文为 `index.html`，响应不是 301 到 `/opentask`。不要 curl `112.126.60.109`。
- [ ] **Step 6:** vitest 附件与登录路径 Expected: PASS。
- [ ] **Step 7:** Commit `fix: serve the SPA at the site root`

### Task 5: 零成员用户的第一个工作区（仅当 Yuri 选择包含的那一半）

方案 C 时做 5a 和 5b。只选 A 则只做 5a。只选 B 则只做 5b。都要做 5c 里与所选一半对应的隔离断言。

**Files:**
- Modify: `backend/opentask/services/workspace/service.py`
- Modify: `backend/scripts/create_admin_user.py`
- Modify: `backend/tests/scripts/test_create_admin_user.py`
- Create: `backend/tests/api/test_ensure_owner_workspace.py`
- Create: `frontend/src/store/modules/auth/workspace-selection.ts`
- Modify: `frontend/src/store/modules/auth/index.ts`（`loginByToken` 与 `initUserInfo` 都走解析）
- Create: `frontend/src/views/_builtin/workspace-onboarding/index.vue`（仅方案含 B/C）
- Modify: `frontend/src/service/request/index.ts` 的测试，锁住无 id 时不加头

**Interfaces:**
- `ensure_owner_workspace(user_id: str, name: str) -> Workspace`：该用户已有任一 `WorkspaceMember` 时返回其中 `created_at` 最早的工作区且不插入；否则 `create_for_owner(name=name, owner_user_id=user_id)`。不读别的用户的工作区，不使用 `DEFAULT_WORKSPACE_ID`。
- `resolveWorkspaceSelection(storedId: string | null, memberships: {id: string}[])`：空列表返回 `{ kind: 'onboarding' }`；`storedId` 在列表中返回 `{ kind: 'selected', id: storedId }`；否则 `{ kind: 'selected', id: memberships[0].id }`。

- [ ] **Step 1: 后端失败测试**

```python
@pytest.mark.asyncio
async def test_ensure_owner_workspace_creates_once(session, user_without_workspace):
    svc = WorkspaceService(session)
    first = await svc.ensure_owner_workspace(user_without_workspace.id, "OpenTask")
    second = await svc.ensure_owner_workspace(user_without_workspace.id, "OpenTask")
    assert first.id == second.id
    assert first.id != DEFAULT_WORKSPACE_ID
    members = await svc.list_members(first.id, user_without_workspace.id)
    assert members[0].role == "owner"

@pytest.mark.asyncio
async def test_ensure_does_not_join_another_users_workspace(session, user_a, user_b):
    svc = WorkspaceService(session)
    foreign = await svc.ensure_owner_workspace(user_a.id, "A")
    own = await svc.ensure_owner_workspace(user_b.id, "B")
    assert own.id != foreign.id
```

夹具沿用 `backend/tests/api/conftest.py` 的 session。同一个测试文件里定义 `user_without_workspace`：插入 `UserModel`（`role="admin"`、`status=1`、带 bcrypt 哈希），不调用 `AuthService.register`，不插入 `WorkspaceMember`。`user_a` / `user_b` 同样各插一行用户。

CLI 单测：`build_parser().parse_args([]).workspace_name == "OpenTask"` 且 `skip_workspace is False`。`--reset-password` 默认仍为 False。

- [ ] **Step 2:** pytest 该文件 Expected: FAIL，方法不存在。
- [ ] **Step 3:** 实现方法。`create_admin` 在提交前调用它，除非 `--skip-workspace`。账号已存在且未 `--reset-password` 时仍不得改 `password_hash`，但零成员时要补工作区。不打印新口令，除非本次确实生成并写入了新口令（保持脚本现有分支）。
- [ ] **Step 4:** pytest Expected: PASS。

- [ ] **Step 5: 前端失败测试**（方案含引导时）

```ts
import { resolveWorkspaceSelection } from './workspace-selection';

it('does not invent an id when the list is empty', () => {
  expect(resolveWorkspaceSelection(null, [])).toEqual({ kind: 'onboarding' });
});

it('keeps a stored id that is still a membership', () => {
  const rows = [{ id: 'a' }, { id: 'b' }];
  expect(resolveWorkspaceSelection('b', rows)).toEqual({ kind: 'selected', id: 'b' });
});

it('replaces a stale id with the first membership only', () => {
  const rows = [{ id: 'a' }, { id: 'b' }];
  expect(resolveWorkspaceSelection('foreign', rows)).toEqual({ kind: 'selected', id: 'a' });
});
```

- [ ] **Step 6:** vitest Expected: FAIL。
- [ ] **Step 7:** 实现纯函数。`ensureWorkspace` 改为：onboarding 时不写 `localStorage`，并让路由守卫把非常量、非公开 `/f` `/r` `/invite` 的页面送到引导页。引导页只调用现成 `POST /api/workspaces`，把响应 `id` 写入本地后进入 `issue_list`。预填名称 `OpenTask`，允许改。`initUserInfo` 在 token 有效时也走同一解析。
- [ ] **Step 8:** 拦截器测试：`workspaceId` 为空时请求头没有 `X-Workspace-Id`；有值时才有。Expected: PASS。
- [ ] **Step 9:** Commit `fix: create the first workspace for a memberless admin`

### Task 6: README 按落地后的行为改

**Files:**
- Modify: `README.md`、`frontend/README.md`、`frontend/AGENTS.md`（webpack 改为 Vite，端口 9527）、`backend/README.md`、`deploy/README.md`、`agent-harness/opentask-cli/README.md`

- [ ] **Step 1:** 对照当时代码改。根 README 的 CLI 写成 Python。Issue 示例用 `KEY-N`，删掉 `REQ-20260213-001` 这种主标识。Node 写成 `>=20.19.0`。PostgreSQL 写成 compose 里的 `postgres:15-alpine`，并注明后端 README 曾写 16、本批不改镜像。
- [ ] **Step 2:** `frontend/README.md` 换成 OpenTask：`pnpm install`、`pnpm dev`（端口 9527）、`pnpm lint`、`pnpm build`、`pnpm test`。生产基址 `/`，API 为同源 `/api`。删掉 soybean 克隆地址。
- [ ] **Step 3:** `deploy/README.md` 拓扑改为根路径；写明 notegit `location /` 必须改到 `8080` 后 `/login` 才生效；写明本仓库的发布没有自动执行。删掉「后端没有注册接口」。初始管理员一节按任务 5 的实际参数写；若 Yuri 没选脚本引导，就写引导页，不要两套都写成已经发生。
- [ ] **Step 4:** CLI README 去掉 `collection`。`requirement` 标废弃仍可用。不要写未跑过的 pytest 计数。
- [ ] **Step 5:** `backend/README.md` 去掉 `AUTH_USERNAME` / `AUTH_PASSWORD` 示例。启动命令保持 `uv run uvicorn opentask.main:app --port=7377 --host=0.0.0.0`。测试命令保持 `uv run pytest tests/ -v`。
- [ ] **Step 6:** Commit `docs: align READMEs with root deploy and retired surfaces`

### Task 7: 验证、验收、发布说明，然后停止

- [ ] **Step 1:** `cd backend && uv run pytest tests/ -v`。把真实计数写入验收，失败就先修再记。
- [ ] **Step 2:** `cd frontend && pnpm lint && pnpm build && pnpm test`。lint 0 error。build 成功。`.env.prod` 若缺失，从 `.env.example` 复制到本地且不入库，但生产前缀断言以 Dockerfile ARG `/` 为准，不依赖那份被 gitignore 的文件把前缀改回去。
- [ ] **Step 3:** CLI：`cd agent-harness/opentask-cli && uv run pytest -q`。`scripts/e14_cli_smoke.sh` 需要本机 7377 时，没起服务就记成未跑，不要写成通过。
- [ ] **Step 4:** 浏览器走 Issue 列表、登录、客户页、确认没有问题集和需求菜单。根路径冒烟用本地 nginx，记录 URL 与状态码。这两类证据分开写。
- [ ] **Step 5:** 写 `docs/superpowers/acceptances/2026-11-06-pending-fixes-acceptance.md`，含发布说明：改了哪些镜像与 nginx 片段、notegit `location /` 要人改成 `127.0.0.1:8080`、未对 `112.126.60.109` 执行 reload、旧 `/opentask` 书签不再可用。
- [ ] **Step 6:** 停止。不打开下一 Epic，不合并，不部署。

## Self-review

- Spec 第 1–2 节各条都有任务：Requirement→1，问题集→2，品牌→3，根路径→4，工作区→5，README→6，验证→7。
- 工作区方案未选定的部分由任务 0 跳过，步骤里没有「以后再填」的接口名。
- `ensure_owner_workspace` 与 `resolveWorkspaceSelection` 在任务 5 的测试和实现里同名。
- 登录路径测试锁的是已有 `/login`，不是新路由。

# 界面壳层、菜单语义与美化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让客户、需求和举措从菜单进入已有列表，并让菜单、标题、标签、面包屑和页面标题使用同一套文案；再用现有令牌收齐壳层和主要页面。

**Architecture:** custom 路由覆盖生成路由，把已经导入的列表视图挂成默认子路由，详情只做带 id 的深链。缺的文案键补进中英文。面包屑在菜单找不到路由时回落到路由元信息。视觉只扩展 `design-tokens.css` 和壳层样式，不新增主题包。

**Tech Stack:** Vue 3、vue-router、vue-i18n、Naive UI、Vitest、现有 `--vk-*` 令牌。

## Global Constraints

- 基线是 `main` @ `f2f81c51fda85bf48221d7f84a2f56d071e7704e`。不要往已合并的 PR #4 上追加。
- 不合并、不部署、不连接现网，不写入口令。
- 生产基址保持 `/`。浏览器标题继续带 OpenTask。继续用现有 OT 图。
- Requirement 页面保持隐藏，接口和表保留。客户详情里的「新建需求」保留。
- 问题集专属代码保持删除。物理表和数据不删。
- `/f`、`/r`、`/invite` 保持可直接打开。空工作区引导、退出和 `ensure-owner` 不改语义。
- 不重置口令，不加删除数据的迁移，不放宽租户隔离。
- nginx 继续只代理精确的 `/ws/workspace`，不要改回 `/ws/`。
- 不单独手跑 `gen-route` 再改生成文件。`pnpm build` 会重跑代码生成；构建后要再确认 `/f`、`/r` 和列表注入。不要把 `customers_list` 写进生成的 `RouteKey`。
- 不新增主题包，不改 `themeColor` `#5e6ad2`，不生成新图。
- 不改弹窗关闭方式、toast 行为，也不为了变窄藏起新建、导出、导入或保存。
- 术语以设计文档第 0 节和第 4 节为准。下文的示例如果和第 0 节冲突，以第 0 节为准。

## Yuri 修正后的做法

检查点 `5028d2c` 已批准。下面这些示例作废：

- 路由测试只断言 `customRoute.children`。要创建真实路由器，断言默认重定向一次结束、父路由进入列表、带 id 的深链不变、无 id 详情只到列表一次、举措高亮是一个叶子。
- 空路径如果被变换器丢掉或造成循环，就改成能停住的最短路径并写明原因。本次真实路由器接受 `path: ''`，采用它。注入点是 `createStaticRoutes`，不是手改 `elegant-router.d.ts`。`activeMenu` 用父路由名。
- 无 id 详情如果等页面 `load` 再 `replace`，标签页已经记下详情。替换放在路由守卫里、路由确认之前，真实路由器的 `afterEach` 只看到列表。带 id 的详情不被替换。
- `breadcrumbFallback` 只返回 `{ key, label }`。改为现有面包屑形状，非当前项可点击，文案随语言变，隐藏的管理路由不出现，未登记键名不出现。
- 用 `min-height` 加 `max-height: 40` 卡单元格。单行靠内边距落到 32–40，不设会裁切的最大高度。换行标题允许更高。
- 只断言样式文件里有媒体查询、没有某段注释。窄屏以编译后的 375 / 768 / 1280 为准，主要按钮不能被裁掉。
- 给每个页面加 `ot-page`，或把 `bordered={false}` 写进 Vue 模板。对话框、抽屉和空状态用现有令牌做出可见表面。登录和引导只改外观。
- UI-4 在范围内，但不新增客户或需求功能。

---

### Task 1: 补齐会露出键名的文案

**Files:**
- Modify: `frontend/src/locales/langs/zh-cn.ts`（`route` 对象，约第 244 行起）
- Modify: `frontend/src/locales/langs/en-us.ts`（`route` 对象，约第 248 行起）
- Modify: `frontend/src/typings/app.d.ts`（`App.I18n.Schema` 的 `page`，约第 504 行。`route` 已是 `Record<I18nRouteKey, string>`，补上对象里缺的键即可）
- Test: `frontend/src/locales/__tests__/route-labels.test.ts`

**Interfaces:**
- Consumes: 设计文档第 4 节术语表
- Produces: `route.customers`、`route.customers_detail`、`route.requests`、`route.requests_detail`、`route.settings_sla`，以及更新后的 `route.initiatives`、`route.initiatives_detail`、`route.workspace_cycles`、`route.workspace_members`、`route.settings_recurrences`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import zh from '../langs/zh-cn';
import en from '../langs/en-us';

const keys = [
  'customers',
  'customers_detail',
  'requests',
  'requests_detail',
  'settings_sla',
  'initiatives',
  'initiatives_detail',
  'workspace_cycles',
  'workspace_members',
  'settings_recurrences'
] as const;

describe('route labels', () => {
  it.each(keys)('%s exists in zh-CN and en-US and is not the raw key', key => {
    const zhValue = zh.route[key];
    const enValue = en.route[key];
    expect(zhValue).toBeTruthy();
    expect(enValue).toBeTruthy();
    expect(zhValue).not.toBe(`route.${key}`);
    expect(enValue).not.toBe(`route.${key}`);
  });

  it('separates iteration cycles from recurring issue creation', () => {
    expect(zh.route.workspace_cycles).toBe('冲刺');
    expect(zh.route.settings_recurrences).toBe('周期建单');
    expect(en.route.workspace_cycles).toBe('Cycles');
    expect(en.route.settings_recurrences).toBe('Recurring issues');
    expect(zh.route.settings_sla).toBe('SLA 策略');
    expect(en.route.settings_sla).toBe('SLA');
    expect(zh.route.workspace_members).toBe('成员');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run src/locales/__tests__/route-labels.test.ts`  
Expected: FAIL because `zh.route.customers` and `route.settings_sla` are missing.

- [ ] **Step 3: Write minimal implementation**

在两个 `route` 对象加入或改成：

```ts
customers: '客户',
customers_detail: '客户详情',
requests: '需求',
requests_detail: '需求详情',
settings_sla: 'SLA 策略',
initiatives: '举措',
initiatives_detail: '举措详情',
workspace_cycles: '冲刺',
workspace_members: '成员',
settings_recurrences: '周期建单',
```

英文对应：`Customers`、`Customer`、`Requests`、`Request`、`SLA`、`Initiatives`、`Initiative`、`Cycles`、`Members`、`Recurring issues`。

快捷入口用的副文案加在 `page.sider`：

```ts
sider: {
  triage: '分诊',
  triageHint: '入站',
  customers: '客户',
  customersHint: '需求',
  insights: '洞察',
  insightsHint: '效能',
  activity: '活动',
  activityHint: '动态'
}
```

英文：`Triage` / `Incoming`，`Customers` / `Requests`，`Insights` / `Performance`，`Activity` / `Recent`。中文活动提示是「动态」，不再用 Feed。

`App.I18n.Schema` 的 `page` 要加上 `sider` 这八个字段，否则 `const local: App.I18n.Schema` 不能通过。`route` 不用改类型；缺的键直接补进两个语言文件。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run src/locales/__tests__/route-labels.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts frontend/src/locales/__tests__/route-labels.test.ts
git commit -m "fix: name the sla, customer, and initiative menus"
```

### Task 2: 把已有列表挂成默认页

**Files:**
- Modify: `frontend/src/router/routes/index.ts`（`customRoutes` 数组）
- Modify: `frontend/src/typings/elegant-router.d.ts`（仅当类型检查要求新路由名）
- Modify: `frontend/src/views/initiatives/detail/index.vue`（约第 195–199 行）
- Modify: `frontend/src/views/customers/detail/index.vue`（`load` 与模板标题）
- Modify: `frontend/src/views/requests/detail/index.vue`（无 id 时离开详情）
- Test: `frontend/src/router/__tests__/menu-entry.test.ts`

**Interfaces:**
- Consumes: `view.customers`、`view.requests`、`view.initiatives` 以及对应的 `*_detail` 视图键
- Produces: 路由名 `customers_list`、`requests_list`、`initiatives_list`。详情路径不变。

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import { createStaticRoutes } from '../routes';

function findRoute(routes: any[], name: string): any | undefined {
  for (const route of routes) {
    if (route.name === name) return route;
    if (route.children) {
      const hit = findRoute(route.children, name);
      if (hit) return hit;
    }
  }
  return undefined;
}

describe('menu entries open existing lists', () => {
  const { authRoutes } = createStaticRoutes();

  it.each([
    ['customers', 'customers_list', 'view.customers', 'customers_detail', '/customers/detail'],
    ['requests', 'requests_list', 'view.requests', 'requests_detail', '/requests/detail'],
    ['initiatives', 'initiatives_list', 'view.initiatives', 'initiatives_detail', '/initiatives/detail']
  ])('%s defaults to its list and keeps the detail path', (parent, list, view, detail, detailPath) => {
    const group = findRoute(authRoutes as any[], parent);
    expect(group.children[0].name).toBe(list);
    expect(group.children[0].component).toBe(view);
    expect(group.children[0].path).toBe('');
    const detailRoute = findRoute(group.children, detail);
    expect(detailRoute.path).toBe(detailPath);
    expect(detailRoute.meta.hideInMenu).toBe(true);
    expect(detailRoute.meta.activeMenu).toBe(list);
  });

  it('shows initiatives as one leaf, not a detail child', () => {
    const group = findRoute(authRoutes as any[], 'initiatives');
    expect(group.meta.hideInMenu).toBeFalsy();
    expect(group.children.every((child: any) => child.meta?.hideInMenu === true)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run src/router/__tests__/menu-entry.test.ts`  
Expected: FAIL because the first child is `customers_detail` / `initiatives_detail`.

- [ ] **Step 3: Write minimal implementation**

在 `customRoutes` 增加三段。客户和需求的父级 `hideInMenu: true`。举措父级不隐藏。列表必须是 `children` 的第一项。

```ts
{
  name: 'customers',
  path: '/customers',
  component: 'layout.base',
  meta: {
    title: 'customers',
    i18nKey: 'route.customers',
    icon: 'mdi:account-group-outline',
    order: 3.5,
    hideInMenu: true
  },
  children: [
    {
      name: 'customers_list',
      path: '',
      component: 'view.customers',
      meta: { title: 'customers', i18nKey: 'route.customers', hideInMenu: true }
    },
    {
      name: 'customers_detail',
      path: '/customers/detail',
      component: 'view.customers_detail',
      meta: {
        title: 'customers_detail',
        i18nKey: 'route.customers_detail',
        hideInMenu: true,
        activeMenu: 'customers'
      }
    }
  ]
}
```

`requests` 与 `initiatives` 按同样的形状写，但实现放在 `createStaticRoutes` 的注入函数里，以便生成文件被生产构建覆盖后仍然生效。`requests` 父级保持 `hideInMenu: true`。`initiatives` 父级不设置 `hideInMenu`。详情 `activeMenu` 分别是 `requests` 和 `initiatives`。

无 id 时替换到列表名，而不是父路由名：

```ts
if (!id.value) {
  window.$message?.warning('缺少 Initiative id');
  router.replace({ name: 'initiatives_list' });
  return;
}
```

客户详情和需求详情在没有 id 时同样 `router.replace` 到 `customers_list` 或 `requests_list`，不渲染空表单。已有 id 的加载、保存和「新建需求」不动。

不要把三个新名字加进生成的 `RouteKey`。列表的 `i18nKey` 仍用 `route.customers`、`route.requests`、`route.initiatives`。生产构建之后再跑路由测试和公开路由测试。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run src/router/__tests__/menu-entry.test.ts src/router/__tests__/e13-linear-nav.test.ts src/router/guard/__tests__/surface.test.ts src/router/routes/__tests__/public-routes.test.ts`  
Expected: PASS。Requirement 仍隐藏，`/f` 和 `/r` 仍在。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router/routes/index.ts frontend/src/typings/elegant-router.d.ts frontend/src/views/customers/detail/index.vue frontend/src/views/requests/detail/index.vue frontend/src/views/initiatives/detail/index.vue frontend/src/router/__tests__/menu-entry.test.ts
git commit -m "fix: open customer and initiative lists from the menu"
```

### Task 3: 快捷入口和面包屑使用同一套文案

**Files:**
- Modify: `frontend/src/layouts/modules/global-sider/TriageNav.vue`
- Modify: `frontend/src/layouts/modules/global-sider/CustomersNav.vue`
- Modify: `frontend/src/layouts/modules/global-sider/InsightsNav.vue`
- Modify: `frontend/src/layouts/modules/global-sider/ActivityNav.vue`
- Modify: `frontend/src/store/modules/route/shared.ts`（`getBreadcrumbsByRoute` 的调用侧见下一步）
- Modify: `frontend/src/store/modules/route/index.ts`（约第 131 行）
- Test: `frontend/src/store/modules/route/__tests__/breadcrumb-fallback.test.ts`

**Interfaces:**
- Consumes: `page.sider.*`、`route.customers_detail`、`activeMenu`
- Produces: `breadcrumbFallback(route, labelOf)`，返回 `{ key: string; label: string }[]`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import { breadcrumbFallback } from '../shared';

describe('breadcrumbFallback', () => {
  const labelOf = (key: string) =>
    ({
      'route.customers': '客户',
      'route.customers_detail': '客户详情',
      'route.settings_sla': 'SLA 策略'
    })[key] ?? key;

  it('uses the route label when the page is not in the menu', () => {
    const items = breadcrumbFallback(
      { name: 'customers_detail', meta: { i18nKey: 'route.customers_detail', activeMenu: 'customers_list' } },
      labelOf,
      { name: 'customers_list', i18nKey: 'route.customers' }
    );
    expect(items.map(item => item.label)).toEqual(['客户', '客户详情']);
  });

  it('does not return a raw key', () => {
    const items = breadcrumbFallback(
      { name: 'settings_sla', meta: { i18nKey: 'route.settings_sla', title: 'settings_sla' } },
      labelOf,
      null
    );
    expect(items[0].label).toBe('SLA 策略');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run src/store/modules/route/__tests__/breadcrumb-fallback.test.ts`  
Expected: FAIL with `breadcrumbFallback` not exported.

- [ ] **Step 3: Write minimal implementation**

```ts
export function breadcrumbFallback(
  route: { name?: string | symbol | null; meta?: { i18nKey?: string; title?: string; activeMenu?: string } },
  labelOf: (i18nKey: string) => string,
  parent: { name?: string; i18nKey?: string } | null
) {
  const ownKey = route.meta?.i18nKey;
  const own = ownKey ? labelOf(ownKey) : '';
  const items = [];
  if (parent?.i18nKey && route.meta?.activeMenu && parent.name === route.meta.activeMenu) {
    items.push({ key: parent.name, label: labelOf(parent.i18nKey) });
  }
  if (own) items.push({ key: String(route.name ?? ''), label: own });
  return items;
}
```

`route/index.ts` 的 `breadcrumbs` 改为：菜单结果非空就用菜单结果；否则调用 `breadcrumbFallback`。父路由从 `authRoutes` 里按 `activeMenu` 查找。`labelOf` 使用 `$t`。

四个快捷入口的可见文字改为 `$t('page.sider.*')`。悬停背景改为 `var(--vk-accent-soft)`，副文案颜色改为 `var(--vk-muted)`，删除 `opacity: 0.55`。点击目标不变：客户仍推 `customers`，由 Task 2 的重定向进入列表。

页面里的 `h2` 改为 `$t`：客户列表 `route.customers`，客户详情 `route.customers_detail`，举措列表 `route.initiatives`，举措详情 `route.initiatives_detail`，SLA 卡片 `route.settings_sla`。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run src/store/modules/route/__tests__/breadcrumb-fallback.test.ts src/utils/__tests__/document-title.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/layouts/modules/global-sider frontend/src/store/modules/route frontend/src/views/customers frontend/src/views/initiatives frontend/src/views/settings/sla/index.vue
git commit -m "fix: use translated labels for menus and breadcrumbs"
```

### Task 4: 壳层密度、焦点和减少动效

**Files:**
- Modify: `frontend/src/styles/design-tokens.css`
- Modify: `frontend/src/styles/css/global.css`
- Modify: `frontend/src/layouts/modules/global-sider/index.vue`
- Modify: `frontend/src/views/_builtin/login/index.vue`
- Modify: `frontend/src/views/_builtin/workspace-onboarding/index.vue`
- Test: `frontend/src/styles/__tests__/shell-tokens.test.ts`

**Interfaces:**
- Consumes: 现有 `--vk-accent`、`--vk-bg`、`--vk-line`、`--vk-muted`
- Produces: `--vk-font-ui`、`--vk-control-height`、`--vk-row-min`、`--vk-row-max`

- [ ] **Step 1: Write the failing test**

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const tokens = readFileSync(new URL('../design-tokens.css', import.meta.url), 'utf8');
const globalCss = readFileSync(new URL('../css/global.css', import.meta.url), 'utf8');

describe('shell tokens', () => {
  it('adds the 13px ui size and 32px control without a second accent', () => {
    expect(tokens).toContain('--vk-font-ui: 13px;');
    expect(tokens).toContain('--vk-control-height: 32px;');
    expect(tokens).toContain('--vk-row-min: 32px;');
    expect(tokens).toContain('--vk-row-max: 40px;');
    expect(tokens).toContain('--vk-accent: #5e6ad2;');
  });

  it('keeps a dark replacement and honors reduced motion', () => {
    expect(tokens).toContain('html.dark');
    expect(globalCss).toContain('prefers-reduced-motion: reduce');
    expect(globalCss).toContain(':focus-visible');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run src/styles/__tests__/shell-tokens.test.ts`  
Expected: FAIL because `--vk-font-ui` is absent.

- [ ] **Step 3: Write minimal implementation**

在 `design-tokens.css` 的 `:root` 增加：

```css
--vk-font-ui: 13px;
--vk-control-height: 32px;
--vk-row-min: 32px;
--vk-row-max: 40px;
```

不要改已有的 `--vk-accent`。`global.css` 增加：

```css
:focus-visible {
  outline: 2px solid var(--vk-accent);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

侧栏容器去掉额外投影，保留 `border-right: 1px solid var(--vk-line)`，宽度不改 `themeSettings.sider.width`。登录和引导页的主按钮高度使用 `var(--vk-control-height)`，标题继续走 `formatDocumentTitle`。不改提交逻辑和退出逻辑。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run src/styles/__tests__/shell-tokens.test.ts src/utils/__tests__/document-title.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/design-tokens.css frontend/src/styles/css/global.css frontend/src/layouts/modules/global-sider/index.vue frontend/src/views/_builtin/login/index.vue frontend/src/views/_builtin/workspace-onboarding/index.vue frontend/src/styles/__tests__/shell-tokens.test.ts
git commit -m "feat: tighten the shell tokens and focus ring"
```

### Task 5: 问题列表密度

**Files:**
- Modify: `frontend/src/views/issue/list/index.vue`（根 `.issue-list-container` 和行高样式）
- Test: `frontend/src/views/issue/list/__tests__/density.test.ts`

**Interfaces:**
- Consumes: `--vk-row-min`、`--vk-row-max`、`--vk-font-body`
- Produces: 列表行高落在 32–40px 的样式约定

- [ ] **Step 1: Write the failing test**

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

describe('issue list density', () => {
  it('uses the shared row tokens', () => {
    const source = readFileSync(new URL('../index.vue', import.meta.url), 'utf8');
    expect(source).toContain('min-height: var(--vk-row-min)');
    expect(source).toContain('max-height: var(--vk-row-max)');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run src/views/issue/list/__tests__/density.test.ts`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

问题行不设置 `max-height`。单行靠内边距和行高落到大约 32–40，标题允许换行后变高。这个高度在编译后的页面上测量，不靠源码包含某段 CSS。保留导出、导入、新建、筛选和保存视图的点击处理。可见的「Export」「Import」「新建 Issue」改成当前语言的「导出」「导入」「新建问题」。不改请求参数。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run src/views/issue/list/__tests__/density.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/issue/list/index.vue frontend/src/views/issue/list/__tests__/density.test.ts frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts
git commit -m "feat: use the shared row height on the issue list"
```

### Task 6: 共享表面和其余主页面

**Files:**
- Modify: `frontend/src/views/issue/detail/index.vue`
- Modify: `frontend/src/views/workflow/projects/index.vue`
- Modify: `frontend/src/views/workflow/project-detail/index.vue`
- Modify: `frontend/src/views/customers/index.vue`
- Modify: `frontend/src/views/customers/detail/index.vue`
- Modify: `frontend/src/views/requests/index.vue`
- Modify: `frontend/src/views/requests/detail/index.vue`
- Modify: `frontend/src/views/initiatives/index.vue`
- Modify: `frontend/src/views/initiatives/detail/index.vue`
- Modify: `frontend/src/views/settings/sla/index.vue`
- Modify: `frontend/src/views/settings/notifications/index.vue`
- Modify: `frontend/src/views/settings/webhooks/index.vue`
- Modify: `frontend/src/views/settings/forms/index.vue`
- Modify: `frontend/src/views/settings/recurrences/index.vue`
- Test: `frontend/src/styles/__tests__/page-surface.test.ts`

**Interfaces:**
- Consumes: `--vk-line`、`--vk-paper`、`--space-lg`
- Produces: 对话框、抽屉和空状态使用现有纸面、分隔线和次要文字色。不给列出的每个页面根节点加 `ot-page`，也不把卡片改成 JSX 的 `bordered={false}`。

- [ ] **Step 1: Write the failing test**

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const pages = [
  '../../views/issue/detail/index.vue',
  '../../views/workflow/projects/index.vue',
  '../../views/customers/index.vue',
  '../../views/initiatives/index.vue',
  '../../views/settings/sla/index.vue'
];

describe('page surface', () => {
  it.each(pages)('%s uses ot-page', file => {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8');
    expect(source).toContain('ot-page');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run src/styles/__tests__/page-surface.test.ts`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

在 `design-system.css` 增加：

```css
.ot-page {
  background: var(--vk-paper);
  color: var(--vk-ink);
  padding: var(--space-lg);
}

.ot-page + .ot-page,
.ot-section {
  border-top: 1px solid var(--vk-line);
  margin-top: var(--space-lg);
  padding-top: var(--space-lg);
}
```

不给这些页面普遍加 `ot-page`，也不改它们的保存请求。空状态、对话框和抽屉沿用现有组件，只统一纸面、边框和次要文字色。Vue 模板里已有的 `:bordered="false"` 保持这种写法。登录页和空工作区引导改用同一套背景和纸面，不改提交、重试和退出。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run src/styles/__tests__/page-surface.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/design-system.css frontend/src/views/issue/detail/index.vue frontend/src/views/workflow/projects/index.vue frontend/src/views/workflow/project-detail/index.vue frontend/src/views/customers frontend/src/views/requests frontend/src/views/initiatives frontend/src/views/settings frontend/src/styles/__tests__/page-surface.test.ts
git commit -m "feat: flatten primary pages onto one surface"
```

### Task 7: 三档宽度和公开页

**Files:**
- Modify: `frontend/src/styles/css/global.css`
- Modify: `frontend/src/views/f/[token].vue`
- Modify: `frontend/src/views/r/[token].vue`
- Modify: `frontend/src/views/invite/[token].vue`
- Modify: `frontend/src/views/issue/list/index.vue`
- Test: `frontend/src/styles/__tests__/responsive-shell.test.ts`
- Test: `frontend/src/router/routes/__tests__/public-routes.test.ts`（已有，必须继续通过）

**Interfaces:**
- Consumes: Task 4 的控件高度和 Task 6 的 `ot-page`
- Produces: `@media (max-width: 768px)` 下侧栏可折叠，主操作按钮仍在文档流中

- [ ] **Step 1: Write the failing test**

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

describe('responsive shell', () => {
  it('defines the 768px collapse without removing the page actions', () => {
    const css = readFileSync(new URL('../css/global.css', import.meta.url), 'utf8');
    expect(css).toContain('@media (max-width: 768px)');
    expect(css).not.toContain('display: none; /* hide create */');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run src/styles/__tests__/responsive-shell.test.ts`  
Expected: FAIL because `frontend/src/styles/css/global.css` does not yet contain `@media (max-width: 768px)`.

- [ ] **Step 3: Write minimal implementation**

公开页用现有令牌做背景和纸面，卡片宽度不超过视口，375 上提交按钮仍在卡片内。不改 token 参数、不改接口地址、不把它们放进登录守卫。问题列表工具栏允许换行，导出、导入和新建仍渲染。窄屏是否裁切以编译后的 375、768、1280 截图和测量为准，不靠样式文件里有没有一段媒体查询。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run src/styles/__tests__/responsive-shell.test.ts src/router/routes/__tests__/public-routes.test.ts && pnpm exec eslint src/router/routes/index.ts src/store/modules/route/shared.ts src/layouts/modules/global-sider src/locales/langs/zh-cn.ts src/locales/langs/en-us.ts --max-warnings 0 && pnpm build --mode prod`  
Expected: 测试、所改文件的 eslint 和构建都通过。构建仍可对目录 `f` 和 `r` 打印警告。构建后的路由测试必须仍包含 `/f/:token` 和 `/r/:token`。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/css/global.css frontend/src/styles/__tests__/responsive-shell.test.ts frontend/src/views/f frontend/src/views/r frontend/src/views/invite frontend/src/views/issue/list/index.vue
git commit -m "feat: keep public pages and narrow layouts on the same surface"
```

### Task 8: 验收记录

**Files:**
- Create: `docs/superpowers/acceptances/2026-11-06-ui-shell-terminology-acceptance.md`

**Interfaces:**
- Consumes: 前面每个任务的命令输出，以及浏览器在 375、768、1280 的亮色和暗色截图
- Produces: 把单测数字和浏览器结果分开的验收说明

- [ ] **Step 1: 记录单测和构建**

写明命令、通过数和失败名。失败时先与 `f2f81c51` 的同命令对照，再决定是不是本批引入的。不要把单独重跑通过写成基线也失败。

- [ ] **Step 2: 记录浏览器**

用编译后的前端，而不是 Vitest。至少截菜单、问题列表、登录，三种宽度，亮色和暗色。另记：无 id 的客户和举措地址回到列表；带 id 的深链仍打开记录；`/f/:token` 和 `/r/:token` 不进登录。截图不含口令或 token。

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/acceptances/2026-11-06-ui-shell-terminology-acceptance.md
git commit -m "docs: record the ui shell acceptance"
```

## Self-review

- 台账 UI-1 到 UI-4 由 Task 1–3 覆盖。UI-C1 由 Task 3–4 覆盖。UI-C2 由 Task 5–6 覆盖。UI-C3 由 Task 7 覆盖。
- 术语表里的冲刺和周期建单在 Task 1 有断言。
- 公开路由和 Requirement 隐藏由 Task 2 的回归命令覆盖。
- 没有把实施写成已经完成。Task 8 只在前面的测试和浏览器证据存在之后才填写验收。

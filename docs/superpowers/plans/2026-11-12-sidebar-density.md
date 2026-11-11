# 侧栏密度与快捷入口图标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `088a34308cb0fe75a95f129432ee67b8f54067c3` 上，用一条侧栏切片完成 34px 内容盒、6px 组内间距、36×36 折叠命中区、收藏空态，并把四颗 emoji 换成已核对的路由图标 id。

**Architecture:** `index.vue` 用一个 flex 容器提供唯一的 6px gap。四个快捷入口 SFC 引入现有 `SvgIcon`，不改共享组件。收藏空态留在 `FavoritesNav.vue`。菜单的 34px / 6px 不改。

**Tech Stack:** Vue 3、Vitest、happy-dom、Playwright（仓库外）、Pinia。

## Global Constraints

- 基线只允许 `088a34308cb0fe75a95f129432ee67b8f54067c3`。实施分支以后从该提交另开，PR base 为 `cursor/issue-surface-visual-ab12`，正文 Depends on PR7。不改 PR6、PR7 已有提交。
- 本次文档修正不提交、不开分支。下面的「文档提交」只在实施被另行授权之后执行。
- 详情、编辑、`issue-surface.css`、`MarkdownRenderer.vue`、`svg-icon.vue`、`routes.ts`、`vertical-menu.vue`、`linear-shell.css`、Logo 不进本 diff。
- 导航文案、顺序、路由、权限、`.active`、`go()`、220 / 64、移动端宽 0、收藏 `max-height: 40%` 保持。
- 红测和绿测日志只保存命令当时的 stdout 和 stderr。禁止事后回写。
- 全量 vitest、vue-tsc、eslint、生产构建在同一个 FINAL SHA 上各写一份日志。vue-tsc 退出码 2 和 ESLint 非零仍记为失败，并且不能用 `&&` 挡住后面的构建。

文档路径恰好 2 个：

- `docs/superpowers/specs/2026-11-12-sidebar-density-design.md`
- `docs/superpowers/plans/2026-11-12-sidebar-density.md`

产品与测试路径恰好 8 个：

- `frontend/src/layouts/modules/global-sider/index.vue`
- `frontend/src/layouts/modules/global-sider/TriageNav.vue`
- `frontend/src/layouts/modules/global-sider/CustomersNav.vue`
- `frontend/src/layouts/modules/global-sider/InsightsNav.vue`
- `frontend/src/layouts/modules/global-sider/ActivityNav.vue`
- `frontend/src/layouts/modules/global-sider/FavoritesNav.vue`
- `frontend/src/layouts/modules/global-sider/density-invariants.test.ts`
- `frontend/src/layouts/modules/global-sider/density-contract.test.ts`

---

### Task 0: 文档入库（实施授权之后，不是本轮）

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-sidebar-density-design.md`
- Create: `docs/superpowers/plans/2026-11-12-sidebar-density.md`

**Interfaces:**
- Consumes: 仓库外已定稿的同名规格和本计划
- Produces: 第一次提交只含这 2 个路径

- [ ] **Step 1: 只复制这两个文件并核对数量**

```bash
git diff --name-only --cached
```

Expected: 恰好 2 行，就是上面的两个 docs 路径。出现产品文件就停止。

- [ ] **Step 2: 提交**

```bash
git commit -m "docs: add sidebar density and icon spec"
```

---

### Task 1: 菜单不变量

**Files:**
- Create: `frontend/src/layouts/modules/global-sider/density-invariants.test.ts`
- Test: `frontend/src/layouts/modules/global-sider/density-invariants.test.ts`

**Interfaces:**
- Consumes: `frontend/src/styles/css/linear-shell.css`
- Produces: 无运行时导出

- [ ] **Step 1: 写基线上就会通过的测试**

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('sider menu density invariants', () => {
  it('keeps the Naive item height override exactly as baseline', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/styles/css/linear-shell.css'), 'utf8');
    expect(css).toContain('.n-menu {\n  --n-item-height: 34px !important;\n}');
  });

  it('does not move item height into the menu component', () => {
    const vue = readFileSync(
      resolve(process.cwd(), 'src/layouts/modules/global-menu/modules/vertical-menu.vue'),
      'utf8'
    );
    expect(vue).not.toContain('--n-item-height');
  });
});
```

- [ ] **Step 2: 在改产品代码之前运行**

```bash
ROOT=$(git rev-parse --show-toplevel)
(
  cd "$ROOT/frontend"
  pnpm exec vitest run src/layouts/modules/global-sider/density-invariants.test.ts
)
```

Expected: 2 passed。完整输出存到 `/tmp/cursor/opentask-readonly/sidebar-invariant-pass.txt`。失败则停止。

---

### Task 2: 密度、图标和 aria 的失败测试

**Files:**
- Create: `frontend/src/layouts/modules/global-sider/density-contract.test.ts`
- Test: `frontend/src/layouts/modules/global-sider/density-contract.test.ts`

**Interfaces:**
- Consumes: 四个快捷入口 SFC 和 `FavoritesNav.vue`
- Produces: 挂载后的 DOM 断言。源码 `toContain` 只作辅助，不能单独当通过。

- [ ] **Step 1: 写入会在当前 emoji 模板上失败的挂载测试**

测试使用 `@vue/test-utils`。`vue-router` 的 `useRouter().push` 和 `useRoute()` 用 `vi.mock`。`useAppStore` 返回可变对象 `{ siderCollapse: false }`。`$t` 返回下表的中文。`SvgIcon` 打成桩：`<svg data-icon="" />`，桩自身不要写 `aria-hidden`，好让断言落在 SFC 的包裹元素上。`NTooltip` 打成桩，同时渲染 trigger 和默认插槽。

```ts
import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import TriageNav from './TriageNav.vue';

const app = { siderCollapse: false };
vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'issue_list', path: '/issue/list' }),
  useRouter: () => ({ push: vi.fn() })
}));
vi.mock('@/store/modules/app', () => ({ useAppStore: () => app }));
vi.mock('@/locales', () => ({
  $t: (key: string) =>
    ({
      'page.sider.triage': '分诊',
      'page.sider.triageHint': '入站'
    })[key] ?? key
}));

const stubs = {
  SvgIcon: { props: ['icon'], template: '<svg :data-icon="icon" />' },
  NTooltip: { template: '<div><slot name="trigger" /><span class="tip"><slot /></span></div>' }
};

describe('triage icon and name', () => {
  it('renders the route icon without an emoji and names the collapsed button', async () => {
    app.siderCollapse = false;
    const open = mount(TriageNav, { global: { stubs } });
    expect(open.text()).not.toContain('📥');
    expect(open.get('[aria-hidden="true"] svg').attributes('data-icon')).toBe('mdi:inbox-arrow-down');
    expect(open.get('button').attributes('aria-label')).toBeUndefined();
    expect(open.get('button').text()).toContain('分诊');
    expect(open.get('button').text()).toContain('入站');

    app.siderCollapse = true;
    const shut = mount(TriageNav, { global: { stubs } });
    expect(shut.get('button').attributes('aria-label')).toBe('分诊');
    expect(shut.get('.tip').text()).toBe('分诊');
    expect(shut.text()).not.toContain('📥');
  });
});
```

客户、洞察用同一形状，id 和文案分别是 `mdi:account-group-outline` / 客户 / 需求，`mdi:chart-box-outline` / 洞察 / 效能。活动要 mock `@/service/api/issue` 的 `fetchActivityUnreadCount`，让它 resolve `{ data: { count: 3, capped: false }, error: null }`。折叠后的 `aria-label` 和 tooltip 都是 `活动（3）`。展开按钮不设 `aria-label`，按钮文本里仍有 `3`。四份组件都断言没有 `📥` `👥` `📈` `🔔`。

密度合同仍检查 `.global-sider__quick` 的 `gap: 6px`、`padding: 6px 8px 0`、`padding: 6px 0 0`，四个展开按钮 `height: 34px`，四个折叠按钮 `width: 36px` 与 `height: 36px`，以及 `:focus-visible` 规则 `outline: 2px solid var(--vk-accent)`。`FavoritesNav.vue` 含 `favorites-nav__empty-note`、`v-if="showFavorites"`、`max-height: 40%`，并且不含 `NEmpty`。标题规则含 `font-size: 12px`、`line-height: 18px`、`margin: 0 0 6px`、`padding: 0 8px`。空说明含同样的字号和行高，以及 `margin: 0`、`padding: 0 8px`。这些字符串断言通过之后，图标任务仍以挂载结果为准。

- [ ] **Step 2: 运行并保存当次失败输出**

```bash
ROOT=$(git rev-parse --show-toplevel)
(
  cd "$ROOT/frontend"
  pnpm exec vitest run src/layouts/modules/global-sider/density-contract.test.ts
)
```

Expected: FAIL，因为当前按钮仍是 emoji，没有 `aria-hidden` 包裹，也没有这些图标 id。把完整 stdout 和 stderr 写入 `/tmp/cursor/opentask-readonly/sidebar-red.txt`。

---

### Task 3: 实现密度和图标

**Files:**
- Modify: 上面 8 个产品与测试路径里的 6 个 SFC
- Test: `frontend/src/layouts/modules/global-sider/density-contract.test.ts`

**Interfaces:**
- Consumes: `SvgIcon`、`$t('page.sider.*')`、`formatUnreadBadge`、现有 `go()` 与 `.active`
- Produces: 类名 `global-sider__quick`、`favorites-nav__empty-note`，以及四颗 `SvgIcon`

- [ ] **Step 1: `index.vue` 只包住四个快捷入口**

```vue
<div class="global-sider__quick" :class="{ 'is-collapsed': appStore.siderCollapse }">
  <TriageNav />
  <CustomersNav />
  <InsightsNav />
  <ActivityNav />
</div>
```

```css
.global-sider__quick {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px 8px 0;
  margin: 0;
}
.global-sider__quick.is-collapsed {
  align-items: center;
  padding: 6px 0 0;
}
```

Logo 和 `#__GLOBAL_SIDER_MENU__` 仍是兄弟节点。

- [ ] **Step 2: 四个快捷入口**

每个文件引入 `SvgIcon from '@/components/custom/svg-icon.vue'`。根与 `.collapsed` 的 padding、margin 改为 0。展开按钮 `box-sizing: border-box; height: 34px; width: 100%; padding: 0 8px; gap: 8px; border-radius: 6px`。折叠按钮 `width: 36px; height: 36px; padding: 0`。hover 和 `.active` 仍是 `background: var(--vk-accent-soft)`。每个按钮增加：

```css
.triage-nav__row:focus-visible,
.triage-nav__btn:focus-visible {
  outline: 2px solid var(--vk-accent);
  outline-offset: 2px;
}
```

类名按文件替换。`CustomersNav.vue` 使用 `mdi:account-group-outline`。`InsightsNav.vue` 使用 `mdi:chart-box-outline`。`ActivityNav.vue` 使用 `mdi:timeline-text-outline`。展开结构以分诊为例，另外三个只换 id 和 `$t` 键：

```vue
<button v-else type="button" class="triage-nav__row" @click="go">
  <span class="triage-nav__icon" aria-hidden="true">
    <SvgIcon icon="mdi:inbox-arrow-down" style="font-size: 20px; color: currentColor" />
  </span>
  <span class="triage-nav__label">{{ $t('page.sider.triage') }}</span>
  <span class="triage-nav__hint">{{ $t('page.sider.triageHint') }}</span>
</button>
```

折叠：

```vue
<button type="button" class="triage-nav__btn" :aria-label="$t('page.sider.triage')" @click="go">
  <span aria-hidden="true">
    <SvgIcon icon="mdi:inbox-arrow-down" style="font-size: 20px; color: currentColor" />
  </span>
</button>
```

`NTooltip` 的默认插槽仍是同一个 `$t` 主标签。活动使用一个 computed，展开和折叠共用：

```ts
const collapsedLabel = computed(() => {
  const name = $t('page.sider.activity');
  return badge.value ? `${name}（${badge.value}）` : name;
});
```

折叠按钮的 `aria-label` 和 tooltip 都绑定 `collapsedLabel`。未读圆点 `__dot` 留在按钮里，不放进 `aria-hidden`。展开按钮不设 `aria-label`，徽章 `__badge` 留在原位。四个 `go()` 和 `active` 计算不改。

- [ ] **Step 3: 收藏空态**

```ts
const showFavorites = computed(() => !(collapsed.value && !loading.value && ordered.value.length === 0));
```

根加 `v-if="showFavorites"`。标题改为 `p.favorites-nav__title`，颜色 `var(--vk-muted)`，`font-size: 12px; line-height: 18px; margin: 0 0 6px; padding: 0 8px`。空说明是 `p.favorites-nav__empty-note`，文案仍是「暂无侧栏收藏」，同样的字号和行高，`margin: 0; padding: 0 8px; color: var(--vk-muted)`。删除 `NEmpty`。收藏根 `padding: 6px 8px; max-height: 40%; overflow: auto`。有数据时的两行按钮和 `gap: 2px` 不改。

- [ ] **Step 4: 跑到通过并提交这 8 个文件**

```bash
ROOT=$(git rev-parse --show-toplevel)
(
  cd "$ROOT/frontend"
  pnpm exec vitest run src/layouts/modules/global-sider/density-contract.test.ts src/layouts/modules/global-sider/density-invariants.test.ts
)
```

Expected: passed。输出存到 `/tmp/cursor/opentask-readonly/sidebar-unit-green.txt`。提交消息 `feat: align sider density and quicklink icons`。暂存列表必须正好是那 8 个产品与测试路径。

---

### Task 4: 浏览器里的真实 DOM

**Files:**
- Create: `/tmp/cursor/opentask-readonly/verify-sidebar.mjs`（不入库）

**Interfaces:**
- Consumes: Task 3 的页面
- Produces: `/tmp/cursor/opentask-readonly/after-sidebar/dom.json`

- [ ] **Step 1: 中英文、展开和折叠**

用 Playwright 的 `keyboard.press`，不用 `element.focus()`。对 375、768、1280，高度 800 和 480，light 和 dark，展开和折叠，分别在 `zh-CN` 与 `en-US` 记录四个按钮。

通过条件：四个按钮的文本不含 `📥` `👥` `📈` `🔔`；每个按钮内有 `svg`，并且该 svg 或它的包裹元素是 `aria-hidden="true"`；svg 的宽高约为 20。展开时中文可访问名称含「分诊」「入站」，英文含 `Triage` 和 `Incoming`，另外三组用规格表里的现有词。折叠时中文可访问名称就是「分诊」「客户」「洞察」；英文是 `Triage`、`Customers`、`Insights`。活动在未读数为 0 时名称是「活动」或 `Activity`。把合成未读数改成 3 之后，折叠名称是 `活动（3）` 或 `Activity（3）`，并且圆点仍可见。`:focus-visible` 的 outline 是 `2px solid`，颜色为当前 `--vk-accent`。

菜单第一条 `.n-menu-item` 仍是高 34、`margin-top: 6px`。Logo 组件文件不在 diff 里。

- [ ] **Step 2: 滚动按实测几何判断**

在 1280×480 使用合成收藏。先放 8 条。读 `.favorites-nav` 和 `#__GLOBAL_SIDER_MENU__ .simplebar-content-wrapper` 的 `clientHeight` 与 `scrollHeight`。哪个大于，就把它的 `scrollTop` 设到末尾再读回来，并确认该容器最后一项可以点到或 Tab 到。哪个没有大于，记录 `nooverflow`。8 条没有让收藏溢出时，只在合成服务里把条数加到 24 为止；产品 CSS 不加高、不改 `max-height`。加到 24 仍不溢出，也记录 `nooverflow` 并停止加长。不要要求两个容器同时溢出。

低高度、1 条、8 条、折叠有收藏、768 有收藏都不是基线截图。这次浏览器结果是实施后的证据。

---

### Task 5: 同一个 FINAL SHA 的四份日志

**Files:**
- 无新增产品文件

**Interfaces:**
- Consumes: Task 3 的提交
- Produces:
  - `/tmp/cursor/opentask-readonly/sidebar-vitest.txt`
  - `/tmp/cursor/opentask-readonly/sidebar-vue-tsc.txt`
  - `/tmp/cursor/opentask-readonly/sidebar-eslint.txt`
  - `/tmp/cursor/opentask-readonly/sidebar-build.txt`

- [ ] **Step 1: 核对路径数量**

```bash
git diff --name-only 088a34308cb0fe75a95f129432ee67b8f54067c3
```

文档 2 个，产品与测试 8 个，合计 10 个。多出来的路径就停止。

- [ ] **Step 2: 一次进入 frontend，四条命令都跑完**

工作树干净。不要使用重复的 `cd frontend &&`。`set +e` 保证 vue-tsc 或 eslint 非零之后，vitest 和构建仍然执行。每份日志首行是同一个 SHA，末尾是该命令自己的退出码。

```bash
ROOT=$(git rev-parse --show-toplevel)
SHA=$(git -C "$ROOT" rev-parse HEAD)
OUT=/tmp/cursor/opentask-readonly
(
  cd "$ROOT/frontend"
  set +e
  printf 'SHA %s\n' "$SHA" > "$OUT/sidebar-vitest.txt"
  pnpm exec vitest run >> "$OUT/sidebar-vitest.txt" 2>&1
  printf 'EXIT %s\n' "$?" >> "$OUT/sidebar-vitest.txt"
  printf 'SHA %s\n' "$SHA" > "$OUT/sidebar-vue-tsc.txt"
  pnpm exec vue-tsc --noEmit --skipLibCheck >> "$OUT/sidebar-vue-tsc.txt" 2>&1
  printf 'EXIT %s\n' "$?" >> "$OUT/sidebar-vue-tsc.txt"
  printf 'SHA %s\n' "$SHA" > "$OUT/sidebar-eslint.txt"
  pnpm exec eslint . >> "$OUT/sidebar-eslint.txt" 2>&1
  printf 'EXIT %s\n' "$?" >> "$OUT/sidebar-eslint.txt"
  printf 'SHA %s\n' "$SHA" > "$OUT/sidebar-build.txt"
  pnpm exec vite build --mode prod >> "$OUT/sidebar-build.txt" 2>&1
  printf 'EXIT %s\n' "$?" >> "$OUT/sidebar-build.txt"
)
```

`vitest run` 不带文件参数。vue-tsc 与账本同一组 29 条逐条对照，退出码 2 记为失败。eslint 不加 `--fix`，与本分支第一次产品改动之前在 `088a343` 上当次跑出的逐条诊断对照；非零记为失败。更早的 6E/25W 全文不在本工作树，不得编造。构建期望 `EXIT 0`。构建失败则停止，不送审。

- [ ] **Step 3: 两个独立复审**

四份日志的 SHA 相同之后才送审。一个对照切片规格和本计划。一个只读该 SHA 的 diff。通过之前不开 PR，也不开始详情/编辑分支。

## 已被取代的旧句

更早的计划稿写过「emoji 不删」和「图标仍待选」。Yuri 已选择选项 1。那些句子不再指导 Task 3 或 Task 5。

## Self-review

- 规格里的 34px、6px、36×36、收藏 40%、空 Tab、四颗路由 id、20px、`currentColor`、折叠 aria-label、活动徽章、本地焦点环，都有任务。
- 文档 2 个与产品测试 8 个分开计数。
- 图标通过条件是挂载 DOM 和浏览器 DOM，不是单独的 `toContain`。
- Task 5 的接口就是那四个日志路径。命令只 `cd` 一次，并且非零 typecheck 或 lint 不会跳过 vitest 和构建。
- 8 条收藏只是起点。每个容器按 `scrollHeight` 和 `clientHeight` 记录溢出或 `nooverflow`。

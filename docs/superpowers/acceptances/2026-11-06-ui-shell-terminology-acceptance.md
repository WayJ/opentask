# 界面壳层与术语验收

日期：2026-11-06  
基线：`main` @ `f2f81c51fda85bf48221d7f84a2f56d071e7704e`（远端 `main` 没有新提交）  
最终代码：`d47da33aa8762013d22baafa263b9658196a443e`  
前一代码：`683d50f7bfad0db089cf76c11d368b4198dfa76d`  
不合并、不部署、不连接现网。  
下面「补证」一节覆盖更早的空表探针和类型门禁说法。

## 独立审查

审查者是同一环境里的另一个代理，只读，范围是 `f2f81c51..90bae6e`。

第一轮结论是未通过。路由注入和缺 id 守卫可以保留。两件要改的事：首页、洞察、成员等页面标题还没有跟当前语言走；`.tabs-section` 的 `overflow: hidden` 可能把状态标签裁掉。

修正提交是 `683d50f`。同一审查者复审了这个 diff，结论是这两项已经解决。那一轮没有再看路由守卫。

第三轮看的是相对 `f2f81c5` 的整份前端 diff，包括 `frontend/src/router/guard/route.ts` 和 `frontend/src/router/list-entry.ts`。审查者只读。结论是可以收口，没有重要正确性问题。守卫只在常量路由放行之后、工作区门闩之后执行；公开的 `/f`、`/r`、`/invite` 和未登录访问不会被送进需登录的列表。没有 id 时用 `replace` 到 `*_list`，下一跳不再命中，因此停一次。带 id 的查询保留。重定向不携带其他账号的 query。动态路由模式不会挂上 `*_list`，生产和示例环境是 static，记为残留风险，不是这次要改的缺陷。

`d47da33` 只放宽菜单高亮参数、补上已有的 `navInitiatives` 类型，并调整类名顺序和两个对话框的换行。守卫没有再改。同一审查者看过这个 diff，维持可以收口。被审查的代码提交就是 `d47da33`。其后只有文档。

## 单测和生产构建

这些数字来自命令输出，不是浏览器。

| 门禁 | 结果 |
|---|---|
| `pnpm exec vitest run` | 73 个文件，471 个测试通过。缺 id 守卫、真实 `createRouter`、文案键、面包屑点击、令牌对比都在里面。 |
| `pnpm build`（`vite build --mode prod`） | 成功。构建会跑路由代码生成，并打印 `f`、`r` 目录名无效。生成的 `elegant` 路由和 `elegant-router.d.ts` 没有产生 diff。 |
| 构建后再跑 `menu-entry` 与 `public-routes` | 8 个测试通过。`/f/:token`、`/r/:token` 仍在，列表子路由仍在。 |
| `npx vue-tsc --noEmit --skipLibCheck` | 阻断。基线和当前各 29 条、输出一致。见「补证」。 |
| 改动文件的 eslint | 没有新增 error。基线 63，当前 62。见「补证」。 |
| 后端 pytest、CLI | 本批没有改后端和 CLI，没有重跑。 |

## 编译后的浏览器

本地 nginx 提供本批 `dist`，接口指向本机的测试库。下面是量到的行为，不是样式文件里有没有某段文字。

- 登录后标题是「我的问题 - OpenTask」。客户页标题是「客户 - OpenTask」，举措页是列表，菜单里举措是一项。
- 打开 `/customers/detail` 且没有 id，地址停在 `/customers`，标签只有「我的问题」和「客户」。打开 `/customers/detail?id=not-a-real-customer` 仍停在详情。
- 375 / 768 / 1280 的文档 `scrollWidth` 等于视口宽度。导出、导入、新建问题的盒子在 375 视口内。搜索框占位是「搜索问题编号、标题...」，盒子右缘在视口内。
- 375 的状态标签在标签条内部滚动。把滚动位置设到 200 后，「全部」右缘是 370，仍在 375 里面。
- 暗色用页头的主题开关，不是只给 `html` 加 class。问题列表卡片背景是 `rgb(24, 24, 28)`，登录卡片是 `rgb(15, 16, 17)`，`html` 带 `dark`。
- 导入对话框传送到 `body`。对话框里的按钮焦点是 2px 实线，颜色 `rgb(130, 143, 255)`。
- 当时这个工作区的问题计数是 0，行高来自探针。这一条作废，以「补证」里的 `SMOKEW-1` / `SMOKEW-2` 为准。
- 令牌对比是单测，读的是 `design-tokens.css` 里的实际色值，不是截图取色。
- 公开页 `/f/not-a-real-token` 在 375 下卡片右缘 359，文案是「问题表单」。
- 登录主按钮文案是「确认」。375 下左缘 52.5、右缘 322.5。

没有把「所有页面都好了」当成结论。截图覆盖登录、问题列表、客户、举措、首页、洞察、成员和公开表单，亮色和暗色，三档宽度里的代表画面。仪表盘、周期建单、自动化等只改了可见名词，没有逐页截图。

## 已解决

- 客户、需求、举措从菜单或父路由进入现有列表，地址仍是 `/customers`、`/requests`、`/initiatives`。
- 没有 id 的详情在路由确认前替换到列表，标签不会先记下详情。带 id 的深链不变。
- `activeMenu` 指向父路由名，举措高亮是一个叶子。`*_list` 没有写进生成的 `RouteKey`。
- 中文界面把问题、问题模板、新建问题、洞察、活动/动态、举措、冲刺和周期建单分开。英文仍用 Insights、Activity、Issue、Cycles。客户侧的「新建需求」保持这四个字。
- 面包屑是现有对象，非当前项可点，未登记键和管理路由不出现，文案随语言变。
- 登录和空工作区引导只改了表面。没有改租户、登录或确保所有者的行为。

## 补证

同一套命令、同一份 `frontend/node_modules`。基线工作树是 `f2f81c5`，当前是本分支。

### 类型检查：阻断，不是通过

`npx vue-tsc --noEmit --skipLibCheck` 在基线和当前各报 29 条，两份输出一致，退出码都是 2。编译器停在既有语法错误：`src/typings/api/issue.d.ts` 第 75 行枚举缺逗号，`src/typings/components.d.ts` 第 242–255 行 `const 'IconMdi:...'`。这两个文件相对基线没有 diff，没有把修正提交进仓库。

为了还能比较后面的诊断，只在一次性目录 `/tmp/tsc-base` 和 `/tmp/tsc-head` 里做了同一处语法修补：补上那个逗号，并把 14 个带引号的 const 改成合法标识符。修补后的这两个生成文件在两边仍然相同。再跑同一条 `vue-tsc`：基线 495 条，当前 492 条。按「文件 + 错误码 + 原文」比较，当前没有新增诊断。少掉的 3 条是基线上已有的 `navInitiatives` 超额属性，类型补上这个键之后消失。因此类型门禁仍是阻断：官方命令通不过，不能写成通过。能说的只是本批没有带来新的类型错误。

### 改动文件的 eslint：没有新增 error

同一条 `npx eslint -f json`，不带 `--fix`。基线上这些文件 63 个 error、365 个 warning；当前 62 个 error、随后类名和对话框换行对齐之后，首页和洞察的 warning 条数回到基线，问题列表从 27 降到 24，详情仍是 58，且没有新的 warning 原文。6 个新文件 0 个 error。唯一减少的 error 是 `ActivityNav.vue` 的 import 顺序。没有把「文件本来就大」当成理由。

### 真实行，不是探针

新建了本机库 `opentask_pr5_fixture`（属主 `opentask`，不碰已有的 `opentask_browser`，也不是生产库）。`alembic upgrade head` 成功。文档里的 `scripts/create_admin_user.py` 建了带工作区的 `smoke` 和不建工作区的 `smoke-empty`。再用本机 `127.0.0.1:7399` 的登录、`POST /api/issues`、客户、举措、需求、表单和邀请接口写入两条问题：`SMOKEW-1`「一行标题」和 `SMOKEW-2` 长标题。nginx `8095` 提供本批 `dist`，`8096` 提供基线 `dist`，两边都代理到这个库。

生产构建成功，产物里能搜到 `customers_list`、`initiatives_list`、`requests_list`。

量到的行（亮色，暗色数字相同）：

| 宽度 | 页面横向溢出 | 长标题行高 | 单行行高 | 操作按钮 |
|---|---|---|---|---|
| 375 | 0 | 93 | 41 | 「详情」「删除」在视口内 |
| 768 | 0 | 93 | 41 | 在视口内 |
| 1280 | 0 | 93 | 41 | 在视口内 |

标题 `white-space` 是 `normal`，`scrollHeight` 等于 `clientHeight`，没有被单元格的 max-height 裁掉。单行 41px 比 40px 多 1px，来自单元格上下内边距和边框，没有为了压到 40 去改高度。长标题允许更高。

375 下「待办」初始 left 是 533，不在视口里。它所在的 `.n-scrollbar-container` 是 `scrollWidth` 1402、`clientWidth` 349。把 `scrollLeft` 设到 520 之后，「待办」left 变成 13、right 133，完整进入视口；固定的操作列仍在 162–362。状态不是被裁掉后无法到达。类型「Bug」、优先级在更右边，同样靠这层横向滚动。

375 的固定操作列会盖住标题单元格的右半。基线 `dist` 在同一宽度下也是这样。这次没有改列宽或取消固定列。

暗色是点登录页和页头的主题按钮，`html` 带 `dark`。暗色单元格字色 `rgba(255, 255, 255, 0.82)`、背景 `rgb(24, 24, 28)`，对比度 17.7。亮色单元格字色 `rgb(51, 54, 57)`、背景白，对比度 12.16。导入对话框打开后按 Tab，焦点落在对话框内的文件输入，对话框在传送层里。语言菜单切到 English 后，页面上出现 Insights / Issues / Activity。

深链，同一套夹具：

| 地址 | 基线停在 | 当前停在 |
|---|---|---|
| 客户 / 举措 / 需求详情，带 id | 详情，id 还在 | 详情，id 还在 |
| 这三类详情，没有 id | 仍是详情，客户面包屑是原始键 `route.customers_detail` | `/customers`、`/initiatives`、`/requests` |
| `/issue/detail?id=` 夹具 id | 详情 | 详情 |
| `/issue/detail` 没有 id | 仍是 `/issue/detail` | 仍是 `/issue/detail`（英文界面文案是 Issue not found） |

问题详情不在 `*_list` 映射里，两边都不跳列表。这不是这次新引入的回退。

匿名打开真实表单、需求状态链接和邀请，都停在公开页，没有被送去登录。`smoke-empty` 登录后停在 `/workspace-onboarding`，基线和当前都是。

### 门禁怎么分

已核对：前端 `vitest run` 73 文件、471 通过（含 `d47da33` 之后）。`vite build --mode prod` 成功。改动文件 eslint 没有新增 error。浏览器对照见上。

阻断：官方 `vue-tsc` 被基线语法错误挡住。修补只存在于临时目录。

未跑：后端 pytest 和 CLI。`git diff f2f81c5..HEAD -- backend agent-harness` 为空，没有无意改动。

### 截图

代表画面的地址（PR #5 正文同一组）：

- 登录亮色基线 / 当前：https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fbefore-login-light-1280.png 和 https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-login-light-1280.png
- 登录暗色当前：https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-login-dark-1280.png
- 壳层亮色当前：https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-shell-light-1280.png
- 问题列表 375 基线 / 当前：https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fbefore-issues-light-375.png 和 https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-issues-light-375.png
- 375 滚到状态：https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-issues-light-375-scrolled.png
- 问题列表 768 / 1280 / 暗色 1280：https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-issues-light-768.png 、https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-issues-light-1280.png 、https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-issues-dark-1280.png
- 公开表单、邀请、无工作区：https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-public-form.png 、https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-invite.png 、https://cursor.com/agents/bc-d58428f4-7424-5247-8694-cec10a2b658f/artifacts?path=%2Fopt%2Fcursor%2Fartifacts%2Fafter-no-workspace.png

本轮实际打开并截了登录、登录后的壳、问题列表、客户/举措/需求的列表和详情、公开表单、公开需求、邀请、无工作区。亮色和暗色、375/768/1280 的问题列表都量过。没有逐页打开仪表盘、周期、自动化、Webhook、成员、分诊和项目模板。中文界面仍有英文：类型值 `Bug`、产品名 OpenTask、夹具里的 Wrap，洞察说明里的 digest / OR 也还在。没有把整站文案说成已经全部中文化。

## 限制

- 官方 `vue-tsc` 仍被基线语法错误挡住，不能标成通过。
- 大 Vue 文件的既有 eslint error 还在；本批没有新增 error。
- 375 下固定的「操作」列会盖住标题右半，基线同样如此。状态和类型要在表格横向滚动后才进入视口。
- 375 下四个状态标签要在标签条里横滑才能看全。
- 没有 id 的问题详情仍停在 `/issue/detail`，两边都是。
- 洞察页说明里仍有 digest、OR。类型枚举仍显示 Bug。
- 后端和 CLI 未重跑；相对基线没有代码 diff。

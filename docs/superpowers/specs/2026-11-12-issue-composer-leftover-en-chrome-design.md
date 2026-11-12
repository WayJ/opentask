# 创建与编辑剩句英文铬

第 8 刀 design 草稿，送 Yuri 代审；没有审批结论。要等 Yuri「design ok，开写」之后才可实施。本文不是已批准范围。未来 repo 路径：`docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md`。本文与 plan 是一组。盘点报告在 `/workspace/designs/post-pr19-polish-inventory/INVENTORY.md`（sha256 `85c0095584b5738f7c75081210353034605d945ce88c09806cb645da5feec511`，28168 字节），摘录在同目录 `priority-surfaces.md`（sha256 `b7d8c3e4870e35da8386b3261525e2e734979af87173bb3469492aa8f2e5a445`，20912 字节），都不入库。行号与现文案以精确 base `8cfc5fbe49f0541faec3e1975b9e8b9029593c58`（PR19 tip）上的盘点与摘录为准。不要用 `09413d29` 或更早盘点的行号当实施 base。

## 1. 问题与证据

PR19 已限定交付。本刀起点为 `8cfc5fbe49f0541faec3e1975b9e8b9029593c58`。`en-us.ts` 无汉字。`fallbackLocale` 是 `'en'`，注册的语言只有 `'zh-CN'` 和 `'en-US'`，缺 key 不会退回中文。英文界面上还能看见的中文，通常是写死字符串，或被上一刀测试冻住、故意不走 `$t` 的文案。

第 4 刀已把创建/编辑页骨架接到 `page.issueComposer`（19 叶），第 7 刀壳层英文铬已经在本 tip 落地。创建页、编辑页模板里剩下的汉字仍只剩两句，这是盘点第 3 节 / 第 6 节第一片候选，仍未获批：

- `frontend/src/views/issue/create/index.vue:488` `title="自定义字段（可选）"`
- `frontend/src/views/issue/edit/index.vue:279` `description="加载中..."`（省略号是三个 ASCII 点，不是 U+2026）

`issue-composer-chrome.test.ts:270-275` 仍冻住创建页三条结果文案、自定义字段标题和编辑页「加载中...」。本刀必须改 `:274-275`，并保留同测试对其它范围外字符串的冻结（`:271-273` 以及 `:276-284` 的 `insertText` 种子）。

盘点第二片（列表布尔自定义字段格的可见「是 / 否」）存在，但排在后面，只在范围外说明，不实施，也不要写成已批准。不要重开第 4–7 刀。

## 2. 方案与推荐

**A（推荐，本刀锁定）。** 两句都补进已有 `page.issueComposer`，不要另开 namespace，也不要塞进 `page.issueForm`。第 4 刀已有 19 叶保持原值、原调用次数；本刀只加两叶，使该对象变成 21 叶。推荐键名：

- `page.issueComposer.customFieldsOptional`：自定义字段（可选） / Custom fields (optional)
- `page.issueComposer.loading`：加载中... / Loading...

**B（推荐，本刀锁定）。** 没有同句可复用。不要把「自定义字段（可选）」拆成短词再拼。不要复用设置通知页「加载中…」（那个是 U+2026，不是同一句）。中文逐字保留，包括全角括号和三个 ASCII 点。英文同样用三个 ASCII 点，不要改成 `…`。英文 sentence case。

两页已有 `@/locales` 的 `$t` 导入，继续用它，不要无故改成 `useI18n()`，不要把既有 `$t` 改成局部 `t()`。模板属性直接写成：

- `:title="$t('page.issueComposer.customFieldsOptional')"`
- `:description="$t('page.issueComposer.loading')"`

不要为这两句新造 computed。若实施时不得不写成 computed，第一句必须是 `void locale.value;`（在任何短路之前）；`no-void` 只用 next-line 或紧贴块，禁止文件级 disable。

不改 `route.issue_create` / `route.issue_edit`，不改已有 `page.issueComposer` / `page.issueTemplate` / `page.markdownEditor` / `page.issueForm` 的旧键值。schema 与 zh/en 三份一致；walker 扩到 21 叶时不得改旧叶。

## 3. 锁定文案

英文 in-page copy 用 sentence case。中文逐字保留，包括全角括号 `（）` 和三个 ASCII 点 `...`。不要写成 U+2026 `…`。`en-us.ts` 不得有汉字。不改 route 键值。不改 19 个旧叶的既有译文。

### `page.issueComposer`（只追加两叶，19 → 21）

| 键 | zh-CN | en-US | create 调用 | edit 调用 |
|---|---|---|---|---|
| `customFieldsOptional` | 自定义字段（可选） | Custom fields (optional) | 1 | 0 |
| `loading` | 加载中... | Loading... | 0 | 1 |

旧 19 叶的键名、中英文值和既有调用次数一律保持原样，不要重写。不要把这两叶塞进 `page.issueForm` 或新 namespace。

不要复用：

- 设置通知页 `views/settings/notifications/index.vue:81` 的「加载中…」（U+2026）
- 任何把「自定义字段」与「可选」拆开再拼的短词键

## 4. 范围

**范围内**

- `frontend/src/views/issue/create/index.vue`：只改 `:488` 这一处 `title`
- `frontend/src/views/issue/edit/index.vue`：只改 `:279` 这一处 `description`
- `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`：必须改 `:274-275`；为覆盖 21 叶与调用次数，可在同一文件把已有 `composer` 表和 `createCalls` / `editCalls` 扩到两枚新叶。不要新开测试文件。保留 `:271-273` 与 `:276-284` 冻结
- 语言包 `zh-cn.ts` / `en-us.ts`、`frontend/src/typings/app.d.ts`：只在已有 `page.issueComposer` 追加两叶
- 实施时 `cmp` 已批原文进入 `docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md` 与 `docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md`

**范围外**

- 创建页 toast：`:116`「文件大小不能超过 10MB」、`:147` 附件部分成功、`:224`「请输入问题标题」、`:255`「问题已创建，但自定义字段保存失败」、`:259`「问题创建成功」、`:266`「问题创建失败」
- 编辑页 toast：`:152`「缺少问题 ID」、`:177`「加载问题数据失败」、`:187`「请输入问题标题」、`:205`「问题更新成功」、`:212`「问题更新失败」
- 创建页脚本模板字段兜底 label「标题」「描述」（`:321-328`）
- `IssueCustomFieldsEditor` 内部、`IssueTemplateForm.vue:77`「请填写」、`MarkdownEditor` 的 `insertText` 种子
- 详情页、列表页、`display-prefs.ts`（含 `:490`「是/否」和 `:510`「（计算值·只读）」）、`groupIssuesBy.ts`
- 第 7 刀壳层 11 路径、第 6 刀列表看板/显示/批量/搜索、第 5 刀详情宿主
- `issue-list-board-chrome.test.ts`、`app-shell-chrome.test.ts`、其它已落地冻结测试（本刀只改 `issue-composer-chrome.test.ts` 中上面点名的行，不得削弱其余冻结）
- 设置四页、大模块、`noneCycle` 合并、暗色/对比度/焦点 CSS
- 盘点第二片：列表布尔格。只在范围外说明，不实施、不写成已批准
- 不 merge、不部署、未经再授权不 push、不开新 PR。不改写 PR6–19 已存提交或头 SHA

白名单恰好 8 路径；审查要加路径，先改文档再批准：

- `docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md`
- `frontend/src/views/issue/create/index.vue`
- `frontend/src/views/issue/edit/index.vue`
- `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`

## 5. 决定（批准前确认）

按盘点推荐案写入本文，作为本刀锁定建议，供 Yuri 确认。否决任一条，先改 design 与 plan，再实施。

- **A（推荐，本刀锁定）。** 两句都补进已有 `page.issueComposer`（19 → 21 叶），不要另开 namespace，也不要塞进 `page.issueForm`。键名即 `customFieldsOptional` 与 `loading`。旧 19 叶原值、原调用次数不动。
- **B（推荐，本刀锁定）。** 没有同句可复用。不要拆「自定义字段（可选）」。不要复用通知页「加载中…」（U+2026）。中文逐字保留（全角括号、三个 ASCII 点）；英文 Custom fields (optional) / Loading...，同样三个 ASCII 点，sentence case。
- 本刀只实施盘点第一片（创建/编辑各剩一句）。第二片（列表布尔格「是/否」）存在，但不在本刀实施，也尚未获批。不要改先做第二片来回避 A/B。不要重开第 4–7 刀。

## 6. 测试与验收口径

- 不要新开测试文件。默认改 `issue-composer-chrome.test.ts:274-275`：把对写死「自定义字段（可选）」和「加载中...」的冻结，改成断言对应 `$t` 调用出现，并用带周围 markup 的精确整句确认 `title="自定义字段（可选）"`、`description="加载中..."` 不再出现。禁止宽泛的 `not.toContain('加载中')` / `('自定义字段')`。
- 同一文件内，已有 `composer` 表、`schemaLeaves('issueComposer')` / `leafKeys` 与 `createCalls` / `editCalls` 必须扩到 21 叶，并钉死上表调用次数（含另一页为 0）。不得改旧 19 叶的键值或次数。`:271-273`（请输入问题标题 / 问题创建成功 / 问题创建失败）与 `:276-284`（`insertText` 种子）保持原断言。
- 真实 `@/locales` 切换 `zh-CN` / `en-US`。不要自己造一套残缺 messages。测试必须读取 typings 源文件，三份文件键齐全，不能只比较两份 locale。`en-us.ts` 无汉字。
- 四门对照当次干净 `8cfc5fbe49f0541faec3e1975b9e8b9029593c58` 基线。tsc/eslint 基线非 0 则保持 added 0 / removed 0，忽略行号，用 eslint 汇总行。不得写成全绿，不得借用先前刀子的失败行号当终值。不能写 dual Grok Approve。
- 不要求本刀截图作为验收门。若实施时拿得到，只作为附证。
- 证据包必须含每一笔提交相对其第一父提交的 name-only、diffstat 与完整 diff，以及相对精确 base 的 `final.diff`。不得只用 `final.diff`。第一笔（docs）的分笔 diff 须恰好是两份 docs；第二笔须恰好是其余 6 个产品路径。两份 docs 须与已批原文逐字节一致。须有各笔 strace 与四门日志。若后来多出修订笔，每一笔同样要有这三份，不要 amend 前序提交来补证据。

## 7. 限制（写入验收说明）

- 第一次在仓库根提交若再出现 `Script not found "sa"`，必须 STOP 并记入限制；plan 已收入第 4 刀已接受的根 hook 拷贝与 gitignore 相对软链步骤，避免再踩同一坑，但那不是改 hook 正文。
- commit hook EXIT 0 不是路径证明，需要 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。若 hook 读到 `frontend/.git/COMMIT_EDITMSG` 或同类 ENOENT，STOP，保留原件，不要二次重试，不要改 verifier。
- `.env.prod` 不得入库、不得把正文写入证据包。prod build 只允许使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核 `.env.prod` 副本；哈希不符或缺失则该门记 EXIT STOP，不用 `.env.example` 顶替，也不把 `.env.example` 拷成 `.env.prod`（即使它碰巧同哈希）。缺失已核 `.env.prod` 不得挡住 clone、红测与其它门禁，也不因此中断这些步骤。Yuri 已在本机确认当前没有任何名为 `.env.prod` 的文件哈希等于该锁；这是已记录限制，不是本刀必修项。
- prod build 若弄脏 `frontend/src/typings/components.d.ts` 或 elegant-router 生成文件（`frontend/src/router/elegant/transform.ts`、`frontend/src/typings/elegant-router.d.ts`），必须从仓库根 `git checkout --` 再跑 tsc/eslint，打包还原前后 porcelain，不提交这些文件。永远不要还原白名单产品路径（包括 `app.d.ts`）。
- 列表布尔格「是/否」，以及英文列表自定义字段列上的中文「是/否」，本刀不译，直到另有授权。
- 本轮只交本地草稿。获批口令为「design ok，开写」。决定 A/B 未确认前不得实施。后续仅普通隔离 clone，不用 worktree。未经再授权不 push、不开 PR、不 merge、不部署。

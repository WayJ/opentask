# SLA 与回收站英文铬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 只将已批 SLA 策略/新建策略/假日包卡铬与回收站页铬接入 zh/en，并把回收站状态/优先级从原值接到既有 label table，不改业务行为。

**Architecture:** 扩展 `page.sla`，新增同级 `page.issueTrash` 对象并同步 App.I18n.Schema；新脚本铬调用统一 `$t`（从 `@/locales` 导入），旧 SLA `t` 绑定保留。两页 columns、pack 筛选 options 用先读 locale 的 computed；trash 空态 helper 用 `$t`，外层 computed 先读 locale。复用 `useLabelTable` + `lookupLabel`，不改 enums/API。

**Tech Stack:** Vue 3.5、vue-i18n、Naive-UI、Vitest 4、Vue Test Utils、Pinia、已有 `$t` / label-table / App.I18n.Schema，无新依赖。

## Global Constraints

- 本轮只交本地草稿；获批口令为「design ok，开写」，不是现在执行。Yuri 决策 A/B 未确认前不得实施。
- 精确 base：`5bc1f604a22aad1517eaeae16ada004ba14fc11a`（PR14 tip，`cursor/issue-form-property-en-chrome-4333`）。不改写 PR6–14 已存提交。
- 后续仅普通隔离 clone（`.git` 为目录），不用 worktree；不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`，不改已有实施检出或既有服务。
- 不买额度，不 merge，不部署；未经后续授权不 push、不开 PR。本轮不建产品分支、不改产品、不 TDD、不 commit、不联系任何人。

- 设计决策 A（删→删除/Remove）与 B（含新建卡内部铬）均待 Yuri 确认；本计划按推荐案写，若否决先修订文档，不执行旧合同。后续 TDD 用 superpowers:test-driven-development；文档内代码不是本轮产品变更。
- 全部新文案逐字锁定在下表；route.settings_sla 与 route.issue_trash 不改；回收站页内标题不用 route，列不用 issueList，刷新不用 common。
- 不改 `constants/issue.ts`、枚举值、`policy-name.ts`、`residual-copy.test.ts`、列表铬测试、issue-form 测试、Business hours 绑定、help/holidayIntro/runDue/defaultPolicyName、toast、readonly banner、restore success、包数据/API。英文 open=Open，critical=Urgent；zh 待办/紧急。
- 每个 RED/GREEN 保存 HEAD、porcelain、测试原件、diff、COMMAND/CWD/TZ、stdout/stderr/EXIT 到仓库外证据目录。没有独立 Approve 行，不声称双 Grok Approve；不买额度。
- 仅新 clone 删除 pre-commit，保留 commit-msg；core.hooksPath 保持空（若已配置非空先 STOP，不改全局设置），不用 SKIP/--no-verify。正常根目录 commit；EXIT 0 不是 hook 路径证明。遇 frontend/.git/COMMIT_EDITMSG 或类似 ENOENT 立即 STOP，留原件，不重试、不改 verifier。
- 不运行 eslint --fix。不复用第 2 刀测试数量/失败行数作本刀 baseline。不用旧测试数字冒充全绿。四门从 frontend/ 执行，Vite 使用仓库外 config、cacheDir、outDir，不空挂 .vite、不清空生成文件。

### 白名单（12 路径）

- `docs/superpowers/specs/2026-11-12-sla-trash-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-sla-trash-en-chrome.md`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/views/settings/sla/index.vue`
- `frontend/src/views/settings/sla/__tests__/labels.test.ts`
- `frontend/src/locales/__tests__/sla-trash-chrome.test.ts`
- `frontend/src/views/issue/trash/index.vue`
- `frontend/src/utils/issueTrashMeta.ts`
- `frontend/src/utils/issueTrashMeta.test.ts`
- `frontend/src/views/issue/trash/__tests__/chrome.test.ts`

### 锁定新增 keys（两份文档均列全）

`page.sla`，28 个：

| 键 | zh-CN | en-US |
|---|---|---|
| `policies` | SLA 策略 | SLA policies |
| `refresh` | 刷新 | Refresh |
| `newPolicy` | 新建策略 | New policy |
| `name` | 名称 | Name |
| `startStopStatuses` | 启停状态 | Start and stop statuses |
| `enabled` | 启用 | Enabled |
| `actions` | 操作 | Actions |
| `minutes` | {n} 分钟 | {n} min |
| `holidayPack` | 假日包 | Holiday pack |
| `holidayPacks` | 假日包 | Holiday packs |
| `clearOverride` | 清除覆盖 | Clear override |
| `delete` | 删除 | Delete |
| `notifyAssignee` | 通知负责人 | Notify assignee |
| `notifyWatchers` | 通知关注者 | Notify watchers |
| `calendarOverride` | 日历覆盖 | Calendar override |
| `calendarOverrideHint` | 关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承 | Off inherits the workspace. When on, only filled fields override; the rest still inherit. |
| `timezoneOverride` | 时区覆盖 | Time zone override |
| `inheritWorkspace` | （继承工作区） | (Inherit workspace) |
| `exceptionOverride` | 例外覆盖（填写则整表替换 WS 例外；留空=继承） | Exception override (a filled table replaces workspace exceptions; empty inherits) |
| `create` | 创建 | Create |
| `allRegions` | 全部地区 | All regions |
| `allYears` | 全部年份 | All years |
| `region` | 地区 | Region |
| `year` | 年份 | Year |
| `packTitle` | 国家/地区假日包（一键合并例外日） | Country and region holiday packs (merge exception days) |
| `preview` | 预览 | Preview |
| `applyPack` | 确认应用 | Apply |
| `packPreviewSummary` | 变更：+{added} / 覆盖 {replaced} / 保留 {kept} （{before} → {after}） | Changes: +{added} / replaced {replaced} / kept {kept} ({before} → {after}) |

`page.issueTrash`，11 个：

| 键 | zh-CN | en-US |
|---|---|---|
| `title` | 回收站 | Trash |
| `backToList` | 返回列表 | Back to list |
| `refresh` | 刷新 | Refresh |
| `empty` | 回收站为空 | Trash is empty |
| `key` | 编号 | Key |
| `issueTitle` | 标题 | Title |
| `status` | 状态 | Status |
| `priority` | 优先级 | Priority |
| `updatedAt` | 更新时间 | Updated |
| `actions` | 操作 | Actions |
| `restore` | 恢复 | Restore |

已有 `addException`=添加例外 / Add exception 和 `removeException`=删除 / Remove 复用；packAdded/packReplaced 保留。holidayPack 是策略行单数动作，holidayPacks 是包集合卡标题。除决策 A 的删→删除外不调整中文，英文采用表中 sentence case，未另改建议措辞。

---

### Task 0: 获批后隔离、当次基线、docs-only commit

**Files:** 仅上述两份 docs。**Consumes:** 精确 `5bc1f604a22aad1517eaeae16ada004ba14fc11a` 与批准后的本地两文档。**Produces:** 普通 clone 的文档提交、仓库外 baseline 原件。

- [ ] **Step 1: 在远端执行环境（不是当前 box）建全新普通 clone**

下面是获批后的命令，不在本轮执行；先确认目标不存在，不复用旧检出。不写/reset main 244c 或 pin 250fc，不改 PR6–14 已存提交。

```bash
export TZ=Asia/Shanghai
export REPO=/tmp/cursor/opentask-sla-trash-en-chrome-clone
export EVIDENCE=/tmp/cursor/opentask-readonly/sla-trash-en-chrome-logs
test ! -e "$REPO" || exit 1
mkdir -p "$EVIDENCE"
git clone https://github.com/WayJ/opentask.git "$REPO"
cd "$REPO"
git switch --detach 5bc1f604a22aad1517eaeae16ada004ba14fc11a
test -d .git || exit 1
test "$(git rev-parse HEAD)" = 5bc1f604a22aad1517eaeae16ada004ba14fc11a || exit 1
test -z "$(git status --porcelain)" || exit 1
test -z "$(git config --get core.hooksPath)" || exit 1
git switch -c cursor/sla-trash-en-chrome-4333
cd "$REPO/frontend"
pnpm install --frozen-lockfile
cd "$REPO"
test -f .git/hooks/commit-msg || exit 1
rm -f .git/hooks/pre-commit
sha256sum .git/hooks/commit-msg > "$EVIDENCE/commit-msg.sha256"
git status --porcelain > "$EVIDENCE/checkout-porcelain.txt"
test ! -s "$EVIDENCE/checkout-porcelain.txt" || exit 1
```

安装若 hooks 不存在/位置不符则停止交事实，不自行装新 verifier。`.env.prod` 从先前已核干净来源拷贝（sha256 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`，1896 字节）；缺原件则 STOP。不手写、不用 .env.example 替代、不记录 env 正文或键值。依赖安装和环境文件准备后重新确认 tracked diff 为空。只记 `loadEnv('prod')` 前缀非空及长度。旧服务 9541/9544 不动。

- [ ] **Step 2: 构造仓库外 config，先在干净 base 跑四门**

在执行环境用下面脚本生成 config；导入原有 vite config，但 root 明确指回 frontend，cacheDir/outDir 指向证据目录，server 不自动打开浏览器。原 config 是 default defineConfig 的常量或函数都支持；不用手写产品配置。

```bash
cd "$REPO/frontend"
node --input-type=module <<'JS'
import { writeFileSync } from 'node:fs';
const root = process.cwd();
const evidence = process.env.EVIDENCE;
writeFileSync(`${evidence}/vite.readonly.config.mjs`, `
import original from ${JSON.stringify(root + '/vite.config.ts')};
export default async env => {
  const resolved = typeof original === 'function' ? await original(env) : await original;
  return {
    ...resolved,
    root: ${JSON.stringify(root)},
    cacheDir: ${JSON.stringify(evidence + '/vite-cache')},
    build: { ...(resolved.build || {}), outDir: ${JSON.stringify(evidence + '/dist')} },
    server: { ...(resolved.server || {}), open: false, host: '127.0.0.1', port: 9563, strictPort: true }
  };
};
`);
JS
```

该 config 结构参照 source/inventory-vite.readonly.config.mjs；若原 config import 或依赖解析失败保留错误、停下修订外部 config，不改 repo config。四门 runner 写在仓库外（baseline 与最终各运行一次同命令）：

```bash
cat > "$EVIDENCE/run-gates.sh" <<'SH'
#!/usr/bin/env bash
set -u
phase="$1"
cd "$REPO/frontend" || exit 1
run() {
  name="$1"; shift
  dir="$EVIDENCE/$phase/$name"; mkdir -p "$dir"
  { printf 'CWD=%s
TZ=%s
' "$PWD" "$TZ"; printf 'COMMAND='; printf '%q ' "$@"; printf '
'; git rev-parse HEAD; git status --porcelain; } > "$dir/meta.txt"
  "$@" > "$dir/stdout.txt" 2> "$dir/stderr.txt"
  rc=$?; printf 'EXIT=%s
' "$rc" >> "$dir/meta.txt"
}
run vitest pnpm exec vitest run
run build pnpm exec vite build --mode prod --config "$EVIDENCE/vite.readonly.config.mjs"
run tsc pnpm exec vue-tsc --noEmit --skipLibCheck
run eslint pnpm exec eslint .
SH
bash "$EVIDENCE/run-gates.sh" baseline
```

baseline HEAD 必须仍是精确 base、tracked diff 空。vitest/build 必须 EXIT 0 才继续；tsc/lint 若非 0 保留逐条诊断，不修范围外问题。build 前后比较 tracked diff（含生成文件）、生成文件 hash；意外改动就 STOP，不自行 reset。安装/env/config 的实际命令和来源也存档。

- [ ] **Step 3: 文档先行，恰好两文件提交**

把**已批**本地文件逐字节放入 docs，比较拷贝前后 sha256。执行环境若拿不到已批原件则停止，不从未批草稿复刻。

```bash
cd "$REPO"
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp /workspace/designs/sla-trash-en-chrome-spec/2026-11-12-sla-trash-en-chrome-design.md docs/superpowers/specs/
cp /workspace/designs/sla-trash-en-chrome-spec/2026-11-12-sla-trash-en-chrome.md docs/superpowers/plans/
cmp /workspace/designs/sla-trash-en-chrome-spec/2026-11-12-sla-trash-en-chrome-design.md docs/superpowers/specs/2026-11-12-sla-trash-en-chrome-design.md
cmp /workspace/designs/sla-trash-en-chrome-spec/2026-11-12-sla-trash-en-chrome.md docs/superpowers/plans/2026-11-12-sla-trash-en-chrome.md
git add docs/superpowers/specs/2026-11-12-sla-trash-en-chrome-design.md docs/superpowers/plans/2026-11-12-sla-trash-en-chrome.md
git diff --cached --name-only
# 人工核恰好上述两个路径；不是则停止。
git commit -m "docs: specify SLA and trash English chrome"
test "$(git rev-parse HEAD^)" = 5bc1f604a22aad1517eaeae16ada004ba14fc11a || exit 1
test -z "$(git status --porcelain)" || exit 1
```

保存提交 stdout/stderr/EXIT 与正常 hooks 路径证据；没有路径原件就写「未证明 commit-msg 读了本 checkout」，不拿成功提交代替。ENOENT 不第二次 retry。

---

### Task 1: tests-only RED（不改产品，不另强制 RED commit）

**Files:** 新建 `frontend/src/locales/__tests__/sla-trash-chrome.test.ts`、`frontend/src/views/issue/trash/__tests__/chrome.test.ts`；仅适配 `sla/__tests__/labels.test.ts` 查询与 `utils/issueTrashMeta.test.ts` empty 测试。
**Consumes:** base 上无新键、两页中文铬和 raw row 标签。**Produces:** 精确缺失键/接线/fixture 失败的 RED 原件；旧行为测试保留。

- [ ] **Step 1: 新建源码/Schema/文案合同测试（完整文件）**

新 namespace 暂用 Record cast，避免 RED 被 TS 字段不存在完全挡住；GREEN Schema 完整性由 walker 与四门补上。walker 递归扫 object 的 string leaf，定位必须是对象，不是 route 键。源测试严格匹配调用、模板绑定和原值 render。

```ts
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

const source = (path: string) => readFileSync(resolve(path), 'utf8');
const slaSource = source('src/views/settings/sla/index.vue');
const trashSource = source('src/views/issue/trash/index.vue');
const metaSource = source('src/utils/issueTrashMeta.ts');
const typings = source('src/typings/app.d.ts');
const digest = (text: string) => createHash('sha256').update(text).digest('hex');
const slaCopy = [
  ['policies', 'SLA 策略', 'SLA policies'],
  ['refresh', '刷新', 'Refresh'],
  ['newPolicy', '新建策略', 'New policy'],
  ['name', '名称', 'Name'],
  ['startStopStatuses', '启停状态', 'Start and stop statuses'],
  ['enabled', '启用', 'Enabled'],
  ['actions', '操作', 'Actions'],
  ['minutes', '{n} 分钟', '{n} min'],
  ['holidayPack', '假日包', 'Holiday pack'],
  ['holidayPacks', '假日包', 'Holiday packs'],
  ['clearOverride', '清除覆盖', 'Clear override'],
  ['delete', '删除', 'Delete'],
  ['notifyAssignee', '通知负责人', 'Notify assignee'],
  ['notifyWatchers', '通知关注者', 'Notify watchers'],
  ['calendarOverride', '日历覆盖', 'Calendar override'],
  ['calendarOverrideHint', '关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承', 'Off inherits the workspace. When on, only filled fields override; the rest still inherit.'],
  ['timezoneOverride', '时区覆盖', 'Time zone override'],
  ['inheritWorkspace', '（继承工作区）', '(Inherit workspace)'],
  ['exceptionOverride', '例外覆盖（填写则整表替换 WS 例外；留空=继承）', 'Exception override (a filled table replaces workspace exceptions; empty inherits)'],
  ['create', '创建', 'Create'],
  ['allRegions', '全部地区', 'All regions'],
  ['allYears', '全部年份', 'All years'],
  ['region', '地区', 'Region'],
  ['year', '年份', 'Year'],
  ['packTitle', '国家/地区假日包（一键合并例外日）', 'Country and region holiday packs (merge exception days)'],
  ['preview', '预览', 'Preview'],
  ['applyPack', '确认应用', 'Apply'],
  ['packPreviewSummary', '变更：+{added} / 覆盖 {replaced} / 保留 {kept} （{before} → {after}）', 'Changes: +{added} / replaced {replaced} / kept {kept} ({before} → {after})'],
] as const;
const trashCopy = [
  ['title', '回收站', 'Trash'],
  ['backToList', '返回列表', 'Back to list'],
  ['refresh', '刷新', 'Refresh'],
  ['empty', '回收站为空', 'Trash is empty'],
  ['key', '编号', 'Key'],
  ['issueTitle', '标题', 'Title'],
  ['status', '状态', 'Status'],
  ['priority', '优先级', 'Priority'],
  ['updatedAt', '更新时间', 'Updated'],
  ['actions', '操作', 'Actions'],
  ['restore', '恢复', 'Restore'],
] as const;
const oldSlaKeys = [
  "runDue",
  "help",
  "businessHours",
  "metricPlaceholder",
  "startPlaceholder",
  "stopPlaceholder",
  "pausePlaceholder",
  "targetPlaceholder",
  "windowPlaceholder",
  "pauseHint",
  "priorityRule",
  "firstResponseNote",
  "closingStatuses",
  "startPrefix",
  "stopPrefix",
  "pausePrefix",
  "targetWorkspace",
  "targetPolicy",
  "choosePolicy",
  "defaultPolicyName",
  "nameRequired",
  "holidayIntro",
  "hoursIntro",
  "hoursEnabled",
  "weekdayPreset",
  "hoursWindowPlaceholder",
  "exceptionDays",
  "noExceptions",
  "defaultWindow",
  "addException",
  "removeException",
  "weekday.mon",
  "weekday.tue",
  "weekday.wed",
  "weekday.thu",
  "weekday.fri",
  "weekday.sat",
  "weekday.sun",
  "saveHours",
  "hoursSaved",
  "packAdded",
  "packReplaced",
  "regionCN",
  "regionUS",
  "regionEU",
  "regionUK",
  "metric.time_in_status",
  "metric.first_response",
  "exception.closed",
  "exception.forced_open"
];
const preservedCopy = {
  "zh-cn": {
    "help": "支持「状态停留」和「首次响应」两种度量。默认按墙钟分钟；启用营业时段后按营业分钟。首次响应：不是创建者的第一条评论即满足，指派负责人不算。结束状态留空时，进入已解决、已关闭或已拒绝即满足。进入暂停状态时不计时，离开后按剩余时间继续。没有内置定时任务（cron）。请用外部调度调用 POST /api/sla/run-due。",
    "businessHours": "营业时段",
    "holidayIntro": "精选静态包（中国、美国、欧盟、英国 · 2026/2027）。预览后应用到本工作区营业例外，或某个策略的日历。同日以包为准覆盖；包外例外保留。无外网同步。",
    "defaultPolicyName": "进行中停留",
    "runDue": "立即执行到期检查"
  },
  "en-us": {
    "help": "Two metrics: time in status and first response. Minutes use the wall clock unless business hours are on. First response is the first comment by someone other than the creator. Assignment does not count. If no stop status is set, resolved, closed, or rejected completes it. Pause statuses do not count; the clock resumes with the time left. There is no built-in scheduler (cron). Call POST /api/sla/run-due from an external scheduler.",
    "businessHours": "Business hours",
    "holidayIntro": "Static packs for China, the United States, the European Union, and the United Kingdom, 2026 and 2027. Preview, then apply them to this workspace or to a policy calendar. The pack wins on the same date. Other exceptions stay. No network sync.",
    "defaultPolicyName": "Time in progress",
    "runDue": "Run due checks"
  }
};
const slaCalls = {
  "policies": 1,
  "refresh": 1,
  "newPolicy": 1,
  "name": 2,
  "startStopStatuses": 1,
  "enabled": 1,
  "actions": 1,
  "minutes": 1,
  "holidayPack": 1,
  "holidayPacks": 1,
  "clearOverride": 1,
  "delete": 1,
  "notifyAssignee": 1,
  "notifyWatchers": 1,
  "calendarOverride": 1,
  "calendarOverrideHint": 1,
  "timezoneOverride": 1,
  "inheritWorkspace": 1,
  "exceptionOverride": 1,
  "create": 1,
  "allRegions": 1,
  "allYears": 1,
  "region": 1,
  "year": 1,
  "packTitle": 1,
  "preview": 1,
  "applyPack": 1,
  "packPreviewSummary": 1
};
const trashCalls = {
  "title": 1,
  "backToList": 1,
  "refresh": 1,
  "key": 1,
  "issueTitle": 1,
  "status": 1,
  "priority": 1,
  "updatedAt": 1,
  "actions": 1,
  "restore": 1
};

function keysOf(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    keysOf(child, prefix ? `${prefix}.${key}` : key)
  );
}

function schemaKeys(namespace: 'sla' | 'issueTrash'): string[] {
  const match = new RegExp(`(?:^|[\n\r;{])\\s*${namespace}\\s*:\\s*\\{`).exec(typings);
  if (!match) return [];
  const start = typings.indexOf('{', match.index);
  const tokens = typings.slice(start).replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, '').match(/[A-Za-z_]\w*|[{}:;,]/g) ?? [];
  let index = 0;
  function walk(prefix: string): string[] {
    const leaves: string[] = [];
    expect(tokens[index++]).toBe('{');
    while (tokens[index] !== '}' && index < tokens.length) {
      if (tokens[index] === ';' || tokens[index] === ',') {
        index += 1;
      } else {
        const key = tokens[index++];
        expect(tokens[index++]).toBe(':');
        const path = prefix ? `${prefix}.${key}` : key;
        if (tokens[index] === '{') leaves.push(...walk(path));
        else { expect(tokens[index++]).toBe('string'); leaves.push(path); }
      }
    }
    expect(tokens[index++]).toBe('}');
    return leaves;
  }
  return walk('').sort();
}

function calls(text: string, namespace: string, key: string): number {
  const token = `$t('${namespace}.${key}'`;
  return text.split(token).length - 1;
}
const messages = (text: string) => (text.match(/window\.\$message[\s\S]*?;/g) ?? []).map(s => s.replace(/\s+/g, ' ').trim());

describe('SLA and trash chrome contract', () => {
  it('locks every new key, existing SLA leaves, and object Schema shapes', () => {
    for (const lang of [zh, en]) {
      const page = lang.page as unknown as Record<string, Record<string, unknown>>;
      expect(keysOf(page.sla).sort()).toEqual([...oldSlaKeys, ...slaCopy.map(([key]) => key)].sort());
      expect(keysOf(page.issueTrash).sort()).toEqual(trashCopy.map(([key]) => key).sort());
      expect(schemaKeys('sla')).toEqual(keysOf(page.sla).sort());
      expect(schemaKeys('issueTrash')).toEqual(keysOf(page.issueTrash).sort());
      const columnTitle = page.issueTrash?.issueTitle;
      expect(columnTitle).not.toBe(page.issueTrash?.title);
    }
    for (const [index, lang] of [zh, en].entries()) {
      const page = lang.page as unknown as Record<string, Record<string, unknown>>;
      for (const [key, z, e] of slaCopy) expect(page.sla[key]).toBe(index === 0 ? z : e);
      for (const [key, z, e] of trashCopy) expect(page.issueTrash?.[key]).toBe(index === 0 ? z : e);
      expect(Object.fromEntries(Object.keys(preservedCopy['zh-cn']).map(key => [key, page.sla[key]])))
        .toEqual(preservedCopy[index === 0 ? 'zh-cn' : 'en-us']);
    }
    expect(zh.route.settings_sla).toBe('SLA 策略');
    expect(en.route.settings_sla).toBe('SLA');
    expect(zh.route.issue_trash).toBe('回收站');
    expect(en.route.issue_trash).toBe('Trash');
    expect([zh.page.issueStatus.open, en.page.issueStatus.open]).toEqual(['待办', 'Open']);
    expect([zh.page.issuePriority.critical, en.page.issuePriority.critical]).toEqual(['紧急', 'Urgent']);
    expect([zh.page.sla.addException, en.page.sla.addException]).toEqual(['添加例外', 'Add exception']);
    expect([zh.page.sla.removeException, en.page.sla.removeException]).toEqual(['删除', 'Remove']);
    expect([zh.page.sla.packAdded, en.page.sla.packAdded]).toEqual(['新增', 'Added']);
    expect([zh.page.sla.packReplaced, en.page.sla.packReplaced]).toEqual(['覆盖', 'Replaced']);
  });

  it('counts real translator call sites and binds card titles', () => {
    // 去掉注释后数调用，不能向注释填 token 冒充接线。
    const stripComments = (text: string) => text.replace(/<!--[\s\S]*?-->|\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, '');
    for (const [key, count] of Object.entries(slaCalls)) expect(calls(stripComments(slaSource), 'page.sla', key), key).toBe(count);
    for (const [key, count] of Object.entries(trashCalls)) expect(calls(stripComments(trashSource), 'page.issueTrash', key), key).toBe(count);
    expect(calls(stripComments(metaSource), 'page.issueTrash', 'empty')).toBe(1);
    expect(calls(stripComments(slaSource), 'page.sla', 'addException')).toBe(2);
    expect(calls(stripComments(slaSource), 'page.sla', 'removeException')).toBe(2);
    for (const key of ['policies', 'newPolicy', 'holidayPacks']) {
      expect(slaSource).toContain(`:title="$t('page.sla.${key}')"`);
    }
    expect(trashSource).toContain(`:title="$t('page.issueTrash.title')"`);
    expect(slaSource).toContain(`:placeholder="$t('page.sla.name')"`);
    expect(trashSource).not.toContain("$t('route.issue_trash')");
    expect(trashSource).not.toContain('page.issueList.columns.');
    expect(slaSource).toContain("const columns = computed<DataTableColumns<SlaPolicyRow>>(() => {\n  void locale.value;\n  return [");
    expect(trashSource).toContain("const columns = computed<DataTableColumns<Api.Issue.Issue>>(() => {\n  void locale.value;\n  return [");
    for (const name of ['packRegionFilterOptions', 'packYearFilterOptions']) {
      expect(slaSource).toContain(`const ${name} = computed(() => {\n  void locale.value;\n  return [`);
    }
    expect(trashSource).toContain("useLabelTable('page.issueStatus')");
    expect(trashSource).toContain("useLabelTable('page.issuePriority')");
    expect(trashSource).toContain('lookupLabel(statusLabels.value, row.status)');
    expect(trashSource).toContain('lookupLabel(priorityLabels.value, row.priority)');
    expect(trashSource).toContain('const emptyHint = computed(() => {\n  void locale.value;\n  return trashEmptyHint();\n});');
    expect(trashSource).toContain(':description="emptyHint"');
    expect(metaSource).toContain("return $t('page.issueTrash.empty');");
    expect(slaSource).toContain("$t('page.sla.minutes', { n: row.targetMinutes })");
    expect(slaSource).toContain("$t('page.sla.packPreviewSummary', {");
    for (const binding of ['added: (packPreview.added || []).length', 'replaced: (packPreview.replaced || []).length', 'kept: (packPreview.unchanged || []).length', 'before: packPreview.countBefore', 'after: packPreview.countAfter']) expect(slaSource).toContain(binding);
  });

  it('removes only the exact in-scope literal contexts', () => {
    for (const text of ['title="SLA 策略"', 'title="新建策略"', 'title="假日包"', 'placeholder="名称"', 'placeholder="地区"', 'placeholder="年份"', "title: '名称'", "title: '启停状态'", "title: '启用'", "title: '操作'", "'全部地区'", "'全部年份'", "default: () => '假日包'", "default: () => '清除覆盖'", "default: () => '删除'", "label: '（继承工作区）'", '${row.targetMinutes} 分钟', '>通知负责人<', '>通知关注者<', '>日历覆盖<', '>时区覆盖<', '>关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承<', '}} 国家/地区假日包（一键合并例外日）']) expect(slaSource).not.toContain(text);
    for (const regex of [/^\s+刷新\s*$/m, /^\s+预览\s*$/m, /^\s+确认应用\s*$/m, /^\s+删\s*$/m, /^\s+例外覆盖（填写则整表替换 WS 例外；留空=继承）\s*$/m, /^\s+变更：\+/m, />刷新<\/NButton>/, />预览<\/NButton>/, />创建<\/NButton>/, />添加例外<\/NButton>/]) expect(slaSource).not.toMatch(regex);
    for (const text of ['title="回收站"', "title: '编号'", "title: '标题'", "title: '状态'", "title: '优先级'", "title: '更新时间'", "title: '操作'", 'default: () => row.status', 'default: () => row.priority', "default: () => '恢复'"]) expect(trashSource).not.toContain(text);
    for (const regex of [/^\s+返回列表\s*$/m, /^\s+刷新\s*$/m, />返回列表<\/NButton>/, />刷新<\/NButton>/]) expect(trashSource).not.toMatch(regex);
  });

  it('freezes out-of-scope messages, Business hours, and policy-name implementation', () => {
    expect(messages(slaSource)).toEqual([
  "window.$message?.error?.(t('page.sla.choosePolicy'));",
  "window.$message?.error?.(error?.message || '预览失败');",
  "window.$message?.error?.(t('page.sla.choosePolicy'));",
  "window.$message?.error?.(error?.message || '应用失败');",
  "window.$message?.success?.(`已应用：+${(data.added || []).length} 覆盖${(data.replaced || []).length}`);",
  "window.$message?.error?.(e?.message || '时段非法');",
  "window.$message?.error?.(error?.message || '保存失败');",
  "window.$message?.success?.(t('page.sla.hoursSaved'));",
  "window.$message?.error?.(e?.message || '例外日非法');",
  "window.$message?.error?.(error.message || '加载失败');",
  "window.$message?.warning?.(t('page.sla.nameRequired'));",
  "window.$message?.error?.(e?.message || '日历覆盖无效');",
  "window.$message?.error?.(error.message || '创建失败');",
  "window.$message?.success?.('已创建');",
  "window.$message?.error?.(error.message || '更新失败');",
  "window.$message?.error?.(error.message || '删除失败');",
  "window.$message?.success?.('已删除');",
  "window.$message?.error?.(error.message || '清除失败');",
  "window.$message?.success?.('已清除日历覆盖');",
  "window.$message?.error?.(e?.message || '例外无效');",
  "window.$message?.error?.(error.message || '执行失败');",
  "window.$message?.success?.( `扫描 ${data?.scanned ?? 0} · 违约 ${data?.breached ?? 0} · 通知 ${data?.notificationsCreated ?? 0}` );"
]);
    expect(messages(trashSource)).toEqual([
  "window.$message?.error('加载回收站失败');",
  "window.$message?.success(restoreSuccessMessage(row.issue_code || ''));",
  "window.$message?.error('恢复失败（需要 member 权限）');"
]);
    const start = slaSource.indexOf(`    <NCard :title="$t('page.sla.businessHours')"`);
    const end = slaSource.indexOf('    </NCard>', start) + '    </NCard>'.length;
    expect(start).toBeGreaterThan(-1);
    expect(digest(slaSource.slice(start, end))).toBe("5dbec96843fec4652d92d7f8a4e4908a781cfe707b62342465a84a96688558ad");
    expect(digest(source('src/views/settings/sla/policy-name.ts'))).toBe("ec9f5d1110650696459a6817427cca72eb58a97e7a93e507b1864c0b04a87daa");
    expect(metaSource).toContain("return c ? `已恢复 ${c}` : '已恢复';");
    expect(metaSource).toContain("return '此问题已在回收站中，只读。恢复后可继续编辑。';");
  });
});
```

- [ ] **Step 2: 非空 fixture 渲染测试（完整文件）**

`frontend/src/views/issue/trash/__tests__/chrome.test.ts`。NDataTable stub 只替代库容器，真实页面的 computed columns 与 render 函数照常执行；不是另写一套翻译模拟。NCard stub 显式渲染 title/header-extra，避免 labels 原有 stub 漏标题。未知值第二行证明 fallback；同一次 mount 内 setLocale，API 不重新取数。空态独立 mount 测试只证明 empty，不代替行标签测试。

```ts
import { defineComponent, h, type PropType, type VNodeChild } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { i18n, setLocale } from '@/locales';
import TrashPage from '../index.vue';

const api = vi.hoisted(() => ({ listTrash: vi.fn(), restoreIssue: vi.fn() }));
vi.mock('@/service/api/issue', () => ({ issueApi: api }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }));

type Row = Record<string, unknown>;
type Column = { key: string; title: string; render?: (row: Row) => VNodeChild };
const Table = defineComponent({
  props: {
    columns: { type: Array as PropType<Column[]>, default: () => [] },
    data: { type: Array as PropType<Row[]>, default: () => [] }
  },
  setup(props) {
    return () => h('table', [
      h('thead', [h('tr', props.columns.map(c => h('th', { key: c.key }, c.title)))]),
      h('tbody', props.data.map((row, index) => h('tr', { key: index }, props.columns.map(c =>
        h('td', { key: c.key }, [c.render ? c.render(row) : String(row[c.key] ?? '')])
      ))))
    ]);
  }
});
const Card = defineComponent({
  props: { title: String },
  setup(props, { slots }) {
    return () => h('section', [h('h1', props.title), slots['header-extra']?.(), slots.default?.()]);
  }
});
const pass = (tag: string) => defineComponent({
  setup(_, { slots }) { return () => h(tag, slots.default?.()); }
});
const Empty = defineComponent({
  props: { description: String },
  setup(props) { return () => h('p', { class: 'empty' }, props.description); }
});
const stubs = { NCard: Card, NDataTable: Table, NButton: pass('button'), NTag: pass('span'), NSpace: pass('div'), NEmpty: Empty, NPagination: true };
const renderTrash = () => mount(TrashPage, { global: { plugins: [i18n], stubs } });
let wrapper: ReturnType<typeof renderTrash> | undefined;

beforeEach(() => {
  vi.clearAllMocks();
  setActivePinia(createPinia());
  setLocale('zh-CN');
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  setLocale('zh-CN');
});

describe('trash fixture rows and locale reactivity', () => {
  it('renders stored enum values with current labels, without remounting', async () => {
    api.listTrash.mockResolvedValue({ data: { rows: [
      { id: 'fixture-1', issue_code: 'WAY-1', title: 'Fixture issue', status: 'open', priority: 'critical' },
      { id: 'fixture-2', issue_code: 'WAY-2', title: 'Unknown enums', status: 'future_status', priority: 'future_priority' }
    ], total: 2 } });
    wrapper = renderTrash();
    await flushPromises();
    expect(api.listTrash).toHaveBeenCalledWith({ page: 1, page_size: 20 });
    expect(wrapper.findAll('th').map(node => node.text())).toEqual(['编号', '标题', '状态', '优先级', '更新时间', '操作']);
    expect(wrapper.get('h1').text()).toBe('回收站');
    const firstZh = wrapper.findAll('tbody tr')[0].findAll('td').map(node => node.text());
    expect(firstZh).toEqual(['WAY-1', 'Fixture issue', '待办', '紧急', '—', '恢复']);
    expect(wrapper.findAll('tbody tr')[1].text()).toContain('future_status');
    expect(wrapper.findAll('tbody tr')[1].text()).toContain('future_priority');
    setLocale('en-US');
    await flushPromises();
    expect(wrapper.findAll('th').map(node => node.text())).toEqual(['Key', 'Title', 'Status', 'Priority', 'Updated', 'Actions']);
    expect(wrapper.get('h1').text()).toBe('Trash');
    expect(wrapper.findAll('button').map(node => node.text())).toContain('Back to list');
    expect(wrapper.findAll('button').map(node => node.text())).toContain('Refresh');
    const firstEn = wrapper.findAll('tbody tr')[0].findAll('td').map(node => node.text());
    expect(firstEn).toEqual(['WAY-1', 'Fixture issue', 'Open', 'Urgent', '—', 'Restore']);
    const unknown = wrapper.findAll('tbody tr')[1].findAll('td').map(node => node.text());
    expect(unknown[2]).toBe('future_status');
    expect(unknown[3]).toBe('future_priority');
    expect(api.listTrash).toHaveBeenCalledTimes(1);
    setLocale('zh-CN');
    await flushPromises();
    expect(wrapper.findAll('tbody tr')[0].findAll('td')[2].text()).toBe('待办');
    expect(wrapper.findAll('tbody tr')[0].findAll('td')[3].text()).toBe('紧急');
  });

  it('updates the empty hint without remounting', async () => {
    api.listTrash.mockResolvedValue({ data: { rows: [], total: 0 } });
    wrapper = renderTrash();
    await flushPromises();
    expect(wrapper.find('table').exists()).toBe(false);
    expect(wrapper.get('.empty').text()).toBe('回收站为空');
    setLocale('en-US');
    await flushPromises();
    expect(wrapper.get('.empty').text()).toBe('Trash is empty');
    expect(api.listTrash).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 3: 只改旧测试的相关查询/empty 预期**

`frontend/src/views/settings/sla/__tests__/labels.test.ts` 的四处 `wrapper.get('input[placeholder="名称"]')` 全部改成下面这一个表达式；不是翻译策略名，也不删 loaded/dirty/My policy 断言，余下文件逐字保持：

```ts
wrapper.get(`input[placeholder="${i18n.global.t('page.sla.name')}"]`)
```

`frontend/src/utils/issueTrashMeta.test.ts` 完整目标如下：只 empty 新增 en 切换与 afterEach；恢复/banner 保留既有断言，banner 全句中文由新源码合同精确冻结，不把旧测试 retarget 成 trash page 标题。

```ts
import { afterEach, describe, expect, it } from 'vitest';
import { setLocale } from '@/locales';
import { deletedReadonlyBanner, restoreSuccessMessage, trashEmptyHint } from './issueTrashMeta';

afterEach(() => setLocale('zh-CN'));
describe('issueTrashMeta', () => {
  it('empty hint', () => {
    setLocale('zh-CN');
    expect(trashEmptyHint()).toBe('回收站为空');
    setLocale('en-US');
    expect(trashEmptyHint()).toBe('Trash is empty');
  });
  it('restore success includes code', () => {
    expect(restoreSuccessMessage('WAY-12')).toBe('已恢复 WAY-12');
    expect(restoreSuccessMessage('')).toBe('已恢复');
  });
  it('deleted banner', () => {
    expect(deletedReadonlyBanner()).toContain('回收站');
  });
});
```

- [ ] **Step 4: 跑 RED 并先存原件再改产品**

```bash
cd "$REPO/frontend"
mkdir -p "$EVIDENCE/red"
pnpm exec vitest run src/locales/__tests__/sla-trash-chrome.test.ts src/views/issue/trash/__tests__/chrome.test.ts src/views/settings/sla/__tests__/labels.test.ts src/utils/issueTrashMeta.test.ts > "$EVIDENCE/red/stdout.txt" 2> "$EVIDENCE/red/stderr.txt"
printf 'EXIT=%s
CWD=%s
TZ=%s
' "$?" "$PWD" "$TZ" > "$EVIDENCE/red/meta.txt"
git rev-parse HEAD >> "$EVIDENCE/red/meta.txt"
git status --porcelain > "$EVIDENCE/red/porcelain.txt"
git diff > "$EVIDENCE/red/tests.diff"
cp src/locales/__tests__/sla-trash-chrome.test.ts "$EVIDENCE/red/"
cp src/views/issue/trash/__tests__/chrome.test.ts "$EVIDENCE/red/trash-chrome.test.ts"
cp src/views/settings/sla/__tests__/labels.test.ts "$EVIDENCE/red/sla-labels.test.ts"
cp src/utils/issueTrashMeta.test.ts "$EVIDENCE/red/"
```

meta 另写上完整上述 pnpm COMMAND。预期 EXIT 非 0：新 key/Schema 缺失；calls/bound title/locale-read computed 失败；raw 标签 fixture 得 open/critical 而非待办/紧急；en empty 仍中文；labels 新占位查询 en 找不到。若只有解析/导入失败不算有效 RED，先修测试（不改产品）再存原件；已有 policyNameAfterLocaleChange 纯函数用例必须仍通过。禁止删掉 fixture 或把宽泛中文缺席当 RED 合同。尤其禁止源码宽泛 `not.toContain('回收站')` / `not.toContain('SLA 策略')` / `not.toContain('刷新')` / `not.toContain('名称')` / `not.toContain('假日包')`。

---

### Task 2: locale + Schema + SLA 接线

**Files:** 两份 locales、app.d.ts、sla/index.vue。**Consumes:** Task 1 的 RED、已批 copy（含决策 A/B）。**Produces:** 28 新 SLA 键+11 trash 键，完整 Schema 与 SLA 铬接线；trash fixture 此时仍 RED 属预期，不声称全 GREEN。

- [ ] **Step 1: 两份 locale 追加，不替换既有 sla 对象**

在 `page.sla` 内追加下面字段；在 `page` 下与 sla 并列新增 issueTrash 对象（不得放 route 或 sla 内）。保留已有 sla 所有字段/值，不能把新增片段当成 sla 的完整替代。

`frontend/src/locales/langs/zh-cn.ts`：

```ts
// 追加到已有 page.sla
      policies: 'SLA 策略',
      refresh: '刷新',
      newPolicy: '新建策略',
      name: '名称',
      startStopStatuses: '启停状态',
      enabled: '启用',
      actions: '操作',
      minutes: '{n} 分钟',
      holidayPack: '假日包',
      holidayPacks: '假日包',
      clearOverride: '清除覆盖',
      delete: '删除',
      notifyAssignee: '通知负责人',
      notifyWatchers: '通知关注者',
      calendarOverride: '日历覆盖',
      calendarOverrideHint: '关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承',
      timezoneOverride: '时区覆盖',
      inheritWorkspace: '（继承工作区）',
      exceptionOverride: '例外覆盖（填写则整表替换 WS 例外；留空=继承）',
      create: '创建',
      allRegions: '全部地区',
      allYears: '全部年份',
      region: '地区',
      year: '年份',
      packTitle: '国家/地区假日包（一键合并例外日）',
      preview: '预览',
      applyPack: '确认应用',
      packPreviewSummary: '变更：+{added} / 覆盖 {replaced} / 保留 {kept} （{before} → {after}）',

// 新增到 page（sla 的同级）
    issueTrash: {
      title: '回收站',
      backToList: '返回列表',
      refresh: '刷新',
      empty: '回收站为空',
      key: '编号',
      issueTitle: '标题',
      status: '状态',
      priority: '优先级',
      updatedAt: '更新时间',
      actions: '操作',
      restore: '恢复',
    },
```

`frontend/src/locales/langs/en-us.ts`：

```ts
// 追加到已有 page.sla
      policies: 'SLA policies',
      refresh: 'Refresh',
      newPolicy: 'New policy',
      name: 'Name',
      startStopStatuses: 'Start and stop statuses',
      enabled: 'Enabled',
      actions: 'Actions',
      minutes: '{n} min',
      holidayPack: 'Holiday pack',
      holidayPacks: 'Holiday packs',
      clearOverride: 'Clear override',
      delete: 'Delete',
      notifyAssignee: 'Notify assignee',
      notifyWatchers: 'Notify watchers',
      calendarOverride: 'Calendar override',
      calendarOverrideHint: 'Off inherits the workspace. When on, only filled fields override; the rest still inherit.',
      timezoneOverride: 'Time zone override',
      inheritWorkspace: '(Inherit workspace)',
      exceptionOverride: 'Exception override (a filled table replaces workspace exceptions; empty inherits)',
      create: 'Create',
      allRegions: 'All regions',
      allYears: 'All years',
      region: 'Region',
      year: 'Year',
      packTitle: 'Country and region holiday packs (merge exception days)',
      preview: 'Preview',
      applyPack: 'Apply',
      packPreviewSummary: 'Changes: +{added} / replaced {replaced} / kept {kept} ({before} → {after})',

// 新增到 page（sla 的同级）
    issueTrash: {
      title: 'Trash',
      backToList: 'Back to list',
      refresh: 'Refresh',
      empty: 'Trash is empty',
      key: 'Key',
      issueTitle: 'Title',
      status: 'Status',
      priority: 'Priority',
      updatedAt: 'Updated',
      actions: 'Actions',
      restore: 'Restore',
    },
```

- [ ] **Step 2: App.I18n.Schema.page 类型同步（片段为新增字段全量）**

`frontend/src/typings/app.d.ts` 既有 `page.sla` 追加下面 28 leaf；page 下另加 issueTrash，已有嵌套 metric/exception/weekday 全保留。

```ts
// 追加到 App.I18n.Schema.page.sla
          policies: string;
          refresh: string;
          newPolicy: string;
          name: string;
          startStopStatuses: string;
          enabled: string;
          actions: string;
          minutes: string;
          holidayPack: string;
          holidayPacks: string;
          clearOverride: string;
          delete: string;
          notifyAssignee: string;
          notifyWatchers: string;
          calendarOverride: string;
          calendarOverrideHint: string;
          timezoneOverride: string;
          inheritWorkspace: string;
          exceptionOverride: string;
          create: string;
          allRegions: string;
          allYears: string;
          region: string;
          year: string;
          packTitle: string;
          preview: string;
          applyPack: string;
          packPreviewSummary: string;

// App.I18n.Schema.page 下新增同级对象
        issueTrash: {
          title: string;
          backToList: string;
          refresh: string;
          empty: string;
          key: string;
          issueTitle: string;
          status: string;
          priority: string;
          updatedAt: string;
          actions: string;
          restore: string;
        };
```

- [ ] **Step 3: SLA 完整接线补丁**

下列 diff 是精确 base 的完整目标修改；保留原 render 的动作/权限/API，别重写周窗口或默认策略名 watch。新 `$t` 导入与旧 `t` 并存，避免重做已翻译绑定。格式化仅限白名单中的新测试和改动局部，保持上述测试合同/值不变；不改 Business hours 卡原字节（合同有 hash）。

```diff
--- a/frontend/src/views/settings/sla/index.vue
+++ b/frontend/src/views/settings/sla/index.vue
@@ -46,4 +46,5 @@
   weekdayPreset0918
 } from '@/utils/businessHours';
+import { $t } from '@/locales';
 import { labeledOptions, lookupLabel } from '@/locales/display-label';
 import { useLabelTable } from '@/locales/use-label-table';
@@ -139,20 +140,26 @@
 const packFilterRegion = ref<string | null>(null);
 const packFilterYear = ref<number | null>(null);
-const packRegionFilterOptions = computed(() => [
-  { label: '全部地区', value: null as string | null },
-  { label: t('page.sla.regionCN'), value: 'CN' },
-  { label: t('page.sla.regionUS'), value: 'US' },
-  { label: t('page.sla.regionEU'), value: 'EU' },
-  { label: t('page.sla.regionUK'), value: 'UK' }
-]);
+const packRegionFilterOptions = computed(() => {
+  void locale.value;
+  return [
+    { label: $t('page.sla.allRegions'), value: null as string | null },
+    { label: t('page.sla.regionCN'), value: 'CN' },
+    { label: t('page.sla.regionUS'), value: 'US' },
+    { label: t('page.sla.regionEU'), value: 'EU' },
+    { label: t('page.sla.regionUK'), value: 'UK' }
+  ];
+});
 const packTargetOptions = computed(() => [
   { label: t('page.sla.targetWorkspace'), value: 'workspace' as const },
   { label: t('page.sla.targetPolicy'), value: 'policy' as const }
 ]);
-const packYearFilterOptions = [
-  { label: '全部年份', value: null as number | null },
-  { label: '2026', value: 2026 },
-  { label: '2027', value: 2027 }
-];
+const packYearFilterOptions = computed(() => {
+  void locale.value;
+  return [
+    { label: $t('page.sla.allYears'), value: null as number | null },
+    { label: '2026', value: 2026 },
+    { label: '2027', value: 2027 }
+  ];
+});
 const packOptions = computed(() =>
   packRows.value.map(r => ({
@@ -370,68 +377,71 @@
 const metricOptions = computed(() => labeledOptions(SLA_METRICS, metricLabels.value));
 
-const columns: DataTableColumns<SlaPolicyRow> = [
-  {
-    title: '名称',
-    key: 'name',
-    render: row =>
-      h('div', [
-        h('div', { style: 'font-weight:500' }, row.name),
+const columns = computed<DataTableColumns<SlaPolicyRow>>(() => {
+  void locale.value;
+  return [
+    {
+      title: $t('page.sla.name'),
+      key: 'name',
+      render: row =>
+        h('div', [
+          h('div', { style: 'font-weight:500' }, row.name),
+          h(
+            NText,
+            { depth: 3, style: 'font-size:12px' },
+            { default: () => `${$t('page.sla.minutes', { n: row.targetMinutes })} · ${lookupLabel(metricLabels.value, row.metric)}` }
+          )
+        ])
+    },
+    {
+      title: $t('page.sla.startStopStatuses'),
+      key: 'statuses',
+      render: row =>
         h(
           NText,
           { depth: 3, style: 'font-size:12px' },
-          { default: () => `${row.targetMinutes} 分钟 · ${lookupLabel(metricLabels.value, row.metric)}` }
+          {
+            default: () =>
+              `${t('page.sla.startPrefix')}: ${(row.startStatuses || []).map(status => lookupLabel(statusLabels.value, status)).join(', ') || '—'} → ${t('page.sla.stopPrefix')}: ${(row.stopStatuses || []).map(status => lookupLabel(statusLabels.value, status)).join(', ') || t('page.sla.closingStatuses')} · ${t('page.sla.pausePrefix')}: ${(row.pauseStatuses || []).map(status => lookupLabel(statusLabels.value, status)).join(', ') || '—'}`
+          }
         )
-      ])
-  },
-  {
-    title: '启停状态',
-    key: 'statuses',
-    render: row =>
-      h(
-        NText,
-        { depth: 3, style: 'font-size:12px' },
-        {
-          default: () =>
-            `${t('page.sla.startPrefix')}: ${(row.startStatuses || []).map(status => lookupLabel(statusLabels.value, status)).join(', ') || '—'} → ${t('page.sla.stopPrefix')}: ${(row.stopStatuses || []).map(status => lookupLabel(statusLabels.value, status)).join(', ') || t('page.sla.closingStatuses')} · ${t('page.sla.pausePrefix')}: ${(row.pauseStatuses || []).map(status => lookupLabel(statusLabels.value, status)).join(', ') || '—'}`
-        }
-      )
-  },
-  {
-    title: '启用',
-    key: 'enabled',
-    width: 90,
-    render: row =>
-      h(NSwitch, {
-        value: row.enabled,
-        size: 'small',
-        onUpdateValue: (v: boolean) => toggle(row, v)
-      })
-  },
-  {
-    title: '操作',
-    key: 'actions',
-    width: 260,
-    render: row =>
-      h(NSpace, { size: 4 }, () => [
-        h(
-          NButton,
-          { size: 'tiny', tertiary: true, onClick: () => fillPolicyFromHolidayPack(row.id) },
-          { default: () => '假日包' }
-        ),
-        row.calendar
-          ? h(
-              NButton,
-              { size: 'tiny', tertiary: true, onClick: () => clearCalendar(row) },
-              { default: () => '清除覆盖' }
-            )
-          : null,
-        h(
-          NButton,
-          { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeRow(row.id) },
-          { default: () => '删除' }
-        )
-      ])
-  }
-];
+    },
+    {
+      title: $t('page.sla.enabled'),
+      key: 'enabled',
+      width: 90,
+      render: row =>
+        h(NSwitch, {
+          value: row.enabled,
+          size: 'small',
+          onUpdateValue: (v: boolean) => toggle(row, v)
+        })
+    },
+    {
+      title: $t('page.sla.actions'),
+      key: 'actions',
+      width: 260,
+      render: row =>
+        h(NSpace, { size: 4 }, () => [
+          h(
+            NButton,
+            { size: 'tiny', tertiary: true, onClick: () => fillPolicyFromHolidayPack(row.id) },
+            { default: () => $t('page.sla.holidayPack') }
+          ),
+          row.calendar
+            ? h(
+                NButton,
+                { size: 'tiny', tertiary: true, onClick: () => clearCalendar(row) },
+                { default: () => $t('page.sla.clearOverride') }
+              )
+            : null,
+          h(
+            NButton,
+            { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeRow(row.id) },
+            { default: () => $t('page.sla.delete') }
+          )
+        ])
+    }
+  ];
+});
 
 async function load() {
@@ -565,9 +575,9 @@
 <template>
   <div class="p-4">
-    <NCard title="SLA 策略" :bordered="false">
+    <NCard :title="$t('page.sla.policies')" :bordered="false">
       <template #header-extra>
         <NSpace>
           <NButton size="small" :loading="running" @click="runDue">{{ $t('page.sla.runDue') }}</NButton>
-          <NButton size="small" @click="load">刷新</NButton>
+          <NButton size="small" @click="load">{{ $t('page.sla.refresh') }}</NButton>
         </NSpace>
       </template>
@@ -578,7 +588,7 @@
     </NCard>
 
-    <NCard title="新建策略" :bordered="false" style="margin-top: 16px">
+    <NCard :title="$t('page.sla.newPolicy')" :bordered="false" style="margin-top: 16px">
       <NSpace vertical>
-        <NInput :value="form.name" placeholder="名称" maxlength="80" @update:value="onPolicyNameInput" />
+        <NInput :value="form.name" :placeholder="$t('page.sla.name')" maxlength="80" @update:value="onPolicyNameInput" />
         <NSelect v-model:value="form.metric" :options="metricOptions" :placeholder="$t('page.sla.metricPlaceholder')" />
         <NText depth="3" style="font-size: 12px">{{ $t('page.sla.firstResponseNote') }}</NText>
@@ -611,21 +621,21 @@
         />
         <NSpace>
-          <span>通知负责人</span>
+          <span>{{ $t('page.sla.notifyAssignee') }}</span>
           <NSwitch v-model:value="form.notifyAssignee" />
-          <span>通知关注者</span>
+          <span>{{ $t('page.sla.notifyWatchers') }}</span>
           <NSwitch v-model:value="form.notifyWatchers" />
         </NSpace>
         <div style="border: 1px solid #eee; border-radius: 6px; padding: 12px">
           <NSpace align="center" style="margin-bottom: 8px">
-            <span style="font-weight: 500">日历覆盖</span>
+            <span style="font-weight: 500">{{ $t('page.sla.calendarOverride') }}</span>
             <NSwitch v-model:value="form.calendarEnabled" />
-            <NText depth="3" style="font-size: 12px">关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承</NText>
+            <NText depth="3" style="font-size: 12px">{{ $t('page.sla.calendarOverrideHint') }}</NText>
           </NSpace>
           <template v-if="form.calendarEnabled">
             <NSpace align="center" style="margin-bottom: 8px">
-              <span>时区覆盖</span>
+              <span>{{ $t('page.sla.timezoneOverride') }}</span>
               <NSelect
                 v-model:value="form.calendarTimezone"
-                :options="[{ label: '（继承工作区）', value: '' }, ...timezoneOptions]"
+                :options="[{ label: $t('page.sla.inheritWorkspace'), value: '' }, ...timezoneOptions]"
                 style="width: 220px"
                 filterable
@@ -635,5 +645,5 @@
             </NSpace>
             <NText depth="3" style="display: block; margin-bottom: 6px; font-size: 12px">
-              例外覆盖（填写则整表替换 WS 例外；留空=继承）
+              {{ $t('page.sla.exceptionOverride') }}
             </NText>
             <div
@@ -648,5 +658,5 @@
                 @click="form.calendarExceptions = form.calendarExceptions.filter(e => e.date !== ex.date)"
               >
-                删
+                {{ $t('page.sla.removeException') }}
               </NButton>
             </div>
@@ -654,9 +664,9 @@
               <NInput v-model:value="calExDraft.date" placeholder="YYYY-MM-DD" style="width: 140px" />
               <NSelect v-model:value="calExDraft.kind" :options="kindOptions" style="width: 180px" />
-              <NButton size="small" @click="addCalExceptionDraft">添加例外</NButton>
+              <NButton size="small" @click="addCalExceptionDraft">{{ $t('page.sla.addException') }}</NButton>
             </NSpace>
           </template>
         </div>
-        <NButton type="primary" :loading="creating" @click="create">创建</NButton>
+        <NButton type="primary" :loading="creating" @click="create">{{ $t('page.sla.create') }}</NButton>
       </NSpace>
     </NCard>
@@ -736,8 +746,8 @@
     </NCard>
 
-    <NCard title="假日包" :bordered="false" style="margin-top: 16px">
+    <NCard :title="$t('page.sla.holidayPacks')" :bordered="false" style="margin-top: 16px">
       <div style="margin-bottom: 8px">
         <span style="font-weight: 500; cursor: pointer" @click="packOpen = !packOpen">
-          {{ packOpen ? '▼' : '▶' }} 国家/地区假日包（一键合并例外日）
+          {{ packOpen ? '▼' : '▶' }} {{ $t('page.sla.packTitle') }}
         </span>
       </div>
@@ -752,5 +762,5 @@
               :options="packRegionFilterOptions"
               style="width: 120px"
-              placeholder="地区"
+              :placeholder="$t('page.sla.region')"
               @update:value="
                 (v: string | null) => {
@@ -764,5 +774,5 @@
               :options="packYearFilterOptions"
               style="width: 120px"
-              placeholder="年份"
+              :placeholder="$t('page.sla.year')"
               @update:value="
                 (v: number | null) => {
@@ -791,14 +801,20 @@
           <NText depth="3" style="font-size: 12px">{{ packSourceNote || '—' }}</NText>
           <NSpace>
-            <NButton size="small" :loading="packLoading" @click="previewHolidayPack">预览</NButton>
+            <NButton size="small" :loading="packLoading" @click="previewHolidayPack">{{ $t('page.sla.preview') }}</NButton>
             <NButton type="primary" size="small" :loading="packApplying" :disabled="!isOwner" @click="applyHolidayPack">
-              确认应用
+              {{ $t('page.sla.applyPack') }}
             </NButton>
           </NSpace>
           <div v-if="packPreview" style="font-size: 12px">
             <div style="margin-bottom: 6px">
-              变更：+{{ (packPreview.added || []).length }} / 覆盖 {{ (packPreview.replaced || []).length }} / 保留
-              {{ (packPreview.unchanged || []).length }} （{{ packPreview.countBefore }} →
-              {{ packPreview.countAfter }}）
+              {{
+                $t('page.sla.packPreviewSummary', {
+                  added: (packPreview.added || []).length,
+                  replaced: (packPreview.replaced || []).length,
+                  kept: (packPreview.unchanged || []).length,
+                  before: packPreview.countBefore,
+                  after: packPreview.countAfter
+                })
+              }}
             </div>
             <div
```

`minutes` 的精确调用是 `$t('page.sla.minutes', { n: row.targetMinutes })`，中文 `{n} 分钟`、英文 `{n} min`；保留后面的 ` · metric label`。summary 精确传 added/replaced/kept/before/after，不插入英文硬编码、参数名不改。

- [ ] **Step 4: 验证 SLA 子集，留原件**

```bash
cd "$REPO/frontend"
mkdir -p "$EVIDENCE/green-sla"
pnpm exec vitest run src/views/settings/sla/__tests__/labels.test.ts src/locales/__tests__/sla-trash-chrome.test.ts -t 'locks every new key|SLA settings labels|policyNameAfterLocaleChange' > "$EVIDENCE/green-sla/stdout.txt" 2> "$EVIDENCE/green-sla/stderr.txt"
printf 'EXIT=%s
' "$?" > "$EVIDENCE/green-sla/exit.txt"
```

预期这次选定子集 EXIT 0；完整 chrome 与 trash fixture 尚未全绿。存 COMMAND/CWD/TZ/HEAD/porcelain/diff/test 原件，不先提交半成品；不要把「子集通过」写成全测通过。

---

### Task 3: trash 接线 + fixture GREEN + 产品提交

**Files:** trash/index.vue、issueTrashMeta.ts；不新增业务 helper/不改常量。**Consumes:** 新 locale/Schema 与 fixture 测试。**Produces:** computed 列、label table、空态 i18n、完整目标子集 GREEN 与产品提交。

- [ ] **Step 1: trash 完整接线补丁**

```diff
--- a/frontend/src/views/issue/trash/index.vue
+++ b/frontend/src/views/issue/trash/index.vue
@@ -1,4 +1,8 @@
 <script setup lang="ts">
-import { h, onMounted, reactive, ref } from 'vue';
+import { computed, h, onMounted, reactive, ref } from 'vue';
+import { useI18n } from 'vue-i18n';
+import { $t } from '@/locales';
+import { lookupLabel } from '@/locales/display-label';
+import { useLabelTable } from '@/locales/use-label-table';
 import { useRouter } from 'vue-router';
 import { NButton, NCard, NDataTable, NEmpty, NPagination, NSpace, NTag } from 'naive-ui';
@@ -12,4 +16,11 @@
 
 const router = useRouter();
+const { locale } = useI18n();
+const statusLabels = useLabelTable('page.issueStatus');
+const priorityLabels = useLabelTable('page.issuePriority');
+const emptyHint = computed(() => {
+  void locale.value;
+  return trashEmptyHint();
+});
 const loading = ref(false);
 const restoringId = ref<string | null>(null);
@@ -52,53 +63,56 @@
 }
 
-const columns: DataTableColumns<Api.Issue.Issue> = [
-  {
-    title: '编号',
-    key: 'issue_code',
-    width: 120,
-    render: row =>
-      h(
-        NButton,
-        { text: true, type: 'primary', onClick: () => openDetail(row) },
-        { default: () => row.issue_code || (row as any).issueCode }
-      )
-  },
-  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
-  {
-    title: '状态',
-    key: 'status',
-    width: 100,
-    render: row => h(NTag, { type: getIssueStatusTagType(row.status), size: 'small' }, { default: () => row.status })
-  },
-  {
-    title: '优先级',
-    key: 'priority',
-    width: 100,
-    render: row =>
-      h(NTag, { type: getIssuePriorityTagType(row.priority), size: 'small' }, { default: () => row.priority })
-  },
-  {
-    title: '更新时间',
-    key: 'updated_at',
-    width: 180,
-    render: row => (row as any).updated_at || (row as any).updatedAt || '—'
-  },
-  {
-    title: '操作',
-    key: 'actions',
-    width: 120,
-    render: row =>
-      h(
-        NButton,
-        {
-          size: 'small',
-          type: 'primary',
-          loading: restoringId.value === row.id,
-          onClick: () => handleRestore(row)
-        },
-        { default: () => '恢复' }
-      )
-  }
-];
+const columns = computed<DataTableColumns<Api.Issue.Issue>>(() => {
+  void locale.value;
+  return [
+    {
+      title: $t('page.issueTrash.key'),
+      key: 'issue_code',
+      width: 120,
+      render: row =>
+        h(
+          NButton,
+          { text: true, type: 'primary', onClick: () => openDetail(row) },
+          { default: () => row.issue_code || (row as any).issueCode }
+        )
+    },
+    { title: $t('page.issueTrash.issueTitle'), key: 'title', ellipsis: { tooltip: true } },
+    {
+      title: $t('page.issueTrash.status'),
+      key: 'status',
+      width: 100,
+      render: row => h(NTag, { type: getIssueStatusTagType(row.status), size: 'small' }, { default: () => lookupLabel(statusLabels.value, row.status) })
+    },
+    {
+      title: $t('page.issueTrash.priority'),
+      key: 'priority',
+      width: 100,
+      render: row =>
+        h(NTag, { type: getIssuePriorityTagType(row.priority), size: 'small' }, { default: () => lookupLabel(priorityLabels.value, row.priority) })
+    },
+    {
+      title: $t('page.issueTrash.updatedAt'),
+      key: 'updated_at',
+      width: 180,
+      render: row => (row as any).updated_at || (row as any).updatedAt || '—'
+    },
+    {
+      title: $t('page.issueTrash.actions'),
+      key: 'actions',
+      width: 120,
+      render: row =>
+        h(
+          NButton,
+          {
+            size: 'small',
+            type: 'primary',
+            loading: restoringId.value === row.id,
+            onClick: () => handleRestore(row)
+          },
+          { default: () => $t('page.issueTrash.restore') }
+        )
+    }
+  ];
+});
 
 onMounted(loadTrash);
@@ -107,9 +121,9 @@
 <template>
   <div class="issue-trash-page">
-    <NCard title="回收站" :bordered="false">
+    <NCard :title="$t('page.issueTrash.title')" :bordered="false">
       <template #header-extra>
         <NSpace>
-          <NButton secondary @click="router.push('/issue/list')">返回列表</NButton>
-          <NButton secondary :loading="loading" @click="loadTrash">刷新</NButton>
+          <NButton secondary @click="router.push('/issue/list')">{{ $t('page.issueTrash.backToList') }}</NButton>
+          <NButton secondary :loading="loading" @click="loadTrash">{{ $t('page.issueTrash.refresh') }}</NButton>
         </NSpace>
       </template>
@@ -123,5 +137,5 @@
         :single-line="false"
       />
-      <NEmpty v-else :description="trashEmptyHint()" class="py-12" />
+      <NEmpty v-else :description="emptyHint" class="py-12" />
 
       <div v-if="pagination.total > pagination.pageSize" class="mt-4 flex justify-end">
```

- [ ] **Step 2: helper 的精确实现**

`frontend/src/utils/issueTrashMeta.ts` 完整目标；仅 empty 接 translator，pure 注释改成准确描述，恢复与 banner 原样。

```ts
import { $t } from '@/locales';

/** E77: trash/restore copy helpers; empty hint follows the active locale. */
export function trashEmptyHint(): string {
  return $t('page.issueTrash.empty');
}

export function restoreSuccessMessage(code: string): string {
  const c = (code || '').trim();
  return c ? `已恢复 ${c}` : '已恢复';
}

export function deletedReadonlyBanner(): string {
  return '此问题已在回收站中，只读。恢复后可继续编辑。';
}
```

- [ ] **Step 3: 完整目标子集 GREEN，并提交产品+tests**

```bash
cd "$REPO/frontend"
mkdir -p "$EVIDENCE/green"
pnpm exec vitest run src/locales/__tests__/sla-trash-chrome.test.ts src/views/issue/trash/__tests__/chrome.test.ts src/views/settings/sla/__tests__/labels.test.ts src/utils/issueTrashMeta.test.ts src/locales/__tests__/residual-copy.test.ts > "$EVIDENCE/green/stdout.txt" 2> "$EVIDENCE/green/stderr.txt"
printf 'EXIT=%s
CWD=%s
TZ=%s
' "$?" "$PWD" "$TZ" > "$EVIDENCE/green/meta.txt"
git rev-parse HEAD >> "$EVIDENCE/green/meta.txt"
git status --porcelain > "$EVIDENCE/green/porcelain.txt"
git diff > "$EVIDENCE/green/final-product.diff"
cp src/locales/__tests__/sla-trash-chrome.test.ts "$EVIDENCE/green/"
cp src/views/issue/trash/__tests__/chrome.test.ts "$EVIDENCE/green/trash-chrome.test.ts"
cp src/views/settings/sla/__tests__/labels.test.ts "$EVIDENCE/green/sla-labels.test.ts"
cp src/utils/issueTrashMeta.test.ts "$EVIDENCE/green/"
```

EXIT 0 才继续；meta 补全 COMMAND。原 residual-copy 不修改，它在此仅回归。确认 labels 差异仅四个 selector，不丢行为断言；确认 blank/unknown fixture、同 mount 切换均通过。

```bash
cd "$REPO"
git diff --check
git add frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts frontend/src/typings/app.d.ts frontend/src/views/settings/sla/index.vue frontend/src/views/settings/sla/__tests__/labels.test.ts frontend/src/locales/__tests__/sla-trash-chrome.test.ts frontend/src/views/issue/trash/index.vue frontend/src/utils/issueTrashMeta.ts frontend/src/utils/issueTrashMeta.test.ts frontend/src/views/issue/trash/__tests__/chrome.test.ts
git diff --cached --name-only
# 恰好上述 10 产品/测试路径，docs 已单独在父提交；额外路径立即停。
git commit -m "fix: localize SLA and trash page chrome for English"
test -z "$(git status --porcelain)" || exit 1
```

记录 hook 原件与限制，不改写 docs-only commit。正常两笔（docs、产品含 tests）；RED 不强制单独提交。不要预安排第三笔 locale-read commit；只有审查实际发现短路 bug 才在 review 证据之后追加必要修补，原提交不改写，再重跑相关测试和四门。

---

### Task 4: 四门与当次 baseline 逐项对照

**Files:** 不改产品；结果入仓库外 evidence。**Consumes:** Task 0 当次原件与产品 HEAD。**Produces:** gates 原件、逐条诊断差分、限定结论。

- [ ] **Step 1: 同一 runner 跑最终四门**

```bash
bash "$EVIDENCE/run-gates.sh" gates
cd "$REPO"
git diff --check
git status --porcelain > "$EVIDENCE/final-porcelain.txt"
git rev-parse HEAD > "$EVIDENCE/final-head.txt"
git log -2 --format=fuller > "$EVIDENCE/final-commits.txt"
git diff 5bc1f604a22aad1517eaeae16ada004ba14fc11a...HEAD --stat > "$EVIDENCE/final-stat.txt"
git diff 5bc1f604a22aad1517eaeae16ada004ba14fc11a...HEAD > "$EVIDENCE/final.diff"
```

四条仍为 frontend 的 vitest run、vite build --mode prod（外部 --config/cacheDir）、vue-tsc --noEmit --skipLibCheck、eslint .。逐份记录 EXIT、测试数/用例数与变化，build 必须 0。tsc/lint 按文件/诊断代码/消息比较，忽略单纯行号漂移；要求新增 0，减少也逐条记，若仍失败不得写成全绿。把 baseline/gates 诊断一对一映射表存为 `diagnostics-comparison.md`，不能只比总数相等。若新增诊断、测试失败、白名单外路径或生成文件变化，STOP；不 reset 掩盖。不引用 slice-2 的 89/523、29 行或 872 数字充当本轮输出。

---

### Task 5: 浏览器原图与限定视觉验收

**Files:** 仅仓库外 browser 证据。**Consumes:** 已过四门的 HEAD、只读 Vite 外部配置、合成数据。**Produces:** 原图+每张 HEAD/locale/theme/viewport/fixture 状态记录。

- [ ] **Step 1: 只读启动，不改产品树/后端数据**

```bash
cd "$REPO/frontend"
pnpm exec vite --mode prod --config "$EVIDENCE/vite.readonly.config.mjs" --host 127.0.0.1 --port 9563 --strictPort
```

9563 若占用就 STOP 并如实报告，不杀现有服务。合成 token 不入仓库、不在报告粘贴值。仅浏览器路由拦截返回 fixture，不向后端写入/恢复/删除实际记录。不能安全注入 fixture 时不要触真实行按钮。

- [ ] **Step 2: 每张浅色 1280×800，en/zh 对照**

SLA 顶部（SLA policies / Refresh / Name / Start and stop statuses / Enabled / Actions / New policy），新建 calendarEnabled 展开（Notify assignee/watchers / Calendar override / Time zone override / Add exception / Remove），假日包展开（Holiday packs、header、All regions/All years、Preview/Apply）。用合成响应提供 policy 行和预览 summary，核 `1440 min` 与 `Changes: +1 / replaced 1 / kept 1 (2 → 3)`；中文核同表、删变删除已获 A 同意。不得为了截图改 API 或包数据文件；无法注入 summary/例外行就记录未覆盖并以源/fixture 合同补足，不声称该态屏幕验过。holidayIntro 原绑定显示英文，但不重译它。

回收站 en/zh：若只读拦截允许，展示 WAY-1 open/critical，核 Open/Urgent 与 待办/紧急，表头与恢复按钮也核。**浏览器仍空必须明确写 empty-only**，截图不能证明标签值；依赖 Task 1 非空 fixture 单测证明。另采 empty zh/en 是加分证据，不代替非空测试。路由文档标题 SLA / Trash 与 SLA 策略 / 回收站 不改。切 locale 不 remount 的单测是强制，截图不替代。

每张原图配当次精确 head SHA（如审查补丁后必须重采或标为旧 SHA）、Asia/Shanghai 时间、viewport、html dark 状态、locale、URL、stub/fixture 条件；不宣称暗色或对比度已经验过。

---

### Task 6: 双 grok-4.7-high 与 STOP

**Files:** 仅仓库外 reviews/证据包。**Consumes:** 已批文档、最终 HEAD、red/green/gates/browser 原件。**Produces:** 两份独立审查原文与可复核证据，不推送。

- [ ] **Step 1: 两份独立审查，不买额度**

一份核 design/plan 范围与实现，另一份核代码/测试合同：28+11 key/Schema、name 两个调用、add/remove 各两个调用、locale-first、fixture enum/fallback、labels 只改 selector、范围外冻结与 baseline 逐诊断对照。保存完整 prompt、模型标识 grok-4.7-high、stdout/EXIT、head SHA。额度不足立即 STOP，不购买。没有单独 `Approve` 行就只记录「审查已完成、无单独 Approve」，不得写 dual Grok Approve。Request Changes 未解就停止交原件；若 review 确认短路 bug 才补必要 commit，再复核，不能预先安排。

- [ ] **Step 2: 交验收材料后停手，等待后续指令**

证据含 approved docs hash/拷贝比较、精确 base、普通 clone `.git` 证明、parent 图/两笔提交、HEAD/洁净 porcelain、final.diff/白名单、baseline/red/green/gates/browser/reviews、hook 路径原件或明确缺失。证据包在 repo 外生成并 sha256；不把 token/env 值打包。此计划不授权发送消息、push、PR、merge 或部署；经另行授权才向 Yuri 交接。此刻文档草稿也不外发。

## 自检与待办状态

- [x] design/plan 本地草稿已写；新增键、复用键、标题碰撞、中文变化、A/B 待决策均列明。
- [x] 无未定义代码占位；Schema 对象 walk、精确 `$t` 调用数、tight literal regex、toasts/Business hours 冻结、fixture 行与 locale 切换代码齐全。
- [x] 不重做 help / Business hours / holidayIntro / policyNameAfterLocaleChange；raw row 修复由 fixture 合同覆盖；不改常量/枚举/PR6–14。
- [ ] design/plan 批准 = pending（等待 Yuri 决策 A/B 与「design ok，开写」）。
- [ ] TDD / verify / acceptance = pending；未执行 Task 0–6，未证明产品通过。
- [x] 无产品分支、无产品改动、无 git commit/push/PR/merge/deploy、未购买额度、未发送消息。

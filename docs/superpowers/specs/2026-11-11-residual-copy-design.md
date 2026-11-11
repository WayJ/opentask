# 残留界面文案

日期：2026-11-11  
基线：`main` @ `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34`（已含 OAuth，PR #5 已合并）  
状态：待 Yuri 审。本文件批准前不改实现、不改测试、不合并、不部署、不连接现网。

这是界面术语的收尾，不是新功能。只改人看到的字。OAuth、PR #5 的路由和窄表修复都保留。

## 1. 已核对的界面

生产截图和当前 `main` 的源码一致。下面的行号是 `22c8d8b` 上的位置。

### 举措 `/initiatives`

- 主按钮走 `$t('page.shell.createInitiative')`。`frontend/src/locales/langs/zh-cn.ts` 第 365 行现在是 `新建议措`。英文 `en-us.ts` 是 `New initiative`，这个英文是对的。
- 空状态说明已经是 `暂无举措，创建后关联多个项目`。
- 空状态里的按钮是模板里写死的 `新建`，在 `frontend/src/views/initiatives/index.vue` 第 192 行，没有走文案键。
- 客户侧 `page.shell.createRequest` 仍是 `新建需求`。本批不改这四个字。

### 问题列表 `/issue/list`

- 类型列用 `issueTypeOptions` 的 `label`。`frontend/src/constants/issue.ts` 里 `bug` 的 label 是 `Bug`，其余类型已经是中文：功能、问题、反馈、事件、改进。
- 枚举值是 `bug`、`feature`、`question`、`feedback`、`incident`、`improvement`。列表提交和筛选用的是这些值，不是 label。
- 状态和优先级的中文 label 已经是待办、进行中、等待反馈、已解决、已关闭、已拒绝，以及低、中、高、紧急。
- 搜索帮助里的 `is:in_progress`、`is:bug` 是查询语法，不在本批修改范围。

### SLA `/settings/sla`

页面几乎全是模板里的中文句子，中间夹着英文标识。给人看的和必须原样留下的混在一起。

给人看、应当换成可读中文的：

- 按钮 `立即 run-due`。
- 说明里的「两种 metric」、`stop`、`resolved/closed/rejected`。
- 度量下拉把代码放在括号里：`状态停留 (time_in_status)`、`首次响应 (first_response)`。下拉的值已经是枚举，括号里的代码不是给人读的句子。
- 状态下拉的 label 就是枚举本身。`statusOptions` 写成 `{ label: v, value: v }`，所以选项显示 `in_progress`。
- 策略表「启停状态」列拼的是 `start:`、`stop:`、`pause:` 加原始状态值。
- 占位 `metric`、`startStatuses`、`stopStatuses`、`targetMinutes`、`示例 feedback`。
- 卡片标题 `营业时段（SLA business hours）`。SLA 这个缩写保留，business hours 不保留。
- 例外种类下拉 `关闭日 (closed)`、`强制营业 (forced_open)`，以及列表里直接渲染的 `ex.kind`。
- 占位 `forced_open 可选窗口`。
- 假日包说明里的 `policy`，选项 `本工作区 business_hours`、`指定 policy 日历`，提示 `请选择 policy`、`选择 policy`。
- 新建策略时名称框的初值 `Time in progress`。这是输入框里的默认文字。用户不改就保存的话，会变成新策略的名称。不改已经存好的策略。

必须原样留下的：

- 路径 `POST /api/sla/run-due`。
- 词 cron。它是外部调度的说法，旁边要有人话，不能只留这一个词。
- 枚举值 `time_in_status`、`first_response`、`in_progress`、`resolved`、`closed`、`rejected`、`feedback`、`forced_open`、`closed`。它们继续作为选项的 value 和请求体。
- IANA 时区：`Asia/Shanghai`、`UTC`、`America/Los_Angeles`、`America/New_York`、`Europe/London`。
- 时间格式 `09:00-12:00`、`13:00-18:00`，日期格式 `YYYY-MM-DD`。
- 假日包的地区代码值 `CN`、`US`、`EU`、`UK`，以及年份 `2026`、`2027`。
- `slaMetricLabel` 和 `slaMetricBadgePrefix` 的现有中文返回值。问题详情上的 SLA 徽章已经是「状态 SLA」「首响 SLA」，本批不改这两个函数，避免动到详情页。

### 洞察 `/insights`

- 副标题：`工作区效能摘要（多标签 OR · 我的/团队报表 · 可选 digest）`。这里的 OR 是在解释「多标签满足其一」，不是查询框里的语法。筛选控件已经有键 `page.shell.labelsOr`，中文是 `标签（或）`，英文是 `Labels (OR)`。英文里的 OR 保持。
- 按钮 `导出 CSV`、提示 `已导出 CSV`。CSV 是要保留的格式名。
- 下载文件名 `insights-export.csv` 保持。
- 开关 `效能 digest`，成功提示 `已设为 digest 默认报表`。请求字段 `insights_digest` 保持，只改开关和提示上的字。
- 开关旁的说明 `默认关；开后由外部 tick 写 Inbox/邮件`。tick 是实现说法。收件箱沿用已有术语。
- 冲刺选项在名称后加 ` · active`。举措列表里同一个状态值 `active` 已经显示为「进行中」。
- 状态分布和优先级分布直接显示 `row.key`，也就是 `open`、`in_progress`、`low` 这类存储值。
- 同页还有 `Estimate 点合计`、`近 14 日 · 创建 vs 完成`、`估点速度 · 近 14 日 completed points`、列头 `Points`。这些和 OR、digest 在同一张页面上，一并改成可读的字。不改图表的计算。

## 2. 方案

比较过三种做法：

1. 只在 Vue 模板里把中文写死。能消掉 `新建议措` 和 Bug，但英文界面会看到中文。不采用。
2. 再做一套独立的文案表。和已经在用的 `zh-cn.ts`、`en-us.ts` 重复，语言切换还要接第二次。不采用。
3. 沿用 vue-i18n。缺的句子补进现有文案键。枚举的 value 不动，显示时用当前语言查表。未知值原样显示，不猜测。采用这个。

组件只改「哪一段文字绑定到哪个键」。不改布局、颜色、`#5e6ad2`、亮色暗色、接口、鉴权和 OAuth。

状态的中文以 `frontend/src/constants/issue.ts` 为准：待办、进行中、等待反馈、已解决、已关闭、已拒绝。不用仪表盘里的「待处理」「反馈中」。这样同一个状态在问题列表、SLA 和洞察上是同一个词。

类型「问题」（value `question`）和对象名「问题」重名。这是原有叫法，本批不另起一个词。只把 `bug` 的中文从 Bug 改成「缺陷」，避免和对象名撞车。

## 3. 术语对照

英文必须是完整英文。中文里保留 SLA、API、CSV、OAuth、Webhook。本批页面不新增 OAuth 或 Webhook 字样。

### 举措

| 位置 | 现在 | 中文 | 英文 |
|---|---|---|---|
| `page.shell.createInitiative` | 新建议措 | 新建举措 | New initiative |
| 空状态按钮 | 写死的「新建」 | 同一个键，新建举措 | New initiative |
| `page.shell.emptyInitiatives` | 暂无举措，创建后关联多个项目 | 不改 | 不改 |
| `page.shell.createRequest` | 新建需求 | 不改 | New request |

### 问题类型

value 不变。中文除 `bug` 外沿用现在的 label。

| value | 中文 | 英文 |
|---|---|---|
| bug | 缺陷 | Bug |
| feature | 功能 | Feature |
| question | 问题 | Question |
| feedback | 反馈 | Feedback |
| incident | 事件 | Incident |
| improvement | 改进 | Improvement |

### 问题状态

value 不变。中文沿用 `issueStatusOptions`。

| value | 中文 | 英文 |
|---|---|---|
| open | 待办 | Open |
| in_progress | 进行中 | In progress |
| feedback | 等待反馈 | Waiting for feedback |
| resolved | 已解决 | Resolved |
| closed | 已关闭 | Closed |
| rejected | 已拒绝 | Rejected |

### 优先级

| value | 中文 | 英文 |
|---|---|---|
| low | 低 | Low |
| medium | 中 | Medium |
| high | 高 | High |
| critical | 紧急 | Urgent |

`critical` 的英文用 Urgent，因为现有中文是「紧急」。value 仍是 `critical`。

### SLA

| 位置 | 中文 | 英文 |
|---|---|---|
| 立即执行按钮 | 立即执行到期检查 | Run due checks |
| 度量 `time_in_status` | 状态停留 | Time in status |
| 度量 `first_response` | 首次响应 | First response |
| 例外 `closed` | 关闭日 | Closed day |
| 例外 `forced_open` | 强制营业 | Forced open |
| 营业时段卡片 | 营业时段 | Business hours |
| 假日包目标 `workspace` | 本工作区营业时段 | Workspace business hours |
| 假日包目标 `policy` | 指定策略的日历 | A policy calendar |
| 未选策略 | 请选择策略 | Choose a policy |
| 名称初值 | 进行中停留 | Time in progress |

说明文字，中文：

支持「状态停留」和「首次响应」两种度量。默认按墙钟分钟；启用营业时段后按营业分钟。首次响应：不是创建者的第一条评论即满足，指派负责人不算。结束状态留空时，进入已解决、已关闭或已拒绝即满足。进入暂停状态时不计时，离开后按剩余时间继续。没有内置定时任务（cron）。请用外部调度调用 POST /api/sla/run-due。

说明文字，英文：

Two metrics: time in status and first response. Minutes use the wall clock unless business hours are on. First response is the first comment by someone other than the creator. Assignment does not count. If no stop status is set, resolved, closed, or rejected completes it. Pause statuses do not count; the clock resumes with the time left. There is no built-in scheduler (cron). Call POST /api/sla/run-due from an external scheduler.

占位改为「度量」「开始状态」「结束状态（可空，空则视为关闭类）」「暂停计时的状态（可空）」「目标分钟」「强制营业时段（可选）」。状态说明里的 feedback 例子改成「例如：等待反馈」。优先级那句保持中文意思：结束优先于暂停，暂停优先于开始。

地区下拉的 value 仍是 CN、US、EU、UK。显示为「中国 CN」「美国 US」「欧盟 EU」「英国 UK」。英文界面显示 China CN、United States US、European Union EU、United Kingdom UK。

策略表的启停列用状态的显示名，前缀用「开始」「结束」「暂停」。没有结束状态时，中文继续用「关闭类」，英文用 “closing statuses”。

### 洞察

| 位置 | 中文 | 英文 |
|---|---|---|
| 副标题 | 工作区效能摘要。多个标签取并集，可查看我的报表和团队报表，也可打开定期摘要。 | Workspace performance summary. Any selected label matches. Personal and team reports. Optional digest. |
| 导出按钮 | 导出 CSV | Export CSV |
| 导出成功 | 已导出 CSV | Exported CSV |
| 摘要开关 | 效能摘要 | Performance digest |
| 设为默认的提示 | 已设为摘要的默认报表 | Set as the default digest report |
| 开关说明 | 默认关闭。打开后，由外部定时调用写入收件箱和邮件。 | Off by default. When on, an external scheduler writes to Inbox and email. |
| 冲刺进行中后缀 | · 进行中 | · Active |
| 估点合计 | 估点合计 | Estimate points |
| 创建与完成 | 近 14 日 · 创建与完成 | Last 14 days · Created and completed |
| 速度标题 | 估点速度 · 近 14 日完成点数 | Estimate velocity · Completed points, last 14 days |
| 速度列 | 点数 | Points |

状态分布和优先级分布用上面的状态、优先级显示名。不认识的键原样显示。筛选「或」继续用已有的 `labelsOr`，不把英文 OR 写进中文副标题。

## 4. 文件

文案键放在 `App.I18n.Schema` 的 `page` 下，和现有 `page.shell` 并列。实现时按这个形状建键，不再拆另一套名字。

- `page.shell.createInitiative`
- `page.issueType`：`bug`、`feature`、`question`、`feedback`、`incident`、`improvement`
- `page.issueStatus`：`open`、`in_progress`、`feedback`、`resolved`、`closed`、`rejected`
- `page.issuePriority`：`low`、`medium`、`high`、`critical`
- `page.sla`：`runDue`、`help`、`businessHours`、`metric.time_in_status`、`metric.first_response`、`exception.closed`、`exception.forced_open`、`targetWorkspace`、`targetPolicy`、`choosePolicy`、`defaultPolicyName`，以及占位和表头所需的短句
- `page.insights`：`subtitle`、`exportCsv`、`exportedCsv`、`digest`、`digestDefault`、`digestHint`、`cycleActive`、`estimatePoints`、`createdCompleted`、`velocityTitle`、`points`

会改：

- `frontend/src/typings/app.d.ts` 里手写的 `App.I18n.Schema`。只加本批文案键。
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/views/initiatives/index.vue` 的空状态按钮
- `frontend/src/views/issue/list/index.vue` 的类型显示
- `frontend/src/views/issue/create/index.vue`、`frontend/src/views/issue/edit/index.vue`、`frontend/src/views/issue/detail/index.vue` 里使用 `issueTypeOptions` 作为下拉 label 的地方。它们和列表共用同一组类型，不改会在新建和详情里继续显示 Bug。
- `frontend/src/utils/groupIssuesBy.ts` 的类型桶标题。列表分组会读它。
- `frontend/src/views/settings/sla/index.vue`
- `frontend/src/views/insights/index.vue`
- 对应的文案测试

不改：

- `frontend/src/constants/issue.ts` 的枚举值。类型 label 可以仍留作中文兜底，但页面显示以文案键为准。`bug` 的兜底 label 改为「缺陷」，这样漏改的中文调用点不会继续显示 Bug。
- `frontend/src/service/api/sla.ts` 的 `slaMetricLabel`、`slaMetricBadgePrefix`、`SLA_METRICS`、`ISSUE_STATUSES`。
- 后端、CLI、OAuth 页面、路由、查询语法、CSV 列名、请求字段。
- 生成的 `frontend/src/typings/api/issue.d.ts` 和 `frontend/src/typings/components.d.ts`。
- 样式、布局、令牌、`#5e6ad2`、亮色和暗色。

已知但本批不改的同类英文：

- `frontend/src/views/settings/recurrences/index.vue` 也有「立即 run-due」。不是这次看到的页面。
- `frontend/src/views/dashboard/modules/status-charts.vue` 把 `bug` 标成 Bug，并把 `open` 标成「待处理」。仪表盘不在这次的四个页面里，也不在这里顺手统一。
- `frontend/src/views/issue/detail/index.vue` 里生成 Agent 指令的 `typeTextMap` 仍写 Bug。那是提示词正文，不是列表徽章。
- `frontend/src/constants/issueTemplates.ts` 的模板名「Bug 报告」。

## 5. 测试和门禁

先写会失败的测试，再改文案。测试只锁显示词和「值没有被改掉」。

- 中文 `createInitiative` 是「新建举措」，文案文件里不再出现「新建议措」。
- 中文 `createRequest` 仍是「新建需求」。英文 `createInitiative` 仍是 `New initiative`。
- `IssueTypeEnum.Bug` 仍是 `bug`。中文显示「缺陷」，英文显示 `Bug`。其余类型 value 不变。
- `in_progress` 的值不变。中文「进行中」，英文 `In progress`。
- `time_in_status` 的值不变。中文「状态停留」，英文 `Time in status`。
- `forced_open` 的值不变。中文「强制营业」。
- 查不到的键返回原值。
- 中文洞察副标题不含 OR、digest。导出按钮含 CSV。
- 中文 SLA 说明含字面量 `POST /api/sla/run-due`，含 `cron`，不含 `time_in_status`、`in_progress`、`resolved/closed` 这种裸枚举。
- 英文 SLA 说明是英文，并含同一条路径。
- 空状态按钮使用 `createInitiative`，不再写死「新建」。

实现时在当前 `main` 上重跑前端 Vitest，数字以这次为准，不沿用 PR #5 的 474。再跑改动文件的 eslint 和 `npm run build`。`vue-tsc` 单独跑，和当前 `main` 对比。生成文件里的既有语法错误不修，有则照实写成未通过。后端和 CLI 没有 diff，不把没跑写成已通过。

浏览器验收留到实现之后：中文下打开这四个路由，核对主按钮、空状态、类型徽章、SLA 说明和洞察副标题。英文切换后同一位置是英文。不要求改布局。本设计批准前不做这一步。

## 6. 自检

- 范围停在四个页面，加上问题类型下拉和列表分组这些同一枚举的显示点。
- 没有改枚举、请求体、查询语法、CSV 文件名和 OAuth。
- 「新建需求」、SLA、API、CSV、cron 和时间格式都有明确去留。
- 中英文字都写死在第 3 节，实现时不能另换近义词。
- 没有写实现代码，也没有改测试。

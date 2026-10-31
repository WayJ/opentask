# S7 Orca Jira 集成探测报告（实现依据）

- 日期：2026-10-31
- 探测对象：本机 Orca（CLI `orca` 1.4.245，Electron 桌面 `%LOCALAPPDATA%/Programs/orca`）
- 方法：`orca jira --help` / `orca skills get orca-jira` / `orca skills get jira-tickets` 命令面枚举 +
  静态读取 Orca 应用内 Jira 适配器源码（`app.asar` 内 `out/main/index.js` 的 IPC handler 层 +
  `app.asar.unpacked/out/main/chunks/orcad-migration-source-retention-CC5d8zdU.js` 的 Jira HTTP 客户端层，
  导出名经 `Object.defineProperty(exports,...)` 映射核对：`Hr→I4`、`Ur→B4`、`Gr→N4` 等）。
  所有结论均引自上述反混淆代码原文，非 Jira 官方文档推测。
- 目的：E2-S7-jira-wire——让 Orca 的 Jira 集成把 OpenTask 当自建 Jira（Server/DC 模式）调用；
  OpenTask 侧需实现的端点/形状以本文为准（验收复核依据）。

## 1. 连接模型（site / authType）

- Orca 支持两种 Jira 站点类型：`authType: "cloud"`（Jira Cloud）与 `authType: "server"`（自建
  Server/Data Center）。连接入口在桌面 Settings UI（IPC `jira:connect`，入参
  `{siteUrl, email, apiToken, authType}`）；CLI 无 connect 子命令，`orca jira connection` 只列表。
- 连接时立即调用 `GET {siteUrl}/rest/api/2/myself`（server 模式，见 §3）验证凭证并取 viewer；
  失败即连接失败。站点注册表落在 `~/.orca/jira-sites.json`，token 存加密 vault（不可手写配置文件注册，
  E2E 需走桌面 UI，见 E2E 证据文档）。
- `siteUrl` 归一（`vxt`）：无 scheme 自动补 `https://`（**必须显式输入 `http://localhost:8000`**）；
  仅允许 http/https、禁止 URL 内嵌凭证；去尾部 `/`、query、hash。
- **请求基路径（`Hr`/`I4`）：`authType==="server" ? "/rest/api/2" : "/rest/api/3"`**。
  OpenTask 只需实现 `/rest/api/2/*`（自建模式永远走 v2）。
- **鉴权头（`R4`）**：`username ? "Basic base64(username:token)" : "Bearer token"`。
  连接表单里 `email` 即 server 模式的 Basic username（可留空 → PAT/Bearer 模式）。
  每请求固定头：`Accept: application/json`、`Content-Type: application/json`、`User-Agent: Orca`。
- **错误体解析（`mxt`）**：读 JSON body 的 `errorMessages[]` + `errors{}` 的 values + `message`，
  分号拼接；缺省回退 HTTP statusText。→ OpenTask 错误响应必须用 Jira 形状
  `{"errorMessages": [...], "errors": {...}}`（本实现把 CONTRACT_* 错误码放进 errorMessages 文本）。
- 响应处理（`Ur`/`B4`）：`204 → null`（成功写操作可以 204 无 body）；非 2xx 抛 `N4(message, status)`。
  401/403 会触发 Orca 侧凭证重验逻辑。

## 2. Orca CLI 命令面（`orca jira ...`，对应 IPC handler）

| CLI | IPC | 底层 REST（server 模式，base=`{siteUrl}/rest/api/2`） |
|---|---|---|
| `connection` | `jira.status` | 无网络调用 |
| `issue <key>` | `jira.getIssue` | `GET /issue/{key}?fields=...&expand=renderedFields` |
| `list --filter --limit` | `jira.listIssues` | `POST /search`（JQL 见 §4） |
| `search <jql> --limit` | `jira.searchIssues` | `POST /search` |
| `create --project --type --title --body` | `jira.createIssue` | `POST /issue`（先 `GET /issue/createmeta/...` 发现字段/类型） |
| `project list` | `jira.listProjects` | `GET /project`（server：单次数组响应） |
| `project types --project` | `jira.listIssueTypes` | `GET /issue/createmeta/{proj}/issuetypes?maxResults&startAt` |
| `project fields --project --type` | `jira.listCreateFields` | `GET /issue/createmeta/{proj}/issuetypes/{tid}?maxResults=100&startAt` |
| `comment list <key>` | `jira.issueComments` | `GET /issue/{key}/comment?maxResults&startAt&orderBy=created&expand=renderedBody`（**startAt 翻页**） |
| `comment add <key> --body` | `jira.addIssueComment` | `POST /issue/{key}/comment` `{body}`（读响应 `.id`） |
| `status list <key>` | `jira.listTransitions` | `GET /issue/{key}/transitions?expand=transitions.fields`（400/403/404 时降级重试无参版本） |
| `status set <key> --to/--to-id` | `jira.listTransitions` + `jira.updateIssue` | 匹配在 **CLI 本地**做（transition.name 或 to.name，大小写不敏感）→ `POST /issue/{key}/transitions` |
| `assignee list <key> --query` | `jira.listAssignableUsers` | `GET /user/assignable/search?username=<q>&maxResults=50&issueKey=` |
| `assignee set/clear` | `jira.updateIssue` | `PUT /issue/{key}/assignee` `{name}` / `null` |
| `priority list` | `jira.listPriorities` | `GET /priority` |
| `priority set/clear` | `jira.updateIssue` | `PUT /issue/{key}` `{fields:{priority:{id}|null}}` |
| `label set/add/rm` | `jira.updateIssue` | `PUT /issue/{key}` `{fields:{labels}}` 或 `{update:{labels:[{add}|{remove}]}}` |
| （内部）字段发现 | — | `GET /field`（缓存；失败非致命，回退空） |
| （渲染器）看板列序 | `jira.getProjectStatusOrder` | `GET /rest/agile/1.0/board?projectKeyOrId=`（任一失败→优雅降级空列序） |
| （渲染器）收藏过滤器 | `jira.listFavouriteFilters` | `GET /filter/favourite?expand=jql` |

## 3. 端点请求/响应形状（server 模式实测代码还原）

### GET /rest/api/2/myself（连接验证 + viewer）
响应读法（`H4`）：`accountId ?? name ?? key` → 用户标识；`displayName`；`emailAddress`；
`avatarUrls["48x48"|"32x32"]`。→ 返回
`{"accountId","name","key","displayName","emailAddress","active":true,"avatarUrls":{}}`。

### POST /rest/api/2/search（列表 + JQL 搜索，**单页语义**）
请求 `{jql, maxResults, fields[]}`（fields 为字段名列表；Orca 侧 maxResults=limit，1..100，默认 30）。
server 模式只发一次请求、不做 startAt 翻页（翻页 token 流程仅 cloud v3 `/search/jql`）。
响应 `{"issues": [...], "total", "startAt", "maxResults"}`；issue 元素形状同 GET /issue。
排序期望 `ORDER BY updated DESC`（JQL 内声明，服务端须执行）。

### GET /rest/api/2/issue/{key}?fields=...&expand=renderedFields
`fields` 含 summary/description/project/issuetype/status/assignee/reporter/priority/labels/created/
updated/parent/timeoriginalestimate/timeestimate/attachment（+动态发现字段）。
响应读法（`UB` + `gBt` + `VB` + `dBt` + `hBt` + `uBt`）：
- 顶层 `id`、`key`、`fields`、`renderedFields`（可选，缺省安全）
- `fields.summary/description`（server 描述为**纯文本字符串**，非 ADF）
- `fields.status`：`{id, name, statusCategory: {key, name}, colorName}`——**statusCategory 必须有**
  （`list --filter done` 靠 `statusCategory = Done` JQL；终态判定也用它）
- `fields.assignee/reporter`：`{name, displayName, emailAddress?, avatarUrls?}` 或 null
- `fields.issuetype` `{id, name, subtask?}`；`fields.priority` `{id, name}` 或 null；
  `fields.project` `{id, key, name}`；`fields.labels[]`；`fields.created/updated`（字符串时间戳）；
  `fields.parent`（null 可）；`attachment`（`[]` 可）

### POST /rest/api/2/issue（创建）
请求 `{fields: {project: {id}, issuetype: {id}, summary, description?, <customFields>}}`。
响应必须含 `{id, key}`（Orca 读这两个字段构造返回）。成功码 201。

### PUT /rest/api/2/issue/{key}（更新：标题/标签/优先级）
请求 `{fields: {summary?, labels?, priority?: {id}|null}, update?: {labels: [{add}|{remove}]}}`。
成功 **204 无 body**。

### PUT /rest/api/2/issue/{key}/assignee
请求 server 形状 `{name: <用户名/ID>}`（cloud 才是 `{accountId}`）；清除为 `{"name": null}` 或 null body。成功 204。

### GET /rest/api/2/issue/{key}/transitions（可流转列表）
响应 `{"transitions": [{"id","name","to": {status 形状}, "fields"?: {...}}]}`；
`fields` 可整体省略（`expand=transitions.fields` 不支持时 400/404 降级重试，OpenTask 直接返回无
fields 版本即可）。CLI `--to` 匹配 `transition.name` 或 `transition.to.name`（大小写不敏感，须唯一命中）。

### POST /rest/api/2/issue/{key}/transitions（执行流转）
请求 `{transition: {id}, fields?: {...}, update?: {comment: [{add: {body}}]}}`。成功 204。

### GET/POST /rest/api/2/issue/{key}/comment
GET 翻页读法（`BB`+`rBt`+`iBt`）：取 `comments[]`，`total` 存在时按
`startAt + len < total` 决定续页，步进 `startAt += maxResults`；响应须含 `total/maxResults/startAt`。
元素读法（`uVt`）：`{id, body, created, updated?, author}`。
POST 请求 `{body}`（server 纯文本）；响应读 `.id`。

### GET /rest/api/2/project
server：**直接数组**（不分页），元素 `{id, key, name}`。

### GET /rest/api/2/issue/createmeta/{projectKey}/issuetypes[/{typeId}]
响应 `{"values": [...], "total", "maxResults", "startAt"}`（BB 翻页同上）。类型元素 `{id, name, ...}`；
字段元素（`pBt`）读 `key|fieldId|id`、`name`、`required`、`schema`、`allowedValues`。

### GET /rest/api/2/priority
数组，元素 `{id, name, iconUrl?}`（`hBt` 读 id/name/iconUrl）。

### GET /rest/api/2/user/search 与 /rest/api/2/user/assignable/search
server 参数名为 `username`（cloud 为 `query`），另带 `maxResults=50`、`issueKey`（assignable）。
响应用户数组，元素 `{name, displayName, emailAddress?, avatarUrls?}`（`VB`：accountId ?? name ?? key）。

### GET /rest/api/2/field
字段元数据数组（含 `schema.custom` 才被用于 sprint/storyPoints 发现）。返回空数组即全部跳过，安全。

### /rest/agile/1.0/board、/rest/api/2/filter/favourite
看板列序与收藏过滤器：任何错误 Orca 侧优雅降级（空列序/空列表），OpenTask **不实现**（404 即可）。

## 4. JQL 生成面（Orca 自产 JQL，OpenTask 必须能翻译）

`orca jira list --filter` 生成（`hVt`）：

```
assigned|done → assignee = currentUser()
reported      → reporter = currentUser()
done          → statusCategory = Done     （否则 statusCategory != Done）
可选          → status in ("A", "B")
可选          → sprint in openSprints()
结尾          → ORDER BY updated DESC
```

`orca jira search` 透传用户任意 JQL（如 `project = X AND text ~ '...'`、`key = OPENTASK-1`）。
→ OpenTask 需实现 JQL 子集：`assignee/reporter = currentUser() | = "<id>"`、
`status =|in`、`statusCategory =|!=|in`、`key =|in`、`project =|in`（恒为 OPENTASK）、
`summary ~ / text ~`（标题/描述包含）、`ORDER BY updated ASC|DESC`；AND 连接。
子集外语法返回 400（Jira 形状错误体），不静默吞掉。

## 5. 对 OpenTask 实现的关键结论

1. **只做 `/rest/api/2/*`**（server 模式固定 v2；v3 是 cloud 专用，含 ADF 描述/nextPageToken 翻页，
   与本任务无关）。
2. `myself` 是连接的第一跳（连接向导里"Test"即它）——必须最先可用。
3. Basic 与 Bearer 双头都要收：`Basic base64(user:vk_...)`（user 任意，取密码位校验）与
   `Bearer vk_...` / `Bearer <JWT>`，映射到契约层 access_token 内核（vk_ API Key / JWT）。
4. 写成功多用 **204 无 body**；comment add 与 create 要回 JSON（`.id` / `{id,key}`）。
5. `status.statusCategory` 三键 `new|indeterminate|done` 必须正确（影响 done 过滤与终态判定）。
6. server 描述/评论是**纯文本**（cloud 才需要 ADF），无需 ADF 解析。
7. key 形状：任务裁定 `OPENTASK-{数字}`；OpenTask issue_code 为 `ISSUE{年}-{序号}`（按年重置），
   为保证跨年不撞，数字取 `年*10^9 + 序号`（如 `ISSUE2026-3 → OPENTASK-202600000003`），
   解码唯一还原 issue_code（序号 ≥10^9 的极端年份超出本投影能力，返回 404）。
8. CLI 端 `status set --to <name>` 的匹配在客户端做，OpenTask 只需保证 transitions 里
   `name`（通用状态 token）与 `to.name`（展示名）一致可达且 id 唯一。

## 6. E2E 配置路径结论

- Orca 站点注册只能经桌面 Settings UI（IPC `jira:connect`；`~/.orca/jira-sites.json` + 加密 vault
  不可手写）。E2E 步骤：Orca 设置 → Integrations/Jira → Add site → Site URL
  `http://localhost:8000`、Server 模式、PAT=`vk_...`（或 email+token → Basic）→ 连接即调
  `GET /rest/api/2/myself` 验证。详证见 `2026-11-01-S7-orca-e2e-evidence.md`。

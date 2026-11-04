# E31 设计：Public Issue Forms（Linear Forms lite）

日期：2026-11-04（Asia/Shanghai）  
Epic：E31  
基线：`sprint/E30-S1` @ `06885b5`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E31-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E32**。

## 1. 目标

可分享的公开表单 → 提交后在工作区创建 Issue（KEY-N）；可选挂 Customer Request。

### A · 模型 + CRUD
- `issue_forms`：name、slug（WS 内唯一，可选）、token（公开凭据）、description、enabled、fields_json、create_customer_request、created_by、workspace_id
- `GET/POST /api/forms`；`GET/PATCH/DELETE /api/forms/{id}`；`POST /api/forms/{id}/regenerate-token`
- 公开：`GET /api/public/forms/{token}`；`POST /api/public/forms/{token}/submit`
- 权限：写 = **owner**；读 = **owner|member**（viewer 403）；强制 `X-Workspace-Id`；跨租户 403/404
- 朴素 rate-limit：同 token 短窗计数；`OPENTASK_FORM_RATE_LIMIT=0` 关闭（测用）

### B · 字段
- 类型：`title`（schema 必含且 required）|`description`|`priority`|`labels`|`assignee`|`custom_field`|`customer_id`
- custom_field 复用 E25 `validate_value`；assignee 按 username（email=username）解析且须为本 WS 成员
- 未知/禁用 token → 404；字段校验失败 → 400 + `errors[{field,message}]`

### C · FE
- `/settings/forms`：列表、创建/编辑、启停、复制公开链接、重生 token
- 公开页 `/f/:token`（blank layout）：渲染 + 提交成功态

### D · CLI **1.15.0**
- `form list|create|update|delete|url`

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 管理路径 `/api/forms`；公开 `/api/public/forms/{token}`（无鉴权，对齐 invites） |
| D2 | token = `secrets.token_urlsafe(24)`；公开 URL 只认 token；slug 仅管理侧可读/可筛 |
| D3 | 写=owner；读=owner\|member；viewer 403（同 E29 Webhooks） |
| D4 | `fields_json`：`[{key,type,label,required?,customFieldId?,help?}]`；必须恰好一个 `type=title` 且 required |
| D5 | 提交 actor / reporter = `form.created_by`（无匿名用户模型） |
| D6 | `create_customer_request=true` 且提交含有效 `customer_id` → 建 CustomerRequest 并链到新 Issue；缺 customer 则跳过不失败 |
| D7 | rate-limit：默认 30 次 / 60s / token（进程内存）；`OPENTASK_FORM_RATE_LIMIT=0` 关闭 |
| D8 | 禁用与未知一律 404，不区分 |
| D9 | FE 公开页 constant + blank；管理页 `/settings/forms` |
| D10 | CLI 1.15.0；`form url ID` 拼 `FRONTEND_BASE_URL/f/{token}` |
| D11 | 非目标：附件上传、验证码厂商、多页向导、品牌域名、Slack、远程 push；不自开 E32 |

## 3. 非目标

文件上传、付费/验证码、多页向导、对外品牌域名、Slack、远程 push、E32。

## 4. 验收摘要

- CRUD + 公开 schema/submit + 权限/租户 + rate-limit；FE 设置+公开页；CLI 1.15.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**

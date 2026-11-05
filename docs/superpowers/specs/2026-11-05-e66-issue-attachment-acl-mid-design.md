# E66 Design：Issue 附件鉴权 mid — ACL · 签名 URL · CLI 1.50.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E66  
基线拟：`sprint/E65-S1` @ `8202d69`（全文 `8202d692a4e560ed9733864b43a1737b783340e5`；E65 design 基线 `c3c0b25`；E64 tip `ab746df` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E66-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E67**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e66-issue-attachment-acl-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E66-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E65 连续闭合 … → Search FTS（E60）→ Insights 共享（E61）→ 评论 FTS（E62）→ Customer 公开状态门户（E63）→ 假日包扩容（E64）→ **Initiative 依赖图 mid（E65：`initiative_relations` · CLI 1.49.0）**。

E65 附录 runners-up（不绑定）：

1. **Activity 实时/推送加厚**（WS 扇出 / 浏览器 Notification / FCM）— 单列易溢；非「明显最优」；**默认不重开**  
2. **Customer 门户再厚**（公开回复线程 / Form 成功页深链）— E63 已隔假日+Initiative 两轮；任务仍 **prefer skip**（非本轮最高 ROI）  
3. **Initiative 甘特精修**（依赖边之上的排程视图）— E65 刚交付轻量依赖；**prefer skip** 本轮甘特

任务硬约束：轮换离开 **Initiative deps / 假日包 / Customer 门户 / Search / Insights** 刚闭弧；Activity Push **勿默认**。

代码实证 @ `8202d69`：

| 面 | 现状 |
|----|------|
| Issue 附件 | 上传/列表/删除走 `/api/issues/{id}/attachments*`（上传/删有会话）；**另有** `api/attachment/router.py`：`GET /api/attachments/{id}/download\|preview` 注释明示 **「公共访问，不需要认证」**，靠 UUID 随机性「基本安全」 |
| FE | `AttachmentList.vue` / `issue.ts` 直接拼 `/api/attachments/{id}/download\|preview`（无 token、无签名） |
| CLI | issue 附件 list/upload/delete/download 已有客户端方法；版本钉 **1.49.0**；无「鉴权/签名」产品叙事 |
| 租户 | 其它 Issue 面已有跨 WS 404；附件公共下载 **可绕过** 成员资格（知 UUID 即可读对象） |
| SLA 时区 | WS `timezone` + business hours 已齐；due/recurrence 仍 UTC（E35/E39 非目标）— 可后置 mid |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | 刚闭弧宜离开；runners-up 三刀均不宜本轮默认；附件公共下载是长期安全债，中厚刀可单 sprint 闭合（鉴权 + 可选短 TTL 签名 URL + FE/CLI），且不重开 Push/门户/甘特 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue 附件鉴权 mid**：`/api/attachments/{id}/download\|preview` 改为 **authenticate + 附件所属 Issue 的 WS 成员**；Issue 作用域 download 同样强制会话；可选 **短 TTL HMAC 签名 URL**（Q2a）供 `<img>`/PDF iframe；FE 改走鉴权或签名 URL；CLI **1.50.0** `issue attachment download` 走鉴权；**无** Push、**无** 假日/Customer/Search/Initiative 再开 | **中厚**；闭合明确安全缺口；复用既有 `authenticate` / WS membership；单 sprint 可交付 |
| B | Activity Push（WS / Notification / FCM） | 单列易溢；E52 已刻意砍；**默认不重开** |
| C | Customer 门户再厚 | 任务 prefer skip；非最高 ROI |
| D | Initiative 甘特精修 | E65 刚闭轻量依赖；prefer skip |
| E | Workspace 时区进 due/recurrence | 真缺口，但低于「未鉴权文件可读」；列入 runners-up |
| F | 仅文档警示「勿外泄 UUID」不动代码 | **过薄**；不治本 |

**建议拍板：A（Issue 附件鉴权 mid）。**  
Activity Push、Customer 门户再厚、Initiative 甘特、（可选）WS 时区进 due/recurrence 列入附录 runners-up。

自检：鉴权/租户、签名 URL 边界、FE 兼容、CLI **1.50.0**、非目标与 no-emit 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 单列易溢；非「明显最优」；任务明确勿默认 |
| Customer 门户再厚 | 任务 prefer skip；刚闭弧轮换离开 |
| Initiative 甘特 | E65 刚交依赖边；prefer skip |
| 假日包再扩 / ICS / 州包 | 刚闭 E64 |
| 再开 Search / Insights / Initiative 关系 | 刚闭；轮换离开 |
| WS 时区进 due/recurrence | 真 mid，但 ROI 低于附件 ACL |
| 真 GitHub App / SSO | 过厚 |

### Why this Epic now（一句话）

Issue 附件已有 MinIO 存储与上传面，但 **公共 `GET /api/attachments/{id}/download|preview` 明确免认证**——知 UUID 即可读任意租户对象；E65 依赖图弧刚闭后轮换离开 Initiative/假日/门户/Search/Insights，用中厚刀补上 **会话鉴权 + 可选短 TTL 签名 URL + FE/CLI**，正好把「能上传」抬到「只有成员能读」，且不重开 Push、甘特或门户大战。

---

## 1. 目标

成功标准：未登录访问附件 download/preview → **401**；登录但非附件所属 Issue 的 WS 成员 → **404**（租户统一）；WS **viewer+** 可读；writer+ 上传/删行为不变；可选签发短 TTL 签名 URL 供内联预览；FE 不再依赖裸公共 URL；CLI **1.50.0**；**不** Activity Push、**不**改 E57–E65 邻面主表面、**不** formula emit、**不**开甘特/门户。

### A · API / 鉴权（BE）

- `GET /api/attachments/{attachment_id}/download`  
- `GET /api/attachments/{attachment_id}/preview`  
  - **Q1a**：强制 `authenticate` + 解析附件 → Issue → `workspace_id` → 当前用户须为该 WS 成员；否则 401/404  
  - 去掉「公共访问 / UUID 即安全」产品叙事（注释与 OpenAPI description 同步改）  
- `GET /api/issues/{issue_id}/attachments/{attachment_id}/download`：同样强制会话 + 成员（与上同 ACL）  
- **不**改上传/列表/删除的写权限矩阵（既有 writer+ / 所有者规则保留）

### B · 签名 URL（可选捆，Q2a）

- `POST /api/attachments/{id}/signed-url`（或挂 issue 作用域）body `{ purpose: "download"|"preview", ttlSeconds? }`  
  - 仅 WS 成员可签发；默认 TTL **900s**（Q3a）；上限 3600  
  - 返回 `{ url, expiresAt }`；URL 带 HMAC（服务端密钥，现有 settings/secret 面）+ `exp` + `aid`  
- `GET /api/attachments/signed/{token}`（或 query `?sig=&exp=`）校验后流式返回；**不**要求会话 cookie（专供 `<img>` / iframe）  
- 过期 / 篡改 → 401/404；**不**把签名 URL 写入 DB（无状态）

### C · FE

- `AttachmentList.vue` / `issue.ts`：预览/下载改为  
  - 优先：带 Authorization 的 blob fetch → object URL；或  
  - 先 `signed-url` 再赋 `<img>`/`iframe` src（Q4a：**签名 URL 路径**，少改组件）  
- 错误态：401/404 友好提示  
- vitest：URL 构建 / 过期文案；build ok

### D · CLI **1.50.0**

- `opentask issue attachment download <issue-id> <attachment-id> [--out path]`（鉴权会话；**Q6a**）  
- 可选 `opentask issue attachment signed-url <…>` 打印短链（调试）  
- pins → **1.50.0**

### E · 安全 / 租户 / no-emit

- 跨 WS / 非成员 → **404**（与既有 IDOR 风格一致）  
- 不引入新 webhook 事件（**Q5a**）；下载不 fire_webhooks  
- formula **no-emit**  
- **不**改 E57–E65 邻面主表面（仅 CLI version pins）  
- **不**复活公共免认证默认；若需「邮件嵌入图」只走签名 URL

---

## 2. 非目标

- Activity Push / 浏览器 Notification / FCM / 实时 WS 产品化加厚  
- Customer 门户再厚、假日包 ICS/州包/2028  
- Initiative 甘特 / 依赖图再开、Search / Insights 再开  
- 附件病毒扫描、客户端加密、对象级 ACL 矩阵（per-file share to external）  
- 真 GitHub App、SSO、原生移动  
- Formula emit  
- 远程 push / 开 PR / 自开 E67

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 无会话 download/preview → 401；非成员 → 404；成员 200 |
| B | 签名 URL 未过期可读；过期/篡改拒绝；TTL 默认/上限遵守 |
| C | FE 预览/下载不再依赖裸公共 URL；vitest+build |
| D | CLI **1.50.0** + attachment download（+可选 signed-url）+ pins |
| E | 无新 webhook；不改 E57–E65 邻面；formula no-emit spy |
| 门禁 | BE 定向（attachments + tenant idor）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E67 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue 附件鉴权 mid**（方案 A）；会话 ACL + 可选签名 URL + FE/CLI；**无** Push / 甘特 / 假日/Customer 再开 |
| D2 | 公共免认证路径废除为默认；成员鉴权为唯一长期读路径（签名 URL 为例外短链） |
| D3 | 跨租户/非成员统一 404；未登录 401 |
| D4 | FE 预览优先短 TTL 签名 URL，避免改整条 axios 拦截器给 `<img>` |
| D5 | 下载/预览本轮不新增 webhook 事件名、不 fire |
| D6 | CLI = **1.50.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E57–E65 邻面；不 push；不自开 E67 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 公共路径处置？ | **Q1a** 强制 authenticate + WS 成员；废除「UUID 即安全」默认；备选 Q1b 保留公共但加全局 feature flag（易漏） |
| Q2 | 是否捆签名 URL？ | **Q2a** 本 Epic 并捆短 TTL HMAC 签名 URL（FE 内联刚需）；备选 Q2b 仅会话 blob fetch（`<img>` 难，下轮再补） |
| Q3 | 默认 TTL？ | **Q3a** 900s，硬顶 3600；备选 Q3b 300s（偏紧，大 PDF 预览易断） |
| Q4 | FE 策略？ | **Q4a** 预览走 signed-url；显式「下载」按钮可走鉴权 blob；备选 Q4b 全部 blob fetch（实现吵） |
| Q5 | webhook / 审计？ | **Q5a** 本轮不新增事件、不 fire；备选 Q5b 写薄 access log 表（偏厚，可后置） |
| Q6 | CLI 表面？ | **Q6a** `issue attachment download` + 可选 `signed-url`；备选 Q6b 仅 pins 无新命令（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. 公共 download/preview + issue-scoped download 鉴权（TDD：401/404/200）  
3. 签名 URL 签发 + 校验流（TDD：TTL/篡改）  
4. FE AttachmentList / issue.ts 改签或 blob（vitest）  
5. CLI 1.50.0 download（+可选 signed-url）  
6. no-emit / 邻面不动 spy + acceptance

---

## 7. 测试要点

- 无 Authorization → 401  
- 他 WS 成员持有效会话 → 404  
- 本 WS viewer → 200 download/preview  
- 签名 URL：未过期 200；改 aid/exp/sig → 拒；过期拒  
- TTL 默认 900、>3600 → 400  
- spy：无新 webhook 事件名；不触 E65 relations / E64 holiday / E63 status-link / E61 share；formula no-emit  
- CLI 1.50.0 pins + download  
- FE vitest；build ok

---

## 附录 · runners-up（供 E67+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52/E23 后再评估；单列易溢；非「明显最优」不重开。  
2. **Customer 门户再厚 thin-mid**（公开回复线程 UI / Form 成功页深链 status URL）— 已隔假日+Initiative；本轮为附件 ACL 让路后再评。  
3. **Initiative 甘特/时间线精修**（依赖边之上的排程视图）— E65 刻意砍画布；有关系数据后再开。  
4. **Workspace 时区进 due/recurrence mid**（复用已有 `workspaces.timezone`；对齐 E35/E39 明示非目标）— 真缺口，ROI 次于附件 ACL。

（备选扫描但本轮不推：假日包 ICS/州包/2028 — 刚闭 E64。再开 Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO — 过厚。Formula emit — 永不。重做 E52–E65 表面 — 无增量，不推。）

## CLI 版本

**1.50.0**

# E69 Design：评论附件 mid — issue_comment Documents · ACL 复用 · CLI 1.53.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E69  
基线拟：`sprint/E68-S1` @ `35f1e0a`（全文 `35f1e0a87192dde7f070701ce49851a3ced4f028`；E68 design 基线 `6e3d1a6`；E67 tip `dcf4c0c` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E69-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E70**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e69-comment-attachments-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E69-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E68 连续闭合 … → 附件鉴权（E66）→ WS 时区 due/recurrence（E67）→ **公开表单 → Triage 入队 mid（E68：`enqueue_triage` · CLI 1.52.0）**。

E68 附录 runners-up（不绑定）：

1. **Activity Push** — 「勿默认」；仅当极薄且 Linear 缺口极清才考虑 — **仍谨慎，非本轮默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b advance** — 刚做 TZ title-only；**rotate off**  
5. **评论附件 mid** — 复用 E66 ACL/签名 URL → **本草案收之（代码实证后）**

任务硬约束：轮换离开 **门户 / 假日 / Initiative deps / 附件 ACL 主面重开 / TZ·due / Form→Triage** 刚闭弧。

代码实证 @ `35f1e0a`：

| 面 | 现状 |
|----|------|
| Issue 附件 | `documents` 多态 `entity_type=issue`；E66 会话 ACL + HMAC signed-url；FE `AttachmentList` |
| Issue 评论 | `issue_comments` 正文/嵌套/反应齐；**无** 附件关联；`CommentsCard` 仅文本 |
| Document 模型 | 已多态 `(entity_type, entity_id)` — **可**挂 `issue_comment` 而无需新表 |
| Form→Triage | E68 **刚闭**；本轮宜离开 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | Linear 评论可挂文件；OpenTask 只能 Issue 级附件；E66 已铺 ACL/签名，评论轴是自然下一刀 mid，且不重开刚闭弧 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **评论附件 mid**：`documents.entity_type=issue_comment`；嵌套 API CRUD；ACL 经评论→Issue→WS（扩 E66 `require_attachment_read`）；download/preview/signed-url 复用；FE 评论区上传+预览；CLI **1.53.0**；**无** Push / 门户 / 甘特 / Form 再开 | **中厚**；接 E68 #5；复用存储+ACL；单 sprint 可交付 |
| B | Activity Push | 易溢；勿默认 |
| C | Customer 门户再厚 | prefer skip |
| D | Initiative 甘特 | prefer skip |
| E | Recurrence Q2b advance | rotate off |
| F | 再开 Form/Triage/TZ/假日 | 刚闭 |
| G | 仅 markdown 链外链当「附件」 | **过薄**；无 ACL/预览 |

**建议拍板：A（评论附件 mid）。**  
Push / 门户 / 甘特 / Q2b / Form 再厚列入附录 runners-up。

自检：多态实体、ACL 复用、FE 评论区、CLI **1.53.0**、非目标与 no-emit 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 非明显最优；仍勿默认 |
| Customer 门户再厚 | prefer skip；刚闭弧轮换 |
| Initiative 甘特 | prefer skip |
| Q2b recurrence advance | 刚做 TZ；震存量 |
| 再开 E63–E68 主表面 | 刚闭 |
| 真 GitHub App / SSO | 过厚 |

### Why this Epic now（一句话）

Issue 附件与 E66 鉴权已齐，但 **评论仍只能纯文本**——协作截图/日志只能挂到 Issue 根或外链；E68 Form→Triage 弧刚闭后轮换离开门户/假日/依赖/TZ/表单，用中厚刀把 **多态 Document 挂到 `issue_comment` + 复用 ACL/签名 URL + 评论区 FE/CLI**，正好补上 Linear 式「回复带文件」，且不重开 Push、甘特或门户。

---

## 1. 目标

成功标准：WS **writer+** 可在某 Issue 的评论上 **上传/列表/删除** 附件；**viewer+** 可读（download/preview/signed-url）；ACL 与 E66 同构（经父 Issue 的 WS 成员，跨租户 404）；FE 评论区可传可预览；CLI **1.53.0**；**不** Activity Push、**不**改 E57–E68 邻面主表面、**不** formula emit、**不**门户深链 / 甘特 / Form 再开。

### A · 存储（BE）

- 复用 `documents` 表；**Q1a** `entity_type = "issue_comment"`，`entity_id = comment.id`  
- **不**新建 `comment_attachments` 表（避免双存储）  
- 上传校验：comment 属于 path 中的 `issue_id`；否则 404  
- 可选：删除评论时级联删其 documents（**Q3a**：软删评论不物理删文件本轮；硬删评论时级联删 Document+MinIO）

### B · API（BE）

- `GET /api/issues/{issue_id}/comments/{comment_id}/attachments`  
- `POST /api/issues/{issue_id}/comments/{comment_id}/attachments`（multipart；writer+）  
- `DELETE /api/issues/{issue_id}/comments/{comment_id}/attachments/{attachment_id}`  
- 读路径：**Q2a** 扩 `require_attachment_read`：若 `entity_type=issue_comment` → 载评论 → 父 Issue → WS 成员；既有 `issue` 类型路径不变  
- `GET /api/attachments/{id}/download|preview` + `POST …/signed-url` + `GET /signed/{token}` **继续服务**评论附件（同一 ACL）  
- 列表评论响应可选嵌入 `attachments: []` 摘要（**Q4a**：详情评论 list 带薄摘要，免 N+1 另拉；cap 例如每评 20）

### C · FE

- `CommentsCard` / 评论输入：附件按钮（复用上传工具）；每条评论下 `AttachmentList`（signed-url 预览，对齐 E66）  
- vitest：URL/摘要 flatten；build ok；守 E63 `f`+`r`

### D · CLI **1.53.0**

- `opentask issue comment attachment list <issue> <comment>`  
- `… upload <issue> <comment> --file …`  
- `… download <issue> <comment> <aid> [--out]`（**Q6a**）  
- pins → **1.53.0**

### E · 安全 / 邻面 / no-emit

- 未登录 401；非成员 404；评论/Issue 跨 WS 404  
- **Q5a**：不新增 webhook 事件名；上传可不 fire（或仅既有 issue timeline `attachment_added` 带 `commentId` 元数据 — 默认 **不**新事件名）  
- formula **no-emit**  
- **不**改 E57–E68 主表面（Form enqueue / TZ / Initiative relations / 假日 / 门户 / Search 仅 pins）  
- **不**把评论附件暴露给公开 `/r` 或 `/f`

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification 产品化  
- Customer 门户再厚、Initiative 甘特、Recurrence Q2b advance  
- 再开 Form→Triage / TZ 语义 / 假日包 / Search / Insights / Initiative 关系  
- 表单公开页附件上传（E31 非目标）  
- 视频转码、病毒扫描、外链网盘  
- Formula emit；远程 push / 开 PR / 自开 E70

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | 评论上 CRUD 附件；`entity_type=issue_comment`；错绑 issue/comment → 404 |
| B | E66 download/preview/signed-url 对评论附件 ACL 生效（401/404/200） |
| C | 评论 list 可带 attachments 摘要；FE 上传+预览；vitest+build |
| D | CLI **1.53.0** + list/upload/download + pins |
| E | 无新 webhook 事件名；不改 E57–E68 邻面；formula no-emit；`f`+`r` 仍在 |
| 门禁 | BE 定向（comment attachments + E66 ACL 回归）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E70 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **评论附件 mid**（方案 A）；多态 Document + E66 ACL 复用 + FE/CLI；**无** Push / 门户 / 甘特 / Form 再开 |
| D2 | `entity_type=issue_comment`；不新建附件表 |
| D3 | ACL 经评论→Issue→WS；读写与 E66 同构 |
| D4 | 评论 list 薄嵌 attachments 摘要；FE 复用 AttachmentList/signed-url |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.53.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E57–E68 邻面；不 push；不自开 E70 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 存储形态？ | **Q1a** 复用 `documents` + `entity_type=issue_comment`；备选 Q1b 新表（重复 MinIO 元数据） |
| Q2 | 读 ACL？ | **Q2a** 扩 `require_attachment_read` 识别 comment 实体；备选 Q2b 独立 router 只用 issue 作用域（双路径易漏签） |
| Q3 | 删评论级联？ | **Q3a** 硬删评论时级联 Document+对象存储；软删不扫文件；备选 Q3b 永不级联（易孤儿） |
| Q4 | 列表嵌入？ | **Q4a** 评论序列化带 attachments 摘要（id/name/size/type）；备选 Q4b 永不嵌入、一律另 GET（FE 吵） |
| Q5 | webhook / timeline？ | **Q5a** 不新增事件名；可选父 Issue timeline 带 `commentId`（仍非新 webhook）；备选 Q5b `comment.attachment_added` 出站（拒默认） |
| Q6 | CLI？ | **Q6a** `issue comment attachment list/upload/download`；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. ACL 扩 issue_comment + 单测（TDD）  
3. 嵌套 attachments API CRUD（TDD）  
4. 评论 list 摘要 + FE CommentsCard（vitest）  
5. CLI 1.53.0  
6. no-emit / 邻面不动 / f+r spy + acceptance

---

## 7. 测试要点

- 上传到评论 A；list 仅见该评；挂到错误 issue → 404  
- 非成员 download/preview/signed → 404；无会话 → 401  
- 成员 signed-url 预览 200；篡改 token 拒  
- 硬删评论 → documents 行与对象清理（Q3a）  
- spy：无新 webhook 事件名；不触 E68 enqueue / E67 TZ tick / E66 仅回归绿 / E65 relations；formula no-emit  
- CLI 1.53.0 pins  
- FE vitest；build ok；elegant-router `f`+`r` 仍在

---

## 附录 · runners-up（供 E70+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WS / Notification / FCM）— 仍勿默认，除非能切成极薄 mid。  
2. **Customer 门户再厚**（Form 成功深链 status / 公开回复线程）— prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence 本地午夜 advance（Q2b）** — rotate off。  
5. **表单公开附件上传** — E31 非目标；有合规/验证码需求再开。

（备选扫描但本轮不推：再开 Form→Triage / TZ / 假日 / Search / Insights / Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO — 过厚。Formula emit — 永不。）

## CLI 版本

**1.53.0**

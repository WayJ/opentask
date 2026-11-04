# CodingWorker（Issue-first）

你是一个**自动化任务 Worker**，依次处理系统里待开发的 **Issue**（工作区单号 `KEY-N`，例如 `WAY-42`）。

> **E12-S3**：产品主路径为 Issue / KEY-N。~~强制每需求走 PGE~~ 已退役。  
> 若需遗留 PGE（Plan-Generation-Evaluation）三子任务流程，见可选指南：[docs/PGE_TASK_USER_GUIDE.md](./docs/PGE_TASK_USER_GUIDE.md)（**非默认**，仅深链/兼容场景）。

处理过程中请输出中间步骤，便于工程师监控。每个 Issue 处理完后，询问是否继续下一个（使用 AskUserQuestion）。

---

### 第一步：获取待处理列表

1. [opentask-works](./opentask-works.txt) 可包含多个 WorkCode（优先 `KEY-N`；历史也可能是 `ISSUE2026-xxx` / `需求2026-xxx`）。
2. 拉取未完成的 WorkCode 列表；若无待办，输出 `没有待处理work` 并结束。

### 第二步：循环处理每个 WorkCode

#### 1. 获取详情

1. 使用 OpenTask CLI：
   - 优先：`opentask issue show WAY-42`（或当前工作区 KEY-N）
   - 兼容：`opentask issue show ISSUE2026-15` / `opentask requirement show 需求2026-127`
2. 从 `main` 切到开发分支 `feat/{WorkCode}`。
3. 工作目录：`.opentask-workflow/{WorkCode}/`（progress.md、临时 md/图片）。

失败则输出错误并请求人类协助；成功则展示标题、描述、关联技能（如有）。

#### 2. 执行开发循环（Issue 驱动）

1. 按 Issue 描述与验收标准实现改动；优先复用仓库内已有技能（brainstorming → TDD → 实现 → 验证）。
2. **不要**默认调用 `POST /api/tasks` 创建 PGE 任务；该 API 已标记 Deprecated。
3. UI 改动须本地/浏览器验证；提交前跑相关测试。

#### 3. Update Progress

写入 `.opentask-workflow/{WorkCode}/progress.md`：

```
## [Date] - Task: [task description]

### What was done:
- [specific changes made]

### Testing:
- [how it was tested]

### Notes:
- [any relevant notes for future agents]
```

#### 4. 更新状态（可选）

成功后可用进度同步工具把本次目录文件回写到 Issue/需求文档；失败记录原因。

#### 5. 询问是否继续

1. 更新 todo，标记当前 WorkCode 完成。
2. 输出：`{WorkCode} 处理完成。是否继续处理下一个？请输入 yes 或 no。`
3. 若工程师要求自动继续，则批量无确认，输出：`[自动模式]继续下一个任务：{WorkCode}`

### 第三步：结束

全部完成或用户停止后输出「Worker 任务结束」，并在结束前做一次人工确认提问。

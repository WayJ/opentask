# OpenTask Workflow - AI Agent 工作规范

> **版本**: 1.2.0
> **更新日期**: 2026-03-10
> **目标读者**: AI 编程助手（Claude Code 等）
> **核心理念**: 复合式工程（Compound Engineering）- 让每单元工作使后续工作更容易

---

## 📖 文档定位

本文档是 **OpenTask 平台的 AI 工作规范手册**，告诉 AI Agent 如何参与到研发工作中。

**OpenTask 是什么：**
- AI 研发管理平台
- 管理 AI 工具（如 Claude Code）参与研发的流程
- 提供需求管理、任务管理、文档管理等功能

**本文档的作用：**
```
AI 收到任务 → 查阅本文档 → 按规范执行 → 记录日志
```

---

## 🎯 核心工作流

### Spec 流程（规范流程）

```
Constitution → Requirements → Plan → Tasks → Implementation → Review → Compound
                      ↓                                                      ↓
                   Clarify                                              知识沉淀
                (可选子阶段)                                        (让下次更容易)
```

**流程说明**：
- **Constitution**：项目治理原则（每个项目必须有）
- **Requirements**：明确"做什么"和"为什么"
  - 包含 **Clarify**（需求澄清，可选子阶段）
- **Plan**：明确"怎么做"（实施规划）
- **Tasks**：任务分解
- **Implementation**：执行实施
- **Review**：审查验收
- **Compound**：知识沉淀（让后续工作更容易）← **核心**

### No-Spec 流程（快速流程）

```
分析需求 → 直接实施 → 测试 → 提交
```

---

## 🤖 AI 决策规则

### 规则 1：Constitution 检查（新项目优先）

**IF** 接收到新项目或项目启动任务：
1. **THEN** 首先检查 Constitution 是否存在：
   - 检查路径：`docs/constitution.md`
   - 检查前端：`/workflow/constitution`

2. **IF** Constitution 不存在：
   - **THEN** 主动创建 Constitution
   - 使用默认模板
   - 提示用户填写项目信息
   - 等待用户确认

3. **IF** Constitution 已存在：
   - **THEN** 读取并遵循其中的规范
   - 继续执行后续流程

**Constitution 优先级**：Constitution > Workflow Guide > AI 默认决策

### 规则 2：选择工作流模式

**IF** 满足以下**任意条件**，**THEN** 使用 **Spec 流程**：
- 新功能开发（从零到一）
- 涉及数据库设计（新建表或重大结构调整）
- 涉及前端页面开发（新建页面或重构交互）
- 涉及第三方服务集成（支付、OSS、消息队列等）
- 涉及多模块协同（前后端、多服务）
- 复杂架构设计

**ELSE** 使用 **No-Spec 流程**：
- 简单 bug 修复（单一逻辑错误）
- 配置修改（环境变量、常量调整）
- 代码重构（不改变功能的优化）
- 文档更新（说明性修改）
- 测试用例编写

### 规则 3：Clarify 触发判断

**IF** 完成 Requirements 阶段后：

**满足以下**任意条件**，**THEN** 进入 Clarify 子阶段：
- ✅ 涉及数据库设计（新建表或重大调整）
- ✅ 涉及多模块集成（前后端、多服务）
- ✅ 涉及权限控制（角色、权限）
- ✅ 涉及第三方集成（支付、OSS 等）
- ✅ 需求描述字数 > 500 字
- ✅ 用户故事数量 > 3 个

**ELSE**：
- 直接确认需求完整
- 进入 Plan 阶段

**用户可手动触发**：
- 命令：`/clarify` - 强制进入 Clarify
- 命令：`/skip_clarify` - 跳过 Clarify

### 规则 4：用户命令优先级

**IF** 用户使用命令：
- `/spec` → 强制使用 Spec 流程
- `/no_spec` → 强制使用 No-Spec 流程
- `/constitute` → 创建/查看 Constitution
- `/clarify` → 强制进入 Clarify

**THEN** 忽略自动判断，按用户命令执行

### 规则 5：UI 相关修改强制测试

**IF** 修改涉及：
- 新建页面
- 大幅修改组件（重构核心逻辑）
- 修改用户交互流程

**THEN** 必须：
- 在浏览器中测试（使用 MCP Playwright）
- 截图确认 UI 正确显示
- 测试所有交互功能

### 规则 6：Compound 触发判断

**IF** 完成任务实施后：

**满足以下**任意条件**，**THEN** 执行 Compound 阶段：
- ✅ 解决了非平凡的问题（非显而易见的解决方案）
- ✅ 创建了可复用的组件或工具
- ✅ 发现了可复用的设计模式
- ✅ 修复了重要的 bug（有学习价值）
- ✅ 优化了性能（有参考价值）
- ✅ 集成了新的第三方服务
- ✅ 踩了有价值的"坑"

**ELSE**：
- 跳过 Compound 阶段
- 直接提交代码

**Compound 优先级**：让后续工作更容易 > 完美主义

### 规则 7：阻塞处理

**IF** 遇到以下情况：
- 缺少环境配置（API 密钥、数据库连接等）
- 外部依赖不可用（第三方 API、OAuth 等）
- 测试无法进行（需要真实账号、特定硬件等）
- 需求不明确（有歧义、缺少业务信息）

**THEN** 必须：
1. 在 `progress.txt` 记录阻塞原因
2. 输出清晰的阻塞信息（格式见下文）
3. 停止任务，等待人工介入
4. **禁止**提交 git commit
5. **禁止**标记 `passes: true`

---

## 📋 Spec 流程详解

### 阶段 0: Constitution（项目宪章，必须）

**目标**：建立项目治理原则

**产出**：`docs/constitution.md`

**必须包含**：
1. 项目信息（名称、目标、技术栈）
2. 代码规范（命名、风格、文件组织）
3. 测试要求（覆盖率、测试类型）
4. 架构原则（设计模式、分层）
5. 安全规范（密钥管理、验证）
6. 性能要求（响应时间、并发）

**在 OpenTask 中**：
- 前端路由：`/workflow/constitution`
- 可视化编辑界面
- 与所有后续阶段关联

**重要**：
- Constitution 是每个项目的必备文档
- 所有后续开发都遵循 Constitution 规范
- Constitution 优先于 Workflow Guide

### 阶段 1: Requirements（需求梳理）

**目标**：明确"**做什么**"和"**为什么**"

**产出**：`requirements.md` 或前端需求记录

**流程**：

#### Step 1: 初步需求收集
- 理解用户需求描述
- 编写用户故事（EARS 语法）
- 定义验收标准

#### Step 2: 判断是否需要 Clarify
- 使用规则 3 进行判断
- 满足条件则进入 Clarify

#### Step 3: Clarify（可选，详见下方）
- 系统性提问
- 澄清模糊细节
- 补充需求文档

#### Step 4: 确认需求完整
- 检视需求完整性
- 请用户确认

**必须包含**：
1. 需求背景和目标
2. 用户故事（EARS 语法）
3. 验收标准（可测试）
4. **Clarify 记录**（如果执行了 Clarify）

**重要**：
- 本阶段**只关注"什么"和"为什么"**
- **不讨论**技术实现、技术栈
- 技术方案在下一阶段（Plan）

**在 OpenTask 中**：
- 访问 `/workflow/requirements` 创建需求
- 可上传需求文档附件

#### Clarify 子阶段（可选）

**目标**：澄清需求细节，确保需求完整

**触发条件**：见规则 3

**提问维度**（8 个）：
1. **功能范围**：边界是什么？不包含什么？
2. **数据模型**：需要哪些字段？约束是什么？
3. **业务逻辑**：核心流程是什么？规则是什么？
4. **用户交互**：如何操作？需要哪些页面？
5. **权限控制**：谁可以访问？权限差异？
6. **数据验证**：验证规则是什么？
7. **性能要求**：数据量？并发？响应时间？
8. **集成需求**：需要调用其他服务吗？

**产出**：
- 更新后的 `requirements.md`
- Clarify 问答记录

### 阶段 2: Plan（实施规划）

**目标**：明确"**怎么做**"

**产出**：`plan.md` 实施规划文档

**必须包含**：
1. **技术栈选型**
   - 前端框架、UI 库
   - 后端框架、数据库
   - 开发工具

2. **系统架构设计**
   - 整体架构图
   - 模块划分和职责
   - 技术分层

3. **数据模型设计**（如涉及数据库）
   - ER 图或表结构
   - 字段定义和约束
   - 索引和关联关系

4. **API 接口设计**（如涉及接口）
   - RESTful API 定义
   - 请求/响应格式
   - 错误码规范

5. **前端页面设计**（如涉及前端）
   - 页面结构
   - 组件划分
   - 路由设计

6. **实施步骤**
   - 分阶段实施计划
   - 任务优先级
   - 依赖关系

7. **技术风险**
   - 潜在风险点
   - 缓解方案

**重要**：
- Plan 是实施规划，不是设计文档
- 强调实施路径、步骤、依赖
- 从 Plan 中自然分解出 Tasks

**在 OpenTask 中**：
- 为需求关联 Plan 文档
- Plan 文档可作为附件上传
- 可发起 Plan 评审流程

### 阶段 3: Tasks（任务分解）

**目标**：将 Plan 拆分为可执行任务

**产出**：`tasks.md` 任务清单

**任务格式**：
```markdown
## Phase 1: 数据层（优先级：高）
- [ ] 1.1 实现用户模型
   - 创建 User 数据表
   - 实现 CRUD 接口
   - 编写单元测试
   - _Plan: Section 3_

## Phase 2: API 层（优先级：高）
- [ ] 2.1 实现用户列表接口
- [ ] 2.2 实现用户创建接口
- [ ] 2.3 实现用户更新接口
- [ ] 2.4 实现用户删除接口

## Phase 3: 前端页面（优先级：中）
- [ ] 3.1 创建用户列表页
- [ ] 3.2 创建用户编辑页
```

**任务状态**：
- `[ ]` - 待处理（PENDING）
- `[-]` - 进行中（IN_PROGRESS）
- `[x]` - 已完成（COMPLETED）

**任务分解原则**：
- 单个任务完成时间 < 4 小时
- 任务间依赖关系清晰
- 每个 Task 可独立测试
- 优先完成基础任务

**在 OpenTask 中**：
- 前端访问：`/workflow/tasks`
- 任务自动关联到需求和 Plan
- 支持任务状态追踪和进度报告
- 实时统计完成率

### 阶段 4: Implementation（实施）

**目标**：执行任务并记录

**产出**：实施日志

**必须记录**：
1. **任务摘要**
   - 完成的工作描述
   - 实施的技术方案

2. **产出物（Artifacts）**
   - API 端点清单（含位置）
   - 前端组件清单（含 props）
   - 工具函数清单（含签名）
   - 数据库变更说明
   - 集成点说明

3. **文件变更**
   - 新增文件列表
   - 修改文件列表
   - 代码行数统计

4. **测试说明**
   - 测试方法
   - 测试结果

**在 OpenTask 中**：
- 任务详情页可查看实施日志
- 自动记录代码变更统计
- 支持关联代码提交

### 阶段 5: Review（审查）

**目标**：确保代码质量和功能完整性

**审查项**：
- [ ] 代码审查通过
- [ ] 单元测试通过
- [ ] 功能测试通过
- [ ] 文档更新完整
- [ ] 性能指标达标

**在 OpenTask 中**：
- 支持在线代码审查
- 集成自动化测试
- 审批流程可视化

### 阶段 6: Compound（知识沉淀）

**目标**：让后续工作更容易

**核心原则**：
> 每单元工程工作应使后续单元工作更容易，而非更难。

**产出**：结构化知识文档

**Compound 类型**：

#### 1️⃣ **问题解决方案（Solution）**
记录如何解决了一个有价值的问题。

**适用场景**：
- 解决了性能问题（如 N+1 query）
- 修复了安全漏洞
- 解决了集成难题
- 攻克了技术难点

**产出物**：
```markdown
# Solution: [问题标题]

## 问题描述
[清晰描述问题]

## 解决方案
[详细说明解决方法]

## 代码示例
```python
[关键代码]
```

## 避免回归
- [ ] 添加测试用例
- [ ] 添加 Lint 规则
- [ ] 更新文档

## 相关资源
- 实现任务：[task-id]
- 相关 Issue：[#xxx]
```

**存储位置**：`docs/solutions/[category]/[problem-name].md`

#### 2️⃣ **可复用组件（Component）**
记录创建的可复用组件。

**适用场景**：
- 新建了通用 UI 组件
- 封装了通用工具函数
- 创建了可复用 Hook
- 开发了通用中间件

**产出物**：
```markdown
# Component: [组件名称]

## 组件功能
[组件用途]

## 使用场景
- 场景1：[描述]
- 场景2：[描述]

## API 文档
### Props
- `prop1`: 类型 - 说明
- `prop2`: 类型 - 说明

### Events
- `event1`: 说明

### Methods
- `method1()`: 说明

## 使用示例
```vue
[代码示例]
```

## 位置
- 文件：[文件路径]
- 导入：`import [ComponentName] from [路径]`

## 下次需要类似功能时
直接使用此组件，不要重复开发！
```

**存储位置**：`docs/components/[component-name].md`

#### 3️⃣ **设计模式（Pattern）**
记录发现的可复用模式。

**适用场景**：
- 发现了架构模式
- 总结了开发模式
- 提炼了最佳实践

**产出物**：
```markdown
# Pattern: [模式名称]

## 模式描述
[模式说明]

## 适用场景
- [场景1]
- [场景2]

## 实现方式
```python
[代码示例]
```

## 优点
- [优点1]
- [优点2]

## 注意事项
- [注意点]

## 相关案例
- 案例1：[链接/描述]
- 案例2：[链接/描述]

## 下次遇到类似场景
自动应用此模式，不要重复设计！
```

**存储位置**：`docs/patterns/[pattern-name].md`

#### 4️⃣ **经验教训（Experience）**
记录踩坑和经验。

**适用场景**：
- 踩了容易掉的坑
- 发现了反直觉的行为
- 总结了调试技巧
- 记录了常见错误

**产出物**：
```markdown
# Experience: [经验标题]

## 踩坑记录
### 问题
[描述遇到的问题]

## 错误做法
```python
[错误代码]
```

## 正确做法
```python
[正确代码]
```

## 根本原因
[分析为什么出错]

## 预防措施
- [ ] 添加 Lint 规则
- [ ] 添加文档说明
- [ ] 更新 Constitution

## 相关资源
- Issue：[#xxx]
- PR：[#xxx]

## 下次遇到类似情况
直接应用此经验，避免重复踩坑！
```

**存储位置**：`docs/experience/[topic].md`

**Compound 完成标志**：
- [ ] 知识已结构化记录
- [ ] 文档已保存到合适位置
- [ ] 已更新索引（如需要）
- [ ] 相关测试/Lint 规则已添加

**重要**：
- Compound 不是"补文档"，而是"沉淀有价值的知识"
- 不要为了 Compound 而 Compound（避免完美主义）
- 优先沉淀高复用价值的知识

**在 OpenTask 中**：
- Implementation 日志中可标记值得 Compound 的内容
- 系统自动生成 Compound 文档草案
- 用户确认后保存到知识库

---

## ⚡ No-Spec 流程

**适用场景**：简单、快速的任务

**流程**：
1. 快速分析需求
2. 直接编码实现
3. 测试验证
4. 记录日志（可选）

**注意**：
- 仍需遵循代码规范
- 必须通过测试
- 建议记录实施日志

---

## 🔧 平台使用规范

### 环境初始化（每次会话必须）

```bash
./init.sh
```

**此脚本会**：
1. 初始化 Git 子模块
2. 安装/更新依赖
3. 检查环境配置
4. 显示启动说明

### 前端路由

```
/workflow/constitution         # Constitution 管理
/workflow/requirements         # 需求管理
/workflow/requirements/:id     # 需求详情（含 Clarify）
/workflow/plan                 # Plan 管理
/workflow/tasks                # 任务管理
/workflow/tasks/:id            # 任务详情
```

> 注：「工作流指南」页面（`/workflow-guide`）与「任务中心」页面（`/mission-center`）已于 2026-11-03 下线，
> 本文档仅保留为参考资料，不再有对应前端入口。

### API 端点

**Constitution 管理**：
```
GET    /api/constitution              # 获取 Constitution
POST   /api/constitution              # 创建 Constitution
PUT    /api/constitution              # 更新 Constitution
```

**需求管理**：
```
GET    /api/requirements              # 获取列表
POST   /api/requirements              # 创建需求
GET    /api/requirements/:id          # 获取详情
PUT    /api/requirements/:id          # 更新需求
POST   /api/requirements/:id/clarify  # 开始 Clarify
PUT    /api/requirements/:id/clarify  # 更新 Clarify 记录
POST   /api/requirements/:id/approve  # 审批需求
```

**Plan 管理**：
```
GET    /api/requirements/:id/plan     # 获取 Plan
POST   /api/requirements/:id/plan     # 创建 Plan
PUT    /api/requirements/:id/plan     # 更新 Plan
```

**任务管理**：
```
GET    /api/tasks                     # 获取列表
POST   /api/tasks                     # 创建任务
GET    /api/tasks/:id                 # 获取详情
PUT    /api/tasks/:id                 # 更新任务
PATCH  /api/tasks/:id/status          # 更新状态
```

### 任务选择规则

**IF** 存在 `task.json`：
1. 优先选择 `passes: false` 的任务
2. 考虑任务依赖关系
3. 从高优先级任务开始

**ELSE**：
- 等待用户指定任务

---

## ✅ 核心规则

### 1. 单一任务原则
每个会话只处理一个任务

### 2. Constitution 优先
每个项目必须有 Constitution，所有开发遵循 Constitution 规范

### 3. 测试驱动验证
- 功能必须经过测试才能标记完成
- UI 修改必须在浏览器验证
- API 接口需要测试覆盖

### 4. 浏览器测试强制
- 新建页面必须浏览器测试
- 大幅修改组件必须浏览器测试
- 使用 MCP Playwright 工具验证

### 5. 进度可追溯
每次工作必须记录到 `progress.txt`

### 6. 原子性提交
一个任务对应一个 commit，包含：代码 + task.json + progress.txt

### 7. 任务完整性
- 永远不删除任务
- 永不修改任务描述
- 仅将 `passes: false` 改为 `true`

### 8. 阻塞即停止
遇到阻塞立即停止，等待人工介入，禁止假装完成

### 9. 复合式增长
通过 Compound 阶段持续沉淀知识，实现团队能力的指数级增长

---

## 📚 知识库结构

OpenTask 通过结构化知识库实现复合式增长：

```
docs/
├── constitution.md           # 项目宪章（最高优先级）
├── patterns/                 # 设计模式（可复用的架构）
│   ├── auth-middleware.md
│   ├── error-handling.md
│   └── state-management.md
├── solutions/                # 问题解决方案（已解决的有价值问题）
│   ├── performance/
│   │   └── n-plus-one-query.md
│   ├── security/
│   │   └── sql-injection.md
│   └── integration/
│       └── payment-gateway.md
├── components/               # 可复用组件（不要重复造轮子）
│   ├── UserPicker.md
│   ├── FileUpload.md
│   └── DataGrid.md
└── experience/               # 经验教训（避免重复踩坑）
    ├── backend-api-best-practices.md
    ├── frontend-state-management.md
    └── common-pitfalls.md
```

**知识检索**：
- AI 开发前自动检索相关知识
- 提醒："上次遇到类似问题..."
- 引用相关模式和解决方案
遇到阻塞立即停止，等待人工介入，禁止假装完成

---

## 🛑 阻塞处理格式

**IF** 任务无法继续，**THEN** 按以下格式输出：

```
🚫 任务阻塞 - 需要人工介入

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前任务**: [任务名称]

**已完成的工作**:
- ✅ [已完成项1]
- ✅ [已完成项2]

**阻塞原因**:
[具体说明为什么无法继续]

**需要人工帮助**:
1. [具体步骤1]
2. [具体步骤2]

**解除阻塞后**:
运行以下命令继续任务：
```bash
[继续执行的命令]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 📝 提交规范

### Git 提交格式

```bash
# 格式：<type>(<scope>): <subject>

# type 类型：
feat:     新功能
fix:      修复 bug
refactor: 重构（不改变功能）
docs:     文档更新
style:    代码格式调整
test:     测试相关
chore:    构建/工具配置

# 示例：
git commit -m "feat(requirements): 添加需求审批功能"
git commit -m "fix(auth): 修复 Token 过期判断错误"
```

### 提交前检查

- [ ] lint 无错误
- [ ] build 成功
- [ ] 测试通过
- [ ] task.json 更新
- [ ] progress.txt 更新

---

## 📊 progress.txt 格式

```markdown
## [Date] - Task: [task description]

### What was done:
- [specific changes made]

### Testing:
- [how it was tested]

### Notes:
- [any relevant notes]
```

---

## 📚 相关文档

- **[API 规范](./API_SPECIFICATION.md)** - API 接口规范
- **[项目 README](../README.md)** - 项目概述
- **[工作流集成方案](./opentask-spec-workflow-integration.md)** - Spec Workflow 集成说明

---

## 📝 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-03-10 | 初始版本，定义 AI 工作规范 |
| 1.1.0 | 2026-03-10 | 更新工作流：增加 Constitution，Design 改为 Plan，Requirements 包含 Clarify 子阶段 |
| 1.2.0 | 2026-03-10 | 引入复合式工程（Compound Engineering）：增加 Compound 阶段，实现知识复利增长 |

---

**OpenTask Workflow** - AI Agent 工作规范（复合式工程）

> 让每单元工程工作使后续单元工作更容易

© 2026 Your Company. All rights reserved.

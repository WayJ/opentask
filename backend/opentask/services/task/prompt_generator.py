"""
OpenTask 任务提示词生成器

基于 Superpowers 项目设计理念，融合心理学与工程学最佳实践。
参考：https://github.com/obra/superpowers
"""

from typing import Dict, List, Optional
from datetime import datetime


class PromptGenerator:
    """任务提示词生成器"""

    def __init__(self):
        self.task_templates = self._init_templates()
        self.skill_descriptions = self._init_skill_descriptions()

    def _init_templates(self) -> Dict[str, str]:
        """初始化任务模板"""
        return {
            "custom": "",
            "feature": self._get_feature_template(),
            "bugfix": self._get_bugfix_template(),
            "refactor": self._get_refactor_template(),
            "performance": self._get_performance_template(),
        }

    def _init_skill_descriptions(self) -> Dict[str, str]:
        """初始化Superpowers技能描述"""
        return {
            "superpowers:using-superpowers": """
**核心元技能**：这是整个系统的入口技能，也是最重要的元规则。

**强制触发机制**：
- 如果在对话开始时，有哪怕**1%**的可能性适用于某个技能，Agent**必须**调用它
- 禁止找借口跳过流程（如"这只是个简单修改"、"我知道该怎么做"）

**技能优先级**：
- 流程类技能（头脑风暴、调试）优先于实现类技能
- 在做出任何响应之前，必须先检查并加载技能
""",

            "superpowers:brainstorming": """
**头脑风暴与设计技能**：在任何创造性工作之前，必须使用此技能。

**苏格拉底式对话**：
- 禁止一上来就抛出代码
- 一次只问一个问题来澄清需求
- 提出问题后等待回答，不要连续提问

**方案探索**：
- 提出2-3个不同的技术方案
- 给出推荐理由和权衡分析（Trade-offs）

**增量验证**：
- 将设计方案拆分成200-300字的小节
- 逐步展示并获得确认

**文档化产出**：
- 最终必须生成设计文档 `docs/design/YYYY-MM-DD-<topic>-design.md`
- 遵循YAGNI原则，无情剔除不必要的功能
""",

            "superpowers:writing-plans": """
**编写实施计划技能**：将设计转化为极细颗粒度的行动指南。

**微任务粒度**：
- 每个步骤必须能在**2-5分钟**内完成
- 例如："编写失败测试"、"运行测试确认失败"、"编写最小实现"

**无上下文假设**：
- 假设执行者是没有项目背景知识的初级工程师
- 计划必须包含：精确的文件路径、完整的代码片段、具体的验证命令

**产出物**：
- 生成详细的实施计划文件 `docs/plans/YYYY-MM-DD-<feature-name>.md`
""",

            "superpowers:test-driven-development": """
**测试驱动开发技能**：这是Superpowers的铁律。

**红-绿-重构循环**：
- 🔴 **RED**：编写一个失败的测试，**必须看着它失败**
- 🟢 **GREEN**：编写最小量的代码让测试通过
- 🔄 **REFACTOR**：在测试保护下重构代码

**绝对禁止**：
- 严禁在没有失败测试的情况下编写生产代码
- 如果先写了代码再补测试，**必须删除代码，重新开始**

**测试反模式**：
- ❌ 测试Mock而非真实行为
- ❌ 在生产代码中添加仅供测试的方法
- ❌ 不理解依赖就Mock
""",

            "superpowers:systematic-debugging": """
**系统化调试技能**：当事情出错时，像福尔摩斯一样工作。

**铁律**：在找到根本原因之前，**禁止尝试修复**

**四阶段流程**：
1. **根本原因调查**：阅读错误日志，复现问题，检查最近变更
2. **模式分析**：寻找代码库中类似的、正常工作的代码作为参考
3. **假设与测试**：提出单一假设，用最小的改动验证假设
4. **实施**：编写一个失败的测试用例，修复它，然后验证

**子工具**：
- `root-cause-tracing`：沿着调用栈反向追踪，找到错误数据的源头
- `defense-in-depth`：在数据流经的每一层都添加校验
- `condition-based-waiting`：使用轮询机制，避免固定延时
""",

            "superpowers:subagent-driven-development": """
**子Agent驱动开发技能**：核心执行引擎。

**单任务单Agent**：
- 对于计划中的每个任务，分派一个新的、上下文干净的Sub-Agent
- 避免长对话导致的上下文污染和注意力漂移

**双重审查循环**：
1. **规格合规性审查**：
   - 由"怀疑论者"Agent进行审查
   - 检查是否严格实现了需求
   - 不要相信实现者的报告，必须亲自阅读代码

2. **代码质量审查**：
   - 只有通过规格审查后才进行
   - 检查代码风格、可维护性、测试覆盖率

**自我反思**：
- 实现者Agent在提交前必须进行自我反思
- 检查是否满足了所有边缘情况
""",

            "superpowers:verification-before-completion": """
**完成前验证技能**：消除LLM的幻觉和虚假承诺。

**核心原则**：证据胜于主张

**门控机制**：
在声称"任务完成"之前，必须：
1. 确定能证明该主张的命令
2. 运行该命令
3. 读取完整输出
4. **只有在输出证实主张的情况下**，才能报告成功

**禁止用语**：
- ❌ "应该修复了"
- ❌ "看起来是对的"
- ❌ "逻辑上是通的"

**正确用语**：
- ✅ "测试通过，输出如下："
- ✅ "验证命令输出显示："
""",

            "superpowers:requesting-code-review": """
**请求代码审查技能**：确保代码质量。

**触发时机**：在任务间隙、功能完成时或合并前

**审查内容**：
- 对比 `{WHAT_WAS_IMPLEMENTED}` 和 `{PLAN_OR_REQUIREMENTS}`
- 将问题分为：致命（Critical）、重要（Important）、次要（Minor）

**规格合规性审查**：
- ✅ 严格实现了需求
- ✅ 没有少做
- ✅ 没有过度设计

**代码质量审查**：
- 代码风格是否符合规范
- 代码是否易于维护
- 测试覆盖率是否足够
""",
        }

    def _get_feature_template(self) -> str:
        """功能开发模板"""
        return """
## 第一阶段：需求分析与设计

**强制要求**：在编写任何代码之前，必须先完成需求分析。

### 1. 苏格拉底式提问（一次只问一个问题）

请回答以下问题来澄清需求：
1. 这个功能的核心价值是什么？
2. 目标用户是谁？
3. 使用场景是什么？
4. 技术约束有哪些？
5. 性能要求是什么？
6. 安全要求是什么？

### 2. 方案设计

提出2-3个技术方案，每个方案包含：
- 技术栈选择
- 架构设计
- 数据模型
- API设计
- 优缺点分析
- 推荐理由

**输出物**：设计文档 `docs/design/{date}-{feature}-design.md`

## 第二阶段：制定实施计划

**任务粒度**：每个任务2-5分钟可完成

**任务示例**：
```markdown
### 任务1: 创建数据模型
- 文件: `src/models/User.ts`
- 步骤:
  1. 定义接口
  2. 实现类
  3. 添加验证
- 验证: `npm run test:unit src/models/User.test.ts`
```

**输出物**：实施计划 `docs/plans/{date}-{feature}.md`

## 第三阶段：环境准备

**验证清单**：
- [ ] Git Worktree已创建（如需要）
- [ ] 依赖已安装
- [ ] 清洁基准已确立

## 第四阶段：测试驱动开发

**🔴 RED - 编写测试**
- 编写失败的测试
- 运行测试并看着它失败

**🟢 GREEN - 实现功能**
- 编写最小量代码
- 让测试通过

**🔄 REFACTOR - 重构代码**
- 在测试保护下重构
- 改善代码质量

## 第五阶段：代码审查

**审查重点**：
- 功能完整性
- 代码质量
- 测试覆盖
- 性能表现
- 安全性

## 第六阶段：完成前验证

**验证命令**：
```bash
# 功能验证
npm run test

# 代码质量
npm run lint
npm run type-check

# 构建验证
npm run build

# 测试覆盖率
npm run test:coverage
```

**门控标准**：
- ✅ 所有测试通过
- ✅ Lint检查通过
- ✅ 构建成功
- ✅ 测试覆盖率 ≥ 80%

## 技术要求

### 代码规范
- 遵循项目代码规范（AGENTS.md）
- 通过ESLint检查
- 通过Prettier格式化

### 测试要求
- 单元测试覆盖率 ≥ 80%
- 集成测试覆盖核心流程
- 边界情况测试完整

### 性能要求
- API响应时间 < 200ms（P95）
- 数据库查询优化
- 前端渲染时间 < 100ms（P95）

### 安全要求
- 输入验证完整
- SQL注入防护
- XSS防护
- CSRF防护
- 敏感数据加密
"""

    def _get_bugfix_template(self) -> str:
        """Bug修复模板"""
        return """
## 🐛 Bug修复流程

### 第一阶段：根本原因调查

**铁律**：在找到根本原因之前，**禁止尝试修复**

**调查步骤**：
1. **阅读错误日志**
   - 错误类型
   - 错误位置
   - 错误堆栈

2. **复现问题**
   - 编写复现步骤
   - 确认问题可稳定复现

3. **检查最近变更**
   - Git历史
   - 代码变更
   - 配置变更

4. **确定故障边界**
   - 添加日志
   - 运行测试
   - 定位问题

**输出物**：调查报告 `docs/debug/{date}-{bug}-investigation.md`

### 第二阶段：模式分析

**参考代码**：
- 寻找代码库中类似的、正常工作的代码
- 对比差异
- 找出根本原因

### 第三阶段：假设与测试

**提出假设**：
- 基于调查结果提出单一假设
- 假设必须具体可验证

**验证假设**：
- 用最小改动验证假设
- 确认假设的正确性

### 第四阶段：TDD修复流程

**🔴 RED - 编写复现测试**
```typescript
it('should reproduce the bug', () => {
  // 复现步骤
  // 预期: 报错或错误行为
});
```

**🟢 GREEN - 修复Bug**
- 编写最小量的修复代码
- 让测试通过

**🔄 REFACTOR - 纵深防御**
- 在数据流经的每一层添加校验
- 让此类Bug在结构上不可能再次发生

### 第五阶段：验证修复

**验证清单**：
- [ ] 复现测试通过
- [ ] 所有测试通过（无回归）
- [ ] 代码质量检查通过
- [ ] 性能无明显影响

**验证命令**：
```bash
npm run test
npm run lint
npm run type-check
```

### 修复原则

**纵深防御**：
在数据流经的每一层都添加校验：
```
用户输入 → API入口验证 → 业务逻辑验证 → 数据库验证 → 输出编码
```

**根因追踪**：
不要只修复报错的地方（症状），要沿着调用栈反向追踪，找到错误数据的源头。

**基于条件的等待**：
- ❌ 禁止使用 `sleep(1000)` 固定延时
- ✅ 必须使用轮询机制等待特定状态
"""

    def _get_refactor_template(self) -> str:
        """代码重构模板"""
        return """
## 🎯 重构目标
改善代码结构，提高可维护性

## 重构原则

### SOLID原则
- **S**ingle Responsibility: 单一职责
- **O**pen/Closed: 开闭原则
- **L**iskov Substitution: 里氏替换
- **I**nterface Segregation: 接口隔离
- **D**ependency Inversion: 依赖倒置

### DRY原则
Don't Repeat Yourself - 消除重复代码

### KISS原则
Keep It Simple, Stupid - 保持简单

### YAGNI原则
You Aren't Gonna Need It - 只实现当前需要的功能

## 重构流程

### 第一阶段：代码审查

**审查重点**：
- 代码结构
- 重复代码
- 复杂度
- 可维护性
- 性能瓶颈

**输出物**：审查报告 `docs/reviews/{date}-refactor-review.md`

### 第二阶段：识别重构机会

**重构指标**：
- 圈复杂度 > 10
- 代码重复率 > 5%
- 函数长度 > 50行
- 类长度 > 300行
- 参数数量 > 5个

### 第三阶段：制定重构计划

**计划要求**：
- 每个重构步骤2-5分钟
- 小步迭代，保持功能不变
- 每步都有测试保护

### 第四阶段：执行重构

**重构循环**：

1. **🔴 RED - 确保有测试保护**
   ```bash
   npm run test
   ```

2. **🟢 GREEN - 小步重构**
   - 一次只重构一处
   - 保持功能不变
   - 运行测试验证

3. **🔄 REFACTOR - 持续改进**
   - 在测试保护下优化
   - 改善代码结构
   - 提高可读性

### 第五阶段：验证重构

**验证清单**：
- [ ] 所有测试通过（功能不变）
- [ ] 代码质量提升
- [ ] 性能无下降
- [ ] 代码可读性提升
- [ ] 复杂度降低

**验证命令**：
```bash
npm run test
npm run complexity
npm run duplication
npm run benchmark
```

## 重构禁忌

❌ 不要同时重构功能和修改代码
❌ 不要在没有测试保护下重构
❌ 不要一次重构太多
❌ 不要为了重构而重构
❌ 不要引入不必要的抽象

✅ 小步迭代，频繁测试
✅ 保持功能不变
✅ 提高代码质量
✅ 改善可维护性
"""

    def _get_performance_template(self) -> str:
        """性能优化模板"""
        return """
## 🎯 优化目标
提升系统性能表现

## 📊 性能分析流程

### 第一阶段：性能分析

**铁律**：在找到性能瓶颈之前，**禁止盲目优化**

**分析步骤**：

1. **建立性能基准**
   ```bash
   npm run benchmark
   ```

2. **性能剖析**
   ```bash
   npm run profile:cpu
   npm run profile:memory
   npm run profile:database
   ```

3. **识别瓶颈**
   - 最慢的API端点
   - 最慢的数据库查询
   - 内存泄漏
   - CPU密集操作

**输出物**：性能分析报告 `docs/performance/{date}-analysis.md`

### 第二阶段：制定优化方案

**优化方向**：

1. **减少不必要的计算和渲染**
   - 缓存计算结果
   - 使用memoization
   - 懒加载组件

2. **优化数据查询和缓存**
   - 添加数据库索引
   - 优化SQL查询
   - 使用Redis缓存

3. **改进算法和数据结构**
   - 选择更高效的算法
   - 优化数据结构
   - 减少时间复杂度

4. **优化资源加载和利用**
   - 代码分割
   - 懒加载
   - CDN加速

### 第三阶段：实施优化

**优化循环**：

1. **🔴 RED - 编写性能测试**
   ```typescript
   it('should respond within 100ms', async () => {
     const start = Date.now();
     await api.call();
     const duration = Date.now() - start;
     expect(duration).toBeLessThan(100);
   });
   ```

2. **🟢 GREEN - 实施优化**
   - 按照优化方案实施
   - 运行性能测试
   - 确认达标

3. **🔄 REFACTOR - 持续优化**
   - 进一步优化
   - 优化热点代码
   - 减少资源消耗

### 第四阶段：验证优化效果

**验证清单**：
- [ ] 性能测试通过
- [ ] 功能测试通过（无回归）
- [ ] 性能提升达标
- [ ] 资源消耗合理

**性能指标**：
| 指标 | 优化前 | 优化后 | 提升 |
|-----|--------|--------|------|
| API响应时间 | {current}ms | {target}ms | {improvement}% |
| 数据库查询 | {current}ms | {target}ms | {improvement}% |
| 内存使用 | {current}MB | {target}MB | {improvement}% |

## 优化禁忌

❌ 不要过早优化
❌ 不要为了优化牺牲可读性
❌ 不要在没有测试保护下优化
❌ 不要忽略业务需求
❌ 不要过度优化

✅ 基于数据驱动优化
✅ 优化真正的瓶颈
✅ 保持代码可维护性
✅ 平衡性能和质量
"""

    def generate_pge_prompt(
        self,
        requirement_title: str,
        requirement_id: str,
        task_id: str,
        description_template: str,
        required_skills: List[str],
        created_at: Optional[str] = None,
    ) -> str:
        """
        生成PGE任务提示词

        Args:
            requirement_title: 需求标题
            requirement_id: 需求ID
            task_id: 任务ID
            description_template: 描述模板类型（custom/feature/bugfix/refactor/performance）或自定义描述
            required_skills: 必需技能列表
            created_at: 创建时间

        Returns:
            完整的PGE任务提示词
        """
        if created_at is None:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 获取模板内容
        template_content = self.task_templates.get(
            description_template,
            description_template if description_template in self.task_templates else ""
        )

        # 生成技能引用部分
        skills_section = self._generate_skills_section(required_skills)

        # 估算Token数
        estimated_tokens = self._estimate_tokens(
            requirement_title, template_content, required_skills
        )

        # 构建完整提示词
        prompt = f"""# PGE 任务：{requirement_title}

> **任务 ID**: {task_id}
> **关联需求**: {requirement_id}
> **执行框架**: PGE (Plan-Generation-Evaluation)
> **创建时间**: {created_at}

---

## 📋 任务描述

{template_content if template_content else "（自定义任务描述）"}

---

## 🎯 必需技能

{', '.join(required_skills) if required_skills else '无'}

---

{skills_section}

---

## 📊 子任务进度

### ✅ 1. Plan（规划）
- **状态**: `pending`
- **描述**: 制定详细的实施方案，包括技术选型、架构设计、任务分解
- **任务编码**: `1.1`
- **输出物**:
  - 技术方案文档
  - 架构设计图
  - 详细任务清单

### ✅ 2. Generation（生成）
- **状态**: `pending`
- **描述**: 按照 Plan 方案实现功能，编写代码和测试
- **任务编码**: `1.2`
- **输出物**:
  - 源代码
  - 单元测试
  - 集成测试
  - 技术文档

### ✅ 3. Evaluation（评估）
- **状态**: `pending`
- **描述**: 评估 Generation 的产出，检查代码质量、测试覆盖、功能完整性
- **任务编码**: `1.3`
- **输出物**:
  - 代码审查报告
  - 测试覆盖率报告
  - 改进建议清单

---

## 🚀 当前执行位置

- ✅ **当前应该执行**: **Plan（规划）**
- ⚠️ **注意**：子任务必须按顺序执行（Plan → Generation → Evaluation）

---

## 📝 执行指南

### 核心原则

1. **严格按照子任务顺序执行**：Plan → Generation → Evaluation
2. **前一个子任务的输出是后一个子任务的输入**
3. **Evaluation 提出修改建议时，Generation 需要继续 session 修改**
4. **使用指定的 Superpower Skills**（如有）
5. **完成每个子任务后更新状态**

### 质量标准

- **代码质量**: 遵循项目代码规范，通过ESLint/Prettier检查
- **测试覆盖**: 核心功能测试覆盖率 ≥ 80%
- **文档完整**: 包含API文档、使用说明、部署指南
- **性能要求**: 响应时间 < 200ms（P95）

### 验证要求

- ✅ 所有测试必须通过（单元测试 + 集成测试）
- ✅ 代码必须通过Lint检查
- ✅ 构建必须成功（npm run build）
- ✅ 功能必须在浏览器/环境中验证通过

---

## 🚨 核心约束与红线

### 1. 禁止偷懒（Anti-Rationalization）

以下想法是**错误**的，必须立即停止并重新加载技能：

❌ "这只是个简单修改，不需要完整流程"
❌ "我知道该怎么做，可以直接开始"
❌ "时间紧迫，可以跳过测试"
❌ "这个技能不适用于当前情况"

**正确做法**:
✅ 使用 `superpowers:brainstorming` 澄清需求
✅ 使用 `superpowers:writing-plans` 制定计划
✅ 使用 `superpowers:test-driven-development` 编写测试
✅ 使用 `superpowers:systematic-debugging` 调试问题

### 2. 证据胜于主张（Evidence over Claims）

**门控机制**：在声称"任务完成"、"Bug已修复"或"测试通过"之前，必须：

1. 确定能证明该主张的命令
2. 运行该命令
3. 读取完整输出
4. **只有在输出证实主张的情况下**，才能报告成功

**禁止用语**:
❌ "应该修复了"
❌ "看起来是对的"
❌ "逻辑上是通的"
❌ "应该可以工作"

**正确用语**:
✅ "测试通过，输出如下："
✅ "验证命令输出显示："
✅ "代码审查结果："

### 3. 明确承诺（Commitment）

**承诺机制**：在开始每个子任务前，必须先回复：

> "**我确认理解任务 [子任务名称] 的要求，并承诺严格遵守TDD与验证纪律。**"

沃顿商学院研究表明，这种"登门槛"式的承诺机制能让后续违约概率大幅降低。

---

## 📊 Token估算

- **预估Token数**: ~{estimated_tokens:,} tokens
- **建议**: 如果超过100K tokens，建议拆分子任务

---

## 🎓 心理学与工程学结合

本提示词设计基于以下研究成果：

### 沃顿商学院实证研究
通过28,000次对话实验证明，运用Cialdini的说服原则时，AI对指令的依从率从**33%飙升至72%**。

### 应用的心理学原则

| 原则 | 应用场景 | 效果 |
|-----|---------|------|
| **权威（Authority）** | 代码审查、质量把关 | 让AI产生对质量的敬畏感 |
| **承诺（Commitment）** | 任务开始前 | 提高履约率 |
| **稀缺性（Scarcity）** | 紧急任务 | 抑制走捷径本能 |

### 应用的工程学原则

- **TDD**: 测试驱动开发
- **红-绿-重构循环**: 持续集成
- **双重审查机制**: 规格合规性 → 代码质量
- **系统化调试**: 根因分析 → 模式匹配 → 假设验证 → 实施

---

## 🤖 自动化执行流程

### 角色定义

**角色 1: Planner**（对应子任务1：Plan）
- 产出计划文件
- 输出 `[PLAN_DONE] 计划文件路径：xxx`
- 然后自动进入角色 2

**角色 2: Generator**（对应子任务2：Generation）
- 按照计划实施 TDD
- 输出 `[GENERATION_DONE]`
- 然后自动进入角色 3

**角色 3: Evaluator**（对应子任务3：Evaluation）
- 产出审查报告
- 如果结论是"通过"，输出 `[FINAL_PASS]` 并停止
- 如果结论是"不通过"，输出 `[EVAL_FAIL]`，然后**自动切换回角色 2**
- 最多循环 3 次。第 3 次仍不通过则输出 `[FAILED_AFTER_MAX_LOOPS]` 并停止

### 执行规则

**禁止行为**:
- 严禁中途询问"是否继续"或"请确认"
- 严禁跳过任何子任务
- 严禁违反TDD纪律

**强制行为**:
- 必须按 Plan → Generation → Evaluation 顺序执行
- 必须在完成前验证所有声称
- 必须提供具体的证据（命令输出、截图、日志）

---

## 📚 参考资料

- **Superpowers项目**: https://github.com/obra/superpowers
- **Anthropic Harness设计**: Claude Code团队官方文档
- **沃顿商学院研究**: "Call Me A Jerk: Persuading AI to Comply with Objectionable Requests"
- **《影响力》**: Robert Cialdini著

---

## 🚀 开始执行

现在，请按以下步骤自动执行：

1. 首先输出：`开始执行自动化 PGE 流程`
2. 立即执行角色 1（Planner）

**记住**: 严禁停下来问我任何问题，严格按照流程执行直到完成或达到上限。
"""

        return prompt

    def _generate_skills_section(self, required_skills: List[str]) -> str:
        """生成技能引用部分"""
        if not required_skills:
            return ""

        section = "## 🎓 引用的 Superpower Skills\n\n"
        section += "每个技能都包含详细的执行指令，AI必须严格遵循。\n\n"

        for skill in required_skills:
            skill_desc = self.skill_descriptions.get(skill, "")
            if skill_desc:
                section += f"### {skill}\n{skill_desc}\n"

        return section

    def _estimate_tokens(
        self, title: str, description: str, skills: List[str]
    ) -> int:
        """
        估算Token数量

        规则：
        - 中文字符（Unicode > 255）：1.5 tokens
        - 英文字符、数字、标点：0.25 tokens（4字符=1token）
        """
        text = f"{title}\n{description}\n{', '.join(skills)}"
        token_count = 0

        for char in text:
            char_code = ord(char)
            if char_code > 255:
                token_count += 1.5  # 中文
            else:
                token_count += 0.25  # 英文

        return int(token_count)


# 全局实例
prompt_generator = PromptGenerator()


def generate_task_prompt(
    requirement_title: str,
    requirement_id: str,
    task_id: str,
    description_template: str,
    required_skills: List[str],
    created_at: Optional[str] = None,
) -> str:
    """
    生成任务提示词的便捷函数

    Args:
        requirement_title: 需求标题
        requirement_id: 需求ID
        task_id: 任务ID
        description_template: 描述模板类型或自定义描述
        required_skills: 必需技能列表
        created_at: 创建时间

    Returns:
        完整的PGE任务提示词
    """
    return prompt_generator.generate_pge_prompt(
        requirement_title=requirement_title,
        requirement_id=requirement_id,
        task_id=task_id,
        description_template=description_template,
        required_skills=required_skills,
        created_at=created_at,
    )

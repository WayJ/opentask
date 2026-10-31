const fs = require('node:fs');

// 读取文件
const filePath = 'src/views/workflow/requirement-detail/components/CreatePGETaskModal.vue';
let content = fs.readFileSync(filePath, 'utf-8');

// 新的 promptPreview 函数
const newPromptPreview = `// 生成提示词预览（与后端完全一致的格式）
const promptPreview = computed(() => {
  const selectedSkills = formData.value.required_skills;

  // 任务标题
  const title = formData.value.title || '未设置任务标题';
  const description = formData.value.description || '无描述';

  // 生成必需技能部分
  let skillsSection = '';
  if (selectedSkills.length > 0) {
    const skillsList = selectedSkills
      .map(skillId => {
        // 从 SUPERPOWER_SKILLS 查找技能信息
        let skillName = skillId;
        let skillDescription = '';
        for (const categorySkills of Object.values(SUPERPOWER_SKILLS)) {
          const skill = categorySkills.find(s => s.id === skillId);
          if (skill) {
            skillName = skill.name;
            skillDescription = skill.description;
            break;
          }
        }
        return \`- ✅ \${skillName} (\${skillId})\\n  - \${skillDescription}\`;
      })
      .join('\\n');
    skillsSection = skillsList + '\\n';
  } else {
    skillsSection = '无\\n\\n';
  }

  // 生成子任务进度部分（固定格式，因为任务还未创建）
  const subtasksSection = \`### ✅ 1. Plan（规划）
- **状态**: pending
- **描述**: 制定详细的实施方案，包括技术选型、架构设计、任务分解
- **任务编码**: 1.1

### ✅ 2. Generation（生成）
- **状态**: pending
- **描述**: 按照 Plan 方案实现功能，编写代码和测试
- **任务编码**: 1.2

### ✅ 3. Evaluation（评估）
- **状态**: pending
- **描述**: 评估 Generation 的产出，检查代码质量、测试覆盖、功能完整性
- **任务编码**: 1.3
\`;

  // 完整的提示词（与后端 generate_task_prompt 输出格式完全一致）
  return \`# PGE 任务：\${title}

> 任务 ID: （创建后自动生成）
> 关联需求: \${props.requirementId}
> 框架: PGE (Plan-Generation-Evaluation)

---

## 📋 任务描述

\${description}

---

## 🎯 必需技能

\${skillsSection}
---

## 📊 子任务进度

\${subtasksSection}
---

## 🚀 当前执行位置

- ✅ 当前应该执行: **Plan（规划）**
- ⚠️ 注意：子任务必须按顺序执行（Plan → Generation → Evaluation）

---

## 📝 执行指南

1. **严格按照子任务顺序执行**：Plan → Generation → Evaluation
2. **前一个子任务的输出是后一个子任务的输入**
3. **Evaluation 提出修改建议时，Generation 需要继续 session 修改**
\${selectedSkills.length > 0 ? '4. **使用指定的 Superpower Skills**（如有）' : ''}
5. **完成每个子任务后更新状态**
\`;
});`;

// 替换旧的 promptPreview 函数（从 "// 生成提示词预览" 到 "});"）
const regex = /\/\/ 生成提示词预览[\s\S]*?\(\);/;
content = content.replace(regex, newPromptPreview);

// 写回文件
fs.writeFileSync(filePath, content, 'utf-8');
console.log('修复成功！');

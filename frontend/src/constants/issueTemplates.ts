/**
 * Issue 模板定义
 * 提供预定义的 Issue 模板，帮助用户快速创建规范的 Issue
 */

export interface IssueTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  fields: IssueTemplateField[];
}

export interface IssueTemplateField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'checkbox';
  placeholder?: string;
  required: boolean;
  options?: string[];
  defaultValue?: string | boolean;
}

/**
 * 预定义的 Issue 模板
 */
export const ISSUE_TEMPLATES: IssueTemplate[] = [
  {
    id: 'bug_report',
    name: 'Bug 报告',
    description: '报告系统中的问题或错误',
    icon: 'i-carbon-bug',
    fields: [
      {
        name: 'title',
        label: '问题标题',
        type: 'text',
        placeholder: '简要描述问题',
        required: true
      },
      {
        name: 'description',
        label: '问题描述',
        type: 'textarea',
        placeholder: '详细描述遇到的问题',
        required: true
      },
      {
        name: 'environment',
        label: '环境信息',
        type: 'textarea',
        placeholder: '- 操作系统:\n- 浏览器:\n- 版本:',
        required: false
      },
      {
        name: 'steps_to_reproduce',
        label: '复现步骤',
        type: 'textarea',
        placeholder: '1. \n2. \n3. ',
        required: true
      },
      {
        name: 'expected_behavior',
        label: '期望行为',
        type: 'textarea',
        placeholder: '描述期望的正确行为',
        required: true
      },
      {
        name: 'actual_behavior',
        label: '实际行为',
        type: 'textarea',
        placeholder: '描述实际发生的错误行为',
        required: true
      },
      {
        name: 'attachments',
        label: '附件',
        type: 'textarea',
        placeholder: '截图、日志文件等（可使用附件上传功能）',
        required: false
      }
    ]
  },
  {
    id: 'feature_request',
    name: '功能请求',
    description: '提出新功能或改进建议',
    icon: 'i-carbon-light',
    fields: [
      {
        name: 'title',
        label: '功能标题',
        type: 'text',
        placeholder: '简要描述功能请求',
        required: true
      },
      {
        name: 'description',
        label: '功能描述',
        type: 'textarea',
        placeholder: '详细描述请求的功能',
        required: true
      },
      {
        name: 'motivation',
        label: '动机和用例',
        type: 'textarea',
        placeholder: '解释为什么需要这个功能，以及使用场景',
        required: true
      },
      {
        name: 'proposed_solution',
        label: '建议的解决方案',
        type: 'textarea',
        placeholder: '描述你期望的功能如何工作',
        required: false
      },
      {
        name: 'alternatives',
        label: '替代方案',
        type: 'textarea',
        placeholder: '描述你考虑过的其他解决方案',
        required: false
      },
      {
        name: 'priority',
        label: '优先级',
        type: 'select',
        options: ['低', '中', '高', '紧急'],
        defaultValue: '中',
        required: true
      }
    ]
  },
  {
    id: 'improvement',
    name: '改进建议',
    description: '改进现有功能或代码',
    icon: 'i-carbon-chart-line-smooth',
    fields: [
      {
        name: 'title',
        label: '改进标题',
        type: 'text',
        placeholder: '简要描述改进建议',
        required: true
      },
      {
        name: 'current_state',
        label: '当前状态',
        type: 'textarea',
        placeholder: '描述当前功能或代码的状态',
        required: true
      },
      {
        name: 'proposed_improvement',
        label: '改进方案',
        type: 'textarea',
        placeholder: '详细描述改进方案',
        required: true
      },
      {
        name: 'benefits',
        label: '预期收益',
        type: 'textarea',
        placeholder: '列出改进带来的好处',
        required: true
      },
      {
        name: 'impact',
        label: '影响范围',
        type: 'textarea',
        placeholder: '描述此改进对系统的影响',
        required: false
      }
    ]
  },
  {
    id: 'question',
    name: '问题咨询',
    description: '提出技术问题或寻求帮助',
    icon: 'i-carbon-help',
    fields: [
      {
        name: 'title',
        label: '问题标题',
        type: 'text',
        placeholder: '简要描述你的问题',
        required: true
      },
      {
        name: 'description',
        label: '问题描述',
        type: 'textarea',
        placeholder: '详细描述你的问题',
        required: true
      },
      {
        name: 'context',
        label: '背景信息',
        type: 'textarea',
        placeholder: '提供相关的背景信息（如使用场景、相关代码等）',
        required: true
      },
      {
        name: 'attempts',
        label: '尝试过的方案',
        type: 'textarea',
        placeholder: '描述你已经尝试过的解决方案',
        required: false
      }
    ]
  },
  {
    id: 'task',
    name: '任务分配',
    description: '创建待办任务',
    icon: 'i-carbon-task',
    fields: [
      {
        name: 'title',
        label: '任务标题',
        type: 'text',
        placeholder: '简要描述任务',
        required: true
      },
      {
        name: 'description',
        label: '任务描述',
        type: 'textarea',
        placeholder: '详细描述任务内容',
        required: true
      },
      {
        name: 'acceptance_criteria',
        label: '验收标准',
        type: 'textarea',
        placeholder: '- [ ] 标准 1\n- [ ] 标准 2\n- [ ] 标准 3',
        required: true
      },
      {
        name: 'complexity',
        label: '复杂度',
        type: 'select',
        options: ['简单', '中等', '复杂', '非常复杂'],
        defaultValue: '中等',
        required: true
      },
      {
        name: 'time_estimate',
        label: '时间估算',
        type: 'text',
        placeholder: '例如：2小时、1天、1周',
        required: false
      }
    ]
  }
];

/**
 * 根据 ID 获取模板
 */
export function getTemplateById(id: string): IssueTemplate | undefined {
  return ISSUE_TEMPLATES.find(t => t.id === id);
}

/**
 * 生成模板表单的初始内容
 */
export function generateTemplateContent(template: IssueTemplate, formData: Record<string, any>): string {
  let content = `## ${template.name}\n\n`;

  for (const field of template.fields) {
    const value = formData[field.name] || field.defaultValue || '';
    const required = field.required ? '**(必填)**' : '';

    if (field.type === 'checkbox') {
      content += `### ${field.label} ${required}\n${value ? '✅' : '☐'}\n\n`;
    } else if (field.type === 'select') {
      content += `### ${field.label} ${required}\n${value || '(未选择)'}\n\n`;
    } else {
      content += `### ${field.label} ${required}\n${value || field.placeholder || '(待填写)'}\n\n`;
    }
  }

  return content;
}

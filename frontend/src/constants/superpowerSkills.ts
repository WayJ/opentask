/** Superpower Skills 常量定义
 *
 * 参考 Anthropic Superpowers 规范
 * https://news.qq.com/rain/a/20260115A08AVR00
 */

/** Superpower Skills 分类定义 */
export const SUPERPOWER_SKILLS = {
  规划类: [
    {
      id: 'superpowers:brainstorming',
      name: '创意风暴',
      description: '在创意工作前使用，强制发散思维，探索多种可能性'
    },
    {
      id: 'superpowers:writing-plans',
      name: '编写计划',
      description: '将需求分解为可执行的任务清单和实施步骤'
    }
  ],
  执行类: [
    {
      id: 'superpowers:test-driven-development',
      name: '测试驱动开发',
      description: '在编写实现代码前先写测试，确保代码质量'
    },
    {
      id: 'superpowers:executing-plans',
      name: '执行计划',
      description: '按照既定计划执行任务，跟踪进度'
    },
    {
      id: 'superpowers:systematic-debugging',
      name: '系统化调试',
      description: '遇到 bug 时系统性排查，而非猜测式修改'
    }
  ],
  审查类: [
    {
      id: 'superpowers:code-review',
      name: '代码审查',
      description: '完成任务后审查代码，确保符合规范'
    },
    {
      id: 'superpowers:verification-before-completion',
      name: '完成前验证',
      description: '标记完成前进行最终验证，确保所有检查项通过'
    }
  ],
  设计类: [
    {
      id: 'superpowers:frontend-design',
      name: '前端设计',
      description: '创建前端界面时使用，确保 UI/UX 质量'
    }
  ]
} as const;

/** Superpower Skills 类型定义 */
export type SuperpowerSkillId = (typeof SUPERPOWER_SKILLS)[keyof typeof SUPERPOWER_SKILLS][number]['id'];

/** 任务框架枚举 */
export enum TaskFramework {
  PGE = 'PGE'
}

/** 任务状态枚举 */
export enum TaskStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED'
}

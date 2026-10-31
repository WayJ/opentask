<script setup lang="ts">
import { computed, h, ref, resolveComponent } from 'vue';
import { NButton, NPopconfirm, NTooltip } from 'naive-ui';
import type { Task } from '@/service/api/requirement';
import { RequirementTaskStatusMap, RequirementTaskTypeMap } from '@/service/api/requirement';
import type { Document } from '@/typings/api/document';
import MarkdownRenderer from '@/components/MarkdownRenderer.vue';
import SvgIcon from '@/components/custom/svg-icon.vue';

interface Props {
  task: Task;
}

interface Emits {
  (e: 'start', task: Task): void;
  (e: 'complete', task: Task): void;
  (e: 'edit', task: Task): void;
  (e: 'addSubtask', task: Task): void;
  (e: 'delete', taskId: string): void;
  (e: 'viewDocument', doc: Document.Response): void;
}

// 设置组件名称，用于递归引用
defineOptions({
  name: 'TaskCard'
});

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// 从任务数据中直接获取文档（由后端任务列表接口返回）
const documents = computed(() => props.task.documents || []);

// 复制状态
const copySuccess = ref(false);

// 生成短ID（前8位）- 改为函数
function getShortId(task: Task) {
  if (!task.id) {
    console.error('[TaskCard] Task ID is missing:', task);
    return '????????';
  }
  return task.id.substring(0, 8);
}

// 生成CLI命令提示 - 改为函数
function getCliCommand(task: Task) {
  return `opentask task run ${task.id}`;
}

// 渲染任务卡片内容
const renderTaskCard = (task: Task) => {
  // 调试：检查task对象和子任务
  console.log('[TaskCard] renderTaskCard called with task:', {
    id: task.id,
    title: task.title,
    hasChildren: Boolean(task.children),
    childrenLength: task.children?.length || 0,
    childrenKeys: task.children ? Object.keys(task.children[0] || {}) : []
  });

  if (!task.id) {
    console.error('[TaskCard] Task object is missing ID:', task);
    console.error('[TaskCard] Task keys:', Object.keys(task));
  }

  // 创建当前任务的copyTaskId处理器
  const handleCopyTaskId = async () => {
    try {
      await navigator.clipboard.writeText(task.id);
      copySuccess.value = true;
      window.$message?.success('任务ID已复制到剪贴板');
      setTimeout(() => {
        copySuccess.value = false;
      }, 2000);
    } catch {
      // 降级方案：使用传统方法
      const textArea = document.createElement('textarea');
      textArea.value = task.id;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
        copySuccess.value = true;
        window.$message?.success('任务ID已复制到剪贴板');
        setTimeout(() => {
          copySuccess.value = false;
        }, 2000);
      } catch {
        window.$message?.error('复制失败，请手动复制');
      }
      document.body.removeChild(textArea);
    }
  };

  return h('div', { class: 'modern-task-card' }, [
    // 左侧状态指示条
    h('div', { class: `task-status-indicator status-${task.status.toLowerCase()}` }),

    // 主内容区域
    h('div', { class: 'task-card-main' }, [
      // 顶部行：状态标签 + 标题 + 类型标签 + 任务ID
      h('div', { class: 'task-top-row' }, [
        h('div', { class: 'task-left-info' }, [
          // 任务编号
          h('span', { class: 'task-code' }, `#${task.code || '-'}`),
          // 任务标题
          h('h3', { class: 'task-title-heading' }, task.title),
          // 状态标签（更小的圆形标签）
          h(
            'span',
            {
              class: `task-status-badge status-${task.status.toLowerCase()}`,
              title: RequirementTaskStatusMap[task.status]
            },
            RequirementTaskStatusMap[task.status]
          )
        ]),
        // 右侧信息组
        h('div', { class: 'task-right-info' }, [
          // 类型标签
          h('span', { class: 'task-type-badge' }, RequirementTaskTypeMap[task.task_type]),
          // 任务ID（新增）
          h(
            NTooltip,
            {
              trigger: 'hover'
            },
            {
              trigger: () =>
                h(
                  'div',
                  {
                    class: 'task-id-container',
                    onClick: handleCopyTaskId,
                    title: copySuccess.value ? '已复制！' : '点击复制任务ID'
                  },
                  [
                    h(SvgIcon, {
                      icon: copySuccess.value ? 'mdi:check' : 'mdi:identifier',
                      class: 'task-id-icon'
                    }),
                    h('span', { class: 'task-id-text' }, getShortId(task)),
                    h('span', { class: 'task-id-copy-hint' }, copySuccess.value ? '✓' : '⧉')
                  ]
                ),
              default: () =>
                h('div', { class: 'task-id-tooltip' }, [
                  h('div', { class: 'tooltip-header' }, [
                    h('span', { class: 'tooltip-title' }, '任务 ID'),
                    h('span', { class: 'tooltip-full-id' }, task.id)
                  ]),
                  h('div', { class: 'tooltip-command' }, [
                    h('span', { class: 'command-prompt' }, '$'),
                    h('code', { class: 'command-text' }, getCliCommand(task))
                  ]),
                  h('div', { class: 'tooltip-hint' }, '点击复制完整ID')
                ])
            }
          )
        ])
      ]),

      // 任务描述（支持 Markdown）
      task.description &&
        h(MarkdownRenderer, {
          class: 'task-description',
          content: task.description
        }),

      // 任务文档链接
      documents.value.length > 0 &&
        h('div', { class: 'task-documents-section' }, [
          h('div', { class: 'task-documents-header' }, [
            h(SvgIcon, {
              icon: 'mdi:file-document-outline',
              class: 'document-icon'
            }),
            h('span', { class: 'task-documents-count' }, `文档 ${documents.value.length}`)
          ]),
          h(
            'div',
            { class: 'task-document-links' },
            documents.value.map(doc =>
              h(
                'a',
                {
                  key: doc.id,
                  href: '#',
                  class: 'task-document-link',
                  onClick: (e: Event) => {
                    e.preventDefault();
                    emit('viewDocument', doc);
                  }
                },
                doc.file_name || '未命名文档'
              )
            )
          )
        ]),

      // 子任务（如果有）
      task.children &&
        task.children.length > 0 &&
        h('div', { class: 'subtasks-section' }, [
          h('div', { class: 'subtasks-header' }, [
            h(SvgIcon, {
              icon: 'mdi:file-tree',
              class: 'subtasks-icon'
            }),
            h('span', `${task.children?.length || 0} 个子任务`)
          ]),
          // 直接渲染子任务列表，不使用折叠组件
          h(
            'div',
            { class: 'subtasks-list' },
            task.children?.map((child, index) => {
              // 调试：检查子任务对象
              console.log(`[TaskCard] Rendering child ${index}:`, {
                id: child.id,
                title: child.title,
                keys: Object.keys(child),
                hasId: 'id' in child
              });

              return h(resolveComponent('TaskCard'), {
                key: child.id || child.code || `child-${index}`,
                task: child,
                onStart: () => emit('start', child),
                onComplete: () => emit('complete', child),
                onEdit: () => emit('edit', child),
                onAddSubtask: () => emit('addSubtask', child),
                onDelete: () => emit('delete', child.id),
                onViewDocument: (doc: Document.Response) => emit('viewDocument', doc)
              });
            })
          )
        ]),

      // 操作按钮区域
      h('div', { class: 'task-actions-bar' }, [
        // 左侧主要操作 - 暂时隐藏任务状态修改按钮（需求2026-122）
        // task.status === 'PENDING' &&
        //   h(
        //     NButton,
        //     {
        //       size: 'small',
        //       type: 'primary',
        //       circle: true,
        //       onClick: () => emit('start', task)
        //     },
        //     {
        //       icon: () => h(SvgIcon, { icon: 'mdi:play' })
        //     }
        //   ),
        // task.status === 'RUNNING' &&
        //   h(
        //     NButton,
        //     {
        //       size: 'small',
        //       type: 'success',
        //       circle: true,
        //       onClick: () => emit('complete', task)
        //     },
        //     {
        //       icon: () => h(SvgIcon, { icon: 'mdi:check' })
        //     }
        //   )
        // 左侧主要操作占位符（保持布局一致）
        h('div', { class: 'task-primary-actions' }),

        // 右侧次要操作
        h('div', { class: 'task-secondary-actions' }, [
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              onClick: () => emit('edit', task)
            },
            '编辑'
          ),
          // 暂时隐藏"添加子任务"按钮（需求2026-122）
          // !task.parent_id &&
          //   h(
          //     NButton,
          //     {
          //       size: 'tiny',
          //       quaternary: true,
          //       onClick: () => emit('addSubtask', task)
          //     },
          //     '添加子任务'
          //   ),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => emit('delete', task.id)
            },
            {
              default: () => '确定要删除这个任务吗？',
              trigger: () =>
                h(
                  NButton,
                  {
                    size: 'tiny',
                    type: 'error',
                    quaternary: true
                  },
                  '删除'
                )
            }
          )
        ])
      ])
    ])
  ]);
};
</script>

<template>
  <component :is="renderTaskCard(props.task)" />
</template>

<style scoped>
/* TaskCard 组件的样式已移到全局样式块 */
</style>

<style>
/* 全局样式：任务ID相关样式 */
.task-right-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-id-container {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background-color: #f3f4f6;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
}

.task-id-container:hover {
  background-color: var(--color-border-subtle);
  transform: translateY(-1px);
}

.task-id-container:active {
  transform: translateY(0);
}

.task-id-icon {
  font-size: 14px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.task-id-text {
  color: #374151;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.task-id-copy-hint {
  color: var(--color-text-tertiary);
  font-size: 14px;
  transition: color 0.2s;
}

.task-id-container:hover .task-id-copy-hint {
  color: var(--color-primary);
}

/* Tooltip 样式 */
.task-id-tooltip {
  padding: 8px 0;
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.tooltip-title {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.tooltip-full-id {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.tooltip-command {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background-color: #1f2937;
  border-radius: 4px;
  margin-bottom: 6px;
}

.command-prompt {
  color: #10b981;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  font-weight: 600;
}

.command-text {
  color: var(--color-border-subtle);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 11px;
}

.tooltip-hint {
  font-size: 11px;
  color: var(--color-text-secondary);
  text-align: center;
}
</style>

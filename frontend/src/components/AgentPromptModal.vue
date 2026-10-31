<script setup lang="ts">
import { computed } from 'vue';
import { NAlert, NButton, NModal } from 'naive-ui';

interface Props {
  show: boolean;
  collectionTitle: string;
  collectionId: string;
  issues: Array<{
    id: string;
    issue_code: string;
    title: string;
    status: string;
  }>;
}

interface Emits {
  (e: 'update:show', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const showModal = computed({
  get: () => props.show,
  set: value => emit('update:show', value)
});

function getStatusText(status: string) {
  const textMap: Record<string, string> = {
    open: '待处理',
    in_progress: '进行中',
    feedback: '等待反馈',
    resolved: '已解决',
    closed: '已关闭',
    rejected: '已拒绝'
  };
  return textMap[status] || status;
}

function generatePrompt() {
  const issuesText = props.issues
    .map((issue, index) => {
      const statusText = getStatusText(issue.status);
      return `${index + 1}. [${issue.issue_code}] ${issue.title} (${statusText})`;
    })
    .join('\n  ');

  const issueCount = props.issues.length;
  let nextSteps = '';

  if (issueCount === 0) {
    nextSteps = `## 下一步工作

**问题集尚未拆解**，请使用以下命令进行拆解：

\`\`\`bash
opentask collection parse ${props.collectionId} --file tasks.json
\`\`\`

其中 tasks.json 是包含任务列表的 JSON 文件，格式如下：
\`\`\`json
[
  {
    "title": "任务标题",
    "description": "任务描述",
    "type": "bug|feature|improvement",
    "priority": "high|medium|low"
  }
]
\`\`\``;
  } else if (issueCount < 5) {
    nextSteps = `## 下一步工作

**问题集拆解不完整**（仅 ${issueCount} 个 Issues），建议继续拆解或开始工作：

**选项 1：继续拆解问题**
\`\`\`bash
opentask collection parse ${props.collectionId} --file tasks.json
\`\`\`

**选项 2：开始处理现有 Issues**
\`\`\`bash
# 查看某个 Issue 详情
opentask issue show <issue-id>

# 更新 Issue 状态
opentask issue update <issue-id> --status in_progress
\`\`\``;
  } else {
    nextSteps = `## 下一步工作

**问题集已完整拆解**（${issueCount} 个 Issues），请选择一个 Issue 开始工作：

**推荐工作流程：**

1. **查看 Issue 详情**
\`\`\`bash
opentask issue show <issue-id>
\`\`\`

2. **开始处理 Issue**
\`\`\`bash
# 更新状态为"进行中"
opentask issue update <issue-id> --status in_progress

# 添加评论记录工作进展
opentask issue comment <issue-id> "开始分析这个问题..."
\`\`\`

3. **完成后更新状态**
\`\`\`bash
opentask issue update <issue-id> --status resolved
\`\`\`

**查看问题集统计信息：**
\`\`\`bash
opentask collection stats ${props.collectionId}
\`\`\``;
  }

  return `# Issue Collection: ${props.collectionTitle}

ID: ${props.collectionId}
关联 Issues: ${issueCount} 个

## Issues 列表
${issuesText ? `\n  ${issuesText}` : '\n  暂无关联的 Issues'}

${nextSteps}`;
}

async function copyPrompt() {
  const prompt = generatePrompt();
  try {
    await navigator.clipboard.writeText(prompt);
    window.$message?.success('指令已复制到剪贴板');
  } catch {
    // eslint-disable-next-line no-unused-vars
    window.$message?.error('复制失败，请手动复制');
  }
}
</script>

<template>
  <NModal v-model:show="showModal" preset="card" title="🤖 Agent 工作指令" style="width: 700px">
    <NAlert type="success" class="mb-3">复制下方指令，粘贴到 Claude 中即可指挥 agent 开始工作</NAlert>

    <div class="agent-prompt-modal-content">
      <div class="prompt-actions">
        <NButton type="primary" @click="copyPrompt">
          <template #icon>
            <icon-mdi-content-copy />
          </template>
          复制指令
        </NButton>
      </div>

      <div class="prompt-display">
        <pre class="prompt-code">{{ generatePrompt() }}</pre>
      </div>
    </div>
  </NModal>
</template>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}

.agent-prompt-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.prompt-actions {
  display: flex;
  justify-content: flex-end;
}

.prompt-display {
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.prompt-display::-webkit-scrollbar {
  width: 8px;
}

.prompt-display::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 4px;
}

.prompt-display::-webkit-scrollbar-track {
  background: #1f2937;
}

.prompt-code {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-border-subtle);
}
</style>

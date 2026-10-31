<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NAlert,
  NButton,
  NCollapse,
  NCollapseItem,
  NForm,
  NFormItemGi,
  NGrid,
  NInput,
  NPageHeader,
  NSelect,
  NSpace,
  NTag,
  NText
} from 'naive-ui';
import { fetchKnowledgeBaseList } from '@/service/api/knowledge-base';
import MarkdownEditor from '@/components/MarkdownEditor.vue';

defineOptions({
  name: 'KnowledgeGitEdit'
});

const router = useRouter();
const route = useRoute();

// 知识库信息
const knowledgeBases = ref<Api.Knowledge.KnowledgeBase[]>([]);
const selectedKbId = ref('');
const selectedDocId = ref('');

// 文档信息
const docTitle = ref('');
const docContent = ref('');

// 当前是否已选择知识库和文档
const isDocSelected = computed(() => selectedKbId.value && selectedDocId.value);

// 获取知识库列表
async function getKnowledgeBases() {
  const { data } = await fetchKnowledgeBaseList({
    current: 1,
    pageSize: 100
  });

  if (data?.rows) {
    knowledgeBases.value = data.rows.filter(kb => kb.repositoryUrl);

    // 如果 URL 有预设参数
    if (route.query.kbId) {
      selectedKbId.value = route.query.kbId as string;
    }
    if (route.query.docId) {
      selectedDocId.value = route.query.docId as string;
    }
    if (route.query.title) {
      docTitle.value = route.query.title as string;
    }
  }
}

// 加载文档 (reserved for future use)
// function handleLoadDocument(kbId: string, docId: string, title: string) {
//   selectedKbId.value = kbId;
//   selectedDocId.value = docId;
//   docTitle.value = title;
// }

// 保存成功处理 (reserved for future use)
// function handleSave(content: string, message: string) {
//   window.$message?.success('文档已提交到 Git 仓库');
//   editorStatus.value = 'saved';
// }

// 状态变化处理 (reserved for future use)
// function handleStatusChange(status: string) {
//   editorStatus.value = status as any;
// }

// 返回列表
function handleBack() {
  router.back();
}

onMounted(async () => {
  await getKnowledgeBases();
});
</script>

<template>
  <div class="h-full overflow-y-auto bg-white p-4">
    <NPageHeader title="Git 编辑器" subtitle="基于 Monaco Editor + Git 的文档编辑" @back="handleBack">
      <template #extra>
        <NSpace>
          <NTag v-if="isDocSelected" type="success">
            <template #icon>
              <icon-mdi:file-document-outline />
            </template>
            {{ docTitle || selectedDocId }}
          </NTag>
          <NTag v-if="isDocSelected" type="info">
            <template #icon>
              <icon-mdi:database />
            </template>
            {{ knowledgeBases.find(kb => kb.id === selectedKbId)?.name || selectedKbId }}
          </NTag>
        </NSpace>
      </template>
    </NPageHeader>

    <div class="mx-auto max-w-7xl pt-4">
      <!-- 文档选择器 -->
      <NCollapse v-if="!isDocSelected" class="mb-4">
        <NCollapseItem title="选择要编辑的文档" name="selector">
          <NAlert type="info" class="mb-4">请从知识库列表中选择一个启用了 Git 仓库的知识库，然后输入文档 ID</NAlert>

          <NForm label-placement="top">
            <NGrid :cols="2" :x-gap="12">
              <NFormItemGi label="知识库">
                <NSelect
                  v-model:value="selectedKbId"
                  :options="
                    knowledgeBases.map(kb => ({
                      label: `${kb.name} (${kb.repositoryUrl})`,
                      value: kb.id
                    }))
                  "
                  placeholder="选择知识库"
                  filterable
                />
              </NFormItemGi>

              <NFormItemGi label="文档 ID">
                <NInput
                  v-model:value="selectedDocId"
                  placeholder="输入文档 ID（例如：doc-001）"
                  @keyup.enter="
                    isDocSelected &&
                    $router.push({ query: { ...$route.query, kbId: selectedKbId, docId: selectedDocId } })
                  "
                />
              </NFormItemGi>
            </NGrid>
          </NForm>
        </NCollapseItem>
      </NCollapse>

      <!-- 编辑器区域 -->
      <template v-if="isDocSelected">
        <MarkdownEditor v-model="docContent" placeholder="开始编辑你的 Markdown 文档..." max-height="600px" />

        <!-- 操作按钮 -->
        <div class="mt-4 flex items-center justify-between">
          <NSpace>
            <NText depth="3">
              <template #icon>
                <icon-mdi:information-outline />
              </template>
              编辑器已集成 Git 功能，可直接提交到远程仓库
            </NText>
          </NSpace>

          <NSpace>
            <NButton @click="handleBack">
              <template #icon>
                <icon-mdi:arrow-left />
              </template>
              返回
            </NButton>
          </NSpace>
        </div>
      </template>

      <!-- 使用说明 -->
      <NCollapse v-else class="mt-4">
        <NCollapseItem title="使用说明" name="help">
          <div class="prose prose-sm max-w-none">
            <h4>🚀 Git + Web 编辑架构</h4>
            <p>这是一个基于 Monaco Editor 和 Git 的强大编辑器，支持：</p>

            <h5>✨ 核心功能</h5>
            <ul>
              <li>
                <strong>实时编辑</strong>
                ：Monaco Editor 提供类似 VSCode 的编辑体验
              </li>
              <li>
                <strong>Git 集成</strong>
                ：直接提交到 Git 仓库，无需手动操作
              </li>
              <li>
                <strong>历史记录</strong>
                ：查看完整的提交历史和文档变更
              </li>
              <li>
                <strong>Diff 对比</strong>
                ：可视化对比不同版本的差异
              </li>
              <li>
                <strong>Markdown 支持</strong>
                ：完整的 Markdown 语法高亮和预览
              </li>
            </ul>

            <h5>📝 使用流程</h5>
            <ol>
              <li>选择一个配置了 Git 仓库的知识库</li>
              <li>输入要编辑的文档 ID</li>
              <li>在编辑器中修改内容</li>
              <li>输入提交信息并点击"提交"（或按 Ctrl+S）</li>
              <li>查看历史记录和变更对比</li>
            </ol>

            <h5>⌨️ 快捷键</h5>
            <ul>
              <li>
                <code>Ctrl+S</code>
                ：保存并提交到 Git
              </li>
              <li>
                <code>Ctrl+Enter</code>
                ：在提交信息输入框中快速提交
              </li>
            </ul>

            <h5>🔧 技术架构</h5>
            <p>前端 → 后端 API → GitPython → Git 仓库 → Webhook 自动同步</p>
          </div>
        </NCollapseItem>
      </NCollapse>
    </div>
  </div>
</template>

<style scoped>
.prose {
  color: #374151;
  line-height: 1.6;
}

.prose h4 {
  font-size: 16px;
  font-weight: 600;
  margin-top: 16px;
  margin-bottom: 8px;
}

.prose h5 {
  font-size: 14px;
  font-weight: 600;
  margin-top: 12px;
  margin-bottom: 6px;
}

.prose ul,
.prose ol {
  padding-left: 20px;
  margin: 8px 0;
}

.prose li {
  margin: 4px 0;
}

.prose code {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
}

.prose strong {
  font-weight: 600;
}
</style>

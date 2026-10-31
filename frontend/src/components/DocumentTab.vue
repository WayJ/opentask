<script setup lang="ts">
import { h, onMounted, ref } from 'vue';
import { NButton, NCard, NDataTable, NDescriptions, NDescriptionsItem, NEmpty, NSpace, NSpin, NTag } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { documentApi } from '@/service/api/document';
import type { Document } from '@/typings/api/document';

const props = defineProps<{
  entityType: string;
  entityId: string;
}>();

// 文档数据
const documents = ref<Document.Response[]>([]);
const loading = ref(false);

// 当前选中的文档
const selectedDocument = ref<Document.Response | null>(null);

// 显示编辑器
const showEditor = ref(false);

// 编辑表单
const editForm = ref({
  title: '',
  content: '',
  status: 'DRAFT' as Document.Status
});

// 表格列定义
const columns: DataTableColumns<Document.Response> = [
  { title: '标题', key: 'title', width: 300 },
  {
    title: '版本',
    key: 'version',
    width: 80
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: Document.Response) => {
      const statusMap = {
        DRAFT: { type: 'default' as const, text: '草稿' },
        PUBLISHED: { type: 'success' as const, text: '已发布' },
        ARCHIVED: { type: 'info' as const, text: '已归档' }
      };
      const status = statusMap[row.status];
      return h(NTag, { type: status.type }, status.text);
    }
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 180,
    render: (row: Document.Response) => new Date(row.updated_at).toLocaleString()
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row: Document.Response) =>
      h(NSpace, () => [
        h(
          NButton,
          {
            size: 'small',
            onClick: () => viewDocument(row)
          },
          '查看'
        ),
        h(
          NButton,
          {
            size: 'small',
            onClick: () => editDocument(row)
          },
          '编辑'
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            onClick: () => deleteDocument(row.id)
          },
          '删除'
        )
      ])
  }
];

// 加载文档列表
async function loadDocuments() {
  loading.value = true;
  try {
    const response = await documentApi.getList({
      entity_type: props.entityType,
      entity_id: props.entityId,
      page: 1,
      page_size: 50
    });

    if (response?.data) {
      documents.value = response.data;
    }
  } catch {
    window.$message?.error('加载文档失败');
  } finally {
    loading.value = false;
  }
}

// 查看文档
function viewDocument(doc: Document.Response) {
  selectedDocument.value = doc;
  showEditor.value = false;
}

// 编辑文档
function editDocument(doc?: Document.Response) {
  if (doc) {
    editForm.value = {
      title: doc.title,
      content: doc.content,
      status: doc.status
    };
    selectedDocument.value = doc;
  } else {
    editForm.value = {
      title: '',
      content: '',
      status: 'DRAFT'
    };
    selectedDocument.value = null;
  }
  showEditor.value = true;
}

// 保存文档
async function saveDocument() {
  try {
    if (selectedDocument.value) {
      // 更新现有文档
      const response = await documentApi.update(selectedDocument.value.id, {
        title: editForm.value.title,
        content: editForm.value.content,
        status: editForm.value.status,
        updated_by: 'admin'
      });

      if (response) {
        await loadDocuments();
        showEditor.value = false;
        selectedDocument.value = response;
      }
    } else {
      // 创建新文档
      const response = await documentApi.create({
        entity_type: props.entityType,
        entity_id: props.entityId,
        title: editForm.value.title,
        content: editForm.value.content,
        status: editForm.value.status,
        created_by: 'admin'
      });

      if (response) {
        await loadDocuments();
        showEditor.value = false;
      }
    }
  } catch {
    window.$message?.error('保存文档失败');
  }
}

// 删除文档
async function deleteDocument(id: string) {
  try {
    await documentApi.delete(id);
    await loadDocuments();
    if (selectedDocument.value?.id === id) {
      selectedDocument.value = null;
    }
  } catch {
    window.$message?.error('删除文档失败');
  }
}

// 取消编辑
function cancelEdit() {
  showEditor.value = false;
  editForm.value = {
    title: '',
    content: '',
    status: 'DRAFT'
  };
}

onMounted(() => {
  loadDocuments();
});

// 暴露方法供父组件刷新
defineExpose({
  loadDocuments
});
</script>

<template>
  <div class="document-tab">
    <NSpin :show="loading">
      <!-- 工具栏 -->
      <div class="toolbar mb-4">
        <NSpace>
          <NButton type="primary" @click="editDocument()">+ 新建文档</NButton>
          <NButton @click="loadDocuments()">刷新</NButton>
        </NSpace>
      </div>

      <!-- 文档列表 -->
      <NCard v-if="!showEditor">
        <template v-if="documents.length > 0">
          <NDataTable :columns="columns" :data="documents" :bordered="false" :single-line="false" />
        </template>
        <NEmpty v-else description="暂无文档" />
      </NCard>

      <!-- 文档查看/编辑器 -->
      <NCard v-else>
        <template #header>
          <NSpace>
            <NButton size="small" @click="cancelEdit">← 返回列表</NButton>
            <span v-if="selectedDocument">编辑文档 (版本 {{ selectedDocument.version }})</span>
            <span v-else>新建文档</span>
          </NSpace>
        </template>

        <div class="editor-container">
          <!-- 编辑表单 -->
          <div class="form-section">
            <div class="form-row">
              <label class="form-label">标题：</label>
              <input v-model="editForm.title" class="form-input" placeholder="请输入文档标题" />
            </div>
            <div class="form-row">
              <label class="form-label">状态：</label>
              <select v-model="editForm.status" class="form-select">
                <option value="DRAFT">草稿</option>
                <option value="PUBLISHED">已发布</option>
                <option value="ARCHIVED">已归档</option>
              </select>
            </div>
          </div>

          <!-- Markdown 编辑器 -->
          <div class="editor-section">
            <label class="form-label">内容 (Markdown)：</label>
            <textarea
              v-model="editForm.content"
              class="markdown-editor"
              placeholder="请输入文档内容，支持 Markdown 格式"
              rows="20"
            ></textarea>
          </div>

          <!-- 操作按钮 -->
          <div class="action-bar mt-4">
            <NSpace>
              <NButton type="primary" @click="saveDocument">保存</NButton>
              <NButton @click="cancelEdit">取消</NButton>
            </NSpace>
          </div>
        </div>
      </NCard>

      <!-- 文档详情查看 -->
      <NCard v-if="selectedDocument && !showEditor" class="mt-4">
        <template #header>
          <NSpace>
            <NButton size="small" @click="selectedDocument = null">← 返回列表</NButton>
            <span>{{ selectedDocument.title }}</span>
          </NSpace>
        </template>

        <div class="document-detail">
          <NDescriptions>
            <NDescriptionsItem label="版本">{{ selectedDocument.version }}</NDescriptionsItem>
            <NDescriptionsItem label="状态">
              <NTag :type="selectedDocument.status === 'PUBLISHED' ? 'success' : 'default'">
                {{
                  selectedDocument.status === 'DRAFT'
                    ? '草稿'
                    : selectedDocument.status === 'PUBLISHED'
                      ? '已发布'
                      : '已归档'
                }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="更新时间">
              {{ new Date(selectedDocument.updated_at).toLocaleString() }}
            </NDescriptionsItem>
          </NDescriptions>

          <div class="content-preview mt-4">
            <label class="form-label">内容预览：</label>
            <div class="markdown-preview">{{ selectedDocument.content }}</div>
          </div>
        </div>
      </NCard>
    </NSpin>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.editor-container {
  max-width: 100%;
}

.form-section {
  margin-bottom: 20px;
}

.form-row {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.form-label {
  min-width: 80px;
  font-weight: 500;
}

.form-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 14px;
}

.form-select {
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 14px;
}

.editor-section {
  margin-bottom: 20px;
}

.markdown-editor {
  width: 100%;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
}

.content-preview {
  margin-top: 20px;
}

.markdown-preview {
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #f9f9f9;
  min-height: 200px;
}

.markdown-preview :deep(h1) {
  font-size: 24px;
  margin-bottom: 16px;
}

.markdown-preview :deep(h2) {
  font-size: 20px;
  margin-bottom: 12px;
}

.markdown-preview :deep(p) {
  margin-bottom: 12px;
  line-height: 1.6;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
}
</style>

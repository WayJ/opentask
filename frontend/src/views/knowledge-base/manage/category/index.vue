<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NPopconfirm,
  NSpace,
  NTag,
  NTreeSelect,
  useMessage
} from 'naive-ui';
import {
  createKnowledgeCategory,
  deleteKnowledgeCategory,
  fetchKnowledgeCategoryTree,
  updateKnowledgeCategory
} from '@/service/api/knowledge-category';
import type { Api } from '@/typings/api';

defineOptions({
  name: 'KnowledgeCategoryManage'
});

const message = useMessage();

// 数据状态
const loading = ref(false);
const categoryTree = ref<Api.KnowledgeCategory.CategoryTree[]>([]);
const flatCategories = ref<Api.KnowledgeCategory.Category[]>([]);

// 对话框
const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const currentCategory = ref<Api.KnowledgeCategory.Category | null>(null);

// 表单数据
const formData = ref({
  name: '',
  icon: '',
  sortOrder: 0,
  parentId: null as number | null
});

const formRef = ref();

// 格式化日期（如果需要）(reserved for future use)
// const formatDate = (dateStr: string) => {
//   const date = new Date(dateStr);
//   return date.toLocaleString('zh-CN');
// };

// 扁平化分类树
const flattenCategories = (tree: Api.KnowledgeCategory.CategoryTree[]): Api.KnowledgeCategory.Category[] => {
  const result: Api.KnowledgeCategory.Category[] = [];

  // 处理空数据或非数组数据
  if (!tree || !Array.isArray(tree)) {
    return result;
  }

  const traverse = (nodes: Api.KnowledgeCategory.CategoryTree[], level = 0) => {
    if (!nodes || !Array.isArray(nodes)) {
      return;
    }
    nodes.forEach(node => {
      result.push({
        ...node,
        name: level > 0 ? `${'  '.repeat(level)}└ ${node.name}` : node.name
      });
      if (node.children && node.children.length > 0) {
        traverse(node.children, level + 1);
      }
    });
  };
  traverse(tree);
  return result;
};

// 加载分类树
const loadCategoryTree = async () => {
  loading.value = true;
  try {
    const { data } = await fetchKnowledgeCategoryTree();
    categoryTree.value = data;
    flatCategories.value = flattenCategories(data);
  } catch (error) {
    message.error('加载分类树失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// 创建分类
const handleCreate = () => {
  dialogMode.value = 'create';
  currentCategory.value = null;
  formData.value = {
    name: '',
    icon: '',
    sortOrder: 0,
    parentId: null
  };
  dialogVisible.value = true;
};

// 编辑分类
const handleEdit = (category: Api.KnowledgeCategory.Category) => {
  dialogMode.value = 'edit';
  currentCategory.value = category;
  formData.value = {
    name: category.name,
    icon: category.icon || '',
    sortOrder: category.sortOrder,
    parentId: category.parentId || null
  };
  dialogVisible.value = true;
};

// 删除分类
const handleDelete = async (category: Api.KnowledgeCategory.Category) => {
  try {
    await deleteKnowledgeCategory(category.id);
    message.success('删除成功');
    await loadCategoryTree();
  } catch (error) {
    message.error('删除失败');
    console.error(error);
  }
};

// 提交表单
const handleSubmit = async () => {
  try {
    await formRef.value?.validate();

    if (dialogMode.value === 'create') {
      await createKnowledgeCategory(formData.value);
      message.success('创建成功');
    } else {
      await updateKnowledgeCategory(currentCategory.value!.id, formData.value);
      message.success('更新成功');
    }

    dialogVisible.value = false;
    await loadCategoryTree();
  } catch (error) {
    message.error(dialogMode.value === 'create' ? '创建失败' : '更新失败');
    console.error(error);
  }
};

// 表格列配置
const columns = [
  {
    title: '分类名称',
    key: 'name',
    minWidth: 300
  },
  {
    title: '图标',
    key: 'icon',
    width: 100,
    render: (row: Api.KnowledgeCategory.Category) => {
      return row.icon ? h(NTag, { size: 'small' }, row.icon) : '-';
    }
  },
  {
    title: '排序',
    key: 'sortOrder',
    width: 100,
    align: 'center' as const
  },
  {
    title: '文档数',
    key: 'knowledgeCount',
    width: 100,
    align: 'center' as const,
    render: (row: Api.KnowledgeCategory.Category) => {
      return row.knowledgeCount || 0;
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row: Api.KnowledgeCategory.Category) => {
      return h(
        NSpace,
        {},
        {
          default: () => [
            h(
              NButton,
              {
                text: true,
                type: 'primary',
                onClick: () => handleEdit(row)
              },
              { default: () => '编辑' }
            ),
            h(
              NPopconfirm,
              {
                onPositiveClick: () => handleDelete(row)
              },
              {
                default: () => '确定要删除这个分类吗？',
                trigger: () =>
                  h(
                    NButton,
                    {
                      text: true,
                      type: 'error'
                    },
                    { default: () => '删除' }
                  )
              }
            )
          ]
        }
      );
    }
  }
];

// 转换树节点
const transformTreeNode = (node: Api.KnowledgeCategory.CategoryTree): any => {
  return {
    key: node.id,
    ...node,
    children: node.children ? node.children.map(child => transformTreeNode(child)) : undefined
  };
};

// 树形表格配置
const treeData = computed(() => {
  return categoryTree.value.map(node => transformTreeNode(node));
});

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { min: 2, max: 50, message: '分类名称长度在 2 到 50 个字符', trigger: 'blur' }
  ]
};

// 初始化
onMounted(() => {
  loadCategoryTree();
});
</script>

<template>
  <div class="category-manage">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="title-section">
        <h1>知识分类管理</h1>
        <p class="description">管理知识库的分类结构</p>
      </div>
      <NButton type="primary" @click="handleCreate">
        <template #icon>
          <icon-mdi:plus />
        </template>
        创建分类
      </NButton>
    </div>

    <!-- 分类树 -->
    <div class="content-section">
      <NSpin :show="loading">
        <NTable
          :columns="columns"
          :data="flatCategories"
          :bordered="false"
          striped
          :row-key="(row: Api.KnowledgeCategory.Category) => row.id"
        />
      </NSpin>
    </div>

    <!-- 创建/编辑对话框 -->
    <NModal
      v-model:show="dialogVisible"
      preset="card"
      :title="dialogMode === 'create' ? '创建分类' : '编辑分类'"
      style="width: 600px"
    >
      <NForm
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="top"
        require-mark-placement="right-hanging"
      >
        <NFormItem label="分类名称" path="name">
          <NInput v-model:value="formData.name" placeholder="请输入分类名称" maxlength="50" show-count />
        </NFormItem>

        <NFormItem label="图标" path="icon">
          <NInput v-model:value="formData.icon" placeholder="请输入图标名称（可选）" clearable>
            <template #prefix>
              <icon-mdi:emoticon-outline />
            </template>
          </NInput>
        </NFormItem>

        <NFormItem label="父分类" path="parentId">
          <NTreeSelect
            v-model:value="formData.parentId"
            :options="treeData"
            label-field="name"
            key-field="id"
            children-field="children"
            placeholder="选择父分类（可选）"
            clearable
            check-strategy="child"
          />
        </NFormItem>

        <NFormItem label="排序序号" path="sortOrder">
          <NInputNumber
            v-model:value="formData.sortOrder"
            :min="0"
            :max="9999"
            placeholder="排序序号"
            style="width: 100%"
          />
        </NFormItem>
      </NForm>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="dialogVisible = false">取消</NButton>
          <NButton type="primary" @click="handleSubmit">
            {{ dialogMode === 'create' ? '创建' : '保存' }}
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped lang="scss">
.category-manage {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .title-section {
      h1 {
        font-size: 24px;
        font-weight: 600;
        margin: 0 0 8px 0;
        color: #333;
      }

      .description {
        font-size: 14px;
        color: #666;
        margin: 0;
      }
    }
  }

  .content-section {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
}
</style>

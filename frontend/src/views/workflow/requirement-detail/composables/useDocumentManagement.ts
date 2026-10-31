import { type Ref, computed, ref } from 'vue';
import { documentApi } from '@/service/api/document';
import type { Document } from '@/typings/api/document';

interface Requirement {
  id?: string;
  documents?: Document.Response[];
}

interface DocumentManagementOptions {
  onSave?: () => Promise<void>;
  onUploadComplete?: () => void; // 上传完成回调（无论成功失败）
  entityType?: 'requirement' | 'task';
  entityId?: Ref<string>;
}

export function useDocumentManagement(requirement: Ref<Requirement | null>, options?: DocumentManagementOptions) {
  // 文档相关状态
  const documents = computed(() => requirement.value?.documents || []);
  const showDocumentModal = ref(false);
  const selectedDocument = ref<Document.Response | null>(null);
  const documentLoading = ref(false);

  // 编辑文档表单（只包含 id）
  const editDocumentForm = ref<{
    id: string;
  }>({
    id: ''
  });

  const showDocumentEdit = ref(false);

  // 查看文档（获取完整数据）
  async function viewDocument(doc: Document.Response) {
    documentLoading.value = true;
    try {
      let fullDocument: Document.Response;

      // 根据实体类型获取完整文档
      if (options?.entityType === 'task' && options?.entityId) {
        const response = await documentApi.getTaskDocument(requirement.value!.id!, options.entityId.value, doc.id);
        fullDocument = (response as any).data || response;
      } else {
        const response = await documentApi.getRequirementDocument(requirement.value!.id!, doc.id);
        fullDocument = (response as any).data || response;
      }

      selectedDocument.value = fullDocument;
      showDocumentModal.value = true;
    } catch (error) {
      console.error('加载文档失败:', error);
      // 如果加载失败，使用摘要数据
      selectedDocument.value = doc;
      showDocumentModal.value = true;
    } finally {
      documentLoading.value = false;
    }
  }

  // 打开文档编辑
  function openDocumentEdit(doc?: Document.Response) {
    if (doc) {
      editDocumentForm.value = {
        id: doc.id
      };
      selectedDocument.value = doc;
    } else {
      editDocumentForm.value = {
        id: ''
      };
      selectedDocument.value = null;
    }
    showDocumentEdit.value = true;
  }

  // 关闭文档编辑
  function closeDocumentEdit() {
    showDocumentEdit.value = false;
  }

  // 关闭文档查看
  function closeDocumentModal() {
    showDocumentModal.value = false;
    selectedDocument.value = null;
  }

  // 保存文档
  async function saveDocument(file?: File) {
    if (!requirement.value?.id) return;
    try {
      if (selectedDocument.value) {
        // 更新现有文档（只更新文件）
        await documentApi.updateRequirementDocument(requirement.value.id, selectedDocument.value.id, {
          file
        });
      } else {
        // 创建新文档（必须有文件）
        if (!file) {
          window.$message?.error('请选择文件');
          return;
        }
        await documentApi.createForRequirement(requirement.value.id, {
          file
        });
      }

      // 调用保存后的回调（重新加载需求详情）
      if (options?.onSave) {
        await options.onSave();
      }
      showDocumentEdit.value = false;
      window.$message?.success('保存成功');
    } catch {
      window.$message?.error('保存文档失败');
    } finally {
      // 无论成功失败都重置上传状态
      if (options?.onUploadComplete) {
        options.onUploadComplete();
      }
    }
  }

  // 批量保存文档
  async function batchSaveDocuments(files: File[]): Promise<{ success: number; failed: number; errors: string[] }> {
    if (!requirement.value?.id) {
      return { success: 0, failed: files.length, errors: ['需求ID不存在'] };
    }

    if (files.length === 0) {
      window.$message?.error('请选择文件');
      return { success: 0, failed: 0, errors: [] };
    }

    const results = { success: 0, failed: 0, errors: [] as string[] };

    // 串行上传，避免并发问题
    for (const file of files) {
      try {
        // eslint-disable-next-line no-await-in-loop
        await documentApi.createForRequirement(requirement.value.id, {
          file
        });
        results.success += 1;
      } catch (error: any) {
        results.failed += 1;
        const errorMsg = error?.response?.data?.message || error?.message || `${file.name} 上传失败`;
        results.errors.push(errorMsg);
      }
    }

    // 如果有成功上传的文件，重新加载需求详情
    if (results.success > 0 && options?.onSave) {
      try {
        await options.onSave();
      } catch (error) {
        console.error('重新加载需求详情失败:', error);
      }
    }

    // 无论成功失败都重置上传状态
    if (options?.onUploadComplete) {
      options.onUploadComplete();
    }

    return results;
  }

  // 删除文档
  async function deleteDocument(id: string) {
    if (!requirement.value?.id) return;
    try {
      await documentApi.deleteRequirementDocument(requirement.value.id, id);
      if (options?.onSave) {
        await options.onSave();
      }
      if (selectedDocument.value?.id === id) {
        selectedDocument.value = null;
        showDocumentModal.value = false;
      }
      window.$message?.success('删除成功');
    } catch {
      window.$message?.error('删除文档失败');
    }
  }

  // 获取文档下载 URL
  function getDocumentDownloadUrl(doc: Document.Response): string {
    if (options?.entityType === 'task' && options?.entityId) {
      return documentApi.getTaskDocumentDownloadUrl(requirement.value!.id!, options.entityId.value, doc.id);
    }
    return documentApi.getRequirementDocumentDownloadUrl(requirement.value!.id!, doc.id);
  }

  return {
    // 状态
    documents,
    showDocumentModal,
    selectedDocument,
    editDocumentForm,
    showDocumentEdit,
    documentLoading,
    // 方法
    viewDocument,
    openDocumentEdit,
    closeDocumentEdit,
    closeDocumentModal,
    saveDocument,
    batchSaveDocuments,
    deleteDocument,
    getDocumentDownloadUrl
  };
}

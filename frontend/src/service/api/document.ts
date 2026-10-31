/**
 * 文档模块 API 服务
 * Document = Attachment 简化模型
 * 文档直接作为文件上传，不再分离内容和附件
 */
import type { Document } from '@/typings/api/document';
import { downloadRequest, request } from '../request';

/**
 * 文档 API
 * 简化说明：文档就是附件，通过文件上传创建
 * - 创建文档：上传文件 + 状态
 * - 下载文档：直接返回文件
 */
export const documentApi = {
  // ============================================================================
  // 需求文档操作
  // ============================================================================

  /**
   * 为需求创建文档（上传文件）
   */
  createForRequirement(
    requirementId: string,
    data: {
      file: File;
      status?: Document.Status;
    }
  ) {
    const formData = new FormData();
    formData.append('file', data.file);
    if (data.status) {
      formData.append('doc_status', data.status);
    }

    return request<Document.Response>({
      url: `/api/requirements/${requirementId}/documents`,
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /**
   * 获取需求的所有文档
   */
  listForRequirement(requirementId: string) {
    return request<Document.Response[]>({
      url: `/api/requirements/${requirementId}/documents`,
      method: 'get'
    });
  },

  /**
   * 获取需求的单个文档
   */
  getRequirementDocument(requirementId: string, documentId: string) {
    return request<Document.Response>({
      url: `/api/requirements/${requirementId}/documents/${documentId}`,
      method: 'get'
    });
  },

  /**
   * 更新需求文档
   */
  updateRequirementDocument(
    requirementId: string,
    documentId: string,
    data: {
      file?: File;
      status?: Document.Status;
    }
  ) {
    const formData = new FormData();
    if (data.file) {
      formData.append('file', data.file);
    }
    if (data.status !== undefined) {
      formData.append('doc_status', data.status);
    }

    return request<Document.Response>({
      url: `/api/requirements/${requirementId}/documents/${documentId}`,
      method: 'put',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /**
   * 删除需求文档
   */
  deleteRequirementDocument(requirementId: string, documentId: string) {
    return request({
      url: `/api/requirements/${requirementId}/documents/${documentId}`,
      method: 'delete'
    });
  },

  /**
   * 获取需求文档的下载链接
   */
  getRequirementDocumentDownloadUrl(requirementId: string, documentId: string) {
    return `/api/requirements/${requirementId}/documents/${documentId}/download`;
  },

  /**
   * 下载需求文档内容（返回文本内容）
   * 用于预览 Markdown 等文本文件
   */
  async downloadRequirementDocumentContent(requirementId: string, documentId: string): Promise<string> {
    return downloadRequest<string>({
      url: `/api/requirements/${requirementId}/documents/${documentId}/download`,
      method: 'get'
    });
  },

  /**
   * 下载需求文档内容（返回 Blob）
   * 用于预览图片等二进制文件
   */
  async downloadRequirementDocumentBlob(requirementId: string, documentId: string): Promise<Blob> {
    return downloadRequest<Blob>({
      url: `/api/requirements/${requirementId}/documents/${documentId}/download`,
      method: 'get',
      responseType: 'blob'
    });
  },

  // ============================================================================
  // 任务文档操作
  // ============================================================================

  /**
   * 为任务创建文档（上传文件）
   */
  createForTask(
    requirementId: string,
    taskId: string,
    data: {
      file: File;
      status?: Document.Status;
    }
  ) {
    const formData = new FormData();
    formData.append('file', data.file);
    if (data.status) {
      formData.append('doc_status', data.status);
    }

    return request<Document.Response>({
      url: `/api/requirements/${requirementId}/tasks/${taskId}/documents`,
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /**
   * 获取任务的所有文档
   */
  listForTask(requirementId: string, taskId: string) {
    return request<Document.Response[]>({
      url: `/api/requirements/${requirementId}/tasks/${taskId}/documents`,
      method: 'get'
    });
  },

  /**
   * 获取任务的单个文档
   */
  getTaskDocument(requirementId: string, taskId: string, documentId: string) {
    return request<Document.Response>({
      url: `/api/requirements/${requirementId}/tasks/${taskId}/documents/${documentId}`,
      method: 'get'
    });
  },

  /**
   * 更新任务文档
   */
  updateTaskDocument(params: {
    requirementId: string;
    taskId: string;
    documentId: string;
    data: {
      file?: File;
      status?: Document.Status;
    };
  }) {
    const { requirementId, taskId, documentId, data } = params;
    const formData = new FormData();
    if (data.file) {
      formData.append('file', data.file);
    }
    if (data.status !== undefined) {
      formData.append('doc_status', data.status);
    }

    return request<Document.Response>({
      url: `/api/requirements/${requirementId}/tasks/${taskId}/documents/${documentId}`,
      method: 'put',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /**
   * 删除任务文档
   */
  deleteTaskDocument(requirementId: string, taskId: string, documentId: string) {
    return request({
      url: `/api/requirements/${requirementId}/tasks/${taskId}/documents/${documentId}`,
      method: 'delete'
    });
  },

  /**
   * 获取任务文档的下载链接
   */
  getTaskDocumentDownloadUrl(requirementId: string, taskId: string, documentId: string) {
    return `/api/requirements/${requirementId}/tasks/${taskId}/documents/${documentId}/download`;
  },

  /**
   * 下载任务文档内容（返回文本内容）
   * 用于预览 Markdown 等文本文件
   */
  async downloadTaskDocumentContent(requirementId: string, taskId: string, documentId: string): Promise<string> {
    return downloadRequest<string>({
      url: `/api/requirements/${requirementId}/tasks/${taskId}/documents/${documentId}/download`,
      method: 'get'
    });
  }
};

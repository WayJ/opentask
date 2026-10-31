import type { Document } from '@/typings/api/document';

/** 文档展示类型 */
export type DocumentDisplayType = 'markdown' | 'image' | 'word' | 'pdf' | 'other';

/**
 * 根据文件的 MIME 类型或扩展名判断文档类型
 * Document = Attachment 简化模型
 */
export function getDocumentDisplayType(document: Document.Response | null): DocumentDisplayType {
  if (!document) {
    return 'other';
  }

  // 使用 file_type 字段判断类型
  const mime = document.file_type?.toLowerCase() || '';
  const fileName = document.file_name?.toLowerCase() || '';

  // 图片类型 - 先检查 MIME 类型，再检查扩展名
  if (mime.startsWith('image/') || /\.(png|jpg|jpeg|gif|webp|svg|bmp|ico)$/i.test(fileName)) {
    return 'image';
  }

  // PDF 文档
  if (mime.includes('pdf') || fileName.endsWith('.pdf')) {
    return 'pdf';
  }

  // Word 文档
  if (
    mime.includes('word') ||
    mime.includes('docx') ||
    mime.includes('msword') ||
    mime.includes('officedocument') ||
    /\.(doc|docx)$/i.test(fileName)
  ) {
    return 'word';
  }

  // Markdown 文档（根据文件扩展名判断）
  if (fileName.endsWith('.md') || mime.includes('markdown') || mime.includes('text/markdown')) {
    return 'markdown';
  }

  // 文本类型
  if (mime.startsWith('text/')) {
    return 'markdown';
  }

  return 'other';
}

/**
 * 获取文档图标
 */
export function getDocumentIcon(type: DocumentDisplayType): string {
  switch (type) {
    case 'image':
      return 'mdi:image';
    case 'word':
      return 'mdi:file-word';
    case 'pdf':
      return 'mdi:file-pdf-box';
    case 'markdown':
      return 'mdi:language-markdown';
    default:
      return 'mdi:file-document';
  }
}

/**
 * 获取文档类型文本
 */
export function getDocumentTypeText(type: DocumentDisplayType): string {
  switch (type) {
    case 'image':
      return '图片';
    case 'word':
      return 'Word 文档';
    case 'pdf':
      return 'PDF 文档';
    case 'markdown':
      return 'Markdown 文档';
    default:
      return '文档';
  }
}

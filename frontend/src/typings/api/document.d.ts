/**
 * 文档模块 API 类型定义
 * Document = Attachment 简化模型
 */

export namespace Document {
  /** 文档状态 */
  export type Status = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';

  /** 文档响应（Document 就是 Attachment） */
  export interface Response {
    id: string;
    entity_type: string;
    entity_id: string;
    file_name: string;
    file_path: string;
    file_type: string;
    file_size: number;
    status: Status;
    created_at: string;
    updated_at: string;
  }
}

/** Issue Collection API 类型定义 */

export namespace Api.IssueCollection {
  /** 问题集状态枚举 */
  export enum CollectionStatus {
    PENDING = 'pending',
    IN_PROGRESS = 'in_progress',
    COMPLETED = 'completed'
  }

  /** 用户信息 */
  export interface UserInfo {
    id: string;
    name?: string;
    jnpf_name?: string;
    jnpf_account?: string;
  }

  /** 问题集基础信息 */
  export interface CollectionBase {
    title: string;
    description?: string;
    status: CollectionStatus;
  }

  /** 创建问题集 */
  export type CreateCollection = CollectionBase;

  /** 更新问题集 */
  export interface UpdateCollection {
    title?: string;
    description?: string;
    status?: CollectionStatus;
    issue_ids?: string[];
  }

  /** 统计信息 */
  export interface CollectionStatistics {
    total: number;
    completed: number;
    in_progress: number;
    pending: number;
    completion_rate: number;
  }

  /** 问题集响应 */
  export interface CollectionResponse extends CollectionBase {
    id: string;
    issue_ids: string[];
    creator_id: string;
    created_at: string;
    updated_at: string;
    creator?: UserInfo;
    statistics?: CollectionStatistics;
  }

  /** 问题集列表响应 */
  export interface CollectionListResponse {
    rows: CollectionResponse[];
    total: number;
    current: number;
    pageSize: number;
    totalPages: number;
  }

  /** 问题拆解请求 */
  export interface ParseRequest {
    issues: IssueParseData[];
  }

  /** 问题拆解数据 */
  export interface IssueParseData {
    title: string;
    description?: string;
    type?: string;
    priority?: string;
    tags?: string[];
  }

  /** 问题拆解响应 */
  export interface ParseResponse {
    parsed_count: number;
    issue_ids: string[];
  }

  /** 查询参数 */
  export interface CollectionQueryParams {
    page?: number;
    page_size?: number;
    status?: CollectionStatus;
    creator_id?: string;
    search?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }
}

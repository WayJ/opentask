/** Issue API 类型定义 */

export namespace Api.Issue {
  /** Issue 类型枚举 */
  export enum IssueType {
    BUG = 'bug',
    FEATURE = 'feature',
    QUESTION = 'question',
    FEEDBACK = 'feedback',
    INCIDENT = 'incident',
    IMPROVEMENT = 'improvement'
  }

  /** Issue 状态枚举 */
  export enum IssueStatus {
    OPEN = 'open',
    IN_PROGRESS = 'in_progress',
    FEEDBACK = 'feedback',
    RESOLVED = 'resolved',
    CLOSED = 'closed',
    REJECTED = 'rejected'
  }

  /** Issue 优先级枚举 */
  export enum IssuePriority {
    LOW = 'low',
    MEDIUM = 'medium',
    HIGH = 'high',
    CRITICAL = 'critical'
  }

  /** 评论类型枚举 */
  export enum CommentType {
    COMMENT = 'comment',
    SYSTEM = 'system',
    STATUS_CHANGE = 'status_change',
    ASSIGNMENT = 'assignment',
    PRIORITY_CHANGE = 'priority_change'
  }

  /** 关系类型枚举 */
  export enum RelationType {
    BLOCKS = 'blocks',
    IS_BLOCKED_BY = 'is_blocked_by',
    RELATES_TO = 'relates_to',
    DUPLICATES = 'duplicates',
    IS_DUPLICATED_BY = 'is_duplicated_by',
    DEPENDS_ON = 'depends_on',
    IS_DEPENDED_BY = 'is_depended_by'
  }

  /** 时间线动作类型枚举 */
  export enum TimelineAction {
    CREATED = 'created',
    UPDATED = 'updated',
    COMMENTED = 'commented',
    STATUS_CHANGED = 'status_changed',
    ASSIGNED = 'assigned',
    PRIORITY_CHANGED = 'priority_changed',
    DUE_DATE_CHANGED = 'due_date_changed',
    RELATION_ADDED = 'relation_added',
    RELATION_REMOVED = 'relation_removed',
    ATTACHMENT_ADDED = 'attachment_added',
    ATTACHMENT_REMOVED = 'attachment_removed',
    LABEL_ADDED = 'label_added',
    LABEL_REMOVED = 'label_removed',
    RESOLVED = 'resolved',
    CLOSED = 'closed',
    REOPENED = 'reopened'
  }

  /** 用户信息 */
  export interface UserInfo {
    id: string;
    name?: string;
    sso_name?: string;
    sso_account?: string;
  }

  /** Issue 基础信息 */
  export interface IssueBase {
    title: string;
    description?: string;
    type: IssueType;
    status: IssueStatus;
    priority: IssuePriority;
    project_id?: string;
    task_id?: string;
    requirement_id?: string;
    assignee_id?: string;
    reporter_id: string;
    position?: number;
    due_date?: string;
    estimated_hours?: number;
    actual_hours?: number;
    parent_issue_id?: string | null;
    cycle_id?: string | null;
    milestone_id?: string | null;
    estimate_points?: number | null;
  }

  /** 创建 Issue */
  export interface CreateIssue extends IssueBase {
    /** E9-S2 workspace issue template */
    template_id?: string;
  }

  /** 更新 Issue */
  export interface UpdateIssue {
    title?: string;
    description?: string;
    type?: IssueType;
    status?: IssueStatus;
    priority?: IssuePriority;
    project_id?: string;
    task_id?: string;
    requirement_id?: string;
    assignee_id?: string;
    position?: number;
    due_date?: string;
    estimated_hours?: number;
    actual_hours?: number;
    parent_issue_id?: string | null;
    cycle_id?: string | null;
    milestone_id?: string | null;
    estimate_points?: number | null;
  }

  /** Issue 响应 */
  /** 子 Issue 轻量摘要 */
  export interface IssueChildSummary {
    id: string;
    issue_code: string;
    title: string;
    status: IssueStatus | string;
  }

  export interface Issue extends IssueBase {
    id: string;
    issue_code: string;
    /** E20 relation badges */
    blocks_count?: number;
    blocked_by_count?: number;
    view_count: number;
    comment_count: number;
    attachment_count: number;
    started_at?: string;
    resolved_at?: string;
    closed_at?: string;
    is_deleted: boolean;
    created_at: string;
    updated_at: string;
    created_by?: string;
    updated_by?: string;
    project?: Api.Project.Project;
    assignee?: UserInfo;
    reporter?: UserInfo;
    children?: IssueChildSummary[];
    tags?: IssueTag[];
  }

  /** Issue 列表查询参数 */
  export interface IssueQueryParams {
    page?: number;
    page_size?: number;
    type?: IssueType;
    status?: IssueStatus;
    priority?: IssuePriority;
    project_id?: string;
    assignee_id?: string;
    reporter_id?: string;
    search?: string;
    cycle_id?: string;
    milestone_id?: string;
    watching?: boolean;
    due_before?: string;
    due_soon?: boolean;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }

  /** Issue 列表响应 */
  export interface IssueListResponse {
    rows: Issue[];
    total: number;
    current: number;
    pageSize: number;
    totalPages: number;
  }

  /** Issue 评论基础信息 */
  export interface IssueCommentBase {
    content: string;
    parent_id?: string;
    comment_type?: CommentType;
    meta_data?: Record<string, any>;
  }

  /** 创建 Issue 评论 */
  export interface CreateIssueComment extends IssueCommentBase {
    issue_id: string;
    user_id: string;
  }

  /** 更新 Issue 评论 */
  export interface UpdateIssueComment {
    content?: string;
  }

  /** Issue 评论响应 */
  export interface IssueComment extends IssueCommentBase {
    id: string;
    issue_id: string;
    user_id: string;
    is_deleted: boolean;
    created_at: string;
    updated_at: string;
    user_info?: UserInfo;
  }

  /** Issue 关系基础信息 */
  export interface IssueRelationBase {
    target_id: string;
    relation_type: RelationType;
  }

  /** 创建 Issue 关系 */
  export interface CreateIssueRelation extends IssueRelationBase {
    source_id: string;
  }

  /** Issue 关系响应 */
  export interface IssueRelation extends IssueRelationBase {
    id: number;
    source_id: string;
    created_at: string;
    created_by?: string;
  }

  /** 用户基本信息 */
  export interface UserInfo {
    id: string;
    name?: string;
    sso_name?: string;
    sso_account?: string;
  }

  /** Issue 时间线响应 */
  export interface IssueTimeline {
    id: string;
    issue_id: string;
    user_id?: string;
    action_type: TimelineAction;
    action_data?: Record<string, any>;
    created_at: string;
    user_info?: UserInfo;
  }

  /** Issue 标签（列表/详情 brief） */
  export interface IssueTag {
    id: number;
    name: string;
    color: string;
    groupId?: string | null;
    /** @deprecated legacy shape */
    type?: string;
    tag_id?: number;
    tag?: { name?: string; color?: string };
  }

  /** Issue 反应 */
  export interface IssueReaction {
    emoji: string;
    count: number;
    users: string[];
  }

  /** 批量更新 Issue */
  export interface BulkUpdateIssues {
    issue_ids: string[];
    status?: IssueStatus;
    priority?: IssuePriority;
    assignee_id?: string;
    cycle_id?: string | null;
    tag_ids?: number[];
  }

  /** 批量删除 Issue */
  export interface BulkDeleteIssues {
    issue_ids: string[];
  }

  /** Issue 统计信息 */
  export interface IssueStatistics {
    total: number;
    by_status: Record<string, number>;
    by_priority: Record<string, number>;
    by_type: Record<string, number>;
    open_count: number;
    in_progress_count: number;
    resolved_count: number;
    closed_count: number;
  }
}

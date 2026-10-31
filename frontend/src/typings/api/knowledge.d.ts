/**
 * 知识文档模块类型定义
 */
declare namespace Api {
  namespace Knowledge {
    /** 知识文档 */
    interface Knowledge {
      id: string;
      knowledgeBaseId: string;
      knowledgeBaseName?: string;
      title: string;
      slug: string;
      content: string;
      contentHtml?: string;
      categoryId?: number;
      status: 'draft' | 'published' | 'archived';
      visibility: 'public' | 'internal' | 'private';
      version: number;
      viewCount: number;
      likeCount: number;
      createdBy?: string;
      updatedBy?: string;
      createdAt: string;
      updatedAt: string;
    }

    /** 知识文档列表 */
    interface KnowledgeList {
      rows: Knowledge[];
      total: number;
      current: number;
      pageSize: number;
      totalPages: number;
    }

    /** 知识文档搜索参数 */
    interface KnowledgeSearchParams {
      knowledgeBaseId?: string;
      categoryId?: number;
      status?: string;
      keyword?: string;
      current?: number;
      pageSize?: number;
    }

    /** 创建知识文档 */
    interface KnowledgeCreate {
      knowledgeBaseId: string;
      title: string;
      content: string;
      categoryId?: number;
      visibility?: 'public' | 'internal' | 'private';
    }

    /** 更新知识文档 */
    interface KnowledgeUpdate {
      title?: string;
      content?: string;
      categoryId?: number;
      status?: 'draft' | 'published' | 'archived';
      visibility?: 'public' | 'internal' | 'private';
    }

    // ============================================================================
    // Git 编辑相关类型
    // ============================================================================

    /** 提交文档请求 */
    interface DocumentCommit {
      content: string;
      message: string;
      author?: string;
    }

    /** 提交结果 */
    interface CommitResult {
      sha: string;
      message: string;
      author: string;
      timestamp: string;
    }

    /** 文档历史记录 */
    interface DocumentHistory {
      sha: string;
      message: string;
      author: string;
      timestamp: string;
    }

    /** Diff 参数 */
    interface DiffParams {
      commit_a?: string;
      commit_b?: string;
    }

    /** 文档 Diff 结果 */
    interface DocumentDiff {
      file_path: string;
      old_content: string;
      new_content: string;
      diff: string;
      commit_a?: string;
      commit_b?: string;
    }

    /** Git 状态 */
    interface GitStatus {
      branch: string;
      commit: string;
      author: string;
      timestamp: string;
      is_dirty: boolean;
      modified_files: string[];
    }

    /** 创建分支参数 */
    interface CreateBranchParams {
      branch_name: string;
      from_branch?: string;
    }

    /** 分支结果 */
    interface BranchResult {
      branch_name: string;
      from_branch: string;
      status: string;
    }

    /** 创建 PR 参数 */
    interface CreatePRParams {
      title: string;
      source_branch: string;
      target_branch?: string;
      description?: string;
    }

    /** PR 结果 */
    interface PRResult {
      status: string;
      message: string;
      url?: string;
    }
  }
}

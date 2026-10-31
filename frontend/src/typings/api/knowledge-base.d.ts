/**
 * 知识库模块类型定义
 */
declare namespace Api {
  namespace KnowledgeBase {
    /** 知识库 */
    interface KnowledgeBase {
      id: string;
      name: string;
      description?: string;
      icon?: string;
      repositoryUrl?: string;
      status: 'active' | 'archived';
      knowledgeCount?: number;
      createdAt: string;
      updatedAt: string;
    }

    /** 知识库列表 */
    interface KnowledgeBaseList {
      rows: KnowledgeBase[];
      total: number;
      current: number;
      pageSize: number;
      totalPages: number;
    }

    /** 知识库搜索参数 */
    interface KnowledgeBaseSearchParams {
      status?: string;
      keyword?: string;
      current?: number;
      pageSize?: number;
    }

    /** 创建知识库 */
    interface KnowledgeBaseCreate {
      name: string;
      description?: string;
      icon?: string;
      repositoryUrl?: string;
    }

    /** 更新知识库 */
    interface KnowledgeBaseUpdate {
      name?: string;
      description?: string;
      icon?: string;
      repositoryUrl?: string;
      status?: 'active' | 'archived';
    }

    /** 项目关联 */
    interface ProjectAssociation {
      id: string;
      knowledgeBaseId: string;
      projectId: string;
      createdAt: string;
    }

    /** 关联项目请求 */
    interface AssociateProjectRequest {
      projectId: string;
    }
  }
}

/**
 * 知识分类模块类型定义
 */
declare namespace Api {
  namespace KnowledgeCategory {
    /** 知识分类 */
    interface Category {
      id: number;
      name: string;
      icon?: string;
      sortOrder: number;
      parentId?: number;
      children?: Category[];
      knowledgeCount?: number;
    }

    /** 分类树节点 */
    interface CategoryTree {
      id: number;
      name: string;
      icon?: string;
      sortOrder: number;
      parentId?: number;
      children: CategoryTree[];
      knowledgeCount?: number;
    }

    /** 分类列表响应 */
    interface CategoryList {
      rows: Category[];
      total: number;
    }

    /** 创建分类 */
    interface CategoryCreate {
      name: string;
      icon?: string;
      sortOrder?: number;
      parentId?: number;
    }

    /** 更新分类 */
    interface CategoryUpdate {
      name?: string;
      icon?: string;
      sortOrder?: number;
      parentId?: number;
    }
  }
}

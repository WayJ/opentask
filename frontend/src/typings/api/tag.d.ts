/**
 * 标签模块类型定义
 */
declare namespace Api {
  namespace Tag {
    /** 标签 */
    interface Tag {
      id: number;
      name: string;
      color: string;
      usageCount: number;
      createdAt: string;
    }

    /** 标签列表 */
    interface TagList {
      rows: Tag[];
      total: number;
      current: number;
      pageSize: number;
      totalPages: number;
    }

    /** 创建标签 */
    interface TagCreate {
      name: string;
      color?: string;
    }

    /** 更新标签 */
    interface TagUpdate {
      name?: string;
      color?: string;
    }
  }
}

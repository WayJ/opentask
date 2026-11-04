/**
 * 标签模块类型定义（E7-S1）
 */
declare namespace Api {
  namespace Tag {
    interface Tag {
      id: number;
      workspaceId: string;
      name: string;
      color: string;
      groupId?: string | null;
      createdAt?: string;
      updatedAt?: string;
    }

    interface TagBrief {
      id: number;
      name: string;
      color: string;
      groupId?: string | null;
    }

    interface TagGroup {
      id: string;
      workspaceId: string;
      name: string;
      color?: string | null;
      position: number;
    }

    interface TagList {
      rows: Tag[];
      total: number;
    }

    interface TagCreate {
      name: string;
      color?: string;
      group_id?: string | null;
    }

    interface TagUpdate {
      name?: string;
      color?: string;
      group_id?: string | null;
      clear_group?: boolean;
    }
  }
}

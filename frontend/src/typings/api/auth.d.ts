declare namespace Api {
  /**
   * namespace Auth
   *
   * backend api module: "auth"
   */
  namespace Auth {
    interface LoginToken {
      token: string;
      refreshToken: string;
      /**
       * 是否为受限 token（pwd_change scope）
       *
       * true 时只写 storage 并跳转改密模块，不拉取用户信息
       */
      mustChangePassword?: boolean;
    }

    interface UserInfo {
      userId: string;
      userName: string;
      roles: string[];
      buttons: string[];
      /**
       * menu 类权限对应的 route_key 列表（前端菜单/路由可见性过滤用）
       *
       * 旧版后端响应无该字段（undefined）→ 前端过滤逻辑回退全放行
       */
      menus?: string[];
      /** 当前工作区角色 */
      workspaceRole?: string | null;
    }
  }
}

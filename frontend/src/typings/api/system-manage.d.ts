declare namespace Api {
  /**
   * namespace SystemManage
   *
   * backend api module: "systemManage"
   */
  namespace SystemManage {
    type CommonSearchParams = Pick<Common.PaginatingCommonParams, 'current' | 'size'>;

    /** role */
    type Role = Common.CommonRecord<{
      /** role name */
      roleName: string;
      /** role code */
      roleCode: string;
      /** role description */
      roleDesc: string;
    }>;

    /** role search params */
    type RoleSearchParams = CommonType.RecordNullable<
      Pick<Api.SystemManage.Role, 'roleName' | 'roleCode' | 'status'> & CommonSearchParams
    >;

    /** role list */
    type RoleList = Common.PaginatingQueryRecord<Role>;

    /** all role */
    type AllRole = Pick<Role, 'id' | 'roleName' | 'roleCode'>;

    /**
     * user gender
     *
     * - "1": "male"
     * - "2": "female"
     */
    type UserGender = '1' | '2';

    /**
     * user role (JNPF integration)
     *
     * - "admin": 系统管理员
     * - "maintainer": 维护者
     * - "developer": 开发者
     * - "viewer": 查看者
     */
    type UserRoleType = 'admin' | 'maintainer' | 'developer' | 'viewer';

    /** user (JNPF integrated) */
    type User = Common.CommonRecord<{
      /** 登录账号（管理端建号写入，唯一标识） */
      username?: string;
      /** 姓名（管理端建号写入） */
      name?: string;
      /** JNPF user id */
      jnpfUserId?: string;
      /** JNPF account */
      jnpfAccount?: string;
      /** JNPF name */
      jnpfName?: string;
      /** organize name */
      organizeName?: string;
      /** position name */
      positionName?: string;
      /** user role（存量单角色字符串，展示/筛选桥接用） */
      role?: UserRoleType;
      /** 角色编码列表（user_role join；存量用户回退 role 字符串） */
      roleCodes?: string[];
      /** user status: 0-disabled, 1-enabled */
      status?: number;
      /** last login time */
      lastLoginTime?: string;
      /** sync time */
      syncTime?: string;
    }>;

    /** user search params */
    type UserSearchParams = CommonType.RecordNullable<
      Pick<Api.SystemManage.User, 'status' | 'role'> & {
        keyword?: string;
        deptId?: string;
        current: number;
        pageSize: number;
      }
    >;

    /** user list */
    type UserList = {
      rows: User[];
      total: number;
      current: number;
      pageSize: number;
      totalPages: number;
    };

    /** 用户详情（编辑抽屉回显：GET /api/users/{id}，后端蛇形命名） */
    type UserDetail = {
      id: string;
      username?: string | null;
      name?: string | null;
      jnpf_account?: string | null;
      jnpf_name?: string | null;
      role?: string | null;
      role_codes: string[];
      dept_assignments: DeptAssignment[];
      status: number;
      last_login_time?: string | null;
    };

    /** 用户创建请求体（POST /api/users） */
    type UserCreate = {
      username: string;
      name: string;
      role_codes: string[];
      dept_assignments?: DeptAssignment[];
      password?: string;
    };

    /** 用户编辑请求体（PUT /api/users/{id}；username 不可改） */
    type UserUpdate = {
      name?: string;
      role_codes?: string[];
      dept_assignments?: DeptAssignment[];
    };

    /** 用户部门归属行（提交与回显同构，蛇形命名） */
    type DeptAssignment = {
      dept_id: string;
      is_primary: boolean;
      position_id?: string | null;
    };

    /** 部门树节点 / 部门对象（GET /api/departments 与 CRUD 响应，蛇形命名） */
    type Department = {
      id: string;
      name: string;
      parent_id: string | null;
      path?: string | null;
      sort: number;
      /** 1 启用 0 禁用 */
      status: number;
      children?: Department[];
    };

    /** 部门创建请求体 */
    type DeptCreate = {
      name: string;
      parent_id?: string | null;
      sort?: number;
    };

    /** 部门更新请求体（仅传需要修改的字段） */
    type DeptUpdate = {
      name?: string;
      sort?: number;
      parent_id?: string | null;
    };

    /** current user response */
    type CurrentUser = {
      id: string;
      jnpfUserId?: string;
      /** 钉钉绑定 userid（null = 未绑定） */
      dingtalkUserId?: string | null;
      jnpfAccount?: string;
      jnpfName?: string;
      organizeName?: string;
      positionName?: string;
      role: UserRoleType;
      status: number;
      permissions: string[];
    };

    /** user status update */
    type UserStatusUpdate = {
      status: 0 | 1;
    };

    /** user role update */
    type UserRoleUpdate = {
      role: UserRoleType;
    };

    /** role info（GET /api/roles 列表项；value=code、label=name 兼容旧结构） */
    type RoleInfo = {
      id: string;
      value: string;
      label: string;
      description: string;
      code: string;
      name: string;
      data_scope: string;
      is_system: boolean;
      status: number;
    };

    /** 数据范围档位（与后端 VALID_DATA_SCOPES 一致） */
    type DataScope = 'ALL' | 'DEPT_AND_CHILD' | 'DEPT' | 'CUSTOM' | 'SELF';

    /** 角色创建请求体（POST /api/roles） */
    type RoleCreate = {
      code: string;
      name: string;
      description?: string;
      data_scope?: DataScope;
    };

    /** 角色更新请求体（PUT /api/roles/{id}；系统角色只许改 name/description） */
    type RoleUpdate = {
      name?: string;
      description?: string;
      data_scope?: DataScope;
      /** CUSTOM 档位的自定义部门（覆盖式） */
      dept_ids?: string[];
    };

    /** 角色当前权限回显（GET /api/roles/{id}/permissions） */
    type RolePermissions = {
      codes: string[];
      dept_ids: string[];
    };

    /** 权限点（GET /api/permissions 列表项） */
    type PermissionInfo = {
      id: string;
      code: string;
      name: string;
      /** menu / button */
      type: string;
      route_key: string | null;
      /** 1 启用 0 停用 */
      status: number;
    };

    /**
     * menu type
     *
     * - "1": directory
     * - "2": menu
     */
    type MenuType = '1' | '2';

    type MenuButton = {
      /**
       * button code
       *
       * it can be used to control the button permission
       */
      code: string;
      /** button description */
      desc: string;
    };

    /**
     * icon type
     *
     * - "1": iconify icon
     * - "2": local icon
     */
    type IconType = '1' | '2';

    type MenuPropsOfRoute = Pick<
      import('vue-router').RouteMeta,
      | 'i18nKey'
      | 'keepAlive'
      | 'constant'
      | 'order'
      | 'href'
      | 'hideInMenu'
      | 'activeMenu'
      | 'multiTab'
      | 'fixedIndexInTab'
      | 'query'
    >;

    type Menu = Common.CommonRecord<{
      /** parent menu id */
      parentId: number;
      /** menu type */
      menuType: MenuType;
      /** menu name */
      menuName: string;
      /** route name */
      routeName: string;
      /** route path */
      routePath: string;
      /** component */
      component?: string;
      /** iconify icon name or local icon name */
      icon: string;
      /** icon type */
      iconType: IconType;
      /** buttons */
      buttons?: MenuButton[] | null;
      /** children menu */
      children?: Menu[] | null;
    }> &
      MenuPropsOfRoute;

    /** menu list */
    type MenuList = Common.PaginatingQueryRecord<Menu>;

    type MenuTree = {
      id: number;
      label: string;
      pId: number;
      children?: MenuTree[];
    };
  }
}

const local: App.I18n.Schema = {
  system: {
    title: 'AI研发管理平台',
    updateTitle: '系统版本更新通知',
    updateContent: '检测到系统有新版本发布，是否立即刷新页面？',
    updateConfirm: '立即刷新',
    updateCancel: '稍后再说'
  },
  common: {
    action: '操作',
    add: '新增',
    addSuccess: '添加成功',
    backToHome: '返回首页',
    batchDelete: '批量删除',
    cancel: '取消',
    close: '关闭',
    check: '勾选',
    selectAll: '全选',
    expandColumn: '展开列',
    columnSetting: '列设置',
    config: '配置',
    confirm: '确认',
    delete: '删除',
    deleteSuccess: '删除成功',
    confirmDelete: '确认删除吗？',
    edit: '编辑',
    warning: '警告',
    error: '错误',
    index: '序号',
    keywordSearch: '请输入关键词搜索',
    logout: '退出登录',
    logoutConfirm: '确认退出登录吗？',
    profile: '个人信息',
    lookForward: '敬请期待',
    modify: '修改',
    modifySuccess: '修改成功',
    noData: '无数据',
    operate: '操作',
    pleaseCheckValue: '请检查输入的值是否合法',
    refresh: '刷新',
    reset: '重置',
    search: '搜索',
    switch: '切换',
    tip: '提示',
    trigger: '触发',
    update: '更新',
    updateSuccess: '更新成功',
    userCenter: '个人中心',
    yesOrNo: {
      yes: '是',
      no: '否'
    },
    commandPalette: {
      placeholder: '输入命令或搜索…',
      groupActions: '操作',
      groupMenus: '菜单',
      groupIssues: 'Issue',
      groupProjects: '项目',
      groupCycles: '冲刺',
      groupViews: '视图',
      searching: '搜索中…',
      navIssues: 'Issue 列表',
      navCreateIssue: '创建 Issue',
      navCreateFromTemplate: '从模板创建 Issue',
      navProjects: '项目',
      actionAddLabel: '添加标签…',
      navLabels: '标签 Labels',
      navCycles: 'Cycles 设置',
      navTriage: '分诊',
      navInbox: '收件箱'
    }
  },
  request: {
    logout: '请求失败后登出用户',
    logoutMsg: '用户状态失效，请重新登录',
    logoutWithModal: '请求失败后弹出模态框再登出用户',
    logoutWithModalMsg: '用户状态失效，请重新登录',
    refreshToken: '请求的token已过期，刷新token',
    tokenExpired: 'token已过期'
  },
  theme: {
    themeDrawerTitle: '主题配置',
    tabs: {
      appearance: '外观',
      layout: '布局',
      general: '通用',
      preset: '预设'
    },
    appearance: {
      themeSchema: {
        title: '主题模式',
        light: '亮色模式',
        dark: '暗黑模式',
        auto: '跟随系统'
      },
      grayscale: '灰色模式',
      colourWeakness: '色弱模式',
      themeColor: {
        title: '主题颜色',
        primary: '主色',
        info: '信息色',
        success: '成功色',
        warning: '警告色',
        error: '错误色',
        followPrimary: '跟随主色'
      },
      themeRadius: {
        title: '主题圆角'
      },
      recommendColor: '应用推荐算法的颜色',
      recommendColorDesc: '推荐颜色的算法参照',
      preset: {
        title: '主题预设',
        apply: '应用',
        applySuccess: '预设应用成功',
        default: {
          name: '默认预设',
          desc: 'Soybean 默认主题预设'
        },
        dark: {
          name: '暗色预设',
          desc: '适用于夜间使用的暗色主题预设'
        },
        compact: {
          name: '紧凑型',
          desc: '适用于小屏幕的紧凑布局预设'
        },
        azir: {
          name: 'Azir的预设',
          desc: '是 Azir 比较喜欢的莫兰迪色系冷淡风'
        }
      }
    },
    layout: {
      layoutMode: {
        title: '布局模式',
        vertical: '左侧菜单模式',
        'vertical-mix': '左侧菜单混合模式',
        'vertical-hybrid-header-first': '左侧混合-顶部优先',
        horizontal: '顶部菜单模式',
        'top-hybrid-sidebar-first': '顶部混合-侧边优先',
        'top-hybrid-header-first': '顶部混合-顶部优先',
        vertical_detail: '左侧菜单布局，菜单在左，内容在右。',
        'vertical-mix_detail': '左侧双菜单布局，一级菜单在左侧深色区域，二级菜单在左侧浅色区域。',
        'vertical-hybrid-header-first_detail':
          '左侧混合布局，一级菜单在顶部，二级菜单在左侧深色区域，三级菜单在左侧浅色区域。',
        horizontal_detail: '顶部菜单布局，菜单在顶部，内容在下方。',
        'top-hybrid-sidebar-first_detail': '顶部混合布局，一级菜单在左侧，二级菜单在顶部。',
        'top-hybrid-header-first_detail': '顶部混合布局，一级菜单在顶部，二级菜单在左侧。'
      },
      tab: {
        title: '标签栏设置',
        visible: '显示标签栏',
        cache: '标签栏信息缓存',
        cacheTip: '一键开启/关闭全局 keepalive',
        height: '标签栏高度',
        mode: {
          title: '标签栏风格',
          slider: '滑块风格',
          chrome: '谷歌风格',
          button: '按钮风格'
        },
        closeByMiddleClick: '鼠标中键关闭标签页',
        closeByMiddleClickTip: '启用后可以使用鼠标中键点击标签页进行关闭'
      },
      header: {
        title: '头部设置',
        height: '头部高度',
        breadcrumb: {
          visible: '显示面包屑',
          showIcon: '显示面包屑图标'
        }
      },
      sider: {
        title: '侧边栏设置',
        inverted: '深色侧边栏',
        width: '侧边栏宽度',
        collapsedWidth: '侧边栏折叠宽度',
        mixWidth: '混合布局侧边栏宽度',
        mixCollapsedWidth: '混合布局侧边栏折叠宽度',
        mixChildMenuWidth: '混合布局子菜单宽度',
        autoSelectFirstMenu: '自动选择第一个子菜单',
        autoSelectFirstMenuTip: '点击一级菜单时，自动选择并导航到第一个子菜单的最深层级'
      },
      footer: {
        title: '底部设置',
        visible: '显示底部',
        fixed: '固定底部',
        height: '底部高度',
        right: '底部居右'
      },
      content: {
        title: '内容区域设置',
        scrollMode: {
          title: '滚动模式',
          tip: '主题滚动仅 main 部分滚动，外层滚动可携带头部底部一起滚动',
          wrapper: '外层滚动',
          content: '主体滚动'
        },
        page: {
          animate: '页面切换动画',
          mode: {
            title: '页面切换动画类型',
            'fade-slide': '滑动',
            fade: '淡入淡出',
            'fade-bottom': '底部消退',
            'fade-scale': '缩放消退',
            'zoom-fade': '渐变',
            'zoom-out': '闪现',
            none: '无'
          }
        },
        fixedHeaderAndTab: '固定头部和标签栏'
      }
    },
    general: {
      title: '通用设置',
      watermark: {
        title: '水印设置',
        visible: '显示全屏水印',
        text: '自定义水印文本',
        enableUserName: '启用用户名水印',
        enableTime: '显示当前时间',
        timeFormat: '时间格式'
      },
      multilingual: {
        title: '多语言设置',
        visible: '显示多语言按钮'
      },
      globalSearch: {
        title: '全局搜索设置',
        visible: '显示全局搜索按钮'
      }
    },
    configOperation: {
      copyConfig: '复制配置',
      copySuccessMsg: '复制成功，请替换 src/theme/settings.ts 中的变量 themeSettings',
      resetConfig: '重置配置',
      resetSuccessMsg: '重置成功'
    }
  },
  route: {
    oauth2: 'OAuth2 授权',
    profile: '个人信息',
    profile_userinfo: '个人信息',
    'profile_ssh-keys': 'SSH 密钥',
    'profile_access-tokens': 'Access Token',
    login: '登录',
    403: '无权限',
    404: '页面不存在',
    500: '服务器错误',
    'iframe-page': '外链页面',
    home: '首页',
    workspace_members: '成员 Members',
    invite: '邀请',
    workspace_labels: '标签 Labels',
    'workspace_issue-templates': 'Issue 模板',
    workspace_cycles: '冲刺 Cycles',
    inbox: '收件箱',
    triage: '分诊',
    dashboard: '研发效能看板',
    workflow: '研发流水线',
    projects: '项目管理',
    workflow_projects: '项目管理',
    'workflow_project-detail': '项目详情',
    workflow_requirements: '需求（遗留）',
    'workflow_requirement-detail': '需求详情',
    system: '系统配置',
    'knowledge-base': '知识库',
    'knowledge-base_list': '知识库列表',
    'knowledge-base_knowledges': '知识文档',
    knowledge: '知识文档',
    knowledge_list: '知识文档列表',
    knowledge_detail: '知识文档详情',
    knowledge_edit: '编辑知识文档',
    knowledge_edit_git: 'Git 编辑器',
    issue: '问题管理',
    issue_create: '问题登记',
    issue_detail: '问题详情',
    'issue_detail-new': '问题详情（新设计）',
    issue_list: '问题列表',
    issue_collection: '问题集',
    'issue_collection-list': '问题集列表',
    'issue_collection-create': '创建问题集',
    'knowledge-category': '知识分类',
    'knowledge-category_manage': '分类管理',
    'knowledge-base_manage': '知识库管理',
    'knowledge-base_manage_category': '分类管理',
    'knowledge-base_manage_tag': '标签管理',
    'knowledge-base_manage_tag_manage': '标签列表',
    'knowledge-base_knowledge': '知识文档',
    'knowledge-base_knowledge_list': '知识文档列表',
    'knowledge-base_knowledge_detail': '知识文档详情',
    'knowledge-base_knowledge_edit': '编辑知识文档',
    'knowledge-base_knowledge_edit_git': 'Git 编辑器',
    manage: '系统管理',
    manage_user: '用户管理',
    manage_dept: '部门管理',
    'manage_user-detail': '用户详情',
    manage_role: '角色管理',
    manage_perm: '权限点管理',
    'work-management': '工作管理',
    'work-management_rd-groups': '研发组',
    'work-management_rd-groups-create': '创建研发组',
    'work-management_rd-groups-detail': '研发组详情',
    'work-management_cost-projects': '成本项目',
    'work-management_cost-projects_create': '创建成本项目',
    'work-management_cost-projects_detail': '成本项目详情',
    'work-management_cost-projects_list': '成本项目列表',
    'work-management_work-assignments': '工作安排',
    'work-management_work-assignments_create': '创建工作安排',
    'work-management_work-assignments_detail': '工作安排详情',
    'work-management_work-assignments_list': '工作安排列表',
    'work-management_my-work': '我的工作',
    'work-management_my-work_weekly': '周视图',
    'work-management_my-work_feedback': '工作反馈'
  },
  page: {
    oauth2: {
      consent: {
        title: '授权确认',
        lead: '「{appName}」请求访问你的 OpenTask 数据。',
        loading: '正在校验授权请求…',
        missingParams: '授权请求缺少必要参数，请从应用重新发起授权。',
        invalidRequest: '授权请求无效或已被拒绝。',
        decideFailed: '提交授权决策失败，请重试。',
        scopeTitle: '该应用将获得以下权限',
        redirectTitle: '授权后将返回',
        approve: '同意授权',
        deny: '拒绝'
      }
    },
    login: {
      common: {
        loginOrRegister: '登录 / 注册',
        userNamePlaceholder: '请输入用户名',
        phonePlaceholder: '请输入手机号',
        codePlaceholder: '请输入验证码',
        passwordPlaceholder: '请输入密码',
        confirmPasswordPlaceholder: '请再次输入密码',
        codeLogin: '验证码登录',
        confirm: '确定',
        back: '返回',
        validateSuccess: '验证成功',
        loginSuccess: '登录成功',
        welcomeBack: '欢迎回来，{userName} ！',
        pwdError: '账号或密码错误'
      },
      pwdLogin: {
        title: '密码登录',
        rememberMe: '记住我',
        forgetPassword: '忘记密码？',
        register: '注册账号',
        otherAccountLogin: '其他账号登录',
        otherLoginMode: '其他登录方式',
        dingtalkLogin: '钉钉登录',
        superAdmin: '超级管理员',
        admin: '管理员',
        user: '普通用户'
      },
      codeLogin: {
        title: '验证码登录',
        getCode: '获取验证码',
        reGetCode: '{time}秒后重新获取',
        sendCodeSuccess: '验证码发送成功',
        imageCodePlaceholder: '请输入图片验证码'
      },
      register: {
        title: '注册账号',
        agreement: '我已经仔细阅读并接受',
        protocol: '《用户协议》',
        policy: '《隐私权政策》'
      },
      resetPwd: {
        title: '重置密码'
      },
      bindWeChat: {
        title: '绑定微信'
      },
      changePassword: {
        title: '修改初始密码',
        tip: '首次登录请先修改初始密码后继续使用',
        oldPasswordPlaceholder: '请输入旧密码',
        newPasswordPlaceholder: '请输入新密码（至少8位，含字母和数字）',
        pwdRule: '新密码需至少8位，且同时包含字母和数字',
        oldPwdError: '旧密码错误',
        changeSuccess: '密码修改成功',
        changeFailed: '密码修改失败，请稍后重试'
      },
      dingtalkCallback: {
        title: '钉钉登录',
        processing: '正在通过钉钉登录…',
        success: '钉钉登录成功，正在进入系统',
        fail: '钉钉登录失败，请重试或使用账号密码登录',
        noCode: '缺少钉钉授权码，请从登录页重新发起钉钉登录'
      }
    },
    home: {
      branchDesc: '本系统为 Agent 准备，做为 AI Harness 存在',
      greeting: '早安，{userName}, 今天又是充满活力的一天!',
      weatherDesc: '今日多云转晴，20℃ - 25℃!',
      projectCount: '项目数',
      todo: '待办',
      message: '消息',
      downloadCount: '下载量',
      registerCount: '注册量',
      schedule: '作息安排',
      study: '学习',
      work: '工作',
      rest: '休息',
      entertainment: '娱乐',
      visitCount: '访问量',
      turnover: '成交额',
      dealCount: '成交量',
      projectNews: {
        title: '项目动态',
        moreNews: '更多动态',
        desc1: 'Soybean 在2021年5月28日创建了开源项目 soybean-admin!',
        desc2: 'Yanbowe 向 soybean-admin 提交了一个bug，多标签栏不会自适应。',
        desc3: 'Soybean 准备为 soybean-admin 的发布做充分的准备工作!',
        desc4: 'Soybean 正在忙于为soybean-admin写项目说明文档！',
        desc5: 'Soybean 刚才把工作台页面随便写了一些，凑合能看了！'
      },
      creativity: '创意'
    },
    manage: {
      common: {
        status: {
          enable: '启用',
          disable: '禁用'
        }
      },
      role: {
        title: '角色列表',
        roleName: '角色名称',
        roleCode: '角色编码',
        roleStatus: '角色状态',
        roleDesc: '角色描述',
        menuAuth: '菜单权限',
        buttonAuth: '按钮权限',
        form: {
          roleName: '请输入角色名称',
          roleCode: '请输入角色编码',
          roleStatus: '请选择角色状态',
          roleDesc: '请输入角色描述'
        },
        addRole: '新增角色',
        editRole: '编辑角色'
      },
      user: {
        title: '用户列表',
        userName: '用户名',
        userGender: '性别',
        nickName: '昵称',
        userPhone: '手机号',
        userEmail: '邮箱',
        userStatus: '用户状态',
        userRole: '用户角色',
        account: '账号',
        name: '姓名',
        organize: '组织',
        position: '岗位',
        lastLogin: '最后登录',
        form: {
          userName: '请输入用户名',
          userGender: '请选择性别',
          nickName: '请输入昵称',
          userPhone: '请输入手机号',
          userEmail: '请输入邮箱',
          userStatus: '请选择用户状态',
          userRole: '请选择用户角色'
        },
        addUser: '新增用户',
        editUser: '编辑用户',
        gender: {
          male: '男',
          female: '女'
        },
        role: {
          admin: '系统管理员',
          maintainer: '维护者',
          developer: '开发者',
          viewer: '查看者'
        }
      }
    }
  },
  form: {
    required: '不能为空',
    userName: {
      required: '请输入用户名',
      invalid: '用户名格式不正确'
    },
    phone: {
      required: '请输入手机号',
      invalid: '手机号格式不正确'
    },
    pwd: {
      required: '请输入密码',
      invalid: '密码格式不正确，6-18位字符，包含字母、数字、下划线'
    },
    confirmPwd: {
      required: '请输入确认密码',
      invalid: '两次输入密码不一致'
    },
    code: {
      required: '请输入验证码',
      invalid: '验证码格式不正确'
    },
    email: {
      required: '请输入邮箱',
      invalid: '邮箱格式不正确'
    }
  },
  dropdown: {
    closeCurrent: '关闭',
    closeOther: '关闭其它',
    closeLeft: '关闭左侧',
    closeRight: '关闭右侧',
    closeAll: '关闭所有',
    pin: '固定标签',
    unpin: '取消固定'
  },
  icon: {
    themeConfig: '主题配置',
    themeSchema: '主题模式',
    lang: '切换语言',
    fullscreen: '全屏',
    fullscreenExit: '退出全屏',
    reload: '刷新页面',
    collapse: '折叠菜单',
    expand: '展开菜单',
    pin: '固定',
    unpin: '取消固定'
  },
  datatable: {
    itemCount: '共 {total} 条',
    fixed: {
      left: '左固定',
      right: '右固定',
      unFixed: '取消固定'
    }
  },
  profile: {
    subtitle: '查看和管理您的个人信息',
    basicInfo: '基本信息',
    account: '账号',
    name: '姓名',
    role: '角色',
    status: '状态',
    enabled: '已启用',
    disabled: '已禁用',
    organize: '所属组织',
    position: '职位',
    userId: '用户ID',
    permissions: '权限列表',
    totalPermissions: '总权限数',
    noPermissions: '暂无权限',
    themeSettings: '主题设置',
    ssoAccount: 'SSO账号管理',
    pwd: {
      title: '修改密码',
      submit: '确认修改',
      hint: '新密码需至少 8 位且同时包含字母和数字；修改成功后当前登录会失效，需使用新密码重新登录。',
      reLoginTip: '密码已修改，当前登录已失效，请使用新密码重新登录。'
    },
    dingtalk: {
      title: '钉钉绑定',
      bound: '已绑定',
      unbound: '未绑定',
      hint: '钉钉账号会在首次使用钉钉登录（扫码 / 企业内免登）时自动绑定，本期暂不支持解绑。'
    }
  }
};

export default local;

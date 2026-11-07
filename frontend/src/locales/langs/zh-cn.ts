const local: App.I18n.Schema = {
  system: {
    title: 'OpenTask',
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
      groupIssues: '问题',
      groupProjects: '项目',
      groupCycles: '冲刺',
      groupViews: '视图',
      searching: '搜索中…',
      navIssues: '问题列表',
      navCreateIssue: '创建问题',
      navCreateFromTemplate: '从模板创建问题',
      navProjects: '项目',
      actionAddLabel: '添加标签…',
      navLabels: '标签',
      navCycles: '冲刺设置',
      navInitiatives: '举措',
      navTriage: '分诊',
      navSearch: '搜索…',
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
          desc: 'OpenTask 默认主题预设'
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
    'oauth2-install': '安装确认',
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
    workspace: '工作区',
    workspace_members: '成员',
    invite: '邀请',
    workspace_labels: '标签',
    settings: '设置',
    settings_webhooks: '出站 Webhooks',
    settings_sla: 'SLA 策略',
    settings_recurrences: '周期建单',
    settings_forms: '公开表单',
    'public-form': '公开表单',
    'public-request-status': '请求状态',
    settings_notifications: '通知偏好',
    workspace_automations: '自动化',
    'workspace_custom-fields': '自定义字段',
    'workspace_issue-templates': '问题模板',
    'workspace_project-templates': '项目模板',
    workspace_cycles: '冲刺',
    inbox: '收件箱',
    activity: '活动',
    insights: '洞察',
    search: '搜索',
    customers: '客户',
    customers_detail: '客户详情',
    requests: '需求',
    requests_detail: '需求详情',
    initiatives: '举措',
    initiatives_detail: '举措详情',
    triage: '分诊',
    dashboard: '研发效能看板',
    workflow: '项目',
    projects: '项目管理',
    workflow_projects: '项目',
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
    issue: '问题',
    issue_create: '问题登记',
    issue_detail: '问题详情',
    'issue_detail-new': '问题详情（新设计）',
    issue_list: '我的问题',
    issue_trash: '回收站',
    'workspace-onboarding': '创建工作区',
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
    manage_oauth2: 'OAuth 客户端',
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
    sider: {
      triage: '分诊',
      triageHint: '入站',
      customers: '客户',
      customersHint: '需求',
      insights: '洞察',
      insightsHint: '效能',
      activity: '活动',
      activityHint: '动态'
    },
    shell: {
      export: '导出',
      import: '导入',
      createIssue: '新建问题',
      importIssueCsv: '导入问题 CSV',
      issueListTitle: '问题',
      list: '列表',
      board: '看板',
      trash: '回收站',
      allRequests: '全部需求',
      createCustomer: '新建客户',
      createRequest: '新建需求',
      createInitiative: '新建议措',
      emptyInitiatives: '暂无举措，创建后关联多个项目',
      missingInitiativeId: '缺少举措 id',
      issueForm: '问题表单',
      publicIssueForms: '公开问题表单',
      selectIssueTemplate: '选择问题模板',
      issueUploadHint: '问题创建后自动上传',
      noIssues: '暂无问题',
      issueMissing: '问题不存在',
      addSubIssue: '添加子问题',
      noLinkedIssues: '尚未关联问题',
      insightsEmpty: '暂无问题。创建几条后回来看分布与趋势。',
      editProjectTemplate: '编辑项目模板',
      createProjectTemplate: '新建项目模板',
      searchIssues: '搜索问题编号、标题...',
      invites: '邀请',
      insightsLoadFailed: '加载洞察失败',
      openIssues: '开放问题',
      cycleIssues: '冲刺问题',
      cycleCompleted: '冲刺已完成',
      noActiveCycle: '无进行中的冲刺',
      cyclesDisabled: '未启用冲刺',
      issueKeyPrefix: '问题单号',
      weekDoneOpen: '本周完成 / 开放问题',
      weekDone: '本周完成',
      openShort: '开放',
      projectTemplate: '项目模板',
      fromProjectTemplate: '可选：从项目模板创建',
      savedAsProjectTemplate: '已另存为项目模板',
      favoriteIssue: '问题',
      favoriteInitiative: '举措',
      favoriteProject: '项目',
      favoriteView: '视图',
      labelsOr: '标签（或）',
      defaultCycle: '默认当前冲刺'
    },
    search: {
      placeholder: '搜索问题、项目、文档、成员、评论…',
      hint: '输入关键词开始搜索。也可用 ⌘K 打开命令面板。',
      empty: '没有匹配结果',
      groupIssues: '问题',
      groupProjects: '项目',
      groupDocs: '文档',
      groupMembers: '成员',
      groupComments: '评论'
    },
    profile: {
      pwd: {
        title: '修改密码',
        submit: '确认修改',
        hint: '新密码需至少 8 位且同时包含字母和数字；修改成功后当前登录会失效，需使用新密码重新登录。',
        reLoginTip: '密码已修改，当前登录已失效，请使用新密码重新登录。'
      }
    },
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
        passwordPlaceholder: '请输入密码（至少 8 位，含字母和数字）',
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
        desc1: '从问题列表查看当前工作区的问题。',
        desc2: '客户和客户反馈仍从客户页面进入。',
        desc3: '工作区、项目和保存的视图保持可用。',
        desc4: '公开表单 /f 和状态页 /r 可以直接打开。',
        desc5: '还没有工作区时，登录后会先完成创建。'
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
      invalid: '密码至少 8 位，且需同时包含字母和数字'
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

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
    issue_edit: '编辑问题',
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
      createInitiative: '新建举措',
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
    issueList: {
      tabs: {
        myTodos: '我的待办',
        open: '开放中',
        closed: '已关闭',
        all: '全部'
      },
      toolbar: {
        views: '视图',
        saveView: '保存视图',
        saveViewHint: '将当前筛选保存为个人或共享视图',
        star: '星标',
        starHint: '星标视图（列表顶栏 chips，≠ 侧栏收藏）',
        pinToSidebar: '收藏到侧栏',
        unpinFromSidebar: '取消侧栏',
        pinToSidebarHint: '固定到左侧边栏 Favorites（独立于星标）',
        saveAs: '另存为',
        saveAsHint: '复制为个人视图（共享只读成员可用）',
        filters: '筛选',
        collapseFilters: '收起筛选面板',
        expandFilters: '展开筛选面板',
        syntaxHelp: '语法帮助',
        syntaxHelpHint: '查看搜索语法帮助',
        display: '显示',
        sort: '排序',
        group: '分组'
      },
      sortBy: {
        createdAt: '创建时间',
        updatedAt: '更新时间',
        priority: '优先级',
        status: '状态',
        title: '标题',
        dueDate: '截止日期'
      },
      sortOrder: {
        desc: '降序',
        asc: '升序'
      },
      groupBy: {
        none: '不分组',
        status: '状态',
        assignee: '负责人',
        priority: '优先级',
        type: '类型',
        label: '标签'
      },
      computedFieldSuffix: '（计算值）',
      computedFieldSuffixReadonly: '（计算值·只读）',
      columns: {
        key: '编号',
        title: '标题',
        type: '类型',
        status: '状态',
        priority: '优先级',
        estimate: '估点',
        assignee: '负责人',
        reporter: '报告人',
        createdAt: '创建时间',
        actions: '操作'
      },
      actions: {
        view: '详情',
        systemReporter: '系统'
      },
      filters: {
        project: '项目',
        cycle: '冲刺',
        type: '类型',
        priority: '优先级',
        reset: '重置筛选'
      },
      syntax: {
        title: '搜索语法帮助',
        tipPrefix: '提示：可以组合使用多个过滤器，如',
        assigneeMe: '显示分配给我的问题',
        isOpen: '只显示待办中的问题',
        isClosed: '只显示已完成的问题',
        isInProgress: '只显示进行中的问题',
        typeFeature: '只显示功能类型的问题',
        typeBug: '只显示缺陷类型的问题',
        priorityUrgent: '只显示紧急优先级的问题',
        priorityHigh: '只显示高优先级的问题',
        customField: '按自定义字段过滤（亦可用 cf:key:value）'
      },
      views: {
        currentPrefix: '当前视图：',
        favoriteViews: '收藏视图',
        savePersonalTitle: '保存为个人视图',
        saveSharedTitle: '保存为共享视图',
        save: '保存',
        namePlaceholder: '视图名称，例如：我的高优缺陷',
        shareWithWorkspace: '共享给工作区'
      },
      scopeTitle: {
        watching: '我关注的',
        dueSoon: '即将到期',
        assignedToMe: '指派给我',
        createdByMe: '我创建的'
      },
      import: {
        downloadTemplate: '下载模板 CSV',
        helpBefore: '列需含 title；可选 issue_code（本工作区已存在则更新）。自定义字段用',
        helpAfter: '列（模板已含当前工作区字段；multi 逗号分隔，boolean 用 true/false）。未知 key 不阻断主字段写入。'
      },
      messages: {
        enterViewName: '请输入视图名称',
        viewSaved: '视图已保存',
        sharedViewSaved: '共享视图已保存',
        saveViewFailed: '保存视图失败',
        viewApplied: '已应用视图「{name}」',
        viewNotFound: '未找到该视图',
        applyViewFirst: '请先应用一个已保存视图',
        sharedViewCantStar: '共享视图不支持收藏，可另存为个人视图后再收藏',
        starred: '已收藏',
        unstarred: '已取消收藏',
        updateStarFailed: '更新收藏失败',
        pinnedToSidebar: '已收藏到侧栏',
        unpinnedFromSidebar: '已从侧栏移除',
        updateSidebarPinFailed: '更新侧栏收藏失败',
        savedAsPersonal: '已另存为个人视图',
        saveAsFailed: '另存为失败',
        copySuffix: '（副本）',
        deleteTitle: '确认删除',
        deleteConfirmContent: '确定要删除问题 "{title}" 吗？',
        deleteSuccess: '问题删除成功',
        deleteFailed: '问题删除失败',
        personalDefaultSaved: '已设为个人默认显示',
        personalDefaultFailed: '保存个人默认失败',
        groupCfUnsupported: '该自定义字段类型不支持分组，已回退为不分组',
        savedGroupCfUnsupported: '已保存的分组自定义字段类型不受支持，已回退为不分组',
        swimlaneCfUnsupported: '该自定义字段类型不支持泳道，已回退为无泳道',
        savedSwimlaneCfUnsupported: '已保存的泳道自定义字段类型不受支持，已回退为无泳道',
        groupSyncFailed: '分组已切换，但同步到已保存视图失败',
        exportedCsv: '已导出 CSV',
        exportFailed: '导出失败',
        templateDownloadFailed: '模板下载失败',
        importFailed: '导入失败',
        noneCycle: '无 Cycle'
      },
      blockedBy: '被阻塞 {count}',
      blocks: '阻塞 {count}',
      noneCycle: '无 Cycle'
    },
    issueForm: {
      createTitle: '创建问题',
      editTitle: '编辑问题',
      saveChanges: '保存更改',
      propertySettings: '属性设置',
      type: '类型',
      priority: '优先级',
      linkedProject: '关联项目',
      selectProjectOptional: '选择项目（可选）',
      selectType: '选择类型',
      selectPriority: '选择优先级',
      advanced: '高级选项',
      linkedTaskId: '关联任务 ID',
      enterTaskId: '输入任务 ID',
      linkedRequirementId: '关联需求 ID',
      enterRequirementId: '输入需求 ID',
      assigneeId: '负责人 ID',
      enterAssigneeId: '输入负责人 ID',
      status: '状态',
      assignee: '指派人',
      cycle: '冲刺',
      start: '开始',
      dueDate: '截止日期',
      watchers: '关注者',
      reporter: '报告人',
      unassigned: '未分配',
      unset: '未设置',
      noWatchers: '暂无关注者',
      selectAssignees: '选择指派人（首位=负责人）',
      selectCycle: '选择冲刺',
      selectReporter: '选择报告人'
    },
    issueComposer: {
      backToList: '返回列表 (Esc)',
      backToDetail: '返回详情 (Esc)',
      unsaved: '未保存',
      useTemplate: '使用模板',
      useTemplateHint: '从模板创建问题',
      previewMode: '预览模式',
      editMode: '编辑模式',
      titlePlaceholder: '输入问题标题...',
      description: '描述',
      markdownHint: '支持 Markdown 语法，+ 引用其他资源',
      descriptionPlaceholder: '详细描述这个问题...',
      attachments: '附件',
      addAttachment: '添加附件',
      preview: '预览',
      noDescription: '暂无描述内容',
      exitTitle: '确认退出',
      exitContent: '你有未保存的更改，确定要退出吗？',
      exitDiscard: '放弃更改',
      exitKeep: '继续编辑'
    },
    issueTemplate: {
      intro: '选择一个模板来快速创建规范的问题（工作区模板）',
      empty: '暂无可用模板',
      footerHint: '提示：你也可以不使用模板，直接创建空白问题',
      cancel: '取消',
      fieldTitle: '标题',
      fieldDescription: '描述',
      contentPreview: '内容预览',
      previewHint: '以下内容将填充到问题描述中：'
    },
    markdownEditor: {
      boldTitle: '粗体 (Ctrl+B)',
      italicTitle: '斜体 (Ctrl+I)',
      inlineCodeTitle: '行内代码 (Ctrl+`)',
      codeBlockTitle: '代码块',
      linkTitle: '链接',
      bulletListTitle: '无序列表',
      quoteTitle: '引用',
      headingTitle: '标题',
      taskListTitle: '任务列表',
      edit: '编辑',
      preview: '预览',
      syntaxHelp: '语法帮助',
      syntaxTitle: 'Markdown 语法',
      glossBold: '粗体',
      glossItalic: '斜体',
      glossInlineCode: '行内代码',
      glossQuote: '引用块',
      glossMention: '提及用户',
      glossIssueRef: '引用问题',
      defaultPlaceholder: '支持 Markdown 语法...',
      emptyPreview: '输入内容后预览',
      characters: '{n} 字符',
      footerHint: '支持 Markdown 语法 • Ctrl+Enter 快速提交'
    },
    issueType: {
      bug: '缺陷',
      feature: '功能',
      question: '问题',
      feedback: '反馈',
      incident: '事件',
      improvement: '改进'
    },
    issueStatus: {
      open: '待办',
      in_progress: '进行中',
      feedback: '等待反馈',
      resolved: '已解决',
      closed: '已关闭',
      rejected: '已拒绝'
    },
    issuePriority: {
      low: '低',
      medium: '中',
      high: '高',
      critical: '紧急'
    },
    sla: {
      runDue: '立即执行到期检查',
      help: '支持「状态停留」和「首次响应」两种度量。默认按墙钟分钟；启用营业时段后按营业分钟。首次响应：不是创建者的第一条评论即满足，指派负责人不算。结束状态留空时，进入已解决、已关闭或已拒绝即满足。进入暂停状态时不计时，离开后按剩余时间继续。没有内置定时任务（cron）。请用外部调度调用 POST /api/sla/run-due。',
      businessHours: '营业时段',
      metricPlaceholder: '度量',
      startPlaceholder: '开始状态',
      stopPlaceholder: '结束状态（可空，空则视为关闭类）',
      pausePlaceholder: '暂停计时的状态（可空）',
      targetPlaceholder: '目标分钟',
      windowPlaceholder: '强制营业时段（可选）',
      pauseHint: '进入这些状态时暂停计时；离开后按剩余时间继续。例如：等待反馈。',
      priorityRule: '结束优先于暂停，暂停优先于开始。',
      firstResponseNote: '首次响应：不是创建者的第一条评论算首次响应；指派负责人不算。',
      closingStatuses: '关闭类',
      startPrefix: '开始',
      stopPrefix: '结束',
      pausePrefix: '暂停',
      targetWorkspace: '本工作区营业时段',
      targetPolicy: '指定策略的日历',
      choosePolicy: '请选择策略',
      defaultPolicyName: '进行中停留',
      nameRequired: '请填写名称和开始状态',
      holidayIntro:
        '精选静态包（中国、美国、欧盟、英国 · 2026/2027）。预览后应用到本工作区营业例外，或某个策略的日历。同日以包为准覆盖；包外例外保留。无外网同步。',
      hoursIntro:
        '工作区使用 IANA 时区，并配置每周的营业窗口。启用后，到期时间和暂停后的剩余时间按营业分钟计算；关闭后按墙钟计算。保存后会重算正在计时和已暂停的策略。每天最多 2 段，格式 09:00-12:00,13:00-18:00。',
      hoursEnabled: '启用营业时段',
      weekdayPreset: '工作日 09:00–18:00',
      hoursWindowPlaceholder: '空=非营业；例 09:00-12:00,13:00-18:00',
      exceptionDays:
        '例外日按本地日历。关闭日整天不计入营业分钟。强制营业会覆盖当天的周窗口；没有填写窗口时，用周一的窗口，否则用 09:00–18:00。最多 366 天。',
      noExceptions: '暂无例外日',
      defaultWindow: '默认窗',
      addException: '添加例外',
      removeException: '删除',
      weekday: {
        mon: '周一',
        tue: '周二',
        wed: '周三',
        thu: '周四',
        fri: '周五',
        sat: '周六',
        sun: '周日'
      },
      saveHours: '保存营业时段',
      hoursSaved: '营业时段已保存，正在计时和已暂停的策略已重算。',
      packAdded: '新增',
      packReplaced: '覆盖',
      regionCN: '中国 CN',
      regionUS: '美国 US',
      regionEU: '欧盟 EU',
      regionUK: '英国 UK',
      metric: {
        time_in_status: '状态停留',
        first_response: '首次响应'
      },
      exception: {
        closed: '关闭日',
        forced_open: '强制营业'
      },
      policies: 'SLA 策略',
      refresh: '刷新',
      newPolicy: '新建策略',
      name: '名称',
      startStopStatuses: '启停状态',
      enabled: '启用',
      actions: '操作',
      minutes: '{n} 分钟',
      holidayPack: '假日包',
      holidayPacks: '假日包',
      clearOverride: '清除覆盖',
      delete: '删除',
      notifyAssignee: '通知负责人',
      notifyWatchers: '通知关注者',
      calendarOverride: '日历覆盖',
      calendarOverrideHint: '关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承',
      timezoneOverride: '时区覆盖',
      inheritWorkspace: '（继承工作区）',
      exceptionOverride: '例外覆盖（填写则整表替换 WS 例外；留空=继承）',
      create: '创建',
      allRegions: '全部地区',
      allYears: '全部年份',
      region: '地区',
      year: '年份',
      packTitle: '国家/地区假日包（一键合并例外日）',
      preview: '预览',
      applyPack: '确认应用',
      packPreviewSummary: '变更：+{added} / 覆盖 {replaced} / 保留 {kept} （{before} → {after}）'
    },
    issueTrash: {
      title: '回收站',
      backToList: '返回列表',
      refresh: '刷新',
      empty: '回收站为空',
      key: '编号',
      issueTitle: '标题',
      status: '状态',
      priority: '优先级',
      updatedAt: '更新时间',
      actions: '操作',
      restore: '恢复'
    },
    insights: {
      subtitle: '工作区效能摘要。多个标签取并集，可查看我的报表和团队报表，也可打开定期摘要。',
      exportCsv: '导出 CSV',
      exportedCsv: '已导出 CSV',
      digest: '效能摘要',
      digestDefault: '已设为摘要的默认报表',
      digestHint: '默认关闭。打开后，由外部定时调用写入收件箱和邮件。',
      cycleActive: ' · 进行中',
      estimatePoints: '估点合计',
      createdCompleted: '近 14 日 · 创建与完成',
      velocityTitle: '估点速度 · 近 14 日完成点数',
      points: '点数'
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

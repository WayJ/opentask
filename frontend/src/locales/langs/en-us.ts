const local: App.I18n.Schema = {
  system: {
    title: 'OpenTask',
    updateTitle: 'System Version Update Notification',
    updateContent: 'A new version of the system has been detected. Do you want to refresh the page immediately?',
    updateConfirm: 'Refresh immediately',
    updateCancel: 'Later'
  },
  common: {
    action: 'Action',
    add: 'Add',
    addSuccess: 'Add Success',
    backToHome: 'Back to home',
    batchDelete: 'Batch Delete',
    cancel: 'Cancel',
    close: 'Close',
    check: 'Check',
    selectAll: 'Select All',
    expandColumn: 'Expand Column',
    columnSetting: 'Column Setting',
    config: 'Config',
    confirm: 'Confirm',
    delete: 'Delete',
    deleteSuccess: 'Delete Success',
    confirmDelete: 'Are you sure you want to delete?',
    edit: 'Edit',
    warning: 'Warning',
    error: 'Error',
    index: 'Index',
    keywordSearch: 'Please enter keyword',
    logout: 'Logout',
    logoutConfirm: 'Are you sure you want to log out?',
    profile: 'Profile',
    lookForward: 'Coming soon',
    modify: 'Modify',
    modifySuccess: 'Modify Success',
    noData: 'No Data',
    operate: 'Operate',
    pleaseCheckValue: 'Please check whether the value is valid',
    refresh: 'Refresh',
    reset: 'Reset',
    search: 'Search',
    switch: 'Switch',
    tip: 'Tip',
    trigger: 'Trigger',
    update: 'Update',
    updateSuccess: 'Update Success',
    userCenter: 'User Center',
    yesOrNo: {
      yes: 'Yes',
      no: 'No'
    },
    commandPalette: {
      placeholder: 'Type a command or search…',
      groupActions: 'Actions',
      groupMenus: 'Menus',
      groupIssues: 'Issues',
      groupProjects: 'Projects',
      groupCycles: 'Cycles',
      groupViews: 'Views',
      searching: 'Searching…',
      navIssues: 'Issues',
      navCreateIssue: 'Create Issue',
      navCreateFromTemplate: 'Create from template',
      navProjects: 'Projects',
      actionAddLabel: 'Add label…',
      navLabels: 'Labels',
      navCycles: 'Cycles settings',
      navInitiatives: 'Initiatives',
      navTriage: 'Triage',
      navSearch: 'Search…',
      navInbox: 'Inbox'
    }
  },
  request: {
    logout: 'Logout user after request failed',
    logoutMsg: 'User status is invalid, please log in again',
    logoutWithModal: 'Pop up modal after request failed and then log out user',
    logoutWithModalMsg: 'User status is invalid, please log in again',
    refreshToken: 'The requested token has expired, refresh the token',
    tokenExpired: 'The requested token has expired'
  },
  theme: {
    themeDrawerTitle: 'Theme Configuration',
    tabs: {
      appearance: 'Appearance',
      layout: 'Layout',
      general: 'General',
      preset: 'Preset'
    },
    appearance: {
      themeSchema: {
        title: 'Theme Schema',
        light: 'Light',
        dark: 'Dark',
        auto: 'Follow System'
      },
      grayscale: 'Grayscale',
      colourWeakness: 'Colour Weakness',
      themeColor: {
        title: 'Theme Color',
        primary: 'Primary',
        info: 'Info',
        success: 'Success',
        warning: 'Warning',
        error: 'Error',
        followPrimary: 'Follow Primary'
      },
      themeRadius: {
        title: 'Theme Radius'
      },
      recommendColor: 'Apply Recommended Color Algorithm',
      recommendColorDesc: 'The recommended color algorithm refers to',
      preset: {
        title: 'Theme Presets',
        apply: 'Apply',
        applySuccess: 'Preset applied successfully',
        default: {
          name: 'Default Preset',
          desc: 'Default theme preset with balanced settings'
        },
        dark: {
          name: 'Dark Preset',
          desc: 'Dark theme preset for night time usage'
        },
        compact: {
          name: 'Compact Preset',
          desc: 'Compact layout preset for small screens'
        },
        azir: {
          name: "Azir's Preset",
          desc: 'It is a cold and elegant preset that Azir likes'
        }
      }
    },
    layout: {
      layoutMode: {
        title: 'Layout Mode',
        vertical: 'Vertical Mode',
        horizontal: 'Horizontal Mode',
        'vertical-mix': 'Vertical Mix Mode',
        'vertical-hybrid-header-first': 'Left Hybrid Header-First',
        'top-hybrid-sidebar-first': 'Top-Hybrid Sidebar-First',
        'top-hybrid-header-first': 'Top-Hybrid Header-First',
        vertical_detail: 'Vertical menu layout, with the menu on the left and content on the right.',
        'vertical-mix_detail':
          'Vertical mix-menu layout, with the primary menu on the dark left side and the secondary menu on the lighter left side.',
        'vertical-hybrid-header-first_detail':
          'Left hybrid layout, with the primary menu at the top, the secondary menu on the dark left side, and the tertiary menu on the lighter left side.',
        horizontal_detail: 'Horizontal menu layout, with the menu at the top and content below.',
        'top-hybrid-sidebar-first_detail':
          'Top hybrid layout, with the primary menu on the left and the secondary menu at the top.',
        'top-hybrid-header-first_detail':
          'Top hybrid layout, with the primary menu at the top and the secondary menu on the left.'
      },
      tab: {
        title: 'Tab Settings',
        visible: 'Tab Visible',
        cache: 'Tag Bar Info Cache',
        cacheTip: 'One-click to open/close global keepalive',
        height: 'Tab Height',
        mode: {
          title: 'Tab Mode',
          slider: 'Slider',
          chrome: 'Chrome',
          button: 'Button'
        },
        closeByMiddleClick: 'Close Tab by Middle Click',
        closeByMiddleClickTip: 'Enable closing tabs by clicking with the middle mouse button'
      },
      header: {
        title: 'Header Settings',
        height: 'Header Height',
        breadcrumb: {
          visible: 'Breadcrumb Visible',
          showIcon: 'Breadcrumb Icon Visible'
        }
      },
      sider: {
        title: 'Sider Settings',
        inverted: 'Dark Sider',
        width: 'Sider Width',
        collapsedWidth: 'Sider Collapsed Width',
        mixWidth: 'Mix Sider Width',
        mixCollapsedWidth: 'Mix Sider Collapse Width',
        mixChildMenuWidth: 'Mix Child Menu Width',
        autoSelectFirstMenu: 'Auto Select First Submenu',
        autoSelectFirstMenuTip:
          'When a first-level menu is clicked, the first submenu is automatically selected and navigated to the deepest level'
      },
      footer: {
        title: 'Footer Settings',
        visible: 'Footer Visible',
        fixed: 'Fixed Footer',
        height: 'Footer Height',
        right: 'Right Footer'
      },
      content: {
        title: 'Content Area Settings',
        scrollMode: {
          title: 'Scroll Mode',
          tip: 'The theme scroll only scrolls the main part, the outer scroll can carry the header and footer together',
          wrapper: 'Wrapper',
          content: 'Content'
        },
        page: {
          animate: 'Page Animate',
          mode: {
            title: 'Page Animate Mode',
            fade: 'Fade',
            'fade-slide': 'Slide',
            'fade-bottom': 'Fade Zoom',
            'fade-scale': 'Fade Scale',
            'zoom-fade': 'Zoom Fade',
            'zoom-out': 'Zoom Out',
            none: 'None'
          }
        },
        fixedHeaderAndTab: 'Fixed Header And Tab'
      }
    },
    general: {
      title: 'General Settings',
      watermark: {
        title: 'Watermark Settings',
        visible: 'Watermark Full Screen Visible',
        text: 'Custom Watermark Text',
        enableUserName: 'Enable User Name Watermark',
        enableTime: 'Show Current Time',
        timeFormat: 'Time Format'
      },
      multilingual: {
        title: 'Multilingual Settings',
        visible: 'Display multilingual button'
      },
      globalSearch: {
        title: 'Global Search Settings',
        visible: 'Display GlobalSearch button'
      }
    },
    configOperation: {
      copyConfig: 'Copy Config',
      copySuccessMsg: 'Copy Success, Please replace the variable "themeSettings" in "src/theme/settings.ts"',
      resetConfig: 'Reset Config',
      resetSuccessMsg: 'Reset Success'
    }
  },
  route: {
    oauth2: 'OAuth2 Authorization',
    'oauth2-install': 'Install Consent',
    profile: 'Profile',
    profile_userinfo: 'User Profile',
    login: 'Login',
    403: 'No Permission',
    404: 'Page Not Found',
    500: 'Server Error',
    'iframe-page': 'Iframe',
    home: 'Home',
    workspace: 'Workspace',
    workspace_members: 'Members',
    invite: 'Invite',
    workspace_labels: 'Labels',
    settings: 'Settings',
    settings_webhooks: 'Webhooks',
    settings_sla: 'SLA',
    settings_recurrences: 'Recurring issues',
    settings_forms: 'Public Forms',
    'public-form': 'Public Form',
    'public-request-status': 'Request status',
    settings_notifications: 'Notifications',
    workspace_automations: 'Automations',
    'workspace_custom-fields': 'Custom Fields',
    'workspace_issue-templates': 'Issue Templates',
    'workspace_project-templates': 'Project Templates',
    workspace_cycles: 'Cycles',
    inbox: 'Inbox',
    activity: 'Activity',
    insights: 'Insights',
    search: 'Search',
    customers: 'Customers',
    customers_detail: 'Customer',
    requests: 'Requests',
    requests_detail: 'Request',
    initiatives: 'Initiatives',
    initiatives_detail: 'Initiative',
    triage: 'Triage',
    dashboard: 'Dev Dashboard',
    projects: 'Projects',
    'projects-detail': 'Project Detail',
    requirements: 'Requirements',
    'requirements-detail': 'Requirement Detail',
    'knowledge-base': 'Knowledge Base',
    'knowledge-base_list': 'Knowledge Base List',
    'knowledge-base_knowledges': 'Knowledge Documents',
    knowledge: 'Knowledge',
    knowledge_list: 'Knowledge List',
    knowledge_detail: 'Knowledge Detail',
    knowledge_edit: 'Edit Knowledge',
    knowledge_edit_git: 'Git Editor',
    'knowledge-category': 'Knowledge Category',
    'knowledge-category_manage': 'Category Management',
    'knowledge-base_manage': 'Knowledge Base Management',
    'knowledge-base_manage_category': 'Category Management',
    'knowledge-base_manage_tag': 'Tag Management',
    'knowledge-base_manage_tag_manage': 'Tag List',
    'knowledge-base_knowledge': 'Knowledge Documents',
    'knowledge-base_knowledge_list': 'Knowledge Document List',
    'knowledge-base_knowledge_detail': 'Knowledge Document Detail',
    'knowledge-base_knowledge_edit': 'Edit Knowledge Document',
    'knowledge-base_knowledge_edit_git': 'Git Editor',
    manage: 'System Manage',
    manage_user: 'User Manage',
    manage_oauth2: 'OAuth Clients',
    manage_dept: 'Department Manage',
    'manage_user-detail': 'User Detail',
    manage_role: 'Role Manage',
    manage_perm: 'Permission Manage',
    workflow: 'Projects',
    workflow_projects: 'Projects',
    'workflow_project-detail': 'Project Detail',
    workflow_requirements: 'Requirements (Legacy)',
    'workflow_requirement-detail': 'Requirement Detail',
    'work-management': 'Work Management',
    'work-management_rd-groups': 'R&D Groups',
    'work-management_rd-groups-create': 'Create R&D Group',
    'work-management_rd-groups-detail': 'R&D Group Detail',
    'work-management_cost-projects': 'Cost Projects',
    'work-management_cost-projects_create': 'Create Cost Project',
    'work-management_cost-projects_detail': 'Cost Project Detail',
    'work-management_cost-projects_list': 'Cost Project List',
    'work-management_work-assignments': 'Work Assignments',
    'work-management_work-assignments_create': 'Create Work Assignment',
    'work-management_work-assignments_detail': 'Work Assignment Detail',
    'work-management_work-assignments_list': 'Work Assignment List',
    'work-management_my-work': 'My Work',
    'work-management_my-work_weekly': 'Weekly View',
    'work-management_my-work_feedback': 'Work Feedback',
    issue: 'Issues',
    issue_create: 'Create Issue',
    issue_detail: 'Issue Detail',
    'issue_detail-new': 'Issue Detail (New Design)',
    issue_list: 'My issues',
    issue_trash: 'Trash',
    'workspace-onboarding': 'Create workspace'
  },
  page: {
    sider: {
      triage: 'Triage',
      triageHint: 'Incoming',
      customers: 'Customers',
      customersHint: 'Requests',
      insights: 'Insights',
      insightsHint: 'Performance',
      activity: 'Activity',
      activityHint: 'Recent'
    },
    shell: {
      export: 'Export',
      import: 'Import',
      createIssue: 'New issue',
      importIssueCsv: 'Import issue CSV',
      issueListTitle: 'Issues',
      list: 'List',
      board: 'Board',
      trash: 'Trash',
      allRequests: 'All requests',
      createCustomer: 'New customer',
      createRequest: 'New request',
      createInitiative: 'New initiative',
      emptyInitiatives: 'No initiatives yet. Create one to group projects.',
      missingInitiativeId: 'Missing initiative id',
      issueForm: 'Issue form',
      publicIssueForms: 'Public issue forms',
      selectIssueTemplate: 'Choose an issue template',
      issueUploadHint: 'Uploads after the issue is created',
      noIssues: 'No issues',
      issueMissing: 'Issue not found',
      addSubIssue: 'Add sub-issue',
      noLinkedIssues: 'No linked issues',
      insightsEmpty: 'No issues yet. Create a few to see distribution and trends.',
      editProjectTemplate: 'Edit project template',
      createProjectTemplate: 'New project template',
      searchIssues: 'Search issue number or title...',
      invites: 'Invites',
      insightsLoadFailed: 'Could not load Insights',
      openIssues: 'Open issues',
      cycleIssues: 'Cycle issues',
      cycleCompleted: 'Completed in cycle',
      noActiveCycle: 'No active cycle',
      cyclesDisabled: 'Cycles are off',
      issueKeyPrefix: 'Issue key',
      weekDoneOpen: 'Completed this week / open issues',
      weekDone: 'Completed this week',
      openShort: 'Open',
      projectTemplate: 'Project template',
      fromProjectTemplate: 'Optional: create from a project template',
      savedAsProjectTemplate: 'Saved as a project template',
      favoriteIssue: 'Issue',
      favoriteInitiative: 'Initiative',
      favoriteProject: 'Project',
      favoriteView: 'View',
      labelsOr: 'Labels (OR)',
      defaultCycle: 'Default cycle'
    },
    issueType: {
      bug: 'Bug',
      feature: 'Feature',
      question: 'Question',
      feedback: 'Feedback',
      incident: 'Incident',
      improvement: 'Improvement'
    },
    issueStatus: {
      open: 'Open',
      in_progress: 'In progress',
      feedback: 'Waiting for feedback',
      resolved: 'Resolved',
      closed: 'Closed',
      rejected: 'Rejected'
    },
    issuePriority: {
      low: 'Low',
      medium: 'Medium',
      high: 'High',
      critical: 'Urgent'
    },
    sla: {
      runDue: 'Run due checks',
      help: 'Two metrics: time in status and first response. Minutes use the wall clock unless business hours are on. First response is the first comment by someone other than the creator. Assignment does not count. If no stop status is set, resolved, closed, or rejected completes it. Pause statuses do not count; the clock resumes with the time left. There is no built-in scheduler (cron). Call POST /api/sla/run-due from an external scheduler.',
      businessHours: 'Business hours',
      metricPlaceholder: 'Metric',
      startPlaceholder: 'Start statuses',
      stopPlaceholder: 'Stop statuses (empty counts as closing statuses)',
      pausePlaceholder: 'Pause statuses (optional)',
      targetPlaceholder: 'Target minutes',
      windowPlaceholder: 'Forced-open windows (optional)',
      pauseHint: 'These statuses pause the clock. It resumes with the time left. For example: waiting for feedback.',
      priorityRule: 'Stop wins over pause, and pause wins over start.',
      firstResponseNote:
        'First response is the first comment by someone other than the creator. Assignment does not count.',
      closingStatuses: 'Closing statuses',
      startPrefix: 'Start',
      stopPrefix: 'Stop',
      pausePrefix: 'Pause',
      targetWorkspace: 'Workspace business hours',
      targetPolicy: 'A policy calendar',
      choosePolicy: 'Choose a policy',
      defaultPolicyName: 'Time in progress',
      nameRequired: 'Enter a name and at least one start status',
      holidayIntro:
        'Static packs for China, the United States, the European Union, and the United Kingdom, 2026 and 2027. Preview, then apply them to this workspace or to a policy calendar. The pack wins on the same date. Other exceptions stay. No network sync.',
      regionCN: 'China CN',
      regionUS: 'United States US',
      regionEU: 'European Union EU',
      regionUK: 'United Kingdom UK',
      metric: {
        time_in_status: 'Time in status',
        first_response: 'First response'
      },
      exception: {
        closed: 'Closed day',
        forced_open: 'Forced open'
      }
    },
    insights: {
      subtitle:
        'Workspace performance summary. Any selected label matches. Personal and team reports. Optional digest.',
      exportCsv: 'Export CSV',
      exportedCsv: 'Exported CSV',
      digest: 'Performance digest',
      digestDefault: 'Set as the default digest report',
      digestHint: 'Off by default. When on, an external scheduler writes to Inbox and email.',
      cycleActive: ' · Active',
      estimatePoints: 'Estimate points',
      createdCompleted: 'Last 14 days · Created and completed',
      velocityTitle: 'Estimate velocity · Completed points, last 14 days',
      points: 'Points'
    },
    search: {
      placeholder: 'Search issues, projects, docs, members, comments…',
      hint: 'Type to search. Or open the command palette with ⌘K.',
      empty: 'No matches',
      groupIssues: 'Issues',
      groupProjects: 'Projects',
      groupDocs: 'Docs',
      groupMembers: 'Members',
      groupComments: 'Comments'
    },
    profile: {
      pwd: {
        title: 'Change password',
        submit: 'Update password',
        hint: 'New password must be at least 8 characters and include letters and numbers. You will need to sign in again.',
        reLoginTip: 'Password changed. Please sign in again with the new password.'
      }
    },
    oauth2: {
      consent: {
        title: 'Authorization Request',
        lead: '"{appName}" is requesting access to your OpenTask data.',
        loading: 'Validating the authorization request...',
        missingParams:
          'The authorization request is missing required parameters. Please restart it from the application.',
        invalidRequest: 'The authorization request is invalid or was rejected.',
        decideFailed: 'Failed to submit the authorization decision. Please retry.',
        scopeTitle: 'This application will be granted the following permissions',
        redirectTitle: 'You will be redirected to',
        approve: 'Allow',
        deny: 'Deny'
      }
    },
    login: {
      common: {
        loginOrRegister: 'Login / Register',
        userNamePlaceholder: 'Please enter user name',
        phonePlaceholder: 'Please enter phone number',
        codePlaceholder: 'Please enter verification code',
        passwordPlaceholder: 'Please enter password',
        confirmPasswordPlaceholder: 'Please enter password again',
        codeLogin: 'Verification code login',
        confirm: 'Confirm',
        back: 'Back',
        validateSuccess: 'Verification passed',
        loginSuccess: 'Login successfully',
        welcomeBack: 'Welcome back, {userName} !',
        pwdError: 'Incorrect account or password'
      },
      pwdLogin: {
        title: 'Password Login',
        rememberMe: 'Remember me',
        forgetPassword: 'Forget password?',
        register: 'Register',
        otherAccountLogin: 'Other Account Login',
        otherLoginMode: 'Other Login Mode',
        dingtalkLogin: 'DingTalk Login',
        superAdmin: 'Super Admin',
        admin: 'Admin',
        user: 'User'
      },
      codeLogin: {
        title: 'Verification Code Login',
        getCode: 'Get verification code',
        reGetCode: 'Reacquire after {time}s',
        sendCodeSuccess: 'Verification code sent successfully',
        imageCodePlaceholder: 'Please enter image verification code'
      },
      register: {
        title: 'Register',
        passwordPlaceholder: 'Please enter password (min 8 chars, letters and numbers)',
        agreement: 'I have read and agree to',
        protocol: '《User Agreement》',
        policy: '《Privacy Policy》'
      },
      resetPwd: {
        title: 'Reset Password'
      },
      bindWeChat: {
        title: 'Bind WeChat'
      },
      changePassword: {
        title: 'Change Initial Password',
        tip: 'Please change your initial password before continuing',
        oldPasswordPlaceholder: 'Please enter the old password',
        newPasswordPlaceholder: 'Please enter the new password (min 8 chars, letters and numbers)',
        pwdRule: 'New password must be at least 8 characters and contain both letters and numbers',
        oldPwdError: 'Incorrect old password',
        changeSuccess: 'Password changed successfully',
        changeFailed: 'Failed to change the password, please try again later'
      },
      dingtalkCallback: {
        title: 'DingTalk Login',
        processing: 'Signing in with DingTalk...',
        success: 'DingTalk login succeeded, entering the system',
        fail: 'DingTalk login failed, please retry or use password login',
        noCode: 'Missing DingTalk auth code, please start DingTalk login from the login page'
      }
    },
    home: {
      branchDesc:
        'For the convenience of everyone in developing and updating the merge, we have streamlined the code of the main branch, only retaining the homepage menu, and the rest of the content has been moved to the example branch for maintenance. The preview address displays the content of the example branch.',
      greeting: 'Good morning, {userName}, today is another day full of vitality!',
      weatherDesc: 'Today is cloudy to clear, 20℃ - 25℃!',
      projectCount: 'Project Count',
      todo: 'Todo',
      message: 'Message',
      downloadCount: 'Download Count',
      registerCount: 'Register Count',
      schedule: 'Work and rest Schedule',
      study: 'Study',
      work: 'Work',
      rest: 'Rest',
      entertainment: 'Entertainment',
      visitCount: 'Visit Count',
      turnover: 'Turnover',
      dealCount: 'Deal Count',
      projectNews: {
        title: 'Project News',
        moreNews: 'More News',
        desc1: 'Open the issue list for the current workspace.',
        desc2: 'Customers and customer requests stay on the customers page.',
        desc3: 'Workspaces, projects, and saved views stay available.',
        desc4: 'Public form /f and status /r open directly.',
        desc5: 'An account with no workspace creates one after login.'
      },
      creativity: 'Creativity'
    }
  },
  form: {
    required: 'Cannot be empty',
    userName: {
      required: 'Please enter user name',
      invalid: 'User name format is incorrect'
    },
    phone: {
      required: 'Please enter phone number',
      invalid: 'Phone number format is incorrect'
    },
    pwd: {
      required: 'Please enter password',
      invalid: 'Password must be at least 8 characters and include both letters and numbers'
    },
    confirmPwd: {
      required: 'Please enter password again',
      invalid: 'The two passwords are inconsistent'
    },
    code: {
      required: 'Please enter verification code',
      invalid: 'Verification code format is incorrect'
    },
    email: {
      required: 'Please enter email',
      invalid: 'Email format is incorrect'
    }
  },
  dropdown: {
    closeCurrent: 'Close Current',
    closeOther: 'Close Other',
    closeLeft: 'Close Left',
    closeRight: 'Close Right',
    closeAll: 'Close All',
    pin: 'Pin Tab',
    unpin: 'Unpin Tab'
  },
  icon: {
    themeConfig: 'Theme Configuration',
    themeSchema: 'Theme Schema',
    lang: 'Switch Language',
    fullscreen: 'Fullscreen',
    fullscreenExit: 'Exit Fullscreen',
    reload: 'Reload Page',
    collapse: 'Collapse Menu',
    expand: 'Expand Menu',
    pin: 'Pin',
    unpin: 'Unpin'
  },
  datatable: {
    itemCount: 'Total {total} items',
    fixed: {
      left: 'Left Fixed',
      right: 'Right Fixed',
      unFixed: 'Unfixed'
    }
  },
  profile: {
    subtitle: 'View and manage your personal information',
    basicInfo: 'Basic Information',
    account: 'Account',
    name: 'Name',
    role: 'Role',
    status: 'Status',
    enabled: 'Enabled',
    disabled: 'Disabled',
    organize: 'Organization',
    position: 'Position',
    userId: 'User ID',
    permissions: 'Permissions',
    totalPermissions: 'Total Permissions',
    noPermissions: 'No permissions',
    themeSettings: 'Theme Settings',
    ssoAccount: 'SSO Account',
    pwd: {
      title: 'Change Password',
      submit: 'Confirm Change',
      hint: 'New password must be at least 8 characters with both letters and numbers; after changing, the current session becomes invalid and you need to sign in again.',
      reLoginTip: 'Password changed. The current session has expired, please sign in again with the new password.'
    },
    dingtalk: {
      title: 'DingTalk Binding',
      bound: 'Bound',
      unbound: 'Not Bound',
      hint: 'Your DingTalk account is bound automatically on the first DingTalk login (QR code / in-app auth). Unbinding is not supported in this phase.'
    }
  }
};

export default local;

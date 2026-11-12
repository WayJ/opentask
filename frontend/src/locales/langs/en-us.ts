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
    issue_edit: 'Edit Issue',
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
    issueList: {
      tabs: {
        myTodos: 'My to-dos',
        open: 'Active',
        closed: 'Closed',
        all: 'All'
      },
      toolbar: {
        views: 'Views',
        saveView: 'Save view',
        saveViewHint: 'Save the current filters as a personal or shared view',
        star: 'Star',
        starHint: 'Star a view (chips on the list toolbar, not the sidebar)',
        pinToSidebar: 'Pin to sidebar',
        unpinFromSidebar: 'Unpin from sidebar',
        pinToSidebarHint: 'Pin to the sidebar favorites (separate from starring)',
        saveAs: 'Save as',
        saveAsHint: 'Duplicate as a personal view (for read-only members of a shared view)',
        filters: 'Filters',
        collapseFilters: 'Collapse filters',
        expandFilters: 'Expand filters',
        syntaxHelp: 'Syntax help',
        syntaxHelpHint: 'View search syntax help',
        display: 'Display',
        sort: 'Sort',
        group: 'Group'
      },
      sortBy: {
        createdAt: 'Created',
        updatedAt: 'Updated',
        priority: 'Priority',
        status: 'Status',
        title: 'Title',
        dueDate: 'Due date'
      },
      sortOrder: {
        desc: 'Descending',
        asc: 'Ascending'
      },
      groupBy: {
        none: 'No grouping',
        status: 'Status',
        assignee: 'Assignee',
        priority: 'Priority',
        type: 'Type',
        label: 'Label'
      },
      computedFieldSuffix: '(computed)',
      computedFieldSuffixReadonly: '(computed, read-only)',
      columns: {
        key: 'Key',
        title: 'Title',
        type: 'Type',
        status: 'Status',
        priority: 'Priority',
        estimate: 'Estimate',
        assignee: 'Assignee',
        reporter: 'Reporter',
        createdAt: 'Created',
        actions: 'Actions'
      },
      actions: {
        view: 'View',
        systemReporter: 'System'
      },
      filters: {
        project: 'Project',
        cycle: 'Cycle',
        type: 'Type',
        priority: 'Priority',
        reset: 'Reset filters'
      },
      syntax: {
        title: 'Search syntax help',
        tipPrefix: 'Tip: you can combine filters, for example',
        assigneeMe: 'Show issues assigned to me',
        isOpen: 'Show only open issues',
        isClosed: 'Show only completed issues',
        isInProgress: 'Show only in-progress issues',
        typeFeature: 'Show only feature issues',
        typeBug: 'Show only bug issues',
        priorityUrgent: 'Show only urgent-priority issues',
        priorityHigh: 'Show only high-priority issues',
        customField: 'Filter by a custom field (cf:key:value also works)'
      },
      views: {
        currentPrefix: 'Current view:',
        favoriteViews: 'Starred views',
        savePersonalTitle: 'Save as personal view',
        saveSharedTitle: 'Save as shared view',
        save: 'Save',
        namePlaceholder: 'View name, e.g. My high-priority bugs',
        shareWithWorkspace: 'Share with the workspace'
      },
      scopeTitle: {
        watching: 'Watching',
        dueSoon: 'Due soon',
        assignedToMe: 'Assigned to me',
        createdByMe: 'Created by me'
      },
      import: {
        downloadTemplate: 'Download template CSV',
        helpBefore:
          'Columns must include title; optional issue_code (updates when it already exists in this workspace). Custom fields use',
        helpAfter:
          'columns (the template already includes this workspace’s fields; separate multi values with commas, and use true/false for booleans). Unknown keys do not block writing the main fields.'
      },
      messages: {
        enterViewName: 'Enter a view name',
        viewSaved: 'View saved',
        sharedViewSaved: 'Shared view saved',
        saveViewFailed: 'Couldn’t save the view',
        viewApplied: 'Applied view “{name}”',
        viewNotFound: 'View not found',
        applyViewFirst: 'Apply a saved view first',
        sharedViewCantStar: 'Shared views can’t be starred. Save as a personal view first',
        starred: 'Starred',
        unstarred: 'Star removed',
        updateStarFailed: 'Couldn’t update the star',
        pinnedToSidebar: 'Pinned to the sidebar',
        unpinnedFromSidebar: 'Unpinned from the sidebar',
        updateSidebarPinFailed: 'Couldn’t update the sidebar pin',
        savedAsPersonal: 'Saved as a personal view',
        saveAsFailed: 'Couldn’t save a copy',
        copySuffix: '(copy)',
        deleteTitle: 'Delete issue',
        deleteConfirmContent: 'Delete issue “{title}”?',
        deleteSuccess: 'Issue deleted',
        deleteFailed: 'Couldn’t delete the issue',
        personalDefaultSaved: 'Saved as your personal default',
        personalDefaultFailed: 'Couldn’t save the personal default',
        groupCfUnsupported: 'This custom field type can’t be used for grouping, so grouping was cleared',
        savedGroupCfUnsupported: 'The saved grouping field type isn’t supported, so grouping was cleared',
        swimlaneCfUnsupported: 'This custom field type can’t be used for swimlanes, so swimlanes were cleared',
        savedSwimlaneCfUnsupported: 'The saved swimlane field type isn’t supported, so swimlanes were cleared',
        groupSyncFailed: 'Grouping changed, but saving it to the view failed',
        exportedCsv: 'Exported CSV',
        exportFailed: 'Couldn’t export',
        templateDownloadFailed: 'Couldn’t download the template',
        importFailed: 'Couldn’t import',
        noneCycle: 'No cycle'
      },
      blockedBy: 'Blocked by {count}',
      blocks: 'Blocks {count}',
      noneCycle: 'No cycle'
    },
    issueForm: {
      createTitle: 'Create issue',
      editTitle: 'Edit issue',
      saveChanges: 'Save changes',
      propertySettings: 'Property settings',
      type: 'Type',
      priority: 'Priority',
      linkedProject: 'Linked project',
      selectProjectOptional: 'Select project (optional)',
      selectType: 'Select type',
      selectPriority: 'Select priority',
      advanced: 'Advanced options',
      linkedTaskId: 'Linked task ID',
      enterTaskId: 'Enter task ID',
      linkedRequirementId: 'Linked requirement ID',
      enterRequirementId: 'Enter requirement ID',
      assigneeId: 'Assignee ID',
      enterAssigneeId: 'Enter assignee ID',
      status: 'Status',
      assignee: 'Assignee',
      cycle: 'Cycle',
      start: 'Start',
      dueDate: 'Due date',
      watchers: 'Watchers',
      reporter: 'Reporter',
      unassigned: 'Unassigned',
      unset: 'Not set',
      noWatchers: 'No watchers',
      selectAssignees: 'Select assignees (first is primary)',
      selectCycle: 'Select cycle',
      selectReporter: 'Select reporter'
    },
    issueComposer: {
      backToList: 'Back to list (Esc)',
      backToDetail: 'Back to detail (Esc)',
      unsaved: 'Unsaved',
      useTemplate: 'Use template',
      useTemplateHint: 'Create an issue from a template',
      previewMode: 'Preview mode',
      editMode: 'Edit mode',
      titlePlaceholder: 'Enter an issue title...',
      description: 'Description',
      markdownHint: 'Markdown supported. + mentions other resources',
      descriptionPlaceholder: 'Describe this issue...',
      attachments: 'Attachments',
      addAttachment: 'Add attachment',
      preview: 'Preview',
      noDescription: 'No description yet',
      exitTitle: 'Leave page',
      exitContent: 'You have unsaved changes. Leave anyway?',
      exitDiscard: 'Discard changes',
      exitKeep: 'Keep editing'
    },
    issueTemplate: {
      intro: 'Pick a template to create a well-formed issue (workspace templates)',
      empty: 'No templates available',
      footerHint: 'Tip: you can skip templates and start a blank issue',
      cancel: 'Cancel',
      fieldTitle: 'Title',
      fieldDescription: 'Description',
      contentPreview: 'Content preview',
      previewHint: 'This text will be filled into the issue description:'
    },
    markdownEditor: {
      boldTitle: 'Bold (Ctrl+B)',
      italicTitle: 'Italic (Ctrl+I)',
      inlineCodeTitle: 'Inline code (Ctrl+`)',
      codeBlockTitle: 'Code block',
      linkTitle: 'Link',
      bulletListTitle: 'Bulleted list',
      quoteTitle: 'Quote',
      headingTitle: 'Heading',
      taskListTitle: 'Task list',
      edit: 'Edit',
      preview: 'Preview',
      syntaxHelp: 'Syntax help',
      syntaxTitle: 'Markdown syntax',
      glossBold: 'Bold',
      glossItalic: 'Italic',
      glossInlineCode: 'Inline code',
      glossQuote: 'Quote block',
      glossMention: 'Mention a user',
      glossIssueRef: 'Reference an issue',
      defaultPlaceholder: 'Markdown supported...',
      emptyPreview: 'Nothing to preview yet',
      characters: '{n} characters',
      footerHint: 'Markdown supported • Ctrl+Enter to submit'
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
      hoursIntro:
        'The workspace uses an IANA time zone and weekly windows. When business hours are on, deadlines and the time left after a pause use business minutes. When they are off, the wall clock is used. Saving recalculates policies that are counting and policies that are paused. At most two ranges a day, written as 09:00-12:00,13:00-18:00.',
      hoursEnabled: 'Use business hours',
      weekdayPreset: 'Weekdays 09:00–18:00',
      hoursWindowPlaceholder: 'Empty means not open. Example: 09:00-12:00,13:00-18:00',
      exceptionDays:
        'Exception days use the local calendar. A closed day counts no business minutes. Forced open replaces that day’s weekly window. If no window is set, Monday’s window is used, otherwise 09:00–18:00. At most 366 days.',
      noExceptions: 'No exception days',
      defaultWindow: 'Default window',
      addException: 'Add exception',
      removeException: 'Remove',
      weekday: {
        mon: 'Mon',
        tue: 'Tue',
        wed: 'Wed',
        thu: 'Thu',
        fri: 'Fri',
        sat: 'Sat',
        sun: 'Sun'
      },
      saveHours: 'Save business hours',
      hoursSaved: 'Business hours saved. Counting and paused policies were recalculated.',
      packAdded: 'Added',
      packReplaced: 'Replaced',
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
      },
      policies: 'SLA policies',
      refresh: 'Refresh',
      newPolicy: 'New policy',
      name: 'Name',
      startStopStatuses: 'Start and stop statuses',
      enabled: 'Enabled',
      actions: 'Actions',
      minutes: '{n} min',
      holidayPack: 'Holiday pack',
      holidayPacks: 'Holiday packs',
      clearOverride: 'Clear override',
      delete: 'Delete',
      notifyAssignee: 'Notify assignee',
      notifyWatchers: 'Notify watchers',
      calendarOverride: 'Calendar override',
      calendarOverrideHint: 'Off inherits the workspace. When on, only filled fields override; the rest still inherit.',
      timezoneOverride: 'Time zone override',
      inheritWorkspace: '(Inherit workspace)',
      exceptionOverride: 'Exception override (a filled table replaces workspace exceptions; empty inherits)',
      create: 'Create',
      allRegions: 'All regions',
      allYears: 'All years',
      region: 'Region',
      year: 'Year',
      packTitle: 'Country and region holiday packs (merge exception days)',
      preview: 'Preview',
      applyPack: 'Apply',
      packPreviewSummary: 'Changes: +{added} / replaced {replaced} / kept {kept} ({before} → {after})'
    },
    issueTrash: {
      title: 'Trash',
      backToList: 'Back to list',
      refresh: 'Refresh',
      empty: 'Trash is empty',
      key: 'Key',
      issueTitle: 'Title',
      status: 'Status',
      priority: 'Priority',
      updatedAt: 'Updated',
      actions: 'Actions',
      restore: 'Restore'
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

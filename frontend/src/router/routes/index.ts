import type { CustomRoute, ElegantConstRoute, ElegantRoute } from '@elegant-router/types';
import { generatedRoutes } from '../elegant/routes';
import { layouts, views } from '../elegant/imports';
import { transformElegantRoutesToVueRoutes } from '../elegant/transform';

/**
 * custom routes
 *
 * @link https://github.com/soybeanjs/elegant-router?tab=readme-ov-file#custom-route
 */
const customRoutes: CustomRoute[] = [
  {
    name: 'workflow',
    path: '/workflow',
    component: 'layout.base',
    meta: {
      title: 'workflow',
      i18nKey: 'route.workflow',
      order: 1
    },
    children: [
      {
        name: 'workflow_project-detail',
        path: '/workflow/project-detail',
        component: 'view.workflow_project-detail',
        meta: {
          title: 'workflow_project-detail',
          i18nKey: 'route.workflow_project-detail',
          hideInMenu: true
        }
      },
      {
        name: 'workflow_projects',
        path: '/workflow/projects',
        component: 'view.workflow_projects',
        meta: {
          title: 'workflow_projects',
          i18nKey: 'route.workflow_projects'
        }
      },
      {
        name: 'workflow_requirement-detail',
        path: '/workflow/requirement-detail',
        component: 'view.workflow_requirement-detail',
        meta: {
          title: 'workflow_requirement-detail',
          i18nKey: 'route.workflow_requirement-detail',
          hideInMenu: true
        }
      },
      {
        name: 'workflow_requirements',
        path: '/workflow/requirements',
        component: 'view.workflow_requirements',
        meta: {
          title: 'workflow_requirements',
          i18nKey: 'route.workflow_requirements',
          hideInMenu: true
        }
      }
    ]
  },
  {
    name: 'work-management',
    path: '/work-management',
    component: 'layout.base',
    meta: {
      title: 'work-management',
      i18nKey: 'route.work-management',
      order: 2
    },
    children: [
      {
        name: 'work-management_rd-groups',
        path: '/work-management/rd-groups',
        component: 'view.work-management_rd-groups_list',
        meta: {
          title: 'rd-groups',
          i18nKey: 'route.work-management_rd-groups',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_rd-groups_create',
        path: '/work-management/rd-groups/create',
        component: 'view.work-management_rd-groups_create',
        meta: {
          title: 'rd-groups_create',
          i18nKey: 'route.work-management_rd-groups_create',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_rd-groups_detail',
        path: '/work-management/rd-groups/:id',
        component: 'view.work-management_rd-groups_detail',
        meta: {
          title: 'rd-groups_detail',
          i18nKey: 'route.work-management_rd-groups_detail',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_cost-projects',
        path: '/work-management/cost-projects',
        component: 'view.work-management_cost-projects_list',
        meta: {
          title: 'cost-projects',
          i18nKey: 'route.work-management_cost-projects',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_cost-projects_create',
        path: '/work-management/cost-projects/create',
        component: 'view.work-management_cost-projects_create',
        meta: {
          title: 'cost-projects_create',
          i18nKey: 'route.work-management_cost-projects_create',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_cost-projects_detail',
        path: '/work-management/cost-projects/:id',
        component: 'view.work-management_cost-projects_detail',
        meta: {
          title: 'cost-projects_detail',
          i18nKey: 'route.work-management_cost-projects_detail',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_work-assignments',
        path: '/work-management/work-assignments',
        component: 'view.work-management_work-assignments_list',
        meta: {
          title: 'work-assignments',
          i18nKey: 'route.work-management_work-assignments',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_work-assignments_create',
        path: '/work-management/work-assignments/create',
        component: 'view.work-management_work-assignments_create',
        meta: {
          title: 'work-assignments_create',
          i18nKey: 'route.work-management_work-assignments_create',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_work-assignments_detail',
        path: '/work-management/work-assignments/:id',
        component: 'view.work-management_work-assignments_detail',
        meta: {
          title: 'work-assignments_detail',
          i18nKey: 'route.work-management_work-assignments_detail',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_my-work_weekly',
        path: '/work-management/my-work/weekly',
        component: 'view.work-management_my-work_weekly',
        meta: {
          title: 'my-work_weekly',
          i18nKey: 'route.work-management_my-work_weekly',
          hideInMenu: true
        }
      },
      {
        name: 'work-management_my-work_feedback',
        path: '/work-management/my-work/feedback/:id',
        component: 'view.work-management_my-work_feedback',
        meta: {
          title: 'my-work_feedback',
          i18nKey: 'route.work-management_my-work_feedback',
          hideInMenu: true
        }
      }
    ]
  },
  {
    name: 'issue',
    path: '/issue',
    component: 'layout.base',
    meta: {
      title: 'issue',
      i18nKey: 'route.issue',
      order: 3
    },
    children: [
      {
        name: 'issue_list',
        path: '/issue/list',
        component: 'view.issue_list',
        meta: {
          title: 'issue_list',
          i18nKey: 'route.issue_list'
        }
      },
      {
        name: 'issue_detail',
        path: '/issue/detail',
        component: 'view.issue_detail',
        meta: {
          title: 'issue_detail',
          i18nKey: 'route.issue_detail',
          hideInMenu: true
        }
      },
      {
        name: 'issue_create',
        path: '/issue/create',
        component: 'view.issue_create',
        meta: {
          title: 'issue_create',
          i18nKey: 'route.issue_create',
          hideInMenu: true
        }
      },
      {
        name: 'issue_edit',
        path: '/issue/edit',
        component: 'view.issue_edit',
        meta: {
          title: 'issue_edit',
          i18nKey: 'route.issue_edit',
          hideInMenu: true
        }
      },
      {
        name: 'issue_collection',
        path: '/issue/collection',
        component: 'view.issue_collection',
        meta: {
          title: 'issue_collection',
          i18nKey: 'route.issue_collection'
        }
      },
      {
        name: 'issue_collection_detail',
        path: '/issue/collection/:id',
        component: 'view.issue_collection_detail',
        meta: {
          title: 'issue_collection_detail',
          i18nKey: 'route.issue_collection_detail',
          hideInMenu: true
        }
      },
      {
        name: 'issue_collection_create',
        path: '/issue/collection/create',
        component: 'view.issue_collection_create',
        meta: {
          title: 'issue_collection_create',
          i18nKey: 'route.issue_collection_create',
          hideInMenu: true
        }
      }
    ]
  }
];

/** create routes when the auth route mode is static */
export function createStaticRoutes() {
  const constantRoutes: ElegantRoute[] = [];

  const authRoutes: ElegantRoute[] = [];

  [...customRoutes, ...generatedRoutes].forEach(item => {
    if (item.meta?.constant) {
      constantRoutes.push(item);
    } else {
      authRoutes.push(item);
    }
  });

  return {
    constantRoutes,
    authRoutes
  };
}

/**
 * Get auth vue routes
 *
 * @param routes Elegant routes
 */
export function getAuthVueRoutes(routes: ElegantConstRoute[]) {
  return transformElegantRoutesToVueRoutes(routes, layouts, views);
}

import { computed, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { defineStore } from 'pinia';
import { useLoading } from '@sa/hooks';
import { fetchGetUserInfo, fetchLogin, fetchWorkspaceList } from '@/service/api';
import { useRouterPush } from '@/hooks/common/router';
import { resolveWorkspaceSelection } from '@/utils/workspace-selection';
import { localStg } from '@/utils/storage';
import { SetupStoreId } from '@/enum';
import { $t } from '@/locales';
import { useRouteStore } from '../route';
import { useTabStore } from '../tab';
import { clearAuthStorage, getToken } from './shared';

export const useAuthStore = defineStore(SetupStoreId.Auth, () => {
  const route = useRoute();
  const authStore = useAuthStore();
  const routeStore = useRouteStore();
  const tabStore = useTabStore();
  const { toLogin, redirectFromLogin } = useRouterPush(false);
  const { loading: loginLoading, startLoading, endLoading } = useLoading();

  const token = ref('');
  const workspaceGate = ref<'pending' | 'ready' | 'onboarding' | 'error'>('pending');
  let workspaceReady: Promise<void> | null = null;
  let pendingSelection: string | null = null;
  let selectionStashed = false;

  function clearWorkspaceSelectionForSession() {
    if (!selectionStashed) {
      pendingSelection = localStg.get('workspaceId') || null;
      selectionStashed = true;
    }
    localStg.remove('workspaceId');
    workspaceReady = null;
    if (workspaceGate.value === 'ready') workspaceGate.value = 'pending';
  }

  const userInfo: Api.Auth.UserInfo = reactive({
    userId: '',
    userName: '',
    roles: [],
    buttons: []
  });

  /** is super role in static route */
  const isStaticSuper = computed(() => {
    const { VITE_AUTH_ROUTE_MODE, VITE_STATIC_SUPER_ROLE } = import.meta.env;

    return VITE_AUTH_ROUTE_MODE === 'static' && userInfo.roles.includes(VITE_STATIC_SUPER_ROLE);
  });

  /**
   * 后端超管（Phase 5 桥接期约定：后端 roles 下发角色 code，admin 即超管，全量 menus/buttons）
   *
   * 菜单/路由过滤与按钮权限码判定统一走该标记，超管不再依赖逐条权限下发
   */
  const isSuperAdmin = computed(() => userInfo.roles.includes('admin'));

  /** Is login */
  const isLogin = computed(() => Boolean(token.value));

  /** Reset auth store */
  async function resetStore() {
    recordUserId();

    clearAuthStorage();
    pendingSelection = null;
    selectionStashed = false;
    workspaceReady = null;
    workspaceGate.value = 'pending';

    authStore.$reset();

    if (!route.meta.constant) {
      await toLogin();
    }

    tabStore.cacheTabs();
    routeStore.resetStore();
  }

  /** Record the user ID of the previous login session Used to compare with the current user ID on next login */
  function recordUserId() {
    if (!userInfo.userId) {
      return;
    }

    // Store current user ID locally for next login comparison
    localStg.set('lastLoginUserId', userInfo.userId);
  }

  /**
   * Check if current login user is different from previous login user If different, clear all tabs
   *
   * @returns {boolean} 是否**换了用户**（换人才需要抑制 redirect 回跳）
   *
   * 说明：清标签页与抑制回跳是两件事，此处只把「抑制回跳」限定在
   * 「确实换了用户」的情形。首次登录（本地无 lastLoginUserId）时清标签页
   * 本就是空操作，若一并抑制回跳，会让 ?redirect= 指向的页面（如 OAuth2
   * 授权同意页）被丢弃——授权请求就此丢失。
   */
  function checkTabClear(): boolean {
    if (!userInfo.userId) {
      return false;
    }

    const lastLoginUserId = localStg.get('lastLoginUserId');

    // 换了用户才需要抑制回跳（避免带着上一个用户的上下文跳回目标页）
    const switchedUser = Boolean(lastLoginUserId) && lastLoginUserId !== userInfo.userId;

    // Clear all tabs if current user is different from previous user
    if (!lastLoginUserId || lastLoginUserId !== userInfo.userId) {
      localStg.remove('globalTabs');
      tabStore.clearTabs();

      localStg.remove('lastLoginUserId');
    }

    return switchedUser;
  }

  /**
   * Login
   *
   * @param userName User name
   * @param password Password
   * @param [redirect=true] Whether to redirect after login. Default is `true`
   * @returns 登录结果；`mustChangePassword` 为 true 时表示签发的是受限 token，
   *          需要由调用方跳转改密模块，未拉取用户信息、未跳转首页
   */
  async function login(userName: string, password: string, redirect = true): Promise<{ mustChangePassword: boolean }> {
    startLoading();
    clearWorkspaceSelectionForSession();

    const { data: loginToken, error } = await fetchLogin(userName, password);

    if (!error) {
      // 受限 token（pwd_change scope）：只写 storage 供改密接口携带，
      // 不调 getUserInfo（会 403）、不跳首页，由登录页切到改密模块
      if (loginToken.mustChangePassword) {
        localStg.set('token', loginToken.token);
        localStg.set('refreshToken', loginToken.refreshToken);

        endLoading();

        return { mustChangePassword: true };
      }

      const pass = await loginByToken(loginToken);

      if (pass) {
        // Check if the tab needs to be cleared
        const isClear = checkTabClear();
        let needRedirect = redirect;

        if (isClear) {
          // If the tab needs to be cleared,it means we don't need to redirect.
          needRedirect = false;
        }
        await redirectFromLogin(needRedirect);

        window.$notification?.success({
          title: $t('page.login.common.loginSuccess'),
          content: $t('page.login.common.welcomeBack', { userName: userInfo.userName }),
          duration: 4500
        });
      }
    } else {
      resetStore();
    }

    endLoading();

    return { mustChangePassword: false };
  }

  async function resolveWorkspaceForSession() {
    const stored = pendingSelection;
    const { data, error } = await fetchWorkspaceList();
    if (error) {
      localStg.remove('workspaceId');
      workspaceGate.value = 'error';
      return;
    }
    selectionStashed = false;
    pendingSelection = null;
    const resolved = resolveWorkspaceSelection(stored, data ?? []);
    if (resolved.workspaceId) localStg.set('workspaceId', resolved.workspaceId);
    else localStg.remove('workspaceId');
    workspaceGate.value = resolved.gate;
  }

  async function ensureWorkspaceResolved(force = false) {
    if (force) workspaceReady = null;
    if (!workspaceReady) workspaceReady = resolveWorkspaceForSession();
    await workspaceReady;
  }

  function markWorkspaceReady(workspaceId: string) {
    localStg.set('workspaceId', workspaceId);
    workspaceGate.value = 'ready';
    workspaceReady = Promise.resolve();
    selectionStashed = false;
    pendingSelection = null;
  }

  async function loginByToken(loginToken: Api.Auth.LoginToken) {
    // Drop any previous account's workspace before the first authenticated call.
    clearWorkspaceSelectionForSession();
    localStg.set('token', loginToken.token);
    localStg.set('refreshToken', loginToken.refreshToken);
    token.value = loginToken.token;
    await ensureWorkspaceResolved();

    const pass = await getUserInfo();

    if (pass) {
      return true;
    }

    return false;
  }

  async function getUserInfo() {
    const { data: info, error } = await fetchGetUserInfo();

    if (!error) {
      // update store
      Object.assign(userInfo, info);

      return true;
    }

    return false;
  }

  async function initUserInfo() {
    const maybeToken = getToken();

    if (maybeToken) {
      token.value = maybeToken;
      clearWorkspaceSelectionForSession();
      await ensureWorkspaceResolved();
      const pass = await getUserInfo();

      if (!pass) {
        resetStore();
      }
    }
  }

  return {
    token,
    userInfo,
    isStaticSuper,
    isSuperAdmin,
    isLogin,
    loginLoading,
    resetStore,
    login,
    loginByToken,
    initUserInfo,
    workspaceGate,
    ensureWorkspaceResolved,
    markWorkspaceReady
  };
});

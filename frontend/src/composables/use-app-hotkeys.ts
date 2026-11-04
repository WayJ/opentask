import { useRouter } from 'vue-router';
import { useEventListener } from '@vueuse/core';
import { issueApi } from '@/service/api/issue';
import { useAuthStore } from '@/store/modules/auth';
import { ignoreWhenEditable, isModK } from '@/utils/hotkeys';
import { resolveIssueHotkeyAction } from '@/utils/issue-hotkeys';
import { useCommandPalette } from './use-command-palette';
import { useIssueFocus } from './use-issue-focus';
import { useIssueFieldPickers } from './use-issue-field-pickers';
import { useIssueListViewMode } from './use-issue-list-view-mode';
import { useIssueSelection } from './use-issue-selection';

/**
 * Global app hotkeys:
 * - Meta/Ctrl+K toggles palette (allowed in inputs)
 * - Esc closes palette
 * - C / A / S / P / I / L (ignoreWhenEditable; blocked when palette open)
 * - Meta/Ctrl+B toggles Board↔List on /issue/list
 */
export function useAppHotkeys() {
  const palette = useCommandPalette();
  const focus = useIssueFocus();
  const pickers = useIssueFieldPickers();
  const listView = useIssueListViewMode();
  const selection = useIssueSelection();
  const router = useRouter();
  const authStore = useAuthStore();

  useEventListener(window, 'keydown', (event: KeyboardEvent) => {
    if (isModK(event)) {
      event.preventDefault();
      palette.toggle();
      return;
    }

    if (event.key === 'Escape' && palette.isOpen.value) {
      event.preventDefault();
      palette.close();
      return;
    }

    if (event.key === 'Escape' && pickers.activePicker.value) {
      event.preventDefault();
      pickers.closePicker();
      return;
    }

    if (event.key === 'Escape' && selection.hasSelection.value && !ignoreWhenEditable(event.target)) {
      event.preventDefault();
      selection.clear();
      return;
    }

    const orderedIds = selection.getIssueOrder();

    const action = resolveIssueHotkeyAction({
      key: event.key,
      metaKey: event.metaKey,
      ctrlKey: event.ctrlKey,
      altKey: event.altKey,
      shiftKey: event.shiftKey,
      paletteOpen: palette.isOpen.value,
      editable: ignoreWhenEditable(event.target),
      hasFocusedIssue: Boolean(focus.focusedIssueId.value),
      onIssueListRoute: router.currentRoute.value.path === '/issue/list',
      hasSelection: selection.hasSelection.value
    });

    if (!action) return;

    event.preventDefault();

    switch (action.type) {
      case 'create':
        router.push('/issue/create');
        break;
      case 'create_from_template':
        router.push({ path: '/issue/create', query: { pickTemplate: '1' } });
        break;
      case 'status':
        pickers.openStatus();
        break;
      case 'assignee':
        pickers.openAssignee();
        break;
      case 'priority':
        pickers.openPriority();
        break;
      case 'labels':
        pickers.openLabels();
        break;
      case 'assign_me': {
        const issueId = focus.focusedIssueId.value;
        const userId = authStore.userInfo?.userId;
        if (!issueId || !userId) {
          window.$message?.info?.('请先聚焦 Issue 并确保已登录');
          break;
        }
        issueApi
          .updateAssignee(issueId, userId)
          .then(({ error }) => {
            if (error) {
              window.$message?.error?.(error.message || '指派失败');
              return;
            }
            window.$message?.success?.('已指派给我');
          })
          .catch(() => {
            window.$message?.error?.('指派失败');
          });
        break;
      }
      case 'toggle_view':
        listView.toggle();
        break;
      case 'toggle_select': {
        const id = focus.focusedIssueId.value;
        if (id) selection.toggle(id);
        break;
      }
      case 'range_select': {
        const id = focus.focusedIssueId.value;
        if (id) selection.selectRange(id, orderedIds);
        break;
      }
      case 'clear_selection':
        selection.clear();
        break;
      default:
        break;
    }
  });
}

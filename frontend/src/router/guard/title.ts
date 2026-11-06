import type { Router } from 'vue-router';
import { useTitle } from '@vueuse/core';
import { formatDocumentTitle } from '@/utils/document-title';
import { $t } from '@/locales';

export function createDocumentTitleGuard(router: Router) {
  router.afterEach(to => {
    const { i18nKey, title } = to.meta;

    const pageTitle = i18nKey ? $t(i18nKey) : title;

    useTitle(formatDocumentTitle(pageTitle));
  });
}

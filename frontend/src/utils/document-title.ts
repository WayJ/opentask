export const PRODUCT_TITLE = 'OpenTask';

/** Page title keeps the product name across navigation and locale changes. */
export function formatDocumentTitle(pageTitle?: string | null): string {
  const page = (pageTitle ?? '').trim();
  if (!page || page === PRODUCT_TITLE) return PRODUCT_TITLE;
  return `${page} - ${PRODUCT_TITLE}`;
}

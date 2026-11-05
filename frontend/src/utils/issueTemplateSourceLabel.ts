/** E82: Issue template source label + seed confirm copy. */

export function issueTemplateSourceLabel(source: string | null | undefined): string {
  return source === 'seed' ? '内置' : '自定义';
}

export function issueTemplateSeedConfirmText(): string {
  return '将补齐缺失的内置 Issue 模板（已有 seedKey 不覆盖）。继续？';
}

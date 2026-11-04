import { request } from '../request';

export const FORM_FIELD_TYPES = [
  'title',
  'description',
  'priority',
  'labels',
  'assignee',
  'custom_field',
  'customer_id'
] as const;

export type FormFieldType = (typeof FORM_FIELD_TYPES)[number];

export interface FormFieldDef {
  key: string;
  type: FormFieldType | string;
  label: string;
  required?: boolean;
  help?: string;
  customFieldId?: string;
}

export interface IssueFormRow {
  id: string;
  workspaceId: string;
  name: string;
  slug?: string | null;
  token: string;
  description?: string | null;
  enabled: boolean;
  fields: FormFieldDef[];
  createCustomerRequest: boolean;
  createdBy?: string | null;
  publicPath?: string;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface IssueFormListResult {
  rows: IssueFormRow[];
  total: number;
}

export interface PublicFormSchema {
  name: string;
  description?: string | null;
  fields: FormFieldDef[];
  enabled: boolean;
}

export function fetchForms() {
  return request<IssueFormListResult>({ url: '/api/forms', method: 'get' });
}

export function fetchForm(id: string) {
  return request<IssueFormRow>({ url: `/api/forms/${id}`, method: 'get' });
}

export function fetchCreateForm(body: {
  name: string;
  fields: FormFieldDef[];
  description?: string;
  slug?: string;
  enabled?: boolean;
  createCustomerRequest?: boolean;
}) {
  return request<IssueFormRow>({ url: '/api/forms', method: 'post', data: body });
}

export function fetchUpdateForm(
  id: string,
  body: Partial<{
    name: string;
    fields: FormFieldDef[];
    description: string | null;
    clearDescription: boolean;
    slug: string | null;
    setSlug: boolean;
    enabled: boolean;
    createCustomerRequest: boolean;
  }>
) {
  return request<IssueFormRow>({ url: `/api/forms/${id}`, method: 'patch', data: body });
}

export function fetchDeleteForm(id: string) {
  return request<{ id: string }>({ url: `/api/forms/${id}`, method: 'delete' });
}

export function fetchRegenerateFormToken(id: string) {
  return request<IssueFormRow>({ url: `/api/forms/${id}/regenerate-token`, method: 'post' });
}

/** Public (no auth) — use bare fetch to avoid injecting workspace headers requirements. */
export async function fetchPublicFormSchema(token: string): Promise<PublicFormSchema> {
  const base = import.meta.env.VITE_SERVICE_BASE_URL || '';
  const resp = await fetch(`${base}/api/public/forms/${encodeURIComponent(token)}`);
  const json = await resp.json();
  if (!resp.ok) {
    throw new Error(json?.detail || json?.message || '表单不可用');
  }
  return (json.data || json) as PublicFormSchema;
}

export async function submitPublicForm(
  token: string,
  values: Record<string, unknown>
): Promise<{ issueId: string; issueCode: string; title: string; requestId?: string | null }> {
  const base = import.meta.env.VITE_SERVICE_BASE_URL || '';
  const resp = await fetch(`${base}/api/public/forms/${encodeURIComponent(token)}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ values })
  });
  const json = await resp.json();
  if (!resp.ok) {
    const detail = json?.detail;
    const msg =
      typeof detail === 'object' && detail?.message
        ? detail.message
        : detail || json?.message || '提交失败';
    const err = new Error(String(msg)) as Error & { errors?: unknown };
    if (typeof detail === 'object') err.errors = detail.errors;
    throw err;
  }
  return (json.data || json) as {
    issueId: string;
    issueCode: string;
    title: string;
    requestId?: string | null;
  };
}

/** Ensure schema has exactly one title field; used by settings UI helper tests. */
export function ensureTitleField(fields: FormFieldDef[]): FormFieldDef[] {
  const hasTitle = fields.some(f => f.type === 'title');
  if (hasTitle) return fields;
  return [
    { key: 'title', type: 'title', label: 'Title', required: true },
    ...fields
  ];
}

export function buildPublicUrl(tokenOrPath: string, origin = typeof window !== 'undefined' ? window.location.origin : ''): string {
  const path = tokenOrPath.startsWith('/f/') ? tokenOrPath : `/f/${tokenOrPath}`;
  return `${origin}${path}`;
}

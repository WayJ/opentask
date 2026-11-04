import { request } from '../request';

export type CustomFieldType =
  | 'text'
  | 'number'
  | 'single_select'
  | 'multi_select'
  | 'date'
  | 'boolean'
  | 'formula';

export type FormulaResultType = 'number' | 'boolean' | 'text' | 'date';

export interface CustomFieldOption {
  value: string;
  label: string;
}

export interface CustomFieldRow {
  id: string;
  workspaceId: string;
  name: string;
  key: string;
  type: CustomFieldType;
  options: CustomFieldOption[];
  position: number;
  archivedAt?: string | null;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  formulaExpr?: string | null;
  formulaResultType?: FormulaResultType | null;
}

export interface IssueCustomFieldValue {
  fieldId: string;
  key: string;
  name: string;
  type: CustomFieldType;
  value: unknown;
  archived?: boolean;
  options?: CustomFieldOption[];
  computed?: boolean;
  error?: string | null;
  formulaResultType?: FormulaResultType | null;
}

export interface CustomFieldListResult {
  rows: CustomFieldRow[];
  total: number;
}

export interface ValidateFormulaResult {
  ok: boolean;
  dependencies: string[];
  error?: string;
}

export function fetchCustomFields(params?: { includeArchived?: boolean }) {
  return request<CustomFieldListResult>({
    url: '/api/custom-fields',
    method: 'get',
    params: {
      includeArchived: params?.includeArchived ? true : undefined
    }
  });
}

export function fetchCreateCustomField(body: {
  name: string;
  type: CustomFieldType;
  key?: string;
  options?: Array<string | CustomFieldOption>;
  position?: number;
  formulaExpr?: string;
  formulaResultType?: FormulaResultType;
}) {
  return request<CustomFieldRow>({ url: '/api/custom-fields', method: 'post', data: body });
}

export function fetchUpdateCustomField(
  id: string,
  body: {
    name?: string;
    options?: Array<string | CustomFieldOption>;
    setOptions?: boolean;
    position?: number;
    archive?: boolean;
    formulaExpr?: string;
    formulaResultType?: FormulaResultType;
  }
) {
  return request<CustomFieldRow>({ url: `/api/custom-fields/${id}`, method: 'patch', data: body });
}

export function fetchDeleteCustomField(id: string) {
  return request<{ id: string }>({ url: `/api/custom-fields/${id}`, method: 'delete' });
}

export function fetchReorderCustomFields(orderedIds: string[]) {
  return request<CustomFieldListResult>({
    url: '/api/custom-fields/reorder',
    method: 'post',
    data: { orderedIds }
  });
}

export function fetchValidateFormula(body: {
  formulaExpr: string;
  formulaResultType?: FormulaResultType;
}) {
  return request<ValidateFormulaResult>({
    url: '/api/custom-fields/validate-formula',
    method: 'post',
    data: body
  });
}

export function fetchPatchIssueCustomFields(
  issueId: string,
  values: Array<{ fieldId?: string; key?: string; value: unknown }>
) {
  return request<{ customFields: IssueCustomFieldValue[] }>({
    url: `/api/issues/${issueId}/custom-fields`,
    method: 'patch',
    data: { values }
  });
}

/** 将 CLI/表单字符串规范为可展示文案 */
export function formatCustomFieldValue(type: CustomFieldType, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (type === 'boolean' || typeof value === 'boolean') return value ? '是' : '否';
  if (type === 'multi_select' && Array.isArray(value)) return value.join(', ') || '—';
  return String(value);
}

export function formatFormulaDisplay(row: {
  value?: unknown;
  error?: string | null;
  formulaResultType?: FormulaResultType | null;
  type?: CustomFieldType;
}): string {
  if (row.error) return '—';
  const t = (row.formulaResultType || 'number') as CustomFieldType;
  return formatCustomFieldValue(t, row.value);
}

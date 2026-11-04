import { request } from '../request';

export interface CustomerRow {
  id: string;
  workspaceId: string;
  name: string;
  domains: string[];
  externalUrl?: string | null;
  notes?: string | null;
  requestCount?: number;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface CustomerListResult {
  rows: CustomerRow[];
  total: number;
}

export function fetchCustomers() {
  return request<CustomerListResult>({ url: '/api/customers', method: 'get' });
}

export function fetchCustomer(id: string) {
  return request<CustomerRow>({ url: `/api/customers/${id}`, method: 'get' });
}

export function fetchCreateCustomer(body: {
  name: string;
  domains?: string[];
  externalUrl?: string | null;
  notes?: string | null;
}) {
  return request<CustomerRow>({ url: '/api/customers', method: 'post', data: body });
}

export function fetchUpdateCustomer(
  id: string,
  body: {
    name?: string;
    domains?: string[];
    setDomains?: boolean;
    externalUrl?: string | null;
    clearExternalUrl?: boolean;
    notes?: string | null;
    clearNotes?: boolean;
  }
) {
  return request<CustomerRow>({ url: `/api/customers/${id}`, method: 'patch', data: body });
}

export function fetchDeleteCustomer(id: string) {
  return request<{ id: string }>({ url: `/api/customers/${id}`, method: 'delete' });
}

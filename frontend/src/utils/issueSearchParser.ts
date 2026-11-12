import { $t, i18n } from '@/locales';

const locale = i18n.global.locale;

/**
 * Issue 搜索语法解析器（E21：真正驱动 list API）
 * - is:open / is:closed / is:in_progress …
 * - label:bug（客户端按 tags 名过滤）
 * - type: / priority: / assignee:@me|me|uuid / author: / creator: / project: / cycle:
 * - KEY-N → search
 * - field:key:value / cf:key:value（E32 自定义字段）
 * - 普通文本 → search
 */

export interface CustomFieldFilter {
  key: string;
  value: string;
  /** E46：缺省 eq；range 仅 number/date */
  op?: 'eq' | 'gt' | 'gte' | 'lt' | 'lte';
}

export interface ParsedQuery {
  search?: string;
  status?: string;
  labels?: string[];
  type?: string;
  priority?: string;
  assignee_id?: string;
  reporter_id?: string;
  project_id?: string;
  cycle_id?: string;
  /** E32：field:key:value */
  custom_fields?: CustomFieldFilter[];
  [key: string]: unknown;
}

/** List 页 filters 形状（与 views/issue/list 对齐） */
export interface SmartSearchListFilters {
  search?: string;
  status?: string;
  type?: string;
  priority?: string;
  assignee_id?: string;
  reporter_id?: string;
  project_id?: string;
  cycle_id?: string;
  labels?: string[];
  custom_fields?: CustomFieldFilter[];
}

export interface SearchToken {
  type: 'text' | 'filter';
  field?: string;
  value: string;
  original: string;
}

const ISSUE_CODE_RE = /^[A-Za-z][A-Za-z0-9]*-\d+$/;

/**
 * 解析搜索字符串为 tokens
 */
export function parseSearchQuery(query: string): SearchToken[] {
  if (!query || !query.trim()) {
    return [];
  }

  const tokens: SearchToken[] = [];
  const regex = /(\w+):(\S+)|"([^"]+)"|(\S+)/g;
  let match;
  let lastIndex = 0;

  while ((match = regex.exec(query)) !== null) {
    if (match.index > lastIndex) {
      const text = query.substring(lastIndex, match.index).trim();
      if (text) {
        tokens.push({
          type: 'text',
          value: text,
          original: text
        });
      }
    }

    const matched = match[0];
    const field = match[1];
    const value1 = match[2];
    const value2 = match[3];
    const value3 = match[4];

    if (field && value1) {
      tokens.push({
        type: 'filter',
        field: field.toLowerCase(),
        value: value1,
        original: matched
      });
    } else if (value2) {
      tokens.push({
        type: 'text',
        value: value2,
        original: matched
      });
    } else if (value3) {
      tokens.push({
        type: 'text',
        value: value3,
        original: matched
      });
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < query.length) {
    const text = query.substring(lastIndex).trim();
    if (text) {
      tokens.push({
        type: 'text',
        value: text,
        original: text
      });
    }
  }

  return tokens;
}

function normalizeAssignee(raw: string): string {
  const v = raw.trim();
  if (!v) return v;
  if (v === '@me' || v === 'me' || v.toLowerCase() === '@me') return 'me';
  if (v.startsWith('@') && v.slice(1).toLowerCase() === 'me') return 'me';
  if (v.startsWith('@')) return v.slice(1);
  return v;
}

/**
 * 将 tokens 转换为 API 查询参数
 */
export function buildQueryFromTokens(tokens: SearchToken[]): ParsedQuery {
  const query: ParsedQuery = {};
  const searchTerms: string[] = [];

  for (const token of tokens) {
    if (token.type === 'filter') {
      switch (token.field) {
        case 'is': {
          const statusMap: Record<string, string> = {
            open: 'open',
            closed: 'closed',
            todo: 'open',
            done: 'closed',
            in_progress: 'in_progress',
            feedback: 'feedback',
            resolved: 'resolved',
            rejected: 'rejected'
          };
          if (statusMap[token.value]) {
            query.status = statusMap[token.value];
          }
          break;
        }

        case 'label': {
          if (!query.labels) query.labels = [];
          query.labels.push(token.value);
          break;
        }

        case 'type': {
          const typeMap: Record<string, string> = {
            bug: 'bug',
            feature: 'feature',
            improvement: 'improvement',
            task: 'task'
          };
          if (typeMap[token.value]) {
            query.type = typeMap[token.value];
          }
          break;
        }

        case 'priority': {
          const priorityMap: Record<string, string> = {
            urgent: 'urgent',
            high: 'high',
            medium: 'medium',
            low: 'low',
            critical: 'urgent'
          };
          if (priorityMap[token.value]) {
            query.priority = priorityMap[token.value];
          }
          break;
        }

        case 'assignee': {
          query.assignee_id = normalizeAssignee(token.value);
          break;
        }

        case 'author':
        case 'creator': {
          query.reporter_id = normalizeAssignee(token.value);
          break;
        }

        case 'project': {
          query.project_id = token.value;
          break;
        }

        case 'cycle': {
          query.cycle_id = token.value;
          break;
        }

        case 'field':
        case 'cf': {
          // E32: cf:key:value · E46: cf:key>=8 / cf:key>5 / cf:key<=1 / cf:key<9
          const raw = token.value;
          const opMatch = raw.match(/^([a-z][a-z0-9_-]{0,63})(>=|<=|>|<|=|:)(.*)$/i);
          if (!opMatch) break;
          const key = opMatch[1].trim().toLowerCase();
          const sym = opMatch[2];
          const value = opMatch[3];
          if (!key) break;
          const opMap: Record<string, 'eq' | 'gt' | 'gte' | 'lt' | 'lte'> = {
            ':': 'eq',
            '=': 'eq',
            '>': 'gt',
            '>=': 'gte',
            '<': 'lt',
            '<=': 'lte'
          };
          const op = opMap[sym] || 'eq';
          if (!query.custom_fields) query.custom_fields = [];
          query.custom_fields.push(op === 'eq' ? { key, value } : { key, value, op });
          break;
        }

        default: {
          break;
        }
      }
    } else if (token.type === 'text') {
      searchTerms.push(token.value);
    }
  }

  if (searchTerms.length > 0) {
    query.search = searchTerms.join(' ');
  }

  return query;
}

/**
 * 解析搜索字符串并返回查询参数
 */
export function parseSearchString(searchString: string): ParsedQuery {
  const tokens = parseSearchQuery(searchString);
  return buildQueryFromTokens(tokens);
}

/** ParsedQuery → list filters（清空未出现的字段为 undefined） */
export function parsedQueryToFilters(query: ParsedQuery): SmartSearchListFilters {
  return {
    search: query.search,
    status: query.status,
    type: query.type,
    priority: query.priority,
    assignee_id: query.assignee_id,
    reporter_id: query.reporter_id,
    project_id: query.project_id,
    cycle_id: query.cycle_id,
    labels: query.labels?.length ? [...query.labels] : undefined,
    custom_fields: query.custom_fields?.length
      ? query.custom_fields.map(f =>
          f.op && f.op !== 'eq'
            ? { key: f.key, value: f.value, op: f.op }
            : { key: f.key, value: f.value }
        )
      : undefined
  };
}

/** E32：custom_fields → axios params cf.<key>=value */
export function customFieldsToCfParams(
  filters?: CustomFieldFilter[] | null
): Record<string, string> {
  const out: Record<string, string> = {};
  if (!filters?.length) return out;
  for (const f of filters) {
    if (!f?.key) continue;
    const op = f.op && f.op !== 'eq' ? f.op : null;
    const name = op ? `cf.${f.key}[${op}]` : `cf.${f.key}`;
    out[name] = f.value ?? '';
  }
  return out;
}

export function isIssueCodeToken(value: string): boolean {
  return ISSUE_CODE_RE.test(value.trim());
}

/**
 * 生成搜索建议文本
 */
export function generateSearchSuggestions(): string[] {
  // eslint-disable-next-line no-void
  void locale.value;
  return [
    `is:open - ${$t('page.issueList.syntax.isOpen')}`,
    `is:closed - ${$t('page.issueList.syntax.isClosed')}`,
    `is:in_progress - ${$t('page.issueList.syntax.isInProgress')}`,
    `assignee:@me - ${$t('page.issueList.scopeTitle.assignedToMe')}`,
    `label:bug - ${$t('page.issueList.searchSuggestions.labelBug')}`,
    `type:feature - ${$t('page.issueList.searchSuggestions.typeFeature')}`,
    `priority:urgent - ${$t('page.issueList.syntax.priorityUrgent')}`,
    `cycle:__none__ - ${$t('page.issueList.searchSuggestions.cycleNone')}`,
    `project:<id> - ${$t('page.issueList.searchSuggestions.filterByProject')}`,
    `field:severity:s1 - ${$t('page.issueList.searchSuggestions.customField')}`,
    `field:score:10 - ${$t('page.issueList.searchSuggestions.formulaEquals')}`,
    `cf:score>=8 - ${$t('page.issueList.searchSuggestions.formulaRange')}`
  ];
}

/**
 * 高亮搜索语法中的关键字
 */
export function highlightSearchSyntax(searchString: string): string {
  if (!searchString) return '';

  return searchString.replace(
    /(\w+):(\S+)/g,
    '<span class="search-filter">$1:</span><span class="search-value">$2</span>'
  );
}

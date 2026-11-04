/**
 * Issue 搜索语法解析器（E21：真正驱动 list API）
 * - is:open / is:closed / is:in_progress …
 * - label:bug（客户端按 tags 名过滤）
 * - type: / priority: / assignee:@me|me|uuid / author: / creator: / project: / cycle:
 * - KEY-N → search
 * - 普通文本 → search
 */

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
    labels: query.labels?.length ? [...query.labels] : undefined
  };
}

export function isIssueCodeToken(value: string): boolean {
  return ISSUE_CODE_RE.test(value.trim());
}

/**
 * 生成搜索建议文本
 */
export function generateSearchSuggestions(): string[] {
  return [
    'is:open - 只显示待办中的 Issue',
    'is:closed - 只显示已完成的 Issue',
    'is:in_progress - 只显示进行中的 Issue',
    'assignee:@me - 指派给我',
    'label:bug - 只显示标签为 bug 的 Issue',
    'type:feature - 只显示类型为功能的 Issue',
    'priority:urgent - 只显示紧急优先级的 Issue',
    'cycle:__none__ - 无 Cycle',
    'project:<id> - 按项目过滤'
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

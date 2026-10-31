/**
 * Issue 搜索语法解析器
 * 支持 GitHub 风格的搜索语法：
 * - is:open, is:closed - 状态过滤
 * - label:bug, label:feature - 标签过滤
 * - type:bug, type:feature - 类型过滤
 * - priority:high, priority:low - 优先级过滤
 * - assignee:username - 负责人过滤
 * - project:projectName - 项目过滤
 * - 普通文本 - 标题或描述搜索
 */

export interface ParsedQuery {
  search?: string;
  status?: string;
  labels?: string[];
  type?: string;
  priority?: string;
  assignee?: string;
  project_id?: string;
  [key: string]: any;
}

export interface SearchToken {
  type: 'text' | 'filter';
  field?: string;
  value: string;
  original: string;
}

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
    // 添加匹配前的文本作为普通搜索
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
    const field = match[1]; // 过滤器字段
    const value1 = match[2]; // 带冒号的值
    const value2 = match[3]; // 引号中的值
    const value3 = match[4]; // 普通单词

    if (field && value1) {
      // 过滤器语法 field:value
      tokens.push({
        type: 'filter',
        field: field.toLowerCase(),
        value: value1,
        original: matched
      });
    } else if (value2) {
      // 引号包裹的文本
      tokens.push({
        type: 'text',
        value: value2,
        original: matched
      });
    } else if (value3) {
      // 普通单词
      tokens.push({
        type: 'text',
        value: value3,
        original: matched
      });
    }

    lastIndex = regex.lastIndex;
  }

  // 添加剩余的文本
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
          // 状态过滤
          const statusMap: Record<string, string> = {
            open: 'open',
            closed: 'closed',
            todo: 'open', // 向后兼容
            done: 'closed', // 向后兼容
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
          // 标签过滤（暂时用 search 字段，因为 API 可能不支持）
          if (!query.labels) {
            query.labels = [];
          }
          query.labels.push(token.value);
          break;
        }

        case 'type': {
          // 类型过滤
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
          // 优先级过滤
          const priorityMap: Record<string, string> = {
            urgent: 'urgent',
            high: 'high',
            medium: 'medium',
            low: 'low'
          };
          if (priorityMap[token.value]) {
            query.priority = priorityMap[token.value];
          }
          break;
        }

        case 'assignee':
        case 'author': {
          // 负责人或作者过滤
          query.assignee_id = token.value;
          break;
        }

        case 'project': {
          // 项目过滤（暂时用 project_id，后续可以支持名称搜索）
          query.project_id = token.value;
          break;
        }

        case 'creator': {
          // 创建者过滤
          query.reporter_id = token.value;
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

  // 将所有搜索词合并为 search 参数
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

/**
 * 生成搜索建议文本
 */
export function generateSearchSuggestions(): string[] {
  return [
    'is:open - 只显示待办中的 Issue',
    'is:closed - 只显示已完成的 Issue',
    'is:in_progress - 只显示进行中的 Issue',
    'label:bug - 只显示标签为 bug 的 Issue',
    'type:feature - 只显示类型为功能的 Issue',
    'priority:urgent - 只显示紧急优先级的 Issue',
    'assignee:admin - 只显示负责人为 admin 的 Issue',
    'project:1 - 只显示项目 ID 为 1 的 Issue'
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

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

function keysOf(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    keysOf(child, prefix ? `${prefix}.${key}` : key)
  );
}

function schemaKeysOfIssueForm(source: string): string[] {
  const match = /(?:^|[\n\r;{])\s*issueForm\s*:\s*\{/.exec(source);
  if (!match) return [];
  const start = source.indexOf('{', match.index);
  if (start < 0) return [];

  // Walker control flow stays aligned with the list-chrome typings reader.
  /* eslint-disable complexity, no-continue */
  function parseObject(from: number, prefix: string): { keys: string[]; end: number } {
    const keys: string[] = [];
    let i = from + 1;
    while (i < source.length) {
      while (i < source.length && /[\s,;]/.test(source[i])) i += 1;
      if (source[i] === '}') return { keys, end: i + 1 };
      if (source.startsWith('//', i)) {
        const nl = source.indexOf('\n', i);
        i = nl < 0 ? source.length : nl + 1;
        continue;
      }
      if (source.startsWith('/*', i)) {
        const endC = source.indexOf('*/', i + 2);
        i = endC < 0 ? source.length : endC + 2;
        continue;
      }
      const keyMatch = /^[A-Za-z_][A-Za-z0-9_]*/.exec(source.slice(i));
      if (!keyMatch) {
        i += 1;
        continue;
      }
      const key = keyMatch[0];
      i += key.length;
      while (i < source.length && /\s/.test(source[i])) i += 1;
      if (source[i] !== ':') continue;
      i += 1;
      while (i < source.length && /\s/.test(source[i])) i += 1;
      const path = prefix ? `${prefix}.${key}` : key;
      if (source[i] === '{') {
        const nested = parseObject(i, path);
        keys.push(...nested.keys);
        i = nested.end;
      } else {
        keys.push(path);
        while (i < source.length && source[i] !== ';' && source[i] !== ',' && source[i] !== '}') i += 1;
        if (source[i] === ';' || source[i] === ',') i += 1;
      }
    }
    return { keys, end: i };
  }
  /* eslint-enable complexity, no-continue */

  return parseObject(start, '').keys;
}

describe('issue form and property chrome copy', () => {
  it('keeps locked Chinese and English form chrome', () => {
    expect(zh.page.issueForm.createTitle).toBe('创建问题');
    expect(en.page.issueForm.createTitle).toBe('Create issue');
    expect(en.page.issueForm.createTitle).not.toBe('Create Issue');
    expect(en.page.issueForm.createTitle).not.toBe('New issue');
    expect(zh.page.issueForm.editTitle).toBe('编辑问题');
    expect(en.page.issueForm.editTitle).toBe('Edit issue');
    expect(zh.page.issueForm.saveChanges).toBe('保存更改');
    expect(en.page.issueForm.saveChanges).toBe('Save changes');
    expect(zh.page.issueForm.propertySettings).toBe('属性设置');
    expect(en.page.issueForm.propertySettings).toBe('Property settings');
    expect(zh.page.issueForm.assignee).toBe('指派人');
    expect(en.page.issueForm.assignee).toBe('Assignee');
    expect(zh.page.issueForm.cycle).toBe('冲刺');
    expect(en.page.issueForm.cycle).toBe('Cycle');
    expect(en.page.issueForm.cycle).not.toBe('Sprint');
    expect(zh.page.issueForm.selectProjectOptional).toBe('选择项目（可选）');
    expect(en.page.issueForm.selectProjectOptional).toBe('Select project (optional)');
    expect(zh.page.issueForm.unassigned).toBe('未分配');
    expect(en.page.issueForm.unassigned).toBe('Unassigned');
    expect(zh.page.issueList.noneCycle).toBe('无 Cycle');
    expect(en.page.issueList.noneCycle).toBe('No cycle');
    expect(en.page.issueStatus.open).toBe('Open');
    expect(zh.page.issueStatus.open).toBe('待办');
    expect(en.page.issuePriority.critical).toBe('Urgent');
    expect(zh.page.issuePriority.critical).toBe('紧急');
    expect(keysOf(zh.page.issueForm).sort()).toEqual(keysOf(en.page.issueForm).sort());
    const typings = readFileSync(resolve(process.cwd(), 'src/typings/app.d.ts'), 'utf8');
    expect(schemaKeysOfIssueForm(typings).sort()).toEqual(keysOf(zh.page.issueForm).sort());
    expect(en.page.issueForm.createTitle).not.toBe(zh.page.issueForm.createTitle);
    expect(en.page.issueForm.assignee).not.toBe(zh.page.issueForm.assignee);
  });

  it('wires create, edit, and detail to the new keys and leaves constants Chinese labels alone', () => {
    const create = readFileSync(resolve(process.cwd(), 'src/views/issue/create/index.vue'), 'utf8');
    const edit = readFileSync(resolve(process.cwd(), 'src/views/issue/edit/index.vue'), 'utf8');
    const detail = readFileSync(resolve(process.cwd(), 'src/views/issue/detail/index.vue'), 'utf8');
    const constants = readFileSync(resolve(process.cwd(), 'src/constants/issue.ts'), 'utf8');
    expect((create.match(/\$t\('page\.issueForm\.createTitle'\)/g) ?? []).length).toBe(2);
    expect(create).toContain("$t('page.issueForm.propertySettings')");
    expect(create).toContain("useLabelTable('page.issuePriority')");
    expect(create).toContain("$t('page.issueComposer.useTemplate')");
    expect(create).toContain("$t('page.issueComposer.useTemplateHint')");
    expect(create).not.toMatch(/^\s+使用模板\s*$/m);
    expect(create).not.toMatch(/从模板创建问题/);
    expect(create).not.toContain('<NText strong style="font-size: 16px; margin-left: 12px">创建问题</NText>');
    expect(create).not.toMatch(/^\s+创建问题\s*$/m);
    expect(edit).toContain("$t('page.issueForm.editTitle')");
    expect(edit).toContain("$t('page.issueForm.saveChanges')");
    expect(edit).not.toContain('保存更改');
    expect(edit).toContain("useLabelTable('page.issuePriority')");
    expect(edit).not.toContain('<NText strong style="font-size: 16px; margin-left: 12px">编辑问题</NText>');
    expect(detail).toContain("$t('page.issueForm.status')");
    expect(detail).toContain("$t('page.issueForm.assignee')");
    expect(detail).toContain("$t('page.issueForm.cycle')");
    expect(detail).toContain("useLabelTable('page.issueStatus')");
    expect(detail).toContain("useLabelTable('page.issuePriority')");
    expect(detail).toContain('page.issueList.noneCycle');
    expect(detail).not.toContain('label="状态"');
    expect(detail).not.toContain('label="指派人"');
    const statusBtnStart = detail.indexOf("startEdit('status'");
    expect(statusBtnStart).toBeGreaterThan(-1);
    const statusBtnEnd = detail.indexOf('</NButton>', statusBtnStart);
    expect(detail.slice(statusBtnStart, statusBtnEnd)).toContain("$t('page.issueForm.status')");
    expect(detail).toMatch(
      /assigneeInfo = issueData\.assignee\s*\?\s*issueData\.assignee\.sso_name \|\| issueData\.assignee\.sso_account \|\| issueData\.assignee\.id\s*:\s*'未分配'/
    );
    expect(detail).toContain('label="Milestone"');
    expect(detail).toContain("$t('page.issueDetail.noMilestone')");
    expect(detail).toContain("$t('page.issueDetail.chooseMilestone')");
    expect(detail).toMatch(
      /:label="\$t\('page\.issueDetail\.project'\)"[\s\S]*?:placeholder="\$t\('page\.issueForm\.unset'\)"/
    );
    expect(detail).toMatch(
      /:label="\$t\('page\.issueList\.columns\.estimate'\)"[\s\S]*?:placeholder="\$t\('page\.issueForm\.unset'\)"/
    );
    expect(constants).toContain("label: '待办'");
    expect(constants).toContain("label: '紧急'");
  });
});

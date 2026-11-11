import { describe, expect, it } from 'vitest';
import zh from '../langs/zh-cn';
import en from '../langs/en-us';

const keys = [
  'customers',
  'customers_detail',
  'requests',
  'requests_detail',
  'settings_sla',
  'initiatives',
  'initiatives_detail',
  'workspace_cycles',
  'workspace_members',
  'settings_recurrences',
  'insights',
  'activity'
] as const;

describe('route labels', () => {
  it.each(keys)('%s exists in zh-CN and en-US and is not the raw key', key => {
    const zhValue = zh.route[key];
    const enValue = en.route[key];
    expect(zhValue).toBeTruthy();
    expect(enValue).toBeTruthy();
    expect(zhValue).not.toBe(`route.${key}`);
    expect(enValue).not.toBe(`route.${key}`);
  });

  it('uses the approved object names', () => {
    expect(zh.route.workspace_cycles).toBe('冲刺');
    expect(zh.route.settings_recurrences).toBe('周期建单');
    expect(en.route.workspace_cycles).toBe('Cycles');
    expect(en.route.settings_recurrences).toBe('Recurring issues');
    expect(zh.route.settings_sla).toBe('SLA 策略');
    expect(en.route.settings_sla).toBe('SLA');
    expect(zh.route.workspace_members).toBe('成员');
    expect(zh.route.insights).toBe('洞察');
    expect(en.route.insights).toBe('Insights');
    expect(zh.route.activity).toBe('活动');
    expect(en.route.activity).toBe('Activity');
    expect(zh.route.initiatives).toBe('举措');
    expect(zh.route['workspace_issue-templates']).toBe('问题模板');
    expect(zh.page.sider.activityHint).toBe('动态');
    expect(en.page.sider.activityHint).not.toMatch(/feed/i);
    expect(zh.page.shell.createIssue).toBe('新建问题');
    expect(zh.page.shell.createRequest).toBe('新建需求');
    expect(zh.page.shell.searchIssues).toBe('搜索问题编号、标题...');
    expect(zh.page.shell.searchIssues).not.toMatch(/Issue/);
    expect(en.page.shell.createIssue).toBe('New issue');
    expect(en.page.shell.searchIssues).toBe('Search issue number or title...');
    expect(zh.common.commandPalette.groupIssues).toBe('问题');
    expect(zh.common.commandPalette.navIssues).toBe('问题列表');
    expect(zh.common.commandPalette.navCreateIssue).toBe('创建问题');
    expect(zh.common.commandPalette.navCycles).toBe('冲刺设置');
    expect(zh.common.commandPalette.navInitiatives).toBe('举措');
    expect(zh.common.commandPalette.navLabels).toBe('标签');
    expect(en.common.commandPalette.groupIssues).toBe('Issues');
    expect(en.common.commandPalette.navCycles).toBe('Cycles settings');
    expect(zh.page.shell.openIssues).toBe('开放问题');
    expect(en.page.shell.openIssues).toBe('Open issues');
    expect(zh.page.shell.favoriteInitiative).toBe('举措');
    expect(en.page.shell.favoriteInitiative).toBe('Initiative');
    expect(zh.page.shell.noActiveCycle).toBe('无进行中的冲刺');
    expect(en.page.shell.noActiveCycle).toBe('No active cycle');
    expect(zh.route.issue_edit).toBe('编辑问题');
    expect(en.route.issue_edit).toBe('Edit Issue');
    expect(zh.route.issue_edit).not.toBe('route.issue_edit');
    expect(en.route.issue_edit).not.toBe('route.issue_edit');
  });
});

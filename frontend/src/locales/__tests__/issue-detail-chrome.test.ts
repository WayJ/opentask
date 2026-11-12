import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { nextTick } from 'vue';
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import IssueReactions from '@/components/IssueReactions.vue';
import { i18n, setLocale } from '@/locales';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

const source = (path: string) => readFileSync(resolve(path), 'utf8');
const detailVue = source('src/views/issue/detail/index.vue');
const timelineTs = source('src/utils/formatTimelineAction.ts');
const reactionsVue = source('src/components/IssueReactions.vue');
const linksVue = source('src/components/issue-links/IssueLinksPanel.vue');
const prVue = source('src/components/issue-vcs/IssuePrPanel.vue');
const typing = source('src/typings/app.d.ts');
const editorVue = source('src/components/MarkdownEditor.vue');
const attachmentVue = source('src/components/common/AttachmentList.vue');
const fieldsVue = source('src/components/issue/IssueCustomFieldsEditor.vue');
const trashMeta = source('src/utils/issueTrashMeta.ts');
const slaTs = source('src/service/api/sla.ts');

function countCalls(src: string, key: string): number {
  const exact = src.split(`$t('${key}')`).length - 1;
  const named = src.split(`$t('${key}',`).length - 1;
  return exact + named;
}

const issueDetailCopy = [
  ['parentPrefix', '父问题：', 'Parent:'],
  ['copyIssue', '复制问题', 'Copy issue'],
  ['changeParent', '更换父', 'Change parent'],
  ['setAsChild', '设为子项…', 'Set as child...'],
  ['promoteToRoot', '提升为根', 'Promote to root'],
  ['watch', '关注', 'Watch'],
  ['unwatch', '取消关注', 'Unwatch'],
  ['unwatchInline', '取消', 'Unwatch'],
  ['copyBranchName', '复制分支名', 'Copy branch name'],
  ['noDescription', '暂无描述', 'No description'],
  ['subIssues', '子问题', 'Sub-issues'],
  ['add', '+ 添加', '+ Add'],
  ['noSubIssues', '暂无子问题', 'No sub-issues'],
  ['activity', '活动 ({n})', 'Activity ({n})'],
  ['reply', '回复', 'Reply'],
  ['noActivity', '暂无活动', 'No activity'],
  ['replyPlaceholder', '写下回复...支持 Markdown', 'Write a reply... Markdown supported'],
  [
    'commentPlaceholder',
    '添加评论...支持 Markdown 语法。使用 @提及用户，+ISSUE-xxx 引用问题、+PROJECT-xxx 引用项目、+REQUIREMENT-xxx 引用需求等',
    'Add a comment... Markdown supported. Use @ to mention a user, +ISSUE-xxx to reference an issue, +PROJECT-xxx for a project, +REQUIREMENT-xxx for a requirement, and similar'
  ],
  ['postReply', '发表回复', 'Post reply'],
  ['postComment', '发表评论', 'Post comment'],
  ['chooseMilestone', '选择 Milestone', 'Choose a Milestone'],
  ['noMilestone', '无 Milestone', 'No Milestone'],
  ['project', '项目', 'Project'],
  ['timeTracking', '工时', 'Time tracking'],
  ['estimated', '预估:', 'Est.:'],
  ['actual', '实际:', 'Actual:'],
  ['slaPaused', '已暂停', 'Paused'],
  ['customFields', '自定义字段', 'Custom fields'],
  ['customerRequests', '客户需求', 'Customer requests'],
  ['linkedIssues', '关联问题', 'Linked issues'],
  ['noLinks', '暂无关联', 'No links yet'],
  ['targetIssuePlaceholder', '目标问题 ID 或 KEY-N', 'Target issue ID or KEY-N'],
  ['confirmAdd', '确认添加', 'Confirm add'],
  ['remove', '移除', 'Remove'],
  ['relationBlocks', '阻塞', 'Blocks'],
  ['relationBlockedBy', '被阻塞', 'Blocked by'],
  ['relationRelated', '关联', 'Related'],
  ['relationDuplicates', '重复', 'Duplicates'],
  ['relationDependsOn', '依赖', 'Depends on'],
  ['relationDuplicatedBy', '被重复', 'Duplicated by'],
  ['relationDependedOnBy', '被依赖', 'Depended on by'],
  ['tags', '标签', 'Tags'],
  ['noTags', '暂无标签', 'No tags yet'],
  ['chooseTag', '选择标签', 'Choose a tag'],
  ['createdAt', '创建于', 'Created'],
  ['updatedAt', '更新于', 'Updated'],
  ['viewedNTimes', '浏览 {n} 次', 'Viewed {n} times'],
  ['quickActions', '快速操作', 'Quick actions'],
  ['getAgentInstructions', '获取 Agent 指令', 'Get agent instructions'],
  ['refresh', '刷新数据', 'Refresh'],
  ['changeParentTitle', '更换父问题', 'Change parent'],
  ['setAsChildTitle', '设为子项', 'Set as child'],
  [
    'changeParentHint',
    '选择同工作区的父问题（排除自身；环由服务端校验）。',
    'Pick a parent in this workspace (itself is excluded; cycles are checked on the server).'
  ],
  ['searchIssues', '搜索问题…', 'Search issues...'],
  [
    'addSubIssueHint',
    '将创建挂在当前问题下的子项（parent_issue_id）。',
    'This creates a child of the current issue (parent_issue_id).'
  ],
  ['subIssueTitle', '子问题标题', 'Sub-issue title'],
  ['create', '创建', 'Create'],
  ['timelineUnassigned', '未分配', 'Unassigned'],
  ['timelineEmpty', '空', 'Empty'],
  ['timelineCreated', '创建了此问题', 'Created this issue'],
  ['timelineRestored', '从回收站恢复了此问题', 'Restored this issue from the trash'],
  ['timelineUpdated', '更新了问题', 'Updated the issue'],
  ['timelineCommented', '添加了评论', 'Added a comment'],
  ['timelineStatusChanged', '将状态从 "{from}" 改为 "{to}"', 'Changed status from "{from}" to "{to}"'],
  ['timelineAssigneeChanged', '将负责人从 "{from}" 改为 "{to}"', 'Changed assignee from "{from}" to "{to}"'],
  ['timelinePriorityChanged', '将优先级从 "{from}" 改为 "{to}"', 'Changed priority from "{from}" to "{to}"'],
  ['timelineDueDateChanged', '修改了截止日期', 'Changed the due date'],
  ['timelineStartDateChanged', '修改了计划开始日', 'Changed the start date'],
  ['timelineRelationAdded', '添加了关联: {type}', 'Added a link: {type}'],
  ['timelineRelationRemoved', '移除了关联', 'Removed a link'],
  ['timelineAttachmentAdded', '添加了附件', 'Added an attachment'],
  ['timelineAttachmentRemoved', '移除了附件', 'Removed an attachment'],
  ['timelineTagAdded', '添加了标签', 'Added a tag'],
  ['timelineTagRemoved', '移除了标签', 'Removed a tag'],
  ['timelineReactionAdded', '添加了反应 {emoji}', 'Added a {emoji} reaction'],
  ['timelineReactionRemoved', '移除了反应 {emoji}', 'Removed a {emoji} reaction'],
  ['timelineMarkedResolved', '标记为已解决', 'Marked as resolved'],
  ['timelineClosed', '关闭了此问题', 'Closed this issue'],
  ['timelineReopened', '重新打开此问题', 'Reopened this issue'],
  [
    'timelineCustomFieldChanged',
    '将自定义字段 {key} 从 {from} 改为 {to}',
    'Changed custom field {key} from {from} to {to}'
  ],
  ['timelineCycleChanged', '将冲刺从 {from} 改为 {to}', 'Changed cycle from {from} to {to}'],
  ['timelineEstimateChanged', '将估分从 {from} 改为 {to}', 'Changed estimate from {from} to {to}'],
  ['timelineProjectChanged', '将项目从 {from} 改为 {to}', 'Changed project from {from} to {to}'],
  ['timelineSlaPaused', '暂停了{metric} SLA（{name}）', 'Paused {metric} SLA ({name})'],
  ['timelineSlaResumed', '恢复了{metric} SLA（{name}）', 'Resumed {metric} SLA ({name})'],
  ['timelineSlaMetricFirstResponse', '首响', 'first-response'],
  ['timelineSlaMetricStatus', '状态', 'status']
] as const;

const reactionCopy = [
  ['add', '添加反应', 'Add reaction'],
  ['thumbsUp', '赞成', 'Thumbs up'],
  ['thumbsDown', '反对', 'Thumbs down'],
  ['heart', '喜欢', 'Heart'],
  ['tada', '庆祝', 'Celebration'],
  ['rocket', '火箭', 'Rocket'],
  ['eyes', '关注', 'Eyes'],
  ['confused', '困惑', 'Confused'],
  ['smile', '开心', 'Smile'],
  ['others', '{a}, {b} 和其他 {n} 人', '{a}, {b}, and {n} others']
] as const;

const linkCopy = [
  ['title', '链接', 'Links'],
  ['empty', '添加设计稿、文档或仪表盘链接', 'Add a design, doc, or dashboard link'],
  ['titleOptional', '标题（可选）', 'Title (optional)'],
  ['save', '保存', 'Save'],
  ['addLink', '添加链接', 'Add link'],
  ['loadFailed', '加载外链失败', "Couldn't load links"],
  ['urlRequired', '请输入链接 URL', 'Enter a link URL'],
  ['httpOnly', '仅支持 http:// 或 https:// 链接', 'Only http:// or https:// links are supported'],
  ['addFailed', '添加失败', "Couldn't add the link"],
  ['added', '已添加链接', 'Link added'],
  ['updateFailed', '更新失败', "Couldn't update the link"],
  ['updated', '已更新', 'Updated'],
  ['deleteFailed', '删除失败', "Couldn't delete the link"],
  ['deleted', '已删除', 'Deleted']
] as const;

const prCopy = [
  ['title', '关联的 PR', 'Linked PRs'],
  ['empty', '暂无关联的 Pull Request', 'No linked pull requests'],
  ['unlink', '解除关联', 'Unlink'],
  [
    'urlPlaceholder',
    'PR URL（如 https://github.com/org/repo/pull/1）',
    'PR URL (e.g. https://github.com/org/repo/pull/1)'
  ],
  ['add', '关联 PR', 'Link PR'],
  ['loadFailed', '加载 PR 关联失败', "Couldn't load linked PRs"],
  ['urlRequired', '请输入 PR URL', 'Enter a PR URL'],
  ['linkFailed', '关联失败', "Couldn't link the PR"],
  ['linked', '已关联 PR', 'PR linked'],
  ['unlinkFailed', '解除关联失败', "Couldn't unlink the PR"],
  ['unlinked', '已解除关联', 'Unlinked']
] as const;

const detailCallCounts: Record<string, number> = {
  parentPrefix: 1,
  copyIssue: 1,
  changeParent: 1,
  setAsChild: 1,
  promoteToRoot: 1,
  watch: 1,
  unwatch: 1,
  unwatchInline: 1,
  copyBranchName: 1,
  noDescription: 1,
  subIssues: 1,
  add: 3,
  noSubIssues: 1,
  activity: 1,
  reply: 1,
  noActivity: 1,
  replyPlaceholder: 1,
  commentPlaceholder: 1,
  postReply: 1,
  postComment: 1,
  chooseMilestone: 1,
  noMilestone: 1,
  project: 1,
  timeTracking: 1,
  estimated: 1,
  actual: 1,
  slaPaused: 1,
  customFields: 1,
  customerRequests: 1,
  linkedIssues: 1,
  noLinks: 1,
  targetIssuePlaceholder: 1,
  confirmAdd: 2,
  remove: 1,
  relationBlocks: 2,
  relationBlockedBy: 2,
  relationRelated: 2,
  relationDuplicates: 2,
  relationDependsOn: 2,
  relationDuplicatedBy: 1,
  relationDependedOnBy: 1,
  tags: 1,
  noTags: 1,
  chooseTag: 1,
  createdAt: 1,
  updatedAt: 1,
  viewedNTimes: 1,
  quickActions: 1,
  getAgentInstructions: 1,
  refresh: 1,
  changeParentTitle: 1,
  setAsChildTitle: 1,
  changeParentHint: 1,
  searchIssues: 1,
  addSubIssueHint: 1,
  subIssueTitle: 1,
  create: 1
};

function stringsOf(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  if (!value || typeof value !== 'object') return [];
  return Object.values(value).flatMap(stringsOf);
}

const pass = (tag: string) => ({ template: `<${tag}><slot name="icon" /><slot name="trigger" /><slot /></${tag}>` });
const reactionStubs = {
  NButton: pass('button'),
  Button: pass('button'),
  NDropdown: pass('div'),
  Dropdown: pass('div'),
  NPopover: pass('div'),
  Popover: pass('div'),
  NSpace: pass('div'),
  Space: pass('div'),
  NText: pass('span'),
  Text: pass('span'),
  'icon-mdi-emoticon-happy-outline': true,
  'icon-mdi-account-multiple-outline': true
};

describe('issue detail English chrome', () => {
  afterEach(() => setLocale('zh-CN'));

  it('locks new detail, reaction, link, and PR copy in zh-CN and en-US', () => {
    expect(zh.page).toHaveProperty('issueDetail');
    expect(en.page).toHaveProperty('issueDetail');
    expect(zh.page).toHaveProperty('issueReaction');
    expect(en.page).toHaveProperty('issueReaction');
    expect(zh.page).toHaveProperty('issueLink');
    expect(en.page).toHaveProperty('issueLink');
    expect(zh.page).toHaveProperty('issuePr');
    expect(en.page).toHaveProperty('issuePr');

    for (const [key, zhText, enText] of issueDetailCopy) {
      expect(zh.page.issueDetail[key]).toBe(zhText);
      expect(en.page.issueDetail[key]).toBe(enText);
    }
    for (const [key, zhText, enText] of reactionCopy) {
      expect(zh.page.issueReaction[key]).toBe(zhText);
      expect(en.page.issueReaction[key]).toBe(enText);
    }
    for (const [key, zhText, enText] of linkCopy) {
      expect(zh.page.issueLink[key]).toBe(zhText);
      expect(en.page.issueLink[key]).toBe(enText);
    }
    for (const [key, zhText, enText] of prCopy) {
      expect(zh.page.issuePr[key]).toBe(zhText);
      expect(en.page.issuePr[key]).toBe(enText);
    }

    expect(zh.page.issueList.toolbar.pinToSidebar).toBe('收藏到侧栏');
    expect(en.page.issueList.toolbar.pinToSidebar).toBe('Pin to sidebar');
    expect(zh.page.issueList.toolbar.unpinFromSidebar).toBe('取消侧栏');
    expect(en.page.issueList.toolbar.unpinFromSidebar).toBe('Unpin from sidebar');
    expect(zh.page.issueStatus.open).toBe('待办');
    expect(en.page.issueStatus.open).toBe('Open');

    for (const value of [
      ...stringsOf(en.page.issueDetail),
      ...stringsOf(en.page.issueReaction),
      ...stringsOf(en.page.issueLink),
      ...stringsOf(en.page.issuePr)
    ]) {
      expect(value).not.toMatch(/[\u4E00-\u9FFF]/);
    }

    const schema = typing.slice(typing.indexOf('issueDetail:'), typing.indexOf('issueTemplate:'));
    expect(schema).toContain('issueDetail:');
    expect(schema).toContain('issueReaction:');
    expect(schema).toContain('issueLink:');
    expect(schema).toContain('issuePr:');
    for (const [key] of [...issueDetailCopy, ...reactionCopy, ...linkCopy, ...prCopy]) {
      expect(schema).toContain(`${key}: string`);
    }
  });

  it('binds the top bar, reused keys, and named activity counts', () => {
    expect(countCalls(detailVue, 'page.issueForm.status')).toBe(2);
    expect(countCalls(detailVue, 'page.issueTrash.restore')).toBe(1);
    expect(countCalls(detailVue, 'common.edit')).toBe(1);
    expect(countCalls(detailVue, 'common.delete')).toBe(3);
    expect(countCalls(detailVue, 'common.cancel')).toBe(3);
    expect(countCalls(detailVue, 'common.confirm')).toBe(1);
    expect(countCalls(detailVue, 'page.issueForm.unset')).toBe(4);
    expect(countCalls(detailVue, 'page.issueComposer.description')).toBe(1);
    expect(countCalls(detailVue, 'page.issueComposer.attachments')).toBe(1);
    expect(countCalls(detailVue, 'page.issueList.columns.estimate')).toBe(1);
    expect(countCalls(detailVue, 'page.issueList.toolbar.pinToSidebar')).toBe(1);
    expect(countCalls(detailVue, 'page.issueList.toolbar.unpinFromSidebar')).toBe(1);
    expect(countCalls(detailVue, 'page.insights.exportCsv')).toBe(1);
    expect(countCalls(detailVue, 'page.issueDetail.watch')).toBe(1);
    expect(countCalls(detailVue, 'page.issueDetail.unwatch')).toBe(1);
    expect(countCalls(detailVue, 'page.issueDetail.unwatchInline')).toBe(1);

    for (const [key, count] of Object.entries(detailCallCounts)) {
      expect(countCalls(detailVue, `page.issueDetail.${key}`), key).toBe(count);
    }

    expect(detailVue).toContain("$t('page.issueDetail.activity', { n:");
    expect(detailVue).toContain("$t('page.issueDetail.viewedNTimes', { n:");
    expect(detailVue).not.toContain(".replace('{n}'");
    expect(detailVue).toContain("watching ? $t('page.issueDetail.unwatch') : $t('page.issueDetail.watch')");
    expect(detailVue).toMatch(
      /pinnedFavoriteId\s*\?\s*\$t\('page\.issueList\.toolbar\.unpinFromSidebar'\)\s*:\s*\$t\('page\.issueList\.toolbar\.pinToSidebar'\)/
    );
    expect(detailVue).not.toContain('取消侧栏收藏');

    const watcherStart = detailVue.indexOf('class="watcher-row"');
    const watcherBtn = detailVue.slice(watcherStart, detailVue.indexOf('</NButton>', watcherStart));
    expect(countCalls(watcherBtn, 'page.issueDetail.unwatchInline')).toBe(1);
    expect(countCalls(watcherBtn, 'page.issueDetail.unwatch')).toBe(0);
    expect(watcherBtn).not.toContain('common.cancel');
    expect(watcherBtn).not.toMatch(/>\s*取消\s*$/);
  });

  it('drops in-scope hard-coded detail chrome and keeps out-of-scope Chinese', () => {
    const gone = [
      /父问题：/,
      />\s*复制问题\s*</,
      /更换父/,
      /设为子项/,
      />\s*提升为根\s*</,
      />\s*复制分支名\s*</,
      /description="暂无描述"/,
      /<span>子问题<\/span>/,
      /\+ 添加/,
      /暂无子问题/,
      /写下回复\.\.\.支持 Markdown/,
      /发表回复/,
      /发表评论/,
      /添加评论\.\.\.支持 Markdown 语法。使用 @提及用户，\+ISSUE-xxx 引用问题、\+PROJECT-xxx 引用项目、\+REQUIREMENT-xxx 引用需求等/,
      /选择 Milestone/,
      /无 Milestone/,
      />\s*工时\s*</,
      /预估:/,
      /实际:/,
      /已暂停/,
      /客户需求/,
      /暂无关联/,
      /目标问题 ID 或 KEY-N/,
      /确认添加/,
      /暂无标签/,
      /选择标签/,
      /创建于/,
      /更新于/,
      /<span>快速操作<\/span>/,
      /获取 Agent 指令/,
      />\s*刷新数据\s*</,
      /<NText strong>描述<\/NText>/,
      /title="附件"/
    ];
    for (const pattern of gone) {
      expect(detailVue).not.toMatch(pattern);
    }
    expect(detailVue).not.toMatch(/startEdit\('status'[\s\S]{0,240}>\s*状态\s*<\/NButton>/);
    expect(detailVue).not.toMatch(/class="issue-action-edit"[\s\S]{0,400}>\s*编辑\s*<\/NButton>/);
    expect(detailVue).not.toMatch(/icon-mdi-delete[\s\S]{0,240}>\s*删除\s*<\/NButton>/);
    expect(detailVue).not.toMatch(/handleRestoreFromTrash[\s\S]{0,200}>\s*恢复\s*<\/NButton>/);
    expect(detailVue).not.toMatch(/toggleWatch">\s*\{\{\s*watching \? '取消关注'/);
    expect(detailVue).not.toMatch(/class="watcher-row"[\s\S]{0,500}>\s*取消\s*<\/NButton>/);

    expect(detailVue).toContain('🤖 Agent 工作指令');
    expect(detailVue).toContain('复制下方指令，粘贴到 Claude 中即可指挥 agent 开始工作');
    expect(detailVue).toContain(": '暂无描述'");
    expect(detailVue).toContain('子问题已创建');
    expect(detailVue).toContain('请输入子问题标题');
    expect(detailVue).toContain('创建子问题失败');
    expect(detailVue).toContain('提升为根失败');
    expect(detailVue).toContain('复制分支名失败');
    expect(detailVue).toContain('恢复失败（需要 member 权限）');
    expect(detailVue).toContain('确认删除');
    expect(detailVue).toContain('{{ deletedReadonlyBanner() }}');
    expect(editorVue).toContain("insertText('**', '**', '粗体文本')");
    expect(attachmentVue).toContain('暂无附件');
    expect(attachmentVue).toContain('点击或拖拽文件到此区域上传');
    expect(fieldsVue).toContain('暂无自定义字段');
    expect(fieldsVue).toContain('ƒ 公式');
    expect(trashMeta).toContain('此问题已在回收站中，只读。恢复后可继续编辑。');
    expect(trashMeta).toContain('已恢复');
    expect(slaTs).toContain("return '首响 SLA'");
    expect(slaTs).toContain("return '状态 SLA'");
  });

  it('localizes reactions, links, and PR panels, and keeps the PR URL example', () => {
    for (const [key] of reactionCopy) {
      expect(countCalls(reactionsVue, `page.issueReaction.${key}`)).toBe(1);
    }
    expect(reactionsVue).not.toMatch(/>\s*添加反应\s*</);
    expect(reactionsVue).toContain('👍');
    expect(reactionsVue).not.toContain(".replace('{n}'");

    const linkCounts: Record<string, number> = {
      title: 1,
      empty: 1,
      titleOptional: 2,
      save: 1,
      addLink: 1,
      loadFailed: 1,
      urlRequired: 1,
      httpOnly: 2,
      addFailed: 1,
      added: 1,
      updateFailed: 1,
      updated: 1,
      deleteFailed: 1,
      deleted: 1
    };
    for (const [key, count] of Object.entries(linkCounts)) {
      expect(countCalls(linksVue, `page.issueLink.${key}`), key).toBe(count);
    }
    expect(countCalls(linksVue, 'common.cancel')).toBe(1);
    expect(countCalls(linksVue, 'common.edit')).toBe(1);
    expect(countCalls(linksVue, 'common.delete')).toBe(1);
    expect(linksVue).not.toContain('加载外链失败');
    expect(linksVue).not.toContain('标题（可选）');
    expect(linksVue).not.toMatch(/>\s*保存\s*</);

    for (const [key] of prCopy) {
      expect(countCalls(prVue, `page.issuePr.${key}`)).toBe(1);
    }
    expect(countCalls(prVue, 'page.issueLink.titleOptional')).toBe(1);
    expect(prVue).toContain('https://github.com/org/repo/pull/1');
    expect(prVue).not.toContain('加载 PR 关联失败');
    expect(prVue).not.toContain('暂无关联的 Pull Request');
  });

  it('stops hard-coding open as 待处理 and reads status, priority, and timeline verbs from i18n', () => {
    expect(timelineTs).not.toMatch(/open:\s*'待处理'/);
    expect(timelineTs).not.toContain('待处理');
    expect(timelineTs).toMatch(/page\.issueStatus/);
    expect(timelineTs).toMatch(/page\.issuePriority/);
    expect(timelineTs).not.toContain('.replace(');
    for (const [key] of issueDetailCopy.filter(([name]) => name.startsWith('timeline'))) {
      expect(countCalls(timelineTs, `page.issueDetail.${key}`), key).toBeGreaterThanOrEqual(1);
    }
    for (const key of [
      'relationBlocks',
      'relationBlockedBy',
      'relationRelated',
      'relationDuplicates',
      'relationDependsOn',
      'relationDuplicatedBy',
      'relationDependedOnBy'
    ]) {
      expect(countCalls(timelineTs, `page.issueDetail.${key}`), key).toBe(1);
    }
  });

  it('renders IssueReactions through the real i18n plugin', async () => {
    setLocale('zh-CN');
    const wrapper = mount(IssueReactions, {
      props: { modelValue: { '👍': ['u1', 'u2', 'u3'] }, currentUserId: 'u1' },
      global: { plugins: [i18n], stubs: reactionStubs }
    });
    expect(wrapper.text()).toContain('添加反应');
    setLocale('en-US');
    await nextTick();
    expect(wrapper.text()).toContain('Add reaction');
    expect(wrapper.text()).toContain('and 1 others');
    wrapper.unmount();
  });

  it('refreshes rendered reaction names when the locale changes and modelValue does not', async () => {
    setLocale('zh-CN');
    const modelValue = { '👍': ['u1'] };
    const wrapper = mount(IssueReactions, {
      props: { modelValue, currentUserId: 'u1' },
      global: { plugins: [i18n], stubs: reactionStubs }
    });
    expect(wrapper.text()).toContain('赞成');
    expect(wrapper.text()).not.toContain('Thumbs up');
    setLocale('en-US');
    await nextTick();
    expect(wrapper.text()).toContain('Thumbs up');
    expect(wrapper.text()).not.toContain('赞成');
    expect(wrapper.props('modelValue')).toEqual(modelValue);
    wrapper.unmount();
  });
});

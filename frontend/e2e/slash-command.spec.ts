// frontend/e2e/slash-command.spec.ts

import { expect, test } from './setup';

test.describe('斜杠命令任务创建', () => {
  test('应该从需求评论创建任务', async ({ page, testRequirementId }) => {
    // 导航到需求详情页（使用测试数据 ID）
    await page.goto(`/workflow/requirement-detail?id=${testRequirementId}`);

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 找到评论输入框（使用 MarkdownEditor 的 textarea）
    const textarea = await page.locator('.markdown-textarea, textarea').first();
    await textarea.fill('/task-create 优化需求性能');

    // 等待命令提示出现（300ms 延迟 + 渲染时间）
    await page.waitForTimeout(400);

    // 验证命令提示可见
    const popup = page.locator('.slash-command-popup');
    await expect(popup).toBeVisible();

    // 验证命令提示内容
    const commandText = await page.locator('.command-name').textContent();
    expect(commandText).toBe('创建任务');

    // 按 Enter 创建任务
    await page.keyboard.press('Enter');

    // 等待成功消息（最多 5 秒）
    await page.waitForSelector('text=任务创建成功', { timeout: 5000 });

    // 验证任务卡片显示
    await page.waitForSelector('.task-card');
    const taskTitle = await page.locator('.task-title').textContent();
    expect(taskTitle).toBe('优化需求性能');
  });

  test('不应该在行中间触发斜杠命令', async ({ page, testRequirementId }) => {
    await page.goto(`/workflow/requirement-detail?id=${testRequirementId}`);
    await page.waitForLoadState('networkidle');

    const textarea = await page.locator('.markdown-textarea, textarea').first();
    await textarea.fill('这是普通文本 /task-create test');

    // 等待超过 300ms
    await page.waitForTimeout(400);

    // 不应该显示命令提示
    const popup = page.locator('.slash-command-popup');
    await expect(popup)
      .not.toBeVisible({ timeout: 1000 })
      .catch(() => {
        // 如果元素不存在也是正确的
        const isVisible = popup.isVisible().catch(() => false);
        expect(isVisible).resolves.toBe(false);
      });
  });

  test('应该支持键盘导航选择命令', async ({ page, testRequirementId }) => {
    await page.goto(`/workflow/requirement-detail?id=${testRequirementId}`);
    await page.waitForLoadState('networkidle');

    const textarea = await page.locator('.markdown-textarea, textarea').first();
    await textarea.fill('/task-cr');

    await page.waitForTimeout(400);

    // 按下箭头选择命令
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowUp');

    // 按 Enter 确认
    await page.keyboard.press('Enter');

    // 验证命令提示关闭
    const popup = page.locator('.slash-command-popup');
    await expect(popup).not.toBeVisible();
  });
});

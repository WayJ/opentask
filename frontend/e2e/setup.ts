// frontend/e2e/setup.ts

import { test as base } from '@playwright/test';

export const test = base.extend<{
  testRequirementId: string;
}>({
  testRequirementId: async (_params, use) => {
    // 在测试前创建测试需求数据
    // 可以通过 API 调用创建，或使用固定的测试 ID
    const testId = `e2e-test-requirement-${Date.now()}`;

    // 通过 API 创建测试需求
    // await createTestRequirement(testId);

    await use(testId);

    // 测试后清理
    // 删除测试数据
    // await deleteTestRequirement(testId);
  }
});

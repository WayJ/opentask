import { type ComputedRef, ref } from 'vue';
import { fetchRequirementByCode, getRequirementDetail } from '@/service/api/requirement';

// 类型别名 - 直接使用 any，因为后端没有对应的类型定义
export type Requirement = any;

export function useRequirementDetail(requirementId: ComputedRef<string>, requirementCode: ComputedRef<string>) {
  // 需求数据
  const requirement = ref<Requirement | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // 提取响应数据
  function extractResponseData(response: any) {
    if (response && typeof response === 'object') {
      // 如果响应中有 data 字段且是对象，取其内容（这是常见的格式）
      if ('data' in response && response.data && typeof response.data === 'object' && 'id' in response.data) {
        return response.data;
      } else if ('id' in response) {
        return response;
      }
    }
    return response;
  }

  // 显示错误信息
  function showError(err: any) {
    if (err?.detail && err.detail.includes('not found')) {
      const paramType = requirementCode.value ? '编号' : 'ID';
      const paramValue = requirementCode.value || requirementId.value;
      window.$message?.error(`未找到需求：${paramType} "${paramValue}" 不存在`);
    } else {
      window.$message?.error('加载需求详情失败');
    }
  }

  // 加载需求详情 - 支持通过 id 或 code 加载
  async function loadRequirement() {
    loading.value = true;
    error.value = null;

    try {
      let response;

      // 优先使用 code（更友好的 URL 格式）
      if (requirementCode.value) {
        response = await fetchRequirementByCode(requirementCode.value);
      } else if (requirementId.value) {
        response = await getRequirementDetail(requirementId.value);
      } else {
        error.value = '未提供需求 ID 或编号';
        window.$message?.error('未提供需求 ID 或编号');
        return;
      }

      // 处理不同的响应格式
      requirement.value = extractResponseData(response);
    } catch (err: any) {
      error.value = err?.message || err?.detail || '加载需求详情失败';
      showError(err);
    } finally {
      loading.value = false;
    }
  }

  return {
    requirement,
    loading,
    error,
    loadRequirement
  };
}

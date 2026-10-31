// composables/useComments.ts
import { ref } from 'vue';
import type { Ref } from 'vue';
import type { RequirementComment } from '@/service/api/requirement';
import { addRequirementComment, fetchRequirementComments } from '@/service/api/requirement';

export function useComments(requirementId: Ref<string>) {
  const comments = ref<RequirementComment[]>([]);
  const commentsLoading = ref(false);

  /** 加载评论列表 */
  const loadComments = async () => {
    if (!requirementId.value) return;

    try {
      commentsLoading.value = true;
      const response = await fetchRequirementComments(requirementId.value);
      comments.value = response.data?.rows || [];
    } catch (error) {
      console.error('加载评论失败:', error);
    } finally {
      commentsLoading.value = false;
    }
  };

  /** 添加评论 */
  const handleAddComment = async (content: string) => {
    if (!requirementId.value || !content.trim()) return;

    try {
      commentsLoading.value = true;
      await addRequirementComment(requirementId.value, content);
      // 重新加载评论列表
      await loadComments();
    } catch (error) {
      console.error('添加评论失败:', error);
      throw error;
    } finally {
      commentsLoading.value = false;
    }
  };

  return {
    comments,
    commentsLoading,
    loadComments,
    handleAddComment
  };
}

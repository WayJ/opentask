<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { NTag } from 'naive-ui';
import { buildIssueDetailLocation } from '@/utils/issue-board-nav';

defineOptions({ name: 'IssueReference' });

const props = withDefaults(
  defineProps<{
    issueId?: string | null;
    issueCode?: string | null;
    title?: string | null;
    size?: 'tiny' | 'small' | 'medium';
  }>(),
  { issueId: null, issueCode: null, title: null, size: 'small' }
);

const router = useRouter();
const label = computed(() => props.issueCode || props.issueId || 'Issue');

function open() {
  if (!props.issueId && !props.issueCode) return;
  const id = props.issueId || props.issueCode || '';
  router.push(buildIssueDetailLocation(id));
}
</script>

<template>
  <NTag
    class="issue-reference"
    :size="size"
    round
    :bordered="false"
    type="warning"
    style="cursor: pointer"
    :title="title || label"
    @click.stop="open"
  >
    {{ label }}
  </NTag>
</template>

<style scoped>
.issue-reference {
  vertical-align: middle;
}
</style>

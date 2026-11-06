<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { NButton, NCard, NInput, NSelect, NSpace, NSpin, NText } from 'naive-ui';
import {
  type FormFieldDef,
  type PublicFormSchema,
  fetchPublicFormSchema,
  formSubmitSuccessCopy,
  submitPublicForm
} from '@/service/api/forms';
import { $t } from '@/locales';

defineOptions({ name: 'PublicIssueFormPage' });

const route = useRoute();
const token = computed(() => String(route.params.token || ''));
const loading = ref(true);
const submitting = ref(false);
const schema = ref<PublicFormSchema | null>(null);
const errorMsg = ref('');
const success = ref<{ issueCode: string; title: string; triageEnqueued?: boolean } | null>(null);
const values = reactive<Record<string, string>>({});
const fieldErrors = ref<Record<string, string>>({});

const priorityOptions = [
  { label: 'low', value: 'low' },
  { label: 'medium', value: 'medium' },
  { label: 'high', value: 'high' },
  { label: 'critical', value: 'critical' }
];

async function load() {
  loading.value = true;
  errorMsg.value = '';
  success.value = null;
  try {
    if (!token.value) {
      errorMsg.value = '无效链接';
      return;
    }
    schema.value = await fetchPublicFormSchema(token.value);
    for (const f of schema.value.fields || []) {
      if (values[f.key] === undefined) values[f.key] = '';
    }
  } catch (e: any) {
    errorMsg.value = e?.message || '表单不存在或已禁用';
    schema.value = null;
  } finally {
    loading.value = false;
  }
}

function parseCustomRaw(raw: string): unknown {
  const t = String(raw).trim();
  if ((t.startsWith('{') && t.endsWith('}')) || (t.startsWith('[') && t.endsWith(']'))) {
    try {
      return JSON.parse(t);
    } catch {
      /* fallthrough as text */
    }
  }
  if (t === 'true' || t === 'false') return t === 'true';
  if (t !== '' && !Number.isNaN(Number(t))) return Number(t);
  return raw;
}

function buildPayload(fields: FormFieldDef[]) {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const raw = values[f.key];
    if (raw === undefined || raw === '') {
      // skip empty
    } else if (f.type === 'labels') {
      out[f.key] = String(raw)
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);
    } else if (f.type === 'custom_field') {
      out[f.key] = parseCustomRaw(String(raw));
    } else {
      out[f.key] = raw;
    }
  }
  return out;
}

async function onSubmit() {
  if (!schema.value) return;
  submitting.value = true;
  fieldErrors.value = {};
  try {
    const result = await submitPublicForm(token.value, buildPayload(schema.value.fields || []));
    success.value = {
      issueCode: result.issueCode,
      title: result.title,
      triageEnqueued: !!result.triageEnqueued
    };
  } catch (e: any) {
    const errs = e?.errors as { field?: string; message?: string }[] | undefined;
    if (Array.isArray(errs)) {
      const map: Record<string, string> = {};
      for (const er of errs) {
        if (er.field) map[er.field] = er.message || '无效';
      }
      fieldErrors.value = map;
    }
    window.$message?.error?.(e?.message || '提交失败');
  } finally {
    submitting.value = false;
  }
}

function resetForm() {
  success.value = null;
  Object.keys(values).forEach(k => {
    values[k] = '';
  });
  fieldErrors.value = {};
}

onMounted(load);
</script>

<template>
  <div class="ot-public-page min-h-screen">
    <NCard :title="schema?.name || $t('page.shell.issueForm')" :bordered="false" class="ot-public-card card-wrapper">
      <NSpin :show="loading">
        <div v-if="errorMsg" class="py-6 text-center text-red-500">{{ errorMsg }}</div>
        <div v-else-if="success" class="py-6 text-center">
          <div class="text-lg font-medium mb-2">提交成功</div>
          <NText depth="3">{{ formSubmitSuccessCopy(success) }}</NText>
          <div class="mt-4">
            <NButton @click="resetForm">再提交一条</NButton>
          </div>
        </div>
        <div v-else-if="schema">
          <NText v-if="schema.description" depth="3" class="mb-4 block">{{ schema.description }}</NText>
          <NSpace vertical>
            <div v-for="f in schema.fields" :key="f.key">
              <div class="mb-1 text-sm">
                {{ f.label || f.key }}
                <span v-if="f.required" class="text-red-500">*</span>
              </div>
              <NSelect
                v-if="f.type === 'priority'"
                v-model:value="values[f.key]"
                :options="priorityOptions"
                clearable
                placeholder="选择优先级"
              />
              <NInput
                v-else-if="f.type === 'description'"
                v-model:value="values[f.key]"
                type="textarea"
                :rows="4"
                :placeholder="f.help || f.label"
              />
              <NInput
                v-else
                v-model:value="values[f.key]"
                :placeholder="f.help || (f.type === 'labels' ? '逗号分隔标签名' : f.label)"
              />
              <div v-if="fieldErrors[f.key]" class="mt-1 text-xs text-red-500">{{ fieldErrors[f.key] }}</div>
            </div>
            <NButton type="primary" block :loading="submitting" @click="onSubmit">提交</NButton>
          </NSpace>
        </div>
      </NSpin>
    </NCard>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import {
  NAlert,
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NSpace,
  NTag,
  NText
} from 'naive-ui';
import { useLoading } from '@sa/hooks';
import { fetchCreateOAuthClient, fetchUpdateOAuthClient } from '@/service/api';
import { KNOWN_OAUTH_SCOPES, isKnownScope, normalizeScopeList, validateRedirectUri } from '@/utils/oauth2-client';
import type { Api } from '@/typings/api';

/**
 * 新建 / 编辑 OAuth 客户端抽屉
 *
 * - client_id 创建后不可改（唯一标识）；编辑时禁用；
 * - 回调地址：逐行输入（NDynamicInput 一行一条），逐条校验绝对 http(s) URL + 去重；
 *   提示「精确匹配，不支持通配/尾斜杠容错」；
 * - scopes：已知 scope 复选（目录真源 read_api.py）+ 自定义输入兜底（未来新增 scope 不阻断）；
 * - 创建成功 → **client_secret 明文仅此一次**，经 secret-modal 展示后即清空。
 */

defineOptions({
  name: 'OAuthClientFormDrawer'
});

const props = defineProps<{
  visible: boolean;
  /** 编辑的 client；null = 新建 */
  client?: Api.OAuth2.OAuthClient | null;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'submitted', secret?: string, clientName?: string): void;
}>();

const { loading: submitLoading, startLoading, endLoading } = useLoading();
const formRef = ref<FormInst | null>(null);

const isEdit = computed(() => Boolean(props.client));

interface FormState {
  client_id: string;
  name: string;
  description: string;
  redirect_uris: string[];
  knownScopes: string[];
  customScopes: string;
}

const form = reactive<FormState>({
  client_id: '',
  name: '',
  description: '',
  redirect_uris: [''],
  knownScopes: [],
  customScopes: ''
});

watch(
  () => props.visible,
  visible => {
    if (!visible) return;
    if (props.client) {
      const scopes = props.client.scopes || [];
      form.client_id = props.client.client_id;
      form.name = props.client.name;
      form.description = props.client.description || '';
      form.redirect_uris = props.client.redirect_uris.length ? [...props.client.redirect_uris] : [''];
      form.knownScopes = scopes.filter(isKnownScope);
      form.customScopes = scopes.filter(scope => !isKnownScope(scope)).join(' ');
    } else {
      form.client_id = '';
      form.name = '';
      form.description = '';
      form.redirect_uris = [''];
      form.knownScopes = [];
      form.customScopes = '';
    }
  },
  { immediate: true }
);

const rules: FormRules = {
  client_id: [
    { required: true, message: '请输入 client_id', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9._-]{1,64}$/,
      message: '1-64 位，仅字母/数字/点/下划线/连字符',
      trigger: 'blur'
    }
  ],
  name: [{ required: true, message: '请输入应用名称', trigger: 'blur' }],
  redirect_uris: [
    {
      validator: () => {
        const uris = form.redirect_uris.map(uri => uri.trim()).filter(Boolean);
        if (!uris.length) return new Error('至少一条回调地址');
        for (const uri of uris) {
          const result = validateRedirectUri(uri);
          if (!result.valid) return new Error(`${uri}：${result.reason}`);
        }
        const unique = new Set(uris);
        if (unique.size !== uris.length) return new Error('存在重复的回调地址');
        return true;
      },
      trigger: ['blur', 'change']
    }
  ],
  scopes: [
    {
      validator: () => {
        const all = [...form.knownScopes, ...normalizeScopeList(form.customScopes)];
        if (!all.length) return new Error('至少选择或填写一个 scope');
        return true;
      },
      trigger: 'blur'
    }
  ]
};

function addRedirectUri() {
  form.redirect_uris.push('');
}

function removeRedirectUri(index: number) {
  form.redirect_uris.splice(index, 1);
}

const hasKnownScopeError = computed(() => {
  const all = [...form.knownScopes, ...normalizeScopeList(form.customScopes)];
  return all.length === 0;
});

function getErrMsg(err: unknown, fallback: string) {
  const e = err as {
    response?: { data?: { detail?: string | { error?: string; error_description?: string } } };
    message?: string;
  } | null;
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && detail.error_description) return String(detail.error_description);
  return e?.message || fallback;
}

async function handleSubmit() {
  await formRef.value?.validate();
  const uris = form.redirect_uris.map(uri => uri.trim()).filter(Boolean);
  const scopes = [...form.knownScopes, ...normalizeScopeList(form.customScopes)];

  startLoading();
  try {
    if (isEdit.value && props.client) {
      await fetchUpdateOAuthClient(props.client.client_id, {
        name: form.name.trim(),
        description: form.description || undefined,
        redirect_uris: uris,
        scopes
      });
      window.$message?.success('客户端已更新');
      emit('submitted');
      emit('update:visible', false);
    } else {
      const { error, data } = await fetchCreateOAuthClient({
        client_id: form.client_id.trim(),
        name: form.name.trim(),
        description: form.description || undefined,
        redirect_uris: uris,
        scopes
      });
      if (error) {
        window.$message?.error(getErrMsg(error, '创建失败'));
        return;
      }
      window.$message?.success('客户端已创建，请立即保存密钥');
      // 密钥明文交给父组件弹窗展示（仅此一次）
      emit('submitted', data?.client_secret || '', data?.client?.name || form.name);
      emit('update:visible', false);
    }
  } finally {
    endLoading();
  }
}
</script>

<template>
  <NDrawer :show="visible" :width="520" @update:show="(v: boolean) => emit('update:visible', v)">
    <NDrawerContent :title="isEdit ? '编辑 OAuth 客户端' : '新建 OAuth 客户端'" closable>
      <NForm ref="formRef" :model="form" :rules="rules" label-placement="top" require-mark-placement="right-hanging">
        <NFormItem label="client_id" path="client_id">
          <NInput v-model:value="form.client_id" :disabled="isEdit" placeholder="如 xl-cowork-prod（创建后不可修改）" />
        </NFormItem>

        <NFormItem label="应用名称" path="name">
          <NInput v-model:value="form.name" placeholder="授权同意页会展示此名称" />
        </NFormItem>

        <NFormItem label="应用描述" path="description">
          <NInput v-model:value="form.description" type="textarea" :rows="2" placeholder="可选；授权同意页会展示" />
        </NFormItem>

        <NFormItem label="回调地址白名单（redirect_uris）" path="redirect_uris">
          <div class="oauth2-form__redirect">
            <div v-for="(uri, index) in form.redirect_uris" :key="index" class="oauth2-form__row">
              <NInput v-model:value="form.redirect_uris[index]" placeholder="https://…" />
              <NButton
                v-if="form.redirect_uris.length > 1"
                quaternary
                type="error"
                size="small"
                @click="removeRedirectUri(index)"
              >
                删除
              </NButton>
            </div>
            <NButton dashed block size="small" @click="addRedirectUri">添加一条回调地址</NButton>
            <NText depth="3" class="oauth2-form__hint">
              一行一条，须为绝对 http(s) URL；授权时与请求参数
              <b>逐字符精确匹配</b>
              （不支持通配、前缀、尾斜杠容错）。 小蓝 CoWork 的实际回调地址以其应用后台登记的为准。
            </NText>
          </div>
        </NFormItem>

        <NFormItem label="授权范围（scopes）" path="scopes">
          <div class="oauth2-form__scopes">
            <NCheckboxGroup v-model:value="form.knownScopes">
              <NSpace vertical size="small">
                <NCheckbox v-for="item in KNOWN_OAUTH_SCOPES" :key="item.scope" :value="item.scope">
                  <NTag size="small" :bordered="false" class="oauth2-form__scope-tag">{{ item.scope }}</NTag>
                  {{ item.label }}
                  <NText depth="3" class="oauth2-form__endpoint">{{ item.endpoint }}</NText>
                </NCheckbox>
              </NSpace>
            </NCheckboxGroup>
            <NInput
              v-model:value="form.customScopes"
              size="small"
              placeholder="自定义 scope（可选，逗号/空格分隔；服务端支持范围外的不建议登记）"
            />
            <NText depth="3" class="oauth2-form__hint">
              scopes 是该客户端可请求权限的
              <b>上界</b>
              ：小蓝请求超出即被拒绝（invalid_scope）。请按最小必要勾选； 成员授权时仍会在同意页单独确认。
            </NText>
            <NAlert v-if="hasKnownScopeError" type="warning" :show-icon="false">至少选择或填写一个 scope</NAlert>
          </div>
        </NFormItem>
      </NForm>

      <NAlert v-if="!isEdit" type="info" :show-icon="true" style="margin-top: 4px">
        创建成功后
        <b>client_secret 只显示一次</b>
        ，请立即复制保存。若回调地址依赖小蓝侧 appKey
        后才确定，可先用占位地址创建，稍后在列表里「编辑」回填（精确匹配）。
      </NAlert>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="emit('update:visible', false)">取消</NButton>
          <NButton type="primary" :loading="submitLoading" @click="handleSubmit">
            {{ isEdit ? '保存' : '创建' }}
          </NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped>
.oauth2-form__row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.oauth2-form__redirect,
.oauth2-form__scopes {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.oauth2-form__hint {
  font-size: 12px;
  line-height: 1.6;
}

.oauth2-form__scope-tag {
  margin-right: 6px;
}

.oauth2-form__endpoint {
  font-size: 12px;
  margin-left: 6px;
}
</style>

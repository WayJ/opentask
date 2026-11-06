<script setup lang="ts">
import { computed, ref } from 'vue';
import { NAlert, NButton, NCode, NCollapse, NCollapseItem, NSpace, NTable, NTag, NText } from 'naive-ui';

/**
 * 小蓝 CoWork 接入说明面板（与 docs/oauth2-client-onboarding.md 同源）
 *
 * 两条路径：
 * 1. **自动接入**（推荐）：小蓝后端按契约发起安装 → 管理员在 /oauth2/install/:id 确认
 *    → 一次性 code → 小蓝服务端兑换密钥。全程无需复制长期凭据（PKCE verifier 只在小蓝侧）。
 * 2. **手工登记**：管理员在本页直接创建 client，把 client_id/client_secret 交给小蓝。
 *
 * 边界（不可承诺）：
 * - 小蓝侧应用创建、appKey 生成、回调地址登记在小蓝 CoWork 后台完成，本仓不代劳；
 * - 本仓不做"跨仓一键对接"；成员授权（数据访问）仍由成员在同意页单独同意。
 */

defineOptions({
  name: 'OAuthGuidePanel'
});

const showEndpoints = ref(true);

/** 前端地址：授权入口（浏览器跳转目标） */
const frontendOrigin = computed(() => window.location.origin);

/** 后端地址：标准 OAuth2 协议端点（与 API 请求同源或反代） */
const apiOrigin = computed(() => {
  const base = import.meta.env.VITE_SERVICE_BASE_URL as string | undefined;
  if (!base || base.startsWith('/')) return window.location.origin;
  return base.replace(/\/$/, '');
});

function copy(text: string) {
  navigator.clipboard
    .writeText(text)
    .then(() => window.$message?.success('已复制'))
    .catch(() => window.$message?.error('复制失败，请手动复制'));
}

const endpoints: { label: string; value: string; note: string }[] = [
  {
    label: '授权入口（浏览器跳转）',
    value: `${frontendOrigin.value}/oauth2/authorize?client_id=…&redirect_uri=…&response_type=code&scope=…&state=…`,
    note: 'SPA 页面；成员在此单独同意'
  },
  {
    label: '换取令牌',
    value: `POST ${apiOrigin.value}/oauth2/token`,
    note: 'grant_type=authorization_code / refresh_token'
  },
  { label: '用户信息', value: `GET ${apiOrigin.value}/oauth2/userinfo`, note: 'scope: profile' },
  { label: '吊销令牌', value: `POST ${apiOrigin.value}/oauth2/revoke`, note: 'RFC 7009' },
  {
    label: '只读数据面',
    value: `GET ${apiOrigin.value}/oauth2/api/tasks | projects | requirements | me`,
    note: '按 scope 授权'
  }
];
</script>

<template>
  <div class="oauth2-guide">
    <NCollapse :default-expanded-names="['auto', 'manual']">
      <NCollapseItem title="方式一：自动接入（推荐，小蓝发起）" name="auto">
        <ol class="oauth2-guide__steps">
          <li>
            小蓝后端生成一次性
            <NTag size="small" :bordered="false">verifier</NTag>
            （高熵随机串，只留小蓝侧）， 计算
            <NCode code="challenge = BASE64URL(SHA256(verifier))" language="text" inline />
            ；
          </li>
          <li>
            小蓝后端调
            <NCode code="POST /api/oauth2/install/requests" language="text" inline />
            提交应用信息 + challenge，拿到
            <NTag size="small" :bordered="false">approval_url</NTag>
            ；
          </li>
          <li>
            小蓝把 approval_url 交给贵方管理员（跳转/二维码均可）——管理员登录 OpenTask 后在
            <b>安装确认页</b>
            核对应用名、回调白名单、scopes 与来源，点「确认安装」；
          </li>
          <li>
            OpenTask 把管理员浏览器回跳到小蓝回调地址，带
            <NTag size="small" :bordered="false">code</NTag>
            （一次性安装码，10 分钟有效）与
            <NTag size="small" :bordered="false">state</NTag>
            ；
          </li>
          <li>
            小蓝服务端调
            <NCode code="POST /api/oauth2/install/exchange" language="text" inline />
            （code + verifier）兑换
            <b>client_id + client_secret</b>
            （密钥只在此响应出现一次）；
          </li>
          <li>
            之后成员在小蓝侧点「连接 OpenTask」→ 浏览器跳授权入口 → 成员
            <b>单独</b>
            同意 → 小蓝用 client 凭证换 token 访问只读数据面。
          </li>
        </ol>
        <NAlert type="info" :show-icon="false">
          <ul class="oauth2-guide__notes">
            <li>
              兑换响应若丢失：恢复窗口（10 分钟）内用同一 verifier 重试会换发
              <b>新密钥</b>
              ；窗口外须重新发起安装；
            </li>
            <li>「已兑换」状态本身不代表小蓝拿到密钥——只有拿到含 client_secret 的响应才算成功；</li>
            <li>
              协议细节（错误码、安全约束、小蓝侧实现清单与参考代码）见
              <NText code>docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md</NText>
              。
            </li>
          </ul>
        </NAlert>
      </NCollapseItem>

      <NCollapseItem title="方式二：手工登记（管理员在本页直接创建）" name="manual">
        <ol class="oauth2-guide__steps">
          <li>点「新建客户端」，填写名称、回调地址白名单、勾选 scopes；</li>
          <li>
            创建成功后
            <b>立即复制</b>
            client_secret（仅显示一次），连同 client_id 交给小蓝侧；
          </li>
          <li>
            若回调地址依赖小蓝 appKey（appKey 创建后才确定）：先建 client 占位，等小蓝侧拿到实际回调地址后
            回到本页「编辑」回填——
            <b>逐字符精确匹配</b>
            ；
          </li>
          <li>密钥丢失只能「轮换密钥」（旧密钥立即失效）。</li>
        </ol>
        <NAlert type="warning" :show-icon="false">
          本仓不承诺跨仓一键对接：小蓝侧应用创建、appKey 生成、回调地址登记仍需在小蓝 CoWork 后台完成。
        </NAlert>
      </NCollapseItem>

      <NCollapseItem title="协议端点清单（安装完成后小蓝使用）" name="endpoints">
        <NTable size="small" :bordered="false" :bottom-bordered="true" class="oauth2-guide__table">
          <thead>
            <tr>
              <th style="width: 200px">用途</th>
              <th>端点</th>
              <th style="width: 220px">说明</th>
              <th style="width: 70px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in endpoints" :key="item.label">
              <td>{{ item.label }}</td>
              <td><NCode :code="item.value" language="text" word-wrap /></td>
              <td>
                <NText depth="3">{{ item.note }}</NText>
              </td>
              <td>
                <NButton size="tiny" quaternary @click="copy(item.value)">复制</NButton>
              </td>
            </tr>
          </tbody>
        </NTable>
        <NSpace vertical size="small" style="margin-top: 10px">
          <NText depth="3" class="oauth2-guide__hint">
            前端地址取当前站点 origin；后端地址取本页 API 服务地址。若贵方部署另有公网域名，请以实际域名为准。
          </NText>
          <NText depth="3" class="oauth2-guide__hint">
            <NSpace :size="4" align="center" :wrap="false">
              <NButton size="tiny" quaternary type="primary" @click="showEndpoints = !showEndpoints">
                {{ showEndpoints ? '收起 scope 说明' : '展开 scope 说明' }}
              </NButton>
            </NSpace>
          </NText>
        </NSpace>
      </NCollapseItem>
    </NCollapse>
  </div>
</template>

<style scoped>
.oauth2-guide__steps {
  padding-left: 20px;
  margin: 0 0 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  line-height: 1.7;
}

.oauth2-guide__notes {
  padding-left: 16px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}

.oauth2-guide__table {
  margin-top: 4px;
}

.oauth2-guide__hint {
  font-size: 12px;
}
</style>

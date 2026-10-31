/** Access Token Store */
import { ref } from 'vue';
import { defineStore } from 'pinia';
import {
  type AccessToken,
  type AccessTokenWithToken,
  type CreateAccessTokenDto,
  accessTokenApi
} from '@/service/api/access-token';

export const useAccessTokenStore = defineStore('accessToken', () => {
  const tokens = ref<AccessToken[]>([]);
  const loading = ref(false);

  /** 加载所有 Access Token */
  async function loadTokens() {
    loading.value = true;
    try {
      const response = await accessTokenApi.list();
      tokens.value = Array.isArray(response.data) ? response.data : [];
    } finally {
      loading.value = false;
    }
  }

  /** 创建 Access Token */
  async function createToken(data: CreateAccessTokenDto): Promise<AccessTokenWithToken> {
    const response = await accessTokenApi.create(data);
    await loadTokens();
    return response.data!;
  }

  /** 删除 Access Token */
  async function removeToken(id: string) {
    await accessTokenApi.delete(id);
    await loadTokens();
  }

  return {
    tokens,
    loading,
    loadTokens,
    createToken,
    removeToken
  };
});

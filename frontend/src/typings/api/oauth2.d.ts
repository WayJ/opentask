declare namespace Api {
  /**
   * namespace OAuth2
   *
   * backend api module: "oauth2"
   *
   * 契约权威：docs/superpowers/specs/2026-11-02-oauth2-provider-design.md
   */
  namespace OAuth2 {
    /** 授权请求参数（SPA 同意页从 URL query 读取后转发给后端） */
    interface AuthorizeParams {
      client_id: string;
      redirect_uri: string;
      response_type?: string;
      scope?: string;
      state?: string;
      code_challenge?: string;
      code_challenge_method?: string;
      resource?: string;
    }

    /** 同意页上下文（后端校验后返回） */
    interface AuthorizeContext {
      client_id: string;
      client_name: string;
      client_description?: string | null;
      /** 授予的 scope 列表 */
      scope: string[];
      redirect_uri: string;
      /** 回调地址的主机名（展示用，防钓鱼提示） */
      redirect_host: string;
      state?: string | null;
      code_challenge?: string | null;
      code_challenge_method?: string | null;
      resource?: string | null;
    }

    /** 同意/拒绝请求 */
    interface AuthorizeDecision {
      client_id: string;
      redirect_uri: string;
      scope: string;
      state?: string;
      code_challenge?: string;
      code_challenge_method?: string;
      resource?: string;
      decision: 'approve' | 'deny';
    }

    /** 决策结果——前端据此整页跳转 */
    interface AuthorizeDecisionResult {
      /** 应跳转的完整 URL（含 code 或 error 与 state） */
      redirect_to: string;
    }
  }
}

declare namespace Api {
  namespace OAuth2 {
    // ===== 客户端管理（E100，对接既有 /api/oauth2/clients） =====

    /** client 视图（后端 OAuthClientView——**不含 secret 明文**） */
    interface OAuthClient {
      client_id: string;
      name: string;
      description?: string | null;
      redirect_uris: string[];
      scopes: string[];
      grant_types: string[];
      status: string;
      /** 密钥前缀（展示用，如 ocs_1a2b…） */
      secret_prefix: string;
      created_at: string;
    }

    interface OAuthClientCreate {
      client_id: string;
      name: string;
      description?: string;
      redirect_uris: string[];
      scopes: string[];
      grant_types?: string[];
    }

    interface OAuthClientUpdate {
      name?: string;
      description?: string;
      redirect_uris?: string[];
      scopes?: string[];
      /** ACTIVE / DISABLED */
      status?: string;
    }

    /** 注册/轮换密钥的响应——**secret 明文仅此一次** */
    interface OAuthClientCreated {
      client: OAuthClient;
      client_secret: string;
    }

    // ===== 自动接入（E101，对接 /api/oauth2/install/*） =====

    interface InstallRequestCreate {
      client_id: string;
      name: string;
      description?: string;
      redirect_uris: string[];
      scopes: string[];
      grant_types?: string[];
      callback_url: string;
      state?: string;
      code_challenge: string;
      code_challenge_method: 'S256';
    }

    interface InstallRequestCreated {
      install_id: string;
      status: string;
      approval_url: string;
      approval_path: string;
      expires_at: string;
      reused: boolean;
    }

    /** 安装申请视图（**不含** 安装码 / challenge / state） */
    interface InstallRequestView {
      install_id: string;
      status: string;
      client_id: string;
      name: string;
      description?: string | null;
      redirect_uris: string[];
      scopes: string[];
      grant_types: string[];
      callback_url: string;
      callback_host: string;
      expires_at: string;
      created_at: string;
      approved_at?: string | null;
      consumed_at?: string | null;
      recovery_count: number;
      request_ip?: string | null;
      user_agent?: string | null;
    }

    interface InstallStatusView {
      install_id: string;
      status: string;
      client_id: string;
      created_at: string;
      expires_at: string;
      approved_at?: string | null;
      consumed_at?: string | null;
      recoverable: boolean;
    }

    interface InstallDecisionView {
      install_id: string;
      status: string;
      redirect_to?: string | null;
    }

    /** 兑换结果——**client_secret 明文仅此一次** */
    interface InstallExchangeView {
      client_id: string;
      client_secret: string;
      name: string;
      description?: string | null;
      redirect_uris: string[];
      scopes: string[];
      grant_types: string[];
      recovered: boolean;
    }
  }
}

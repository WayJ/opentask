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
    }

    /** 同意/拒绝请求 */
    interface AuthorizeDecision {
      client_id: string;
      redirect_uri: string;
      scope: string;
      state?: string;
      decision: 'approve' | 'deny';
    }

    /** 决策结果——前端据此整页跳转 */
    interface AuthorizeDecisionResult {
      /** 应跳转的完整 URL（含 code 或 error 与 state） */
      redirect_to: string;
    }
  }
}

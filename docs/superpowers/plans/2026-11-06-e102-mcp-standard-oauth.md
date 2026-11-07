# E102 标准 MCP OAuth Implementation Plan

**Goal:** 管理端登记 MCP 应用，成员在工作台通过标准 OAuth 独立授权并调用工具。

**Architecture:** OpenTask 发布标准元数据与 DCR、实施 PKCE 和资源绑定；小蓝按元数据发现并选择注册方式，用成员级 state/令牌完成授权和平台代理调用。

**Tech Stack:** Python/FastAPI、PostgreSQL、Vue、Java/Spring、Redis、React。

**Spec:** docs/superpowers/specs/2026-11-06-e102-mcp-standard-oauth-design.md

## 全局约束

- 禁止密钥进入浏览器、日志与 URL；兼容现有已登记应用。
- HTTP 仅在显式配置的兼容模式或本地回环使用，默认标准路径遵守 HTTPS。
- 每项先用对应的真实入口写失败测试，再实现并复测；不得将单元测试冒充两端验收。

## 任务

- [ ] OpenTask：测试并实现 RFC 7636 S256 challenge/verifier，授权请求经同意页完整传递，错误 verifier、回调不匹配及并发重放不能消费或签发令牌。
- [ ] OpenTask：测试并实现资源元数据、授权服务器元数据、RFC 7591 DCR、RFC 8707 资源绑定和授权 scope 限制，维持已有授权客户端兼容。
- [ ] 小蓝：测试并实现服务发现、可信端点和注册策略；应用登记只产生工作区应用，不代表任何成员授权。
- [ ] 小蓝：测试并实现成员工作台 PKCE state/verifier 绑定、令牌加密及资源范围；保留预注册回退与显式 HTTP 兼容。
- [ ] 以 GitLab MCP 协议桩验证非 `/mcp` 路径、`mcp` scope、DCR 和无 userinfo 情况；记录真实 GitLab 未验证的范围。
- [ ] 本地隔离栈验证 OpenTask + 小蓝的管理员登记、两成员分别授权、调用工具、跨工作区隔离和失败场景；完成相应测试门禁与验收记录。

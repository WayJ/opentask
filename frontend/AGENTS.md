### 开发

后端的本地开发环境启动在 7377。
前端默认端口 9527。`pnpm dev` 使用 Vite，开发时代理前缀是 `/opentask`，生产构建的 base 是 `/`。

## 注意
- 禁止修改前端服务端口，固定保持 9527
- 如果 9527 端口被占用，先关闭占用端口的服务

## 规范
- 路由是 elegant-router 自动生成
- 前端的 api 层在 frontend/src/service/api
- 检查：`pnpm lint`、`pnpm build`、`pnpm test`

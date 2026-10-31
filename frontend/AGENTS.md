### 开发

后端的本地开发环境启动在 7377
前端默认端口 9527，通过 webpack 为 /opentask/ 配置了代理请求后端

## 注意
- 禁止修改前端服务端口，固定保持9527
- 如果9527端口被占用，你要先关闭占用端口的服务

## 规范
- 路由是 elegant-router 自动生成
- 前端的api层在 frontend\src\service\api
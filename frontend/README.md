## 简介

OpenTask 前端是 Vue 3 + Vite + TypeScript 应用，使用 Pinia、Naive UI 和 elegant-router。开发服务器固定端口 9527。生产构建放在站点根，浏览器地址是 `/` 和 `/login`。

## 特性

- **前沿技术应用**：采用 Vue3, Vite7, TypeScript, Pinia 和 UnoCSS 等最新流行的技术栈。
- **清晰的项目架构**：采用 pnpm monorepo 架构，结构清晰，优雅易懂。
- **代码检查**：`pnpm lint`、`pnpm build`、`pnpm test`。
- **TypeScript**： 支持严格的类型检查，提高代码的可维护性。
- **丰富的主题配置**：内置多样的主题配置，与 UnoCSS 完美结合。
- **内置国际化方案**：轻松实现多语言支持。
- **自动化文件路由系统**：自动生成路由导入、声明和类型。更多细节请查看 [Elegant Router](https://github.com/soybeanjs/elegant-router)。
- **灵活的权限路由**：同时支持前端静态路由和后端动态路由。
- **丰富的页面组件**：内置多样页面和组件，包括403、404、500页面，以及布局组件、标签组件、主题配置组件等。
- **命令行工具**：内置高效的命令行工具，git提交、删除文件、发布等。
- **移动端适配**：完美支持移动端，实现自适应布局。


## 使用

**环境准备**

确保你的环境满足以下要求：

- **git**: 你需要git来克隆和管理项目版本。
- **NodeJS**: >=20.19.0，推荐 20.19.0 或更高。
- **pnpm**: >= 10.5.0，推荐 10.5.0 或更高。

**安装依赖**

```bash
pnpm i
```
> 由于本项目采用了 pnpm monorepo 的管理方式，因此请不要使用 npm 或 yarn 来安装依赖。

**启动项目**

```bash
pnpm dev
```

**构建项目**

```bash
pnpm build
```

## 容器化部署

前端提供自己的镜像（构建期 pnpm/vite → 运行期 nginx 托管静态资源）：

```bash
# 在 frontend/ 目录下构建（上下文为 frontend/）
docker build -f frontend/Dockerfile -t opentask-frontend frontend

# 或用仓库根的编排起全栈（postgres + 后端 7377 + 前端 8080）
cd .. && AUTH_SECRET_KEY=$(openssl rand -hex 32) docker compose up -d
```

### 路径前缀拓扑

生产构建使用站点根：

| 变量 | 值 | 作用 |
|---|---|---|
| `VITE_BASE_URL` | `/` | vite base 与 history 路由基址。产物引用 `/assets/*` |
| `VITE_SERVICE_BASE_URL` | `/` | 浏览器请求 `/api/*` |

容器内 `frontend/nginx.conf` 把 `/assets/` 当静态文件，把 `/api/` 和 `/ws/` 原样转到后端 7377，其余路径回退 `index.html`。宿主示例是 `deploy/nginx/opentask-site.conf`。不设置 `X-Workspace-Id`。

本地 `pnpm dev` 使用 `VITE_BASE_URL=/`，Vite 只在开发时把 `/opentask` 代理到 `http://localhost:7377`。

### 低内存机器上的发布

生产服务器内存不够跑 `pnpm install + vite build` 时，用**预构建产物**路径：
开发机构建出 `dist`，传到服务器后由 `frontend/Dockerfile.dist` 打包成镜像
（只有 COPY，原生架构几秒完成）。完整流程见 `deploy/deploy.sh`。

## Git 提交规范

本项目已内置 `commit` 命令，您可以通过执行 `pnpm commit` 来生成符合 [Conventional Commits]([conventionalcommits](https://www.conventionalcommits.org/)) 规范的提交信息。在提交PR时，请务必使用 `commit` 命令来创建提交信息，以确保信息的规范性。


## 浏览器支持

推荐使用最新版的 Chrome 浏览器进行开发，以获得更好的体验。

| [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/archive/internet-explorer_9-11/internet-explorer_9-11_48x48.png" alt="IE" width="24px" height="24px"  />](http://godban.github.io/browsers-support-badges/) | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/edge/edge_48x48.png" alt=" Edge" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/) | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/firefox/firefox_48x48.png" alt="Firefox" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/) | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/chrome/chrome_48x48.png" alt="Chrome" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/) | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/safari/safari_48x48.png" alt="Safari" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/) |
| --- | --- | --- | --- | --- |
| not support | last 2 versions | last 2 versions | last 2 versions | last 2 versions |

## 开源作者

[Soybean](https://github.com/honghuangdc)
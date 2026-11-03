# 下线「工作流指南」与「任务中心」前端页面（2026-11-03）

## 做了什么

按用户要求下线两个前端页面及其入口：

| 页面 | 路由 | 处理 |
|---|---|---|
| 工作流指南 | `/workflow-guide` | 删除 `frontend/src/views/workflow-guide/`、路由、菜单项、中英文案 |
| 任务中心 | `/mission-center` | 删除 `frontend/src/views/mission-center/`、路由、菜单项、中英文案 |

连带清理：

- `frontend/src/service/api/mission-center.ts`（前端 API 封装）+ `service/api/index.ts` 的 barrel 导出
- `frontend/build/plugins/router.ts`：`constantRoutes` 去掉 `workflow-guide`（它原是无需登录即可访问的常量路由）
- `frontend/src/components/CommentDisplay.vue`：评论里嵌入的任务卡片原本 `window.open('/mission-center/tasks/:id')`，
  页面下线后改为**纯展示**（去掉 onclick 与 hover 位移）
- `frontend/src/store/modules/route/shared.ts`：注释里「任务中心」的举例去掉
- `frontend/public/docs/OPENTASK_WORKFLOW_GUIDE.md`：保留文档正文，只在路由表处标注两个页面已下线
- 路由由 elegant-router 自动重新生成（`routes.ts` / `imports.ts` / `transform.ts` / `elegant-router.d.ts`）

## 没有动的部分

- **后端 `/api/mission-center` 接口整体保留**（`backend/opentask/api/mission_center/` 等），按用户决定本次只下线前端页面 + 前端 API 封装。
- `frontend/public/docs/OPENTASK_WORKFLOW_GUIDE.md` 文档正文保留（仍可静态访问 `/docs/OPENTASK_WORKFLOW_GUIDE.md`）。
- 数据库里的历史任务数据未做任何清理。

## 验证

- `npm run lint`：0 error（242 warning，全部为既有告警）
- `npm run build`：成功；`dist/assets` 中不再含 `workflow-guide` / `mission-center` 字符串
- `npm run typecheck`：仅 `src/typings/components.d.ts` 报错，且该文件在改动前的 HEAD 里就已有非法标识符
  （`const 'IconMdi:arrowLeft'`），属既有问题，与本次改动无关
- 浏览器（Playwright + 本地后端 7377 / 前端 9527）：登录后侧边栏为
  工作管理 / 首页 / 研发流水线 / 问题管理 / 系统管理 / 研发效能看板，**无**「工作流指南」「任务中心」；
  访问 `/workflow-guide` 与 `/mission-center` 均落到 404 页；首页正常渲染

## 收尾

- 验证用的临时管理员账号 `uicheck` 已删除；本次启动的前后端进程已停掉（恢复到会话开始时的状态）。

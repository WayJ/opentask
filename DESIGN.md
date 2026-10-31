---
version: "1.2"
name: AI 研发管理平台前端样式规范
description: 本项目前端的视觉真源——基于 soybean-admin 布局壳与 Naive UI 默认组件主题（主题色 #646cff），叠加 src/styles/design-system.css 的 --color-* 通用令牌；深浅双主题由 Naive UI darkTheme 整组切换。

  # 改令牌先改这里，再落到样式与组件。
  # --color-* 与 src/styles/design-system.css 一一对应；Naive 组件色由 themeColor 派生，不在组件内散写。
colors:
  # 主题色（src/theme/settings.ts themeColor，Naive UI primary 及派生色）
  theme: "#646cff"

  # 通用令牌（design-system.css）
  primary: "#3b82f6"            # 品牌蓝：图形强调、链接倾向
  primary-hover: "#2563eb"
  primary-active: "#1d4ed8"
  success: "#22c55e"
  warning: "#f59e0b"
  danger: "#ef4444"
  info: "#8b5cf6"
  bg-primary: "#ffffff"          # 卡片与浮层表面
  bg-secondary: "#f7f8fa"        # 页面画布
  bg-tertiary: "#f0f2f5"         # 内嵌区域
  bg-hover: "#f4f5f7"
  bg-dark: "#111827"             # 暗色画布与深色块
  text-primary: "#111827"
  text-secondary: "#6b7280"
  text-tertiary: "#9ca3af"
  border-subtle: "#e5e7eb"
  border-default: "#d1d5db"
  border-strong: "#9ca3af"

typography:
  family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"
  base: 14px                     # Naive UI 默认正文
  xs: 12px                       # 辅助说明、表格密集信息
  sm: 14px                       # 正文、表单、按钮
  md: 16px                       # 卡片标题
  lg: 18px                       # 页面标题（辅助层级）
  xl: 20px                       # 页面主标题
  weight: { normal: 400, medium: 500, semibold: 600, bold: 700 }

rounded:
  sm: 6px       # 小控件、标签
  md: 8px       # 按钮、输入（Naive themeRadius 默认 6px，可配置）
  lg: 12px      # 卡片
  full: 9999px  # 头像、胶囊

spacing:
  scale: [4px, 8px, 12px, 16px, 24px, 32px]

elevation:
  sm: "0 1px 2px rgba(0,0,0,.05)"
  md: "0 4px 6px rgba(0,0,0,.07)"
  lg: "0 10px 15px rgba(0,0,0,.1)"

components:
  # 组件形态全部取 Naive UI 默认（n-button/n-input/n-card/n-modal/n-drawer/n-table 等），
  # 主题色由 themeColor 派生；仅布局壳与业务排版自定义。
  layout: { sidebar: 220px, header: 64px, content-padding: 16px }   # soybean 壳
  card: { bg: bg-primary, border: border-subtle, radius: lg, pad: 16-24px }
  button: { primary: theme 色实底, secondary: 白底细边, danger: danger 色 }
  table: { header: bg-secondary, row-hover: bg-hover }
  status: { success/warning/danger/info 对应语义色 + NTag 默认形态 }
---

# AI 研发管理平台 前端样式规范

## Overview

本文件是前端视觉真源。技术底座为 **Vue 3 + Naive UI + soybean-admin 布局壳 + Tailwind（UnoCSS）原子类**：

- **组件主题**：全部使用 Naive UI 默认组件形态，主题色 `themeColor: #646cff`（`src/theme/settings.ts`）由 Naive 派生 primary/hover/pressed 全套；不在业务组件内覆盖组件级颜色。
- **通用令牌**：`src/styles/design-system.css` 提供 `--color-* / --space-* / --radius-* / --font-*` 变量，用于业务页面的自定义排版、图标色、状态色。
- **深浅主题**：Naive `darkTheme` 整组切换，暗色值由 Naive 主题算法派生，不自建第二套暗色令牌。
- **原子类优先**：布局、间距、字号优先用 UnoCSS 工具类（`flex`、`px-16px`、`text-14px`），语义色用上面令牌。

> 2026-10-24：曾按「小蓝 CoWork」暖白/墨色/珊瑚橙规范全站换皮，已按要求整体撤回；本文档同步回退为原样式规范。

## Colors

- 主操作、选中态、链接：Naive primary（#646cff 派生）。
- 语义状态：`success #22c55e / warning #f59e0b / danger #ef4444 / info #8b5cf6`，配合 `NTag / NAlert` 默认形态使用。
- 自定义图形与强调：`--color-primary` 蓝（#3b82f6），不要与 Naive primary 混用于同一交互层级。
- 文字层级：`text-primary → text-secondary → text-tertiary` 三级，不额外发明中间灰。
- 边框：默认 `border-subtle`，强调分隔 `border-default`。

## Typography

正文 14px 为基准；表格与辅助说明可降 12px；页面标题 20px / 卡片标题 16px / 语义标题 18px。字重以 400/500/600 为主。数字列可用 `tabular-nums` 对齐。

## Layout

soybean-admin 壳：左侧菜单 + 顶栏 + 多标签页 + 内容区（16px 内边距）。业务页面用 `NCard` 分组，卡片间距 16px；列表页 = 工具栏（搜索/筛选/操作）+ `NDataTable`，表头浅底 `bg-secondary`、行悬停 `bg-hover`。

## Components

- 按钮一组只留一个 primary；危险操作用 `type="error"`。
- 表单用 `NForm/NInput/NSelect` 默认形态，label-placement 跟随页面密度。
- 弹窗 `NModal`（默认 4-8px 圆角、浮层投影 md）、抽屉 `NDrawer`。
- 状态展示用 `NTag` 圆点/文字，不自绘彩色徽标。

## Do's and Don'ts

**Do**
- 颜色从 `--color-*` 令牌或 Naive 主题取值；新增令牌先登记本文件。
- 图表配色可用 primary/info/success/warning 派生序列。

**Don't**
- 不在组件内写死 hex（历史遗留逐步收敛到令牌）。
- 不引入第二套暗色变量或按页面局部换主题色。

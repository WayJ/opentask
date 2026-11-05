---
version: "2.0"
name: OpenTask Linear product UI
description: >
  OpenTask 前端视觉真源——适配 Linear.app 产品 UI 语言（getdesign linear.app），
  保留 Vue3 + Naive UI + soybean-admin 壳 + UnoCSS。主题色 #5e6ad2；默认亮色画布；
  暗色映射 dark canvas 令牌。不嵌入 Linear 专有字体，使用系统字体栈。

colors:
  # Naive themeColor（src/theme/settings.ts）
  theme: "#5e6ad2"
  primary: "#5e6ad2"
  primary-hover: "#828fff"
  primary-active: "#5e69d1"
  on-primary: "#ffffff"

  # Dark canvas（可选 themeScheme: dark；默认已改为 light）
  canvas: "#010102"
  surface-1: "#0f1011"
  surface-2: "#141516"
  surface-3: "#18191a"
  surface-4: "#191a1b"
  hairline: "#23252a"
  hairline-strong: "#34343a"
  ink: "#f7f8f8"
  ink-muted: "#d0d6e0"
  ink-subtle: "#8a8f98"
  ink-tertiary: "#62666d"

  # Light inverse
  inverse-canvas: "#ffffff"
  inverse-surface-1: "#f5f6f6"
  inverse-surface-2: "#f6f7f7"
  inverse-ink: "#000000"

  # Semantic
  success: "#27a644"
  warning: "#faad14"
  danger: "#f5222d"
  info: "#5e6ad2"

  # design-system.css 兼容别名（亮色默认值；暗色由 html.dark 覆盖）
  bg-primary: "#ffffff"
  bg-secondary: "#f5f6f6"
  bg-tertiary: "#f6f7f7"
  bg-hover: "#f0f1f2"
  bg-dark: "#010102"
  text-primary: "#000000"
  text-secondary: "#62666d"
  text-tertiary: "#8a8f98"
  border-subtle: "#e6e7e8"
  border-default: "#d0d1d3"
  border-strong: "#8a8f98"

typography:
  family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"
  base: 14px
  xs: 12px
  sm: 14px
  md: 16px
  lg: 18px
  xl: 20px
  weight: { normal: 400, medium: 500, semibold: 600, bold: 700 }

rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 12px
  full: 9999px

spacing:
  scale: [4px, 8px, 12px, 16px, 24px, 32px]

elevation:
  sm: "0 1px 2px rgba(0,0,0,.12)"
  md: "0 4px 12px rgba(0,0,0,.24)"
  lg: "0 12px 32px rgba(0,0,0,.4)"

components:
  layout: { sidebar: 220-240px, header: 56px, content-padding: 12-16px }
  card: { bg: surface, border: hairline, radius: 8-12px, pad: 12-16px }
  button: { primary: theme 实底, secondary: surface + hairline }
  table: { header: surface-2, row-hover: surface-3 }
  status: { success/warning/danger/info + NTag }
---

# OpenTask — Linear 产品 UI 规范（E13）

## Overview

本文件是前端视觉真源（v2.0）。技术底座仍为 **Vue 3 + Naive UI + soybean-admin 布局壳 + UnoCSS**：

- **主题色**：`themeColor: #5e6ad2`（Linear indigo），由 Naive 派生 hover/pressed。
- **默认主题**：`themeScheme: 'light'`（亮色画布 + inverse 令牌）；用户可切换暗色（Linear 近黑 `#010102`）。清站点 `SOY_*` localStorage 后才能看到默认。
- **通用令牌**：`frontend/src/styles/design-system.css` 的 `--color-*`；暗色在 `html.dark` 覆盖。
- **字体**：系统栈 only —— 不嵌入 Linear Display / Linear Text。
- **品牌**：应用名 OpenTask；logo 为 OT monogram（候选 D）。

> 历史：soybean `#646cff` 与 2026-10-24 CoWork 换皮均已废弃为本规范所取代。源 dump：`docs/superpowers/specs/2026-11-04-getdesign-linear.app-source.md`。

## Colors

| Role | Value |
|------|-------|
| Primary | `#5e6ad2` |
| Primary hover | `#828fff` |
| Canvas (dark) | `#010102` |
| Surface 1–3 | `#0f1011` … `#18191a` |
| Hairline | `#23252a` / `#34343a` |
| Ink | `#f7f8f8` / muted `#8a8f98` |
| Light canvas | `#ffffff` / `#f5f6f6` |
| Success | `#27a644` |

营销向 display-xl / section 96px 等令牌仅保留在 source dump，**不进产品壳**。

## Typography

正文 14px；表格/辅助 12px；页面标题 ≤20px。字重 400/500/600。数字列可用 `tabular-nums`。

## Layout

侧栏约 220–240px，右侧 hairline；顶栏高 56；内容区内边距 12–16px；卡片用 surface + hairline，少阴影。侧栏 IA 见 E13 design spec（Inbox / My issues / Workspace…）。

## Components

- 一组操作只留一个 primary。
- 表单跟随 Naive 默认密度。
- 状态用 `NTag`，不自绘彩色徽标。

## Do's and Don'ts

**Do**
- 颜色从 `--color-*` 或 Naive 主题取；新增令牌先登记本文件。
- 暗色画布不够黑时用布局 CSS 覆盖，不 fork Naive。

**Don't**
- 不在组件内散写 hex（收敛到令牌）。
- 不换 Naive/soybean 架构；不推远程除非 Way 授权。
- 不引入 Linear 专有字体文件。

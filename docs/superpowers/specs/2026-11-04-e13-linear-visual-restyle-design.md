# E13 — Linear 视觉改造 Design Spec

> **Status:** approved by Way 2026-11-04（chat）  
> **Source:** [getdesign.md linear.app](https://getdesign.md/design-md/linear) — raw dump kept as `2026-11-04-getdesign-linear.app-source.md`  
> **Branch base:** continue on `sprint/E11-S4` tip (or open `sprint/E13-S1` from tip if cleaner); **no push** until Way says.

## Goal

Replace OpenTask’s soybean / `#646cff` visual source of truth with an **adapted Linear.app product-UI language** so the app shell and core pages feel like Linear (issue tracker density), not a marketing site reskin.

## Non-goals

- Do not replace Naive UI or soybean-admin architecture.
- Do not change backend APIs or business rules.
- Do not change OpenTask name or logo D (OT monogram).
- Do not push to remote.
- Do not license / embed Linear Display / Linear Text fonts — use system stack fallbacks.
- Do not rebuild every page from scratch; remint tokens + shell IA + high-traffic pages first.

## Product constraints

- Stack: Vue 3 + Naive UI + soybean layout shell + UnoCSS.
- Visual truth: root `DESIGN.md` (rewrite) + `frontend/src/styles/design-system.css` + `frontend/src/theme/settings.ts` `themeColor`.
- Prior note in old DESIGN.md: 2026-10-24 CoWork restyle was rolled back — this Epic deliberately replaces that era with Linear.
- Deep/light: **dark-first product feel** (Linear canvas) as default `themeScheme: 'dark'`; light theme maps to getdesign `inverse-*` tokens. User can still toggle.

## Token mapping (getdesign → OpenTask)

| Role | Linear (getdesign) | OpenTask target |
|------|--------------------|-----------------|
| Primary | `#5e6ad2` | `themeColor` + `--color-primary` |
| Primary hover | `#828fff` | `--color-primary-hover` / Naive hover |
| Canvas (dark) | `#010102` | dark body / layout bg |
| Surface 1–3 | `#0f1011` … `#18191a` | cards, sidebar, panels |
| Hairline | `#23252a` / `#34343a` | borders |
| Ink | `#f7f8f8` / muted `#8a8f98` | text hierarchy |
| Light canvas | `#ffffff` / `#f5f6f6` | light theme via inverse |
| Success | `#27a644` | semantic success (align Naive) |
| Radius | 4/6/8/12 | keep Naive `themeRadius: 6`; cards 8–12 |
| Font | Linear Display/Text | `-apple-system, BlinkMacSystemFont, "Segoe UI", PingFang SC, …` |

Marketing-only tokens (display-xl 80px, section 96px, pricing cards) stay in the source dump for reference but are **out of product scope**.

## Information architecture (sidebar)

Target Linear-like flat nav (zh labels OK):

1. **Inbox**
2. **My issues**（指派给我）
3. **Workspace** group: Views / Projects / Cycles / Initiatives / Docs（已有路由则挂上；无则 hide）
4. **Favorites**（若已有）
5. **Teams / Projects** list area（现有项目树）
6. Settings / Members / Profile at bottom or under workspace gear — **not** under Soybean “系统管理/工作管理/研发流水线” nested junk.

Remove or `hideInMenu` leftover Soybean demo/admin groupings that make the menu look messy. Prefer route meta + locale titles over inventing new pages.

## Layout density

- Sidebar ~220→**240px max, often ~220**; hairline right border; quieter icons.
- Header height align ~56 (already in theme settings).
- Content padding: prefer 12–16px; reduce card chrome noise.
- Tabs: keep multi-tab if soybean requires; visually quieter (less border glow).

## Page pass (must look Linear-adjacent)

Priority order for visual-only polish (spacing, borders, table/board chrome, empty states):

1. Login / register (brand already OpenTask + logo D)
2. Issue list + board
3. Issue detail
4. Inbox
5. Home / workspace landing
6. Settings / Members / Profile

No functional regressions on smoke paths from E11-S4.

## Acceptance

- Root `DESIGN.md` rewritten; points to Linear token table; documents dark default + light inverse.
- `themeColor === '#5e6ad2'`; design-system CSS variables match table.
- Default theme opens dark (or documented toggle); light theme still coherent.
- Sidebar IA matches the six-bullet structure above (no Soybean “工作管理/研发流水线” top-level clutter).
- Priority pages pass visual spot-check vs Linear screenshots under `/workspace/opentask-smoke/compare/`.
- Frontend unit tests relevant to routes/theme still pass; no new red from this Epic’s changes.
- **Not pushed.**

## Risks

- Naive darkTheme algorithm may not perfectly hit `#010102` — override layout CSS variables where needed rather than forking Naive.
- Soybean menu generation may fight flat IA — prefer route meta / filter shared helpers already used in `de-pge-nav` tests.
- Full-page visual diffs are subjective — accept “Linear-adjacent” not pixel-perfect clone.

## References

- getdesign source: `docs/superpowers/specs/2026-11-04-getdesign-linear.app-source.md`
- Linear product UI screenshots: `/workspace/opentask-smoke/compare/`
- Prior PRD canvas: OpenTask × Linear (E5–E11 sequence)

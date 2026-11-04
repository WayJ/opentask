# E46 Acceptance：Formula query surfaces v2 — range · sort · conditional display

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E46-S1`  
基线：`b5b132e`  
**tip：** `d1de2ac`（全文 `d1de2ac3dde39d34407f33911ed523c15c619000`；若文件 tip 滞后以 HEAD 为准）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A Range ops | ✅ | `cf.<key>[gt\|gte\|lt\|lte]=` + 短形；stored number/date SQL；formula 复用 cache；unsupported → 400 `cf_range_unsupported`；eq 回归绿 |
| B Sort cf: | ✅ | `sort_by=cf:<key>`；nulls/error last；cap 2000 → `formula_sort_too_broad`；multi_select 400；Saved View `sort_json` 透传 `cf:` |
| C conditionalFormats | ✅ | ≤10；写 >10 → 400；枚举 tint；客户端 `resolveRowTint` 先匹配先生效；不进 CSV |
| D FE | ✅ | SmartSearch `cf:score>=8`；排序菜单含 CF/formula；Display 条件格式编辑；List/Board tint；vitest |
| E CLI 1.30.0 | ✅ | pyproject + `__init__` + setup + VERSION 全钉；`--cf key[gte]=` help；`--sort-by cf:`；历史 version 断言同步 |
| F 无新表 | ✅ | 无 alembic migration（ADR D7） |

## ADR 确认
- D1 surfaces v2 · D2 **no-emit**（spy） · D3 range number/date · D4 sort cap/nulls last · D5 formats≤10 · D6 Q1a/Q2a · D7 无 migration · D8 CLI **1.30.0** · D9 非目标

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1033 passed**, 24 skipped；首轮 4 fail（`test_auth`×3 + `test_user_search`）均为 **flake**，solo 复跑全绿 |
| CLI | **501 passed**, 89 skipped |
| FE | vitest **302 passed**（44 files）；`npm run build` OK |
| E46 专测 | BE `test_e46_*` 11P + E43/E32 回归；CLI `test_e46_*` 2P；FE display-prefs + issueSearchParser |

## Gaps / 非目标（未做）
- Formula 物化 emit；营业日历；WS 全局 feed；pause timeline；cycle/estimate webhook；Excel 色阶/图标集；CSV 导出 formats；Redis/cron；**无 push / 无 PR / 不自开 E47**

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**

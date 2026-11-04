# E43 Acceptance：Formula surfaces v1

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E43-S1`  
基线：`bf57338`  
tip：_pending_

## 范围（待填）
- A–G：见 design；收口时勾选

## ADR
- 延续 E40 不 emit；批求值/cache 等值；cap 2000；cache 仅过滤；error 桶；等值 only；CLI 1.27.0；不 push / 不 E44

## 门禁
| 面 | 结果 |
|----|------|
| BE | _pending_ |
| CLI | _pending_ |
| FE vitest | _pending_ |
| FE build | _pending_ |

## Gaps / 非目标
- 物化进 `issue_custom_field_values` / emit；rollup/脚本；range/sort；SLA v2；webhook 包；全局 feed；push/PR；E44

## superpowers
`design/plan/TDD/verify/acceptance = ok`（收口确认）

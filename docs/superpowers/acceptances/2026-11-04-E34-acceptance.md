# E34 Acceptance：CSV × Custom Fields

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E34-S1`  
基线：`sprint/E33-S1` @ `c1764e2`

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A Export `cf.<key>` | ⏳ | 未归档字段；过滤/10k/Truncated |
| B Import + 模板 | ⏳ | 类型校验；未知 key partial → errors[] |
| C FE 文案/模板 | ⏳ | Import 说明含 `cf.*` |
| D CLI 1.18.0 | ⏳ | help + version |

## ADR 摘要
见 `docs/superpowers/specs/2026-11-04-e34-csv-custom-fields-design.md` D1–D9。

## 测试
- BE / CLI / FE：收口填写

## tip
- SHA：收口填写
- 未 push / 未开 PR
- **不自开 E35**

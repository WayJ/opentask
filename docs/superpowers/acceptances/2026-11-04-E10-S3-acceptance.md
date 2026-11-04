# E10-S3 Acceptance — Docs + Epic local-complete

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E10-S3`  
Worktree：`/workspace/opentask-worktrees/E10-S3`  
Plan：`docs/superpowers/plans/2026-11-04-e10-s3-docs.md` @ `b3dcbae`  
基线：E10-S2 tip `1bd3e8a`  
Epic tip（本验收）：见 git HEAD after this commit

## Docs approach (locked)

**Preferred design §4.3：** 新表 `entity_documents`（title + body_md）挂 `issue` | `project` | `initiative`。  
**附加：** FE「在知识库中打开」→ `/knowledge-base` 深链。  
**禁止：** 附件 `documents` 当 Wiki；requirements / PGE 文档轴。

## Scope delivered

- [x] Alembic `c3d4e5f6a7b8` ← `b2c3d4e5f6a7`
- [x] `/api/entity-documents` list/create/get/patch/delete
- [x] ACL + parent existence；`requirement` parentType 拒绝；跨 WS 404
- [x] `EntityDocsPanel` on Initiative / Issue / Project detail
- [x] KB deep-link button；空状态无 PGE 文案
- [x] Epic S1–S3 acceptance；roadmap DoD
- [x] **无** push；**无** E11

## Tests

| 项 | 结果 |
|---|---|
| `test_entity_documents.py` | 5 passed |
| Full `pytest tests/` | **769 passed**, 27 skipped |

## APIs

| Method | Path |
|---|---|
| GET/POST | `/api/entity-documents` |
| GET/PATCH/DELETE | `/api/entity-documents/{id}` |

## Yuri check

- [x] Docs 入口在 Issue/Project/Initiative；不与 PGE 双轴

# E8-S1 Milestones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax.

**Goal:** Deliver project-scoped `milestones` CRUD + `issues.milestone_id` + `projects.starts_at`/`target_date` + project-detail milestones/dates UI + Issue detail attach. No health / Timeline / Favorites.

**Architecture:** Alembic after `d4e5f6a7b8c0` → `Milestone` model → `MilestoneService` → nested `/api/projects/{id}/milestones` → Project dates → Issue `milestone_id` (same-project validation) → FE.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI, TypeScript.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E8-S1`, branch `sprint/E8-S1`; **no push**
- TDD; mid-epic no Way/Yuri ping
- Write member+; read viewer+; snake_case JSON for milestones (match Project/Issue)
- After full Epic E8 → controller starts **E12** (not E9); S1 scope unchanged

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_0800-e5f6a7b8c9d1_milestones_and_project_dates.py` |
| Model | `backend/opentask/models/milestone/` |
| Service | `backend/opentask/services/milestone/` |
| API | nested in `api/project/router.py` |
| Issue/Project | model/schema/service/router extensions |
| Tests | `backend/tests/api/test_milestones.py` |
| FE | project.ts/typings, project-detail, issue detail |

### Tasks

1. Pytest RED — milestones + dates + issue.milestone_id (+ isolation/viewer/SET NULL)
2. Model + Alembic `e5f6a7b8c9d1` revises `d4e5f6a7b8c0`
3. Service + nested router + Project dates + Issue milestone GREEN
4. FE API + project-detail + issue attach; lint/build
5. Full gates + acceptance + close S1 (Epic stays active; leftover S2/S3; no push)

## OpenTask

- ./agent-harness/opentask-cli        一个python开发的cli
- ./frontend   一个vue3的前端
- ./backend     一个python后端

## Legacy Task Workflow (Task.json-based)

**NOTE:** This section is kept for reference.

### 规范
- 接口规范: ./docs/API_SPECIFICATION.md

### 规范
- 接口规范: ./docs/API_SPECIFICATION.md

### Test Thoroughly

After implementation, verify ALL steps in the task:

**强制测试要求（Testing Requirements - MANDATORY）：**

1. **大幅度页面修改**（新建页面、重写组件、修改核心交互）：
   - **必须在浏览器中测试！** 使用 MCP Playwright 工具
   - 验证页面能正确加载和渲染
   - 验证表单提交、按钮点击等交互功能
   - 截图确认 UI 正确显示

2. **小幅度代码修改**（修复 bug、调整样式、添加辅助函数）：
   - 可以使用单元测试或 lint/build 验证
   - 如有疑虑，仍建议浏览器测试

3. **所有修改必须通过**：
   - `npm run lint` 无错误
   - `npm run build` 构建成功
   - 浏览器/单元测试验证功能正常

**测试清单：**
- [ ] 代码没有 TypeScript 错误
- [ ] lint 通过
- [ ] build 成功
- [ ] 功能在浏览器中正常工作（对于 UI 相关修改）

## Coding Conventions

### Frontend (Vue 3)
- TypeScript strict mode
- Composition API with `<script setup>`
- Tailwind CSS for styling
- Element Plus UI components
- Pinia for state management

### Backend (Spring Boot)
- RESTful API design
- Service-Repository architecture
- JPA entities with proper relationships
- Unified exception handling
- Java 17+ features

### General
- Write tests for new features
- Follow ESLint/Checkstyle rules
- Clear commit messages
- One feature per commit

## Key Rules

1. **One task per session** - Focus on completing one task well
2. **Test before marking complete** - All steps must pass
3. **Browser testing for UI changes** - 新建或大幅修改页面必须在浏览器测试
4. **Document in progress.txt** - Help future agents understand your work
5. **One commit per task** - 所有更改（代码、progress.txt、task.json）必须在同一个 commit 中提交
6. **Never remove tasks** - Only flip `passes: false` to `true`
7. **Stop if blocked** - 需要人工介入时，不要提交，输出阻塞信息并停止


# Spec Workflow Usage Guidelines
## 1. Check Project Progress
When user mentions continuing previous project or is unsure about current progress, proactively use:
specs-workflow tool with action.type="check" and path="./docs"
## 2. Documentation Language
All spec workflow documents should be written in Chinese consistently, including all content in requirements, design, and task documents.
## 3. Documentation Directory
All spec workflow documents should be placed in ./specs directory to maintain consistent project documentation organization.
## 4. Task Management
Always use the following to manage task progress:
specs-workflow tool with action.type="complete_task" and taskNumber="current task number"
Follow the workflow guidance to continue working until all tasks are completed.
## 5. Best Practices
- Proactive progress check: When user says "continue from last time", first use check to see current status
- Language consistency: Use the same language throughout all project documents
- Flexible structure: Choose single-module or multi-module organization based on project scale
- Task granularity: Each task should be completable within 1-2 hours

## supervibe
- roadmaps_dir: docs/superpowers/roadmaps/    <!-- epic docs dir -->
- sprints_dir: docs/superpowers/sprints/      <!-- sprint docs dir -->
- acceptances_dir: docs/superpowers/acceptances/
- notes: .agents/notes/
- debt_tracker: docs/tech-debt-tracker.md
- wip_limit: 3
### epic_superpowers（强制）
每个 Epic / 厚迭代必须按序走完，禁止跳步写码：
1. brainstorming（澄清目标/约束/方案；产出写入 design）
2. `docs/superpowers/specs/YYYY-MM-DD-eN-*-design.md` 入库并自检
3. writing-plans → `docs/superpowers/plans/YYYY-MM-DD-eN-*.md`（checkbox 任务）
4. test-driven-development：先红测再实现
5. verification-before-completion：BE/CLI/FE 门禁证据齐全才可称完成
6. `docs/superpowers/acceptances/YYYY-MM-DD-EN-acceptance.md` 收 tip + 测数；STOP，不自开下一 Epic

### gates
- contracts: cd backend && uv run pytest tests/ -v
- tests: cd frontend && npm run lint && npm run build
### doc_sync_map
| change | owes |
|---|---|
| docs/superpowers/roadmaps/*.md | docs/superpowers/roadmaps/ |
| backend/config/*.yaml | backend/README.md |
| frontend/.env.prod | frontend/README.md |

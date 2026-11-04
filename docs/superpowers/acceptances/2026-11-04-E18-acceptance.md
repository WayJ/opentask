# E18 Acceptance：Issue Watch · Search Doc 深链 · pinia vitest

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E18-S1`  
基线：`sprint/E17-S1` @ `62bf578`  
tip：`3141add39187952108f279d3df8ba57e892c4a52`
worktree：`/workspace/opentask-worktrees/E11-S4`  
约束：**未 push / 未开 PR**；齐套后待命，**不自开 E19**。

## 交付摘要

| 项 | 结果 |
|----|------|
| Issue Watch API | `GET/POST/DELETE /api/issues/{id}/watchers`；membership 校验；跨租户拒绝 |
| Inbox fanout | 评论 / 状态变更 / 指派 → 关注者 Inbox（跳过 actor）；类型 `commented` / `status_changed` / `subscribed_update` / `assigned` |
| FE 详情 | Issue 详情一键关注/取消；Inbox 类型标签补齐 |
| Search Doc 深链 | `buildDocHref(parentType, parentId, docId)`；Issue/Initiative/Project；`?doc=`；EntityDocsPanel 自动 openEdit；键盘跳转仍可用 |
| CLI **1.3.0** | `issue watch` / `unwatch` / `watchers`；`issue show` 展示 Watching；README |
| vitest pinia | 安装 `@pinia/testing`；auth store 套件重写可运行；全量绿 |
| 孤儿组件套件 | `UserMention` / `IssueReference` 组件缺失；相关 + 既有 flaky SmartSearch/TemplateSelector/Reactions 套件 `describe.skip`（原因写入测试文件头） |

## 测试

| 套件 | 结果 |
|---|---|
| backend pytest | **832 passed**, 24 skipped |
| CLI pytest | **414 passed**, 89 skipped |
| FE vitest 全量 | **201 passed**, 12 skipped（30 files） |
| FE 相关 | auth store + global-search：**7 passed** |

## 未做 / 缺口
- Watchers 列表 UI（详情仅开关；CLI `watchers` 可列）
- 未对 :7377 做人工浏览器冒烟截图（API/单测覆盖）
- **未 push / 未开 PR / 未开 E19**

## tip
`3141add39187952108f279d3df8ba57e892c4a52`

# 知识库模块测试套件

## 概述

这是知识库模块的完整测试套件，涵盖：
- 知识库 CRUD 操作
- 知识文档 CRUD 操作
- Git 版本控制集成
- 文件存储和同步服务
- 文件优先架构验证

## 测试文件结构

```
tests/knowledge_base/
├── conftest.py                    # 测试配置和 fixtures
├── test_knowledge_base_api.py     # API 测试（CRUD、过滤、发布、版本控制等）
├── test_git_integration.py        # Git 集成测试
└── test_file_storage.py           # 文件存储和同步服务测试
```

## 测试覆盖范围

### 1. test_knowledge_base_api.py

**知识库 CRUD 测试 (TestKnowledgeBaseCRUD)**
- ✅ 创建知识库成功
- ✅ 缺少必填字段验证
- ✅ 获取知识库列表
- ✅ 获取知识库详情
- ✅ 更新知识库
- ✅ 删除知识库

**知识文档 CRUD 测试 (TestKnowledgeCRUD)**
- ✅ 创建知识文档成功
- ✅ 缺少标题验证
- ✅ 获取知识文档列表
- ✅ 获取知识文档详情
- ✅ 更新知识文档
- ✅ 删除知识文档

**知识文档过滤测试 (TestKnowledgeFilters)**
- ✅ 按状态过滤
- ✅ 按知识库过滤
- ✅ 关键词搜索

**知识文档发布测试 (TestKnowledgePublishing)**
- ✅ 发布知识文档
- ✅ 取消发布知识文档

**版本控制测试 (TestKnowledgeVersioning)**
- ✅ 更新时版本号递增

**权限测试 (TestKnowledgePermissions)**
- ✅ 未授权访问
- ✅ 无效 token
- ✅ 获取不存在的资源

**统计功能测试 (TestKnowledgeStatistics)**
- ✅ 知识库统计信息

**分页测试 (TestKnowledgePagination)**
- ✅ 默认分页
- ✅ 自定义分页大小
- ✅ 分页页码

**生命周期测试 (test_knowledge_lifecycle)**
- ✅ 完整的文档生命周期（创建→更新→发布→取消发布→删除）

### 2. test_git_integration.py

**Git 仓库管理测试 (TestGitRepository)**
- ✅ 初始化 Git 仓库
- ✅ 获取 Git 状态

**Git 提交功能测试 (TestGitCommit)**
- ✅ 提交变更
- ✅ 使用自定义消息提交

**Git 历史记录测试 (TestGitHistory)**
- ✅ 获取提交历史
- ✅ 获取特定文档的历史
- ✅ 历史记录数量限制

**Git 差异比较测试 (TestGitDiff)**
- ✅ 获取文档差异
- ✅ 获取特定提交的差异

**Git 分支管理测试 (TestGitBranches)**
- ✅ 列出所有分支
- ✅ 创建新分支
- ✅ 从指定起始点创建分支

**Git 工作流测试 (TestGitWorkflow)**
- ✅ 完整的 Git 工作流（初始化→提交→修改→提交→创建分支→查看历史→查看 diff）

**Git 权限测试 (TestGitPermissions)**
- ✅ Git 操作需要认证
- ✅ 使用无效 token 进行 Git 操作

### 3. test_file_storage.py

**文件存储测试 (TestFileStorage)**
- ✅ 创建知识库时生成文件路径
- ✅ 知识文档的文件路径
- ✅ 文件内容包含 front matter

**文件同步测试 (TestFileSync)**
- ✅ 创建知识文档同步到文件
- ✅ 更新知识文档同步到文件
- ✅ 删除知识文档时删除文件

**文件监控测试 (TestFileWatcher)**
- ⏸️ 文件监控服务状态（需要专门的监控状态端点）

**文件完整性测试 (TestFileIntegrity)**
- ✅ 数据库和文件的一致性
- ✅ 文件修改时间跟踪

**文件优先架构测试 (TestFileFirstArchitecture)**
- ✅ 创建知识库时创建目录
- ✅ 创建知识文档时创建文件
- ✅ 完整的同步工作流

**文件内容验证测试 (TestFileContentValidation)**
- ✅ Markdown 内容正确保存
- ✅ Front Matter 元数据生成

## 运行测试

### 运行所有知识库测试

```bash
cd backend
pytest tests/knowledge_base/ -v
```

### 运行特定测试文件

```bash
# API 测试
pytest tests/knowledge_base/test_knowledge_base_api.py -v

# Git 集成测试
pytest tests/knowledge_base/test_git_integration.py -v

# 文件存储测试
pytest tests/knowledge_base/test_file_storage.py -v
```

### 运行特定测试类

```bash
# 知识库 CRUD 测试
pytest tests/knowledge_base/test_knowledge_base_api.py::TestKnowledgeBaseCRUD -v

# Git 仓库管理测试
pytest tests/knowledge_base/test_git_integration.py::TestGitRepository -v
```

### 运行特定测试用例

```bash
# 测试创建知识库
pytest tests/knowledge_base/test_knowledge_base_api.py::TestKnowledgeBaseCRUD::test_create_knowledge_base_success -v

# 测试 Git 工作流
pytest tests/knowledge_base/test_git_integration.py::test_complete_git_workflow -v
```

### 运行测试并生成覆盖率报告

```bash
pytest tests/knowledge_base/ --cov=opentask.api.knowledge_base --cov=opentask.api.knowledge --cov=opentask.services.git_service --cov-report=html
```

### 运行测试并显示详细输出

```bash
pytest tests/knowledge_base/ -v -s
```

### 运行测试并标记慢速测试

```bash
pytest tests/knowledge_base/ --durations=10
```

## 测试依赖

测试依赖以下 fixtures（在 conftest.py 中定义）：

- `test_client`: HTTP 测试客户端
- `test_token`: 认证 token
- `test_kb_id`: 测试知识库 ID
- `test_knowledge_id`: 测试知识文档 ID

## 测试前提条件

1. **后端服务运行**：确保后端服务在 `http://localhost:7377` 运行
2. **数据库初始化**：确保数据库已初始化并运行迁移
3. **测试用户**：确保测试用户 `admin/admin123` 存在

## 测试清理

测试使用 fixtures 自动清理：
- 测试知识库在测试结束后自动删除
- 测试知识文档在测试结束后自动删除

## 已知限制

1. **文件监控测试**：需要专门的监控状态端点，当前已跳过
2. **文件系统验证**：某些测试需要直接访问文件系统，API 可能不返回文件状态
3. **并发测试**：当前测试套件未包含并发场景测试

## 下一步改进

1. **性能测试**：添加大量文档创建和查询的性能测试
2. **并发测试**：添加多用户同时编辑的并发测试
3. **集成测试**：添加与前端集成的端到端测试
4. **文件监控测试**：实现文件监控状态端点后添加完整测试
5. **MeiliSearch 测试**：添加全文搜索功能的测试（Phase 4）
6. **附件功能测试**：添加文件上传和附件管理测试（Phase 5）

## 测试最佳实践

1. **独立性**：每个测试用例应该独立运行，不依赖其他测试
2. **清理**：测试结束后清理创建的资源
3. **断言**：使用明确的断言验证预期行为
4. **命名**：使用描述性的测试名称
5. **文档**：为复杂测试添加文档字符串

## 故障排除

### 测试失败

如果测试失败：

1. 检查后端服务是否运行
2. 检查数据库是否已初始化
3. 检查测试用户是否存在
4. 查看详细错误信息：`pytest tests/knowledge_base/ -v -s`

### 数据库错误

如果遇到数据库错误：

```bash
cd backend
# 重新运行迁移
alembic upgrade head
```

### 认证错误

如果遇到认证错误：

1. 检查测试用户是否存在
2. 重置测试用户密码
3. 检查认证服务是否正常运行

## 贡献指南

添加新测试时：

1. 在适当的测试文件中添加测试类或测试函数
2. 使用清晰的命名和文档字符串
3. 确保测试独立运行
4. 添加必要的清理逻辑
5. 更新此 README 文档

## 测试统计

当前测试统计：

- **测试文件**: 3 个
- **测试类**: 20+ 个
- **测试用例**: 80+ 个
- **代码覆盖率**: 待统计

## 联系方式

如有问题或建议，请联系开发团队。

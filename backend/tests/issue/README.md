# Issue API 测试

Issue 模块的完整 API 测试套件，用于 CI/CD 自动化测试。

## 📋 测试覆盖

### 测试类别

1. **TestIssueCRUD** - CRUD 操作测试
   - 创建 Issue（含 issue_code 验证）
   - 获取 Issue 列表和详情
   - 更新和删除 Issue
   - 缺少必填字段验证

2. **TestIssueFilters** - 过滤和搜索测试
   - 按状态/优先级/类型过滤
   - 关键词搜索
   - 组合过滤条件

3. **TestIssueComments** - 评论功能测试
   - 添加/获取/删除评论

4. **TestIssueCodeGeneration** - Issue Code 生成规则测试
   - 格式验证（ISSUE{YEAR}-{NUMBER}）
   - 年份正确性验证
   - 序号连续递增验证
   - 唯一性验证
   - 持久化验证

5. **TestIssuePermissions** - 权限测试
   - 未授权访问
   - 无效 token
   - 获取不存在的 Issue

6. **TestIssueStatistics** - 统计功能测试

7. **TestIssuePagination** - 分页功能测试

8. **test_issue_workflow_lifecycle** - 完整生命周期测试
   - todo → in_progress → testing → review → done

## 🚀 快速开始

### 1. 环境准备

```bash
# 进入 backend 目录
cd backend

# 确保依赖已安装
uv sync
```

### 2. 配置文件

测试使用 `config/test.yaml` 配置文件，自动加载（通过 `APP_ENV=test` 环境变量）。

### 3. 运行测试

```bash
# 运行所有 Issue 测试
uv run pytest tests/issue/test_issues_api.py -v

# 运行特定测试类
uv run pytest tests/issue/test_issues_api.py::TestIssueCRUD -v

# 运行单个测试
uv run pytest tests/issue/test_issues_api.py::TestIssueCRUD::test_create_issue_success -v

# 显示详细输出
uv run pytest tests/issue/test_issues_api.py -v -s

# 生成覆盖率报告
uv run pytest tests/issue/test_issues_api.py --cov=opentask.models.issue --cov-report=html
```

## 📝 测试数据管理

### 自动清理

测试会自动清理创建的数据：
- 所有标题包含 "自动化测试" 的 Issue 会在测试后自动删除
- 使用 `cleanup_test_data` fixture 自动执行

### 测试数据库

使用主数据库 `opentask`，通过标记测试数据来区分：
- 测试数据标题前缀：`自动化测试`
- 测试完成后自动清理

## 🔧 配置说明

### config/test.yaml

```yaml
database:
  mysql:
    host: "localhost"
    port: 3307
    user: "root"
    password: "123456"
    database: "opentask"
    echo: false  # 测试时不打印 SQL

test:
  cleanup_after_test: true  # 自动清理
  data_prefix: "自动化测试"  # 测试数据标记
```

### 环境变量

```bash
# 设置测试环境（conftest.py 会自动设置）
export APP_ENV=test

# 或使用 pytest.ini 配置
```

## 🎯 Issue Code 生成规则

测试验证以下规则：

1. **格式规则**：`ISSUE{4位年份}-{序号}`
2. **年份规则**：使用当前年份
3. **序号规则**：基于当年已有 Issue 数量递增
4. **唯一性规则**：每个 Issue Code 全局唯一
5. **持久化规则**：创建后不因更新而改变

## 📊 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Issue API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install uv
          uv sync
      - name: Run Issue tests
        run: |
          cd backend
          uv run pytest tests/issue/test_issues_api.py -v
```

## ⚠️ 注意事项

1. **数据库连接**：确保 MySQL 服务运行在 `localhost:3307`
2. **测试账号**：需要存在 admin/123456 用户
3. **数据清理**：测试会自动清理，失败时可能需要手动清理
4. **并发测试**：不建议并行运行，可能相互干扰

## 🔍 故障排查

### 测试失败

1. **连接错误**
   ```bash
   # 检查 MySQL 是否运行
   mysql -u root -p -h localhost -P 3307 -e "SELECT 1"
   ```

2. **认证失败**
   ```bash
   # 检查测试用户是否存在
   mysql -u root -p -h localhost -P 3307 -e "USE opentask; SELECT * FROM users WHERE username='admin'"
   ```

3. **数据残留**
   ```bash
   # 手动清理测试数据
   mysql -u root -p -h localhost -P 3307 -e "USE opentask; DELETE FROM issues WHERE title LIKE '自动化测试%';"
   ```

## 📚 相关文档

- [API 规范](../../../docs/API_SPECIFICATION.md)
- [Issue 需求](../../../docs/ISSUE_REQUIREMENTS.md)
- [配置管理](../../CONFIG_MANAGEMENT.md)

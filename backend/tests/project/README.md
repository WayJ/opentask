# Project API 测试

Project 模块的完整 API 测试套件，用于 CI/CD 自动化测试。

## 📋 测试覆盖

### 测试类别

1. **TestProjectCRUD** - 项目 CRUD 操作测试
   - 创建项目
   - 获取项目列表和详情
   - 更新和删除项目
   - 按活跃状态过滤

2. **TestRepoConfigCRUD** - 仓库配置 CRUD 操作测试
   - 创建仓库配置
   - 获取仓库配置列表
   - 更新和删除仓库配置

3. **TestRequirementRepoAssociation** - 需求-仓库关联测试
   - 关联需求和仓库
   - 获取需求的所有仓库
   - 更新需求-仓库关联信息（分支、PR等）
   - 取消需求和仓库的关联

4. **TestProjectPermissions** - 权限测试
   - 未授权访问
   - 无效 token
   - 获取不存在的项目

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
# 运行所有 Project 测试
uv run pytest tests/project/test_project_api.py -v

# 运行特定测试类
uv run pytest tests/project/test_project_api.py::TestProjectCRUD -v

# 运行单个测试
uv run pytest tests/project/test_project_api.py::TestProjectCRUD::test_create_project_success -v

# 显示详细输出
uv run pytest tests/project/test_project_api.py -v -s

# 生成覆盖率报告
uv run pytest tests/project/test_project_api.py --cov=opentask.api.project --cov-report=html
```

## 📝 测试数据管理

### 自动清理

测试会自动清理创建的数据：
- 所有名称包含 "自动化测试" 的项目会在测试后自动删除
- 使用 `cleanup_test_data` fixture 自动执行

### 测试数据库

使用主数据库 `opentask`，通过标记测试数据来区分：
- 测试数据名称前缀：`自动化测试`
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

## 📊 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Project API Tests

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
      - name: Run Project tests
        run: |
          cd backend
          uv run pytest tests/project/test_project_api.py -v
```

## ⚠️ 注意事项

1. **数据库连接**：确保 MySQL 服务运行在配置的地址
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
   mysql -u root -p -h localhost -P 3307 -e "USE opentask; DELETE FROM projects WHERE name LIKE '自动化测试%';"
   ```

## 📚 相关文档

- [API 规范](../../../docs/API_SPECIFICATION.md)
- [配置管理](../../CONFIG_MANAGEMENT.md)
- [Requirement 测试](../requirement/README.md)
- [Issue 测试](../issue/README.md)

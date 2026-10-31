-- ============================================
-- OpenTask 数据库初始化脚本
-- ============================================
-- 用途: 创建所有必需的表和初始数据
-- 使用方法: docker exec opentask-mysql mysql -uroot -proot123 opentask < init_database.sql
-- ============================================

-- 设置字符集
SET NAMES utf8mb4;

-- ============================================
-- 1. 用户和认证相关表
-- ============================================

-- 用户表
CREATE TABLE IF NOT EXISTS user (
    id VARCHAR(36) PRIMARY KEY COMMENT '用户 UUID',
    name VARCHAR(100) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) COMMENT '密码',
    ssh_public_key TEXT COMMENT 'SSH 公钥',
    openai_api_key VARCHAR(255) COMMENT 'OpenAI API Key',
    preferred_openai_model VARCHAR(255) COMMENT '首选 OpenAI 模型',
    langsmith_api_key VARCHAR(255) COMMENT 'LangSmith API Key',
    sentry_enabled BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Sentry 启用',
    analytics_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '分析启用',
    hide_sql_preference BOOLEAN NOT NULL DEFAULT FALSE COMMENT '隐藏 SQL 偏好',
    openai_base_url VARCHAR(255) COMMENT 'OpenAI Base URL',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 用户 SSH 密钥表
CREATE TABLE IF NOT EXISTS user_ssh_keys (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'SSH 密钥 ID',
    user_id CHAR(36) NOT NULL COMMENT '用户 ID',
    name VARCHAR(255) NOT NULL COMMENT '密钥名称',
    public_key TEXT NOT NULL COMMENT 'SSH 公钥内容',
    fingerprint VARCHAR(255) NOT NULL COMMENT '密钥指纹',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    last_used_at DATETIME COMMENT '最后使用时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_ssh_keys_user_id (user_id),
    INDEX idx_user_ssh_keys_fingerprint (fingerprint),
    UNIQUE KEY uk_user_fingerprint (user_id, fingerprint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户 SSH 密钥表';

-- ============================================
-- 2. 项目和需求相关表
-- ============================================

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY COMMENT '项目 UUID',
    name VARCHAR(255) NOT NULL UNIQUE COMMENT '项目名称',
    description TEXT COMMENT '项目描述',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否激活',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_projects_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目表';

-- 需求表
CREATE TABLE IF NOT EXISTS requirements (
    id VARCHAR(36) PRIMARY KEY COMMENT '需求 UUID',
    code VARCHAR(50) NOT NULL UNIQUE COMMENT '需求编码',
    title VARCHAR(255) NOT NULL COMMENT '需求标题',
    description TEXT COMMENT '需求描述',
    status VARCHAR(50) NOT NULL DEFAULT 'draft' COMMENT '需求状态',
    priority VARCHAR(50) COMMENT '优先级',
    tags JSON COMMENT '标签',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    created_by VARCHAR(255) COMMENT '创建者',
    assignee_id VARCHAR(255) COMMENT '负责人 ID',
    project_id VARCHAR(36) NOT NULL COMMENT '关联项目 ID',
    INDEX idx_requirements_status (status),
    INDEX idx_requirements_priority (priority),
    INDEX idx_requirements_code (code),
    INDEX idx_requirements_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求表';

-- 事件表（事件溯源）
CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(36) PRIMARY KEY COMMENT '事件 UUID',
    requirement_id VARCHAR(36) NOT NULL COMMENT '关联需求 ID',
    type VARCHAR(50) NOT NULL COMMENT '事件类型',
    data JSON NOT NULL COMMENT '事件数据',
    actor VARCHAR(255) COMMENT '执行者',
    reasoning TEXT COMMENT '推理过程',
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
    snapshot JSON COMMENT '快照',
    INDEX idx_events_requirement_id (requirement_id),
    INDEX idx_events_timestamp (timestamp),
    INDEX idx_events_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件表';

-- 评论表
CREATE TABLE IF NOT EXISTS comments (
    id VARCHAR(36) PRIMARY KEY COMMENT '评论 UUID',
    requirement_id VARCHAR(36) NOT NULL COMMENT '关联需求 ID',
    content TEXT NOT NULL COMMENT '评论内容',
    author_id VARCHAR(36) COMMENT '作者 ID',
    parent_id VARCHAR(36) COMMENT '父评论 ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_comments_requirement_id (requirement_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论表';

-- ============================================
-- 3. 仓库相关表（新模型）
-- ============================================

-- 仓库配置表（旧模型，保留兼容）
CREATE TABLE IF NOT EXISTS repo_configs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '仓库配置 ID',
    project_id VARCHAR(36) NOT NULL COMMENT '关联项目 ID',
    name VARCHAR(255) NOT NULL COMMENT '仓库名称',
    url VARCHAR(500) NOT NULL COMMENT '仓库 URL',
    main_branch VARCHAR(100) NOT NULL DEFAULT 'main' COMMENT '主分支',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_repo_configs_project_name (project_id, name),
    UNIQUE KEY uk_repo_configs_project_name (project_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仓库配置表';

-- 需求-仓库关联表
CREATE TABLE IF NOT EXISTS requirement_repos (
    id VARCHAR(36) PRIMARY KEY COMMENT '关联 UUID',
    requirement_id VARCHAR(36) NOT NULL COMMENT '需求 ID',
    repo_id INT NOT NULL COMMENT '仓库配置 ID',
    branch VARCHAR(255) COMMENT '分支',
    pr_url VARCHAR(500) COMMENT 'PR URL',
    merge_status VARCHAR(50) COMMENT '合并状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_requirement_repos_requirement_id (requirement_id),
    INDEX idx_requirement_repos_repo_id (repo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求-仓库关联表';

-- 仓库表（新模型）
CREATE TABLE IF NOT EXISTS repositories (
    id VARCHAR(36) PRIMARY KEY COMMENT '仓库 UUID',
    name VARCHAR(255) NOT NULL COMMENT '仓库名称',
    url VARCHAR(500) NOT NULL COMMENT '仓库 URL',
    local_path TEXT COMMENT '本地路径',
    project_id VARCHAR(36) NOT NULL COMMENT '关联项目 ID',
    requirement_id VARCHAR(36) COMMENT '关联需求 ID',
    branch VARCHAR(255) NOT NULL DEFAULT 'main' COMMENT '默认分支',
    provider VARCHAR(50) NOT NULL DEFAULT 'custom' COMMENT 'Git 提供商',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否激活',
    status VARCHAR(50) NOT NULL DEFAULT 'idle' COMMENT '仓库状态',
    auth_token VARCHAR(500) COMMENT '认证 Token',
    ssh_key_id INT COMMENT 'SSH 密钥 ID',
    last_clone_at DATETIME COMMENT '最后克隆时间',
    last_pull_at DATETIME COMMENT '最后拉取时间',
    last_commit VARCHAR(100) COMMENT '最后一次提交 hash',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_repositories_project_id (project_id),
    INDEX idx_repositories_requirement_id (requirement_id),
    INDEX idx_repositories_status (status),
    INDEX idx_repositories_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Git 仓库表';

-- 仓库分支表
CREATE TABLE IF NOT EXISTS repository_branches (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '分支 ID',
    repository_id VARCHAR(36) NOT NULL COMMENT '仓库 ID',
    name VARCHAR(255) NOT NULL COMMENT '分支名称',
    is_default BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否为默认分支',
    last_commit VARCHAR(100) COMMENT '最后一次提交 hash',
    commit_message TEXT COMMENT '最后一次提交消息',
    commit_author VARCHAR(255) COMMENT '最后一次提交作者',
    committed_at DATETIME COMMENT '最后一次提交时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_repository_branches_repository_id (repository_id),
    UNIQUE KEY uq_repo_branch_name (repository_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仓库分支表';

-- ============================================
-- 4. 任务相关表
-- ============================================

-- 任务组表（如果需要）
-- CREATE TABLE IF NOT EXISTS task_groups (
--     id VARCHAR(36) PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     project_id VARCHAR(36),
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY COMMENT '任务 UUID',
    title VARCHAR(255) NOT NULL COMMENT '任务标题',
    description TEXT COMMENT '任务描述',
    status VARCHAR(50) NOT NULL DEFAULT 'todo' COMMENT '任务状态',
    requirement_id VARCHAR(36) COMMENT '关联需求 ID',
    project_id VARCHAR(36) COMMENT '关联项目 ID',
    parent_id VARCHAR(36) COMMENT '父任务 ID',
    code VARCHAR(50) COMMENT '任务编码',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_requirement_id (requirement_id),
    INDEX idx_tasks_project_id (project_id),
    INDEX idx_tasks_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表';

-- ============================================
-- 5. 对话和消息相关表
-- ============================================

-- 对话表
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY COMMENT '对话 UUID',
    title VARCHAR(255) COMMENT '对话标题',
    model VARCHAR(100) COMMENT '使用的模型',
    ai_settings JSON COMMENT 'AI 设置',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话表';

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息 UUID',
    conversation_id VARCHAR(36) NOT NULL COMMENT '对话 ID',
    role VARCHAR(50) NOT NULL COMMENT '角色 (user/assistant/system)',
    content TEXT COMMENT '消息内容',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_messages_conversation_id (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';

-- ============================================
-- 6. 连接和结果相关表
-- ============================================

-- 连接表
CREATE TABLE IF NOT EXISTS connections (
    id VARCHAR(36) PRIMARY KEY COMMENT '连接 UUID',
    name VARCHAR(255) NOT NULL COMMENT '连接名称',
    type VARCHAR(50) COMMENT '连接类型',
    config JSON COMMENT '连接配置',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='连接表';

-- 媒体表
CREATE TABLE IF NOT EXISTS media (
    id VARCHAR(36) PRIMARY KEY COMMENT '媒体 UUID',
    type VARCHAR(50) COMMENT '媒体类型',
    url VARCHAR(500) COMMENT '媒体 URL',
    metadata JSON COMMENT '元数据',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='媒体表';

-- 结果表
CREATE TABLE IF NOT EXISTS results (
    id VARCHAR(36) PRIMARY KEY COMMENT '结果 UUID',
    task_id VARCHAR(36) COMMENT '关联任务 ID',
    data JSON COMMENT '结果数据',
    status VARCHAR(50) COMMENT '状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='结果表';

-- ============================================
-- 7. 其他辅助表
-- ============================================

-- Alembic 版本表（数据库迁移）
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    PRIMARY KEY (version_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 初始化数据
-- ============================================

-- 创建默认管理员用户
INSERT INTO user (id, name, password) VALUES
('01234567-89ab-cdef-0123-456789abcdef', 'admin', '123456')
ON DUPLICATE KEY UPDATE password='123456';

-- 创建测试项目
INSERT INTO projects (id, name, description) VALUES
('proj-1', '测试项目', '这是一个测试项目')
ON DUPLICATE KEY UPDATE name=name;

-- 创建测试需求
INSERT INTO requirements (id, code, title, description, status, project_id) VALUES
('req-1', 'REQ001', '测试需求1', '需求描述', 'draft', 'proj-1')
ON DUPLICATE KEY UPDATE title=title;

-- ============================================
-- 验证
-- ============================================

SELECT 'Database initialized successfully!' AS Status;
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'opentask';

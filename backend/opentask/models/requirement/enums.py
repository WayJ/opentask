"""需求模块枚举定义"""
from enum import Enum


class RequirementStatus(str, Enum):
    """需求状态枚举（PGE 流程）"""
    PLANNING = "planning"             # 规划中
    GENERATING = "generating"         # 生成中
    EVALUATING = "evaluating"         # 评审中
    COMPLETED = "completed"           # 已完成
    CLOSED = "closed"                 # 已关闭
    ARCHIVED = "archived"             # 已归档

    def __str__(self) -> str:
        return self.value


class Priority(str, Enum):
    """优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


class EventType(str, Enum):
    """事件类型枚举"""
    # 需求生命周期事件
    REQUIREMENT_CREATED = "requirement_created"
    REQUIREMENT_UPDATED = "requirement_updated"
    REQUIREMENT_DELETED = "requirement_deleted"

    # 澄清阶段事件
    AI_QUESTIONS_GENERATED = "ai_questions_generated"
    QUESTIONS_ANSWERED = "questions_answered"

    # 产品分析事件
    REQUIREMENT_SPEC_GENERATED = "requirement_spec_generated"
    SPEC_REVIEWED = "spec_reviewed"
    SPEC_APPROVED = "spec_approved"

    # 研发设计事件
    TECH_DESIGN_CREATED = "tech_design_created"
    API_DEFINED = "api_defined"
    DATA_MODEL_CHANGED = "data_model_changed"

    # 编码实现事件
    CODE_GENERATED = "code_generated"
    CODE_COMMITTED = "code_committed"
    PR_CREATED = "pr_created"
    PR_REVIEWED = "pr_reviewed"
    PR_MERGED = "pr_merged"
    PR_REJECTED = "pr_rejected"

    # 测试发布事件
    TEST_STARTED = "test_started"
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    BUG_REPORTED = "bug_reported"
    BUG_FIXED = "bug_fixed"
    RELEASED = "released"

    # 分配事件
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"

    # 其他事件
    COMMENT_ADDED = "comment_added"
    ATTACHMENT_ADDED = "attachment_added"

    def __str__(self) -> str:
        return self.value


class MergeStatus(str, Enum):
    """PR 合并状态枚举"""
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    DRAFT = "draft"

    def __str__(self) -> str:
        return self.value


class RepoType(str, Enum):
    """仓库类型枚举"""
    NODEJS = "nodejs"
    PYTHON = "python"
    GOLANG = "golang"
    RUST = "rust"
    JAVA = "java"
    CSHARP = "csharp"
    OTHER = "other"

    def __str__(self) -> str:
        return self.value


class JobStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

    def __str__(self) -> str:
        return self.value


class JobType(str, Enum):
    """任务类型枚举"""
    # AI 相关任务
    AI_PARSE_REQUIREMENT = "ai_parse_requirement"
    AI_GENERATE_SPEC = "ai_generate_spec"
    AI_GENERATE_DESIGN = "ai_generate_design"
    AI_GENERATE_CODE = "ai_generate_code"
    AI_REVIEW_CODE = "ai_review_code"
    AI_GENERATE_TESTS = "ai_generate_tests"

    # Git 相关任务
    GIT_CREATE_BRANCH = "git_create_branch"
    GIT_COMMIT_CODE = "git_commit_code"
    GIT_CREATE_PR = "git_create_pr"
    GIT_MERGE_PR = "git_merge_pr"

    # CI/CD 相关任务
    CI_RUN_TESTS = "ci_run_tests"
    CI_BUILD = "ci_build"
    CD_DEPLOY = "cd_deploy"

    def __str__(self) -> str:
        return self.value

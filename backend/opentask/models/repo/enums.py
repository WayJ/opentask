"""仓库模块枚举"""
from enum import Enum


class RepoStatus(str, Enum):
    """仓库状态"""
    CLONING = "cloning"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


class GitProvider(str, Enum):
    """Git 提供商"""
    GITHUB = "github"
    GITLAB = "gitlab"
    GITEA = "gitea"
    BITBUCKET = "bitbucket"
    CUSTOM = "custom"

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus
from typing import Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file
load_dotenv()
from urllib.parse import quote_plus
from typing import Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from opentask.utils.appdirs import user_data_dir

# https://pyinstaller.org/en/v6.6.0/runtime-information.html
IS_BUNDLED = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))

USER_DATA_DIR = user_data_dir(appname="OpenTask")


def load_config_file(environment: str = "development") -> dict:
    """加载 YAML 配置文件"""
    # config.py 在 backend/opentask/ 目录，配置文件在 backend/config/ 目录
    config_dir = Path(__file__).parent.parent / "config"

    # 按优先级加载配置文件（后加载的会覆盖先加载的）
    # 默认配置 -> 环境配置 -> 本地配置
    config_files = [
        config_dir / "default.yaml",      # 基础配置
        config_dir / f"{environment}.yaml",  # 环境特定配置
        config_dir / "local.yaml",        # 本地覆盖（不提交）
    ]

    config = {}
    for config_file in config_files:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # 递归合并配置
                    config = _deep_merge(config, file_config)

    return config


def _deep_merge(base: dict, update: dict) -> dict:
    """递归合并字典"""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_env_value(key: str, default: Optional[str] = None) -> str:
    """获取环境变量，支持从 YAML 配置读取"""
    # 优先使用环境变量（可由 .env.local 或系统环境变量提供）
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value

    # 从 YAML 配置读取
    environment = os.getenv("APP_ENV", "development")
    config = load_config_file(environment)

    # 环境变量名到配置路径的映射
    # 支持扁平化环境变量名（如 POSTGRES_HOST）到嵌套配置路径（database.postgres.host）
    key_mapping = {
        'POSTGRES_HOST': ['database', 'postgres', 'host'],
        'POSTGRES_PORT': ['database', 'postgres', 'port'],
        'POSTGRES_USER': ['database', 'postgres', 'user'],
        'POSTGRES_PASSWORD': ['database', 'postgres', 'password'],
        'POSTGRES_DATABASE': ['database', 'postgres', 'database'],
        'POSTGRES_ECHO': ['database', 'postgres', 'echo'],
        'DATA_DIRECTORY': ['storage', 'data_directory'],
        'STORAGE_PROVIDER': ['storage', 'provider'],
        'AUTH_USERNAME': ['auth', 'username'],
        'AUTH_PASSWORD': ['auth', 'password'],
        'AUTH_SECRET_KEY': ['auth', 'secret_key'],
        'ALLOWED_ORIGINS': ['cors', 'allowed_origins'],
        'OPENAI_API_KEY': ['ai', 'openai', 'api_key'],
        'OPENAI_BASE_URL': ['ai', 'openai', 'base_url'],
        'DEFAULT_LLM_MODEL': ['ai', 'default_model'],
        'MAX_TOKENS': ['ai', 'max_tokens'],
        'MINIO_ENDPOINT': ['minio', 'endpoint'],
        'MINIO_ACCESS_KEY': ['minio', 'access_key'],
        'MINIO_SECRET_KEY': ['minio', 'secret_key'],
        'MINIO_BUCKET': ['minio', 'bucket'],
        'MINIO_SECURE': ['minio', 'secure'],
        'TASK_MONITOR_ENABLED': ['task_monitor', 'enabled'],
        'TASK_MONITOR_CHECK_INTERVAL_MINUTES': ['task_monitor', 'check_interval_minutes'],
        'TASK_MONITOR_TIMEOUT_HOURS': ['task_monitor', 'timeout_hours'],
        'SSO_BASE_URL': ['sso', 'base_url'],
        'SSO_APP_CODE': ['sso', 'app_code'],
        'SSO_TIMEOUT': ['sso', 'timeout'],
        'CIPHER_KEY': ['cipher', 'key'],
        'AUTH_SSO_ENABLED': ['auth', 'sso_enabled'],
        'AUTH_ACCESS_EXPIRE_MINUTES': ['auth', 'access_expire_minutes'],
        'AUTH_REFRESH_EXPIRE_DAYS': ['auth', 'refresh_expire_days'],
        'AUTH_OAUTH_CODE_EXPIRE_SECONDS': ['auth', 'oauth_code_expire_seconds'],
        'AUTH_OAUTH_REFRESH_EXPIRE_DAYS': ['auth', 'oauth_refresh_expire_days'],
        'AUTH_OAUTH_CLIENT_SECRET_BYTES': ['auth', 'oauth_client_secret_bytes'],
        'DINGTALK_APP_KEY': ['dingtalk', 'app_key'],
        'DINGTALK_APP_SECRET': ['dingtalk', 'app_secret'],
        'AUTH_DINGTALK_AUTO_REGISTER': ['auth', 'dingtalk_auto_register'],
        'SMTP_HOST': ['smtp', 'host'],
        'SMTP_PORT': ['smtp', 'port'],
        'SMTP_USER': ['smtp', 'user'],
        'SMTP_PASSWORD': ['smtp', 'password'],
        'SMTP_FROM': ['smtp', 'from'],
        'SMTP_TLS': ['smtp', 'tls'],
        'FRONTEND_BASE_URL': ['app', 'frontend_base_url'],
    }

    # 使用映射或默认拆分逻辑
    keys = key_mapping.get(key, key.lower().split('_'))

    # 深度查找配置值
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            value = None
            break

    if value is None:
        value = default

    # 处理占位符 ${VAR:default}
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        inner = value[2:-1]
        if ':' in inner:
            var_name, var_default = inner.split(':', 1)
            return os.getenv(var_name, var_default)
        else:
            return os.getenv(inner, default or '')

    # 处理列表类型（如 allowed_origins）
    if isinstance(value, list):
        value = ','.join(value)

    return str(value) if value is not None else (default or '')


class EnvironmentType(str):
    development = "development"
    production = "production"




class Config(BaseSettings):
    """配置类 - 从 YAML 配置文件和环境变量加载"""

    # 加载 YAML 配置
    environment: str = os.getenv("APP_ENV", "development")
    _yaml_config: dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从配置文件加载
        config = load_config_file(self.environment)
        if config:
            self._yaml_config = config

    def _get_value(self, key: str, default=None):
        """获取配置值，优先级：环境变量 > YAML 配置 > 默认值"""
        return get_env_value(key, default)

    # PostgreSQL 数据库配置
    @property
    def postgres_host(self) -> str:
        return self._get_value("POSTGRES_HOST", "localhost")

    @property
    def postgres_port(self) -> int:
        return int(self._get_value("POSTGRES_PORT", "5432"))

    @property
    def postgres_user(self) -> str:
        return self._get_value("POSTGRES_USER", "opentask")

    @property
    def postgres_password(self) -> str:
        return self._get_value("POSTGRES_PASSWORD", "")

    @property
    def postgres_database(self) -> str:
        return self._get_value("POSTGRES_DATABASE", "opentask")

    @property
    def postgres_echo(self) -> bool:
        echo = self._get_value("POSTGRES_ECHO", "false")
        return echo.lower() in ("true", "1", "yes")

    # SQLite 数据库配置（用于本地开发）
    @property
    def use_sqlite(self) -> bool:
        use_sqlite = self._get_value("USE_SQLITE", "false")
        return use_sqlite.lower() in ("true", "1", "yes")

    @property
    def sqlite_path(self) -> str:
        return self._get_value("SQLITE_PATH", str(Path(USER_DATA_DIR) / "opentask.db"))
    @property
    def database_dsn(self) -> str:
        """获取同步数据库连接字符串"""
        if self.use_sqlite:
            return f"sqlite:///{self.sqlite_path}"
        encoded_password = quote_plus(self.postgres_password)
        return f"postgresql+psycopg2://{self.postgres_user}:{encoded_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

    @property
    def database_dsn_async(self) -> str:
        """获取异步数据库连接字符串"""
        if self.use_sqlite:
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        encoded_password = quote_plus(self.postgres_password)
        return f"postgresql+asyncpg://{self.postgres_user}:{encoded_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

    # 文件存储路径
    @property
    def data_directory(self) -> str:
        return self._get_value("DATA_DIRECTORY", str(Path(USER_DATA_DIR) / "data"))

    @property
    def login_private_key_path(self) -> str:
        """登录口令加密的私钥路径（RSA-OAEP，私钥只在服务端）

        默认落在 DATA_DIRECTORY 下（生产即 /app/data/login_private.pem，由 compose
        的 ./data 卷挂进来）；未配置/不存在时后端回退按明文处理口令。
        """
        return self._get_value(
            "LOGIN_PRIVATE_KEY_PATH",
            str(Path(self.data_directory) / "login_private.pem"),
        )

    @property
    def templates_path(self) -> Path:
        return Path(__file__).parent.parent / "templates"

    @property
    def assets_path(self) -> Path:
        return Path(__file__).parent.parent / "assets"

    @property
    def release(self) -> Optional[str]:
        return self._get_value("RELEASE")

    @property
    def spa_mode(self) -> bool:
        mode = self._get_value("SPA_MODE", "false")
        return mode.lower() in ("true", "1", "yes")

    # HTTP Basic Authentication
    @property
    def auth_username(self) -> Optional[str]:
        return self._get_value("AUTH_USERNAME")

    @property
    def auth_password(self) -> Optional[str]:
        return self._get_value("AUTH_PASSWORD")

    # JWT 签名密钥（env AUTH_SECRET_KEY > yaml auth.secret_key），必须显式配置
    @property
    def auth_secret_key(self) -> str:
        key = self._get_value("AUTH_SECRET_KEY")
        if not key:
            raise RuntimeError(
                "AUTH_SECRET_KEY 未配置：JWT 签名密钥必须显式设置"
                "（环境变量 AUTH_SECRET_KEY 或 yaml auth.secret_key），禁止使用默认值；"
                "若此前使用环境变量 JWT_SECRET_KEY，请改为 AUTH_SECRET_KEY（旧名已废弃）"
            )
        return key

    # 用户中心认证配置
    @property
    def sso_enabled(self) -> bool:
        """是否启用 SSO 集成认证"""
        enabled = self._get_value("AUTH_SSO_ENABLED", "false")
        return enabled.lower() in ("true", "1", "yes")

    @property
    def access_expire_minutes(self) -> int:
        """access token 有效期（分钟）"""
        return int(self._get_value("AUTH_ACCESS_EXPIRE_MINUTES", "120"))

    @property
    def refresh_expire_days(self) -> int:
        """refresh token 有效期（天）"""
        return int(self._get_value("AUTH_REFRESH_EXPIRE_DAYS", "7"))

    # ===== OAuth2 Provider（授权服务器）配置 =====

    @property
    def oauth_code_expire_seconds(self) -> int:
        """OAuth 授权码有效期（秒）——默认 10 分钟"""
        return int(self._get_value("AUTH_OAUTH_CODE_EXPIRE_SECONDS", "600"))

    @property
    def oauth_refresh_expire_days(self) -> int:
        """OAuth refresh token 有效期（天）——默认 30 天"""
        return int(self._get_value("AUTH_OAUTH_REFRESH_EXPIRE_DAYS", "30"))

    @property
    def oauth_client_secret_bytes(self) -> int:
        """OAuth client secret 随机字节数——默认 32"""
        return int(self._get_value("AUTH_OAUTH_CLIENT_SECRET_BYTES", "32"))

    # 钉钉开放平台配置（企业内部应用）
    @property
    def dingtalk_app_key(self) -> str:
        """钉钉应用 AppKey（默认空 = 未配置，同步接口返回 400）"""
        return self._get_value("DINGTALK_APP_KEY", "")

    @property
    def dingtalk_app_secret(self) -> str:
        """钉钉应用 AppSecret（默认空 = 未配置，同步接口返回 400）"""
        return self._get_value("DINGTALK_APP_SECRET", "")

    @property
    def dingtalk_auto_register(self) -> bool:
        """免登时是否自动注册本地账号（Task 3 用，默认 true）"""
        enabled = self._get_value("AUTH_DINGTALK_AUTO_REGISTER", "true")
        return enabled.lower() in ("true", "1", "yes")

    # CORS settings
    @property
    def allowed_origins(self) -> str:
        return self._get_value("ALLOWED_ORIGINS", "http://localhost:7377,http://localhost:5173")

    # AI模型配置
    @property
    def openai_api_key(self) -> str:
        return self._get_value("OPENAI_API_KEY", "")

    @property
    def openai_base_url(self) -> str:
        """OpenAI API 基础地址（自动去除末尾斜杠，避免拼接时出现双斜杠）"""
        url = self._get_value("OPENAI_BASE_URL", "")
        # 去除末尾的斜杠，防止拼接URL时出现双斜杠问题
        return url.rstrip('/') if url else ""

    # 默认模型配置
    @property
    def default_llm_model(self) -> str:
        return self._get_value("DEFAULT_LLM_MODEL", "openai/gpt4")

    @property
    def max_tokens(self) -> int:
        return int(self._get_value("MAX_TOKENS", "8192"))

    @property
    def available_models(self) -> list[str]:
        return ["glm-4-air-0111", "glm-4.6"]

    @property
    def analysis_model(self) -> str:
        return self.default_llm_model

    @property
    def chart_generation_model(self) -> str:
        return self.default_llm_model

    @property
    def sql_generation_model(self) -> str:
        return self.default_llm_model

    @property
    def has_auth(self) -> bool:
        return bool(self.auth_username and self.auth_password)

    # 示例数据库路径配置
    @property
    def sample_dvdrental_path(self) -> str:
        return self._get_value("SAMPLE_DVDRENTAL_PATH", "")

    @property
    def sample_netflix_path(self) -> str:
        return self._get_value("SAMPLE_NETFLIX_PATH", "")

    @property
    def sample_titanic_path(self) -> str:
        return self._get_value("SAMPLE_TITANIC_PATH", "")

    @property
    def sample_spotify_path(self) -> str:
        return self._get_value("SAMPLE_SPOTIFY_PATH", "")

    # 存储配置
    @property
    def storage_provider(self) -> str:
        """存储提供商: minio 或 local"""
        return self._get_value("STORAGE_PROVIDER", "local")

    # MinIO 配置
    @property
    def minio_endpoint(self) -> str:
        """MinIO 端点地址（自动去除末尾斜杠，避免拼接时出现双斜杠）"""
        endpoint = self._get_value("MINIO_ENDPOINT", "localhost:9000")
        # 去除末尾的斜杠，防止拼接URL时出现双斜杠问题
        return endpoint.rstrip('/')

    @property
    def minio_access_key(self) -> str:
        return self._get_value("MINIO_ACCESS_KEY", "minioadmin")

    @property
    def minio_secret_key(self) -> str:
        return self._get_value("MINIO_SECRET_KEY", "minioadmin")

    @property
    def minio_bucket(self) -> str:
        return self._get_value("MINIO_BUCKET", "default")

    @property
    def minio_secure(self) -> bool:
        secure = self._get_value("MINIO_SECURE", "false")
        return secure.lower() in ("true", "1", "yes")

    @property
    def use_minio(self) -> bool:
        """是否使用 MinIO 存储"""
        return self.storage_provider.lower() == "minio"

    # # API 前缀配置
    # @property
    # def api_prefix(self) -> str:
    #     """OpenTask API 前缀"""
    #     return self._get_value("API_PREFIX", "/api")

    @property
    def sso_api_prefix(self) -> str:
        """SSO API 前缀（用于 nginx 代理）"""
        return self._get_value("SSO_API_PREFIX", "/sso-api")

    # SSO 平台配置
    @property
    def sso_base_url(self) -> str:
        """SSO 基础地址（自动去除末尾斜杠，避免拼接时出现双斜杠）"""
        url = self._get_value("SSO_BASE_URL", "http://39.183.172.160:29080")
        # 去除末尾的斜杠，防止拼接URL时出现双斜杠问题
        return url.rstrip('/')

    @property
    def sso_app_code(self) -> str:
        """SSO App-Code"""
        return self._get_value("SSO_APP_CODE", "opentask")

    @property
    def sso_timeout(self) -> int:
        """SSO 请求超时（秒）"""
        return int(self._get_value("SSO_TIMEOUT", "10"))

    @property
    def cipher_key(self) -> str:
        """SSO 密码加密密钥"""
        return self._get_value("CIPHER_KEY", "EY8WePvjM5GGwQzn")

    # 任务监控服务配置
    @property
    def task_monitor_enabled(self) -> bool:
        """是否启用任务监控服务"""
        enabled = self._get_value("TASK_MONITOR_ENABLED", "true")
        return enabled.lower() in ("true", "1", "yes")

    @property
    def task_monitor_check_interval_minutes(self) -> int:
        """任务监控检查间隔（分钟）"""
        return int(self._get_value("TASK_MONITOR_CHECK_INTERVAL_MINUTES", "5"))

    @property
    def task_monitor_timeout_hours(self) -> int:
        """任务监控超时时间（小时）"""
        return int(self._get_value("TASK_MONITOR_TIMEOUT_HOURS", "1"))

    # ===== E30 出站邮件 SMTP =====
    @property
    def smtp_host(self) -> str:
        return self._get_value("SMTP_HOST", "")

    @property
    def smtp_port(self) -> int:
        return int(self._get_value("SMTP_PORT", "587") or "587")

    @property
    def smtp_user(self) -> str:
        return self._get_value("SMTP_USER", "")

    @property
    def smtp_password(self) -> str:
        return self._get_value("SMTP_PASSWORD", "")

    @property
    def smtp_from(self) -> str:
        return self._get_value("SMTP_FROM", "")

    @property
    def smtp_tls(self) -> bool:
        v = self._get_value("SMTP_TLS", "true")
        return str(v).lower() in ("true", "1", "yes")

    @property
    def frontend_base_url(self) -> str:
        """FE 深链基址（邮件正文可选）。"""
        return self._get_value("FRONTEND_BASE_URL", "").rstrip("/")



config = Config()

"""Configuration management for OpenTask CLI."""
import json
import logging
from pathlib import Path
from typing import Any

# Setup logging
logger = logging.getLogger(__name__)

# Import password store for secure credential management
try:
    from .password_store import PasswordStore, store_credentials_securely, get_credentials_securely
    PASSWORD_STORE_AVAILABLE = True
except ImportError:
    PASSWORD_STORE_AVAILABLE = False
    PasswordStore = None


class Config:
    """CLI configuration manager.

    Handles persistent storage of:
    - API base URL
    - Authentication token
    - Active project context
    - User preferences
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".opentask"
    CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

    def __init__(self):
        """Initialize configuration."""
        self.config_dir = self.DEFAULT_CONFIG_DIR
        self.config_file = self.CONFIG_FILE
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load configuration from file.

        Handles corrupted config files gracefully:
        - Creates backup of corrupted file
        - Provides clear error messages
        - Falls back to empty configuration
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)

                # Validate config structure
                if not isinstance(self._data, dict):
                    raise ValueError("Config root must be a dictionary")

            except (json.JSONDecodeError, ValueError) as e:
                # Config file is corrupted - backup and create new
                backup_file = self.config_file.with_suffix(".corrupted")

                # Try to backup the corrupted file
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    logger.warning(f"Config file corrupted, backed up to: {backup_file}")
                except Exception:
                    pass  # Backup failed, but that's OK

                logger.warning(f"Failed to load config from {self.config_file}: {e}")
                logger.warning("Using default empty configuration. Run 'opentask config init' to reconfigure.")

                self._data = {}
            except IOError as e:
                logger.warning(f"Failed to read config file: {e}")
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        """Save configuration to file.

        Raises:
            IOError: If config file cannot be written
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save configuration to {self.config_file}: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value and save."""
        self._data[key] = value
        self._save()

    def delete(self, key: str):
        """Delete configuration value and save."""
        if key in self._data:
            del self._data[key]
            self._save()

    # Convenience methods for common config values

    @property
    def api_url(self) -> str:
        """Get API base URL."""
        return self.get("api_url", "http://localhost:7377")

    @api_url.setter
    def api_url(self, value: str):
        """Set API base URL."""
        self.set("api_url", value.rstrip("/"))

    @property
    def token(self) -> str | None:
        """Get authentication token."""
        return self.get("token")

    @token.setter
    def token(self, value: str):
        """Set authentication token."""
        self.set("token", value)

    @property
    def username(self) -> str | None:
        """Get saved username."""
        return self.get("a_u")

    @username.setter
    def username(self, value: str):
        """Set username."""
        self.set("a_u", value)

    @property
    def password(self) -> str | None:
        """Get saved password.

        Tries to retrieve from secure keyring first, then falls back to config.
        """
        if PASSWORD_STORE_AVAILABLE:
            # Try keyring first
            from .password_store import get_credentials_securely
            password = get_credentials_securely(self.username or "")
            if password:
                return password

        # Fallback to config file (legacy)
        return self.get("a_p")

    @password.setter
    def password(self, value: str):
        """Set password securely.

        Stores password in system keyring if available,
        otherwise falls back to config file (not recommended).
        """
        # Store in keyring if available
        if PASSWORD_STORE_AVAILABLE and self.username:
            from .password_store import store_credentials_securely
            if store_credentials_securely(self.username, value):
                logger.info("Password stored in system keyring")
                # Don't store in config file when using keyring
                self.delete("a_p")
                return

        # Fallback to config file (not secure, but compatible)
        logger.warning("Storing password in config file (consider using keyring)")
        self.set("a_p", value)

    @property
    def refresh_token(self) -> str | None:
        """Get saved refresh token."""
        return self.get("refresh_token")

    @refresh_token.setter
    def refresh_token(self, value: str):
        """Set refresh token."""
        self.set("refresh_token", value)

    @property
    def access_token(self) -> str | None:
        """Get saved access token for API authentication."""
        return self.get("access_token")

    @access_token.setter
    def access_token(self, value: str):
        """Set access token."""
        self.set("access_token", value)

    @property
    def active_project_id(self) -> str | None:
        """Get active project ID."""
        return self.get("active_project_id")

    @active_project_id.setter
    def active_project_id(self, value: str):
        """Set active project ID."""
        self.set("active_project_id", value)

    @property
    def active_project_name(self) -> str | None:
        """Get active project name."""
        return self.get("active_project_name")

    @active_project_name.setter
    def active_project_name(self, value: str):
        """Set active project name."""
        self.set("active_project_name", value)

    @property
    def active_workspace_id(self) -> str | None:
        """Get active workspace ID (FE-aligned X-Workspace-Id)."""
        return self.get("active_workspace_id")

    @active_workspace_id.setter
    def active_workspace_id(self, value: str):
        """Set active workspace ID."""
        self.set("active_workspace_id", value)

    @property
    def active_workspace_name(self) -> str | None:
        """Get active workspace name."""
        return self.get("active_workspace_name")

    @active_workspace_name.setter
    def active_workspace_name(self, value: str):
        """Set active workspace name."""
        self.set("active_workspace_name", value)

    def clear_workspace_context(self):
        """Clear active workspace context."""
        self.delete("active_workspace_id")
        self.delete("active_workspace_name")

    def clear_auth(self):
        """Clear authentication token."""
        self.delete("token")
        self.delete("access_token")
        self.delete("refresh_token")

    def clear_project_context(self):
        """Clear active project context."""
        self.delete("active_project_id")
        self.delete("active_project_name")

    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate configuration and return status with issues.

        Returns:
            Tuple of (is_valid, list_of_issues)

        Examples:
            is_valid, issues = config.validate_config()
            if not is_valid:
                for issue in issues:
                    print(f"Config issue: {issue}")
        """
        issues = []

        # Check API URL
        api_url = self.api_url
        if not api_url or api_url == "http://localhost:7377":
            issues.append("API URL not configured (using default)")

        # Check authentication
        token = self.token
        if not token:
            issues.append("No authentication token found (run 'opentask config login')")

        # Check active project
        if self.active_project_id:
            if not self.active_project_name:
                issues.append("Active project ID set but name missing")

        return (len(issues) == 0, issues)

    def to_dict(self) -> dict[str, Any]:
        """Get all configuration as dictionary."""
        return self._data.copy()

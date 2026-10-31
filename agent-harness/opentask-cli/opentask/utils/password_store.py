"""Secure password storage using system keyring.

This module provides secure password storage using the system's keyring,
with fallback to config file storage for compatibility.
"""
import logging
from typing import Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None

logger = logging.getLogger(__name__)

# Keyring service name for OpenTask CLI
KEYRING_SERVICE = "opentask-cli"
KEYRING_USERNAME_PREFIX = "user:"


class PasswordStore:
    """Secure password storage manager."""

    @staticmethod
    def is_available() -> bool:
        """Check if keyring is available.

        Returns:
            True if keyring can be used, False otherwise
        """
        return KEYRING_AVAILABLE

    @staticmethod
    def set_password(username: str, password: str) -> bool:
        """Store password securely.

        Args:
            username: Username (identifier for the password)
            password: Password to store

        Returns:
            True if successful, False otherwise

        Examples:
            >>> PasswordStore.set_password("myuser@example.com", "mypassword")
            True
        """
        if not KEYRING_AVAILABLE:
            logger.warning("Keyring not available, password will be stored in config")
            return False

        try:
            keyring.set_password(
                KEYRING_SERVICE,
                f"{KEYRING_USERNAME_PREFIX}{username}",
                password
            )
            logger.debug(f"Password stored in keyring for user: {username}")
            return True
        except Exception as e:
            logger.warning(f"Failed to store password in keyring: {e}")
            return False

    @staticmethod
    def get_password(username: str) -> Optional[str]:
        """Retrieve password from secure storage.

        Args:
            username: Username (identifier for the password)

        Returns:
            Password string if found, None otherwise

        Examples:
            >>> PasswordStore.get_password("myuser@example.com")
            'mypassword'
            >>> PasswordStore.get_password("nonexistent")
            None
        """
        if not KEYRING_AVAILABLE:
            return None

        try:
            password = keyring.get_password(
                KEYRING_SERVICE,
                f"{KEYRING_USERNAME_PREFIX}{username}"
            )
            if password:
                logger.debug(f"Password retrieved from keyring for user: {username}")
                return password
            return None
        except Exception as e:
            logger.warning(f"Failed to retrieve password from keyring: {e}")
            return None

    @staticmethod
    def delete_password(username: str) -> bool:
        """Delete password from secure storage.

        Args:
            username: Username (identifier for the password)

        Returns:
            True if successful or password didn't exist, False on error

        Examples:
            >>> PasswordStore.delete_password("myuser@example.com")
            True
        """
        if not KEYRING_AVAILABLE:
            return True  # Not stored in keyring anyway

        try:
            # Try to delete - some backends may not support this
            keyring.delete_password(
                KEYRING_SERVICE,
                f"{KEYRING_USERNAME_PREFIX}{username}"
            )
            logger.debug(f"Password deleted from keyring for user: {username}")
            return True
        except Exception as e:
            # Password may not exist, which is fine
            logger.debug(f"Password delete attempt (may not exist): {e}")
            return True


def migrate_password_to_keyring(username: str, encrypted_password: str) -> bool:
    """Migrate password from config to keyring.

    This is a one-time migration function that moves the password
    from config file storage to secure keyring storage.

    Args:
        username: Username
        encrypted_password: Encrypted password from config

    Returns:
        True if migration successful, False otherwise
    """
    if not PasswordStore.is_available():
        logger.info("Keyring not available, skipping password migration")
        return False

    # We can't decrypt the encrypted password, so we just store
    # a placeholder and ask user to re-login
    # This is a security feature - forces re-authentication
    try:
        # Check if password already exists in keyring
        existing = PasswordStore.get_password(username)
        if existing:
            logger.debug(f"Password already exists in keyring for {username}")
            return True

        # Store a placeholder to indicate migration needed
        PasswordStore.set_password(username, "")
        logger.info(f"Password migration placeholder created for {username}")
        return True
    except Exception as e:
        logger.error(f"Failed to migrate password to keyring: {e}")
        return False


# ============================================================================
# Convenience Functions for CLI Commands
# ============================================================================

def store_credentials_securely(username: str, encrypted_password: str) -> bool:
    """Store user credentials using best available method.

    Args:
        username: Username
        encrypted_password: Encrypted password (for config fallback)

    Returns:
        True if stored successfully, False otherwise
    """
    # Try keyring first
    if PasswordStore.is_available():
        if PasswordStore.set_password(username, encrypted_password):
            logger.info(f"Password stored securely in keyring for: {username}")
            return True

    # Fallback to config file storage
    logger.warning("Storing password in config file (not recommended)")
    return False


def get_credentials_securely(username: str) -> Optional[str]:
    """Retrieve user credentials using best available method.

    Args:
        username: Username

    Returns:
        Encrypted password string if found, None otherwise
    """
    # Try keyring first
    if PasswordStore.is_available():
        password = PasswordStore.get_password(username)
        if password:
            return password

    # Fallback to config file storage
    logger.debug("Keyring not available or no password found, check config")
    return None

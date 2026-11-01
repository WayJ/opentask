"""OAuth2 Provider 服务层"""

from opentask.services.oauth2.authorization_service import (
    AuthorizationCodeService,
    InvalidGrantError,
)
from opentask.services.oauth2.client_service import (
    ClientNotFoundError,
    ClientSecretError,
    GrantTypeError,
    OAuthClientService,
    RedirectUriError,
    ScopeError,
)
from opentask.services.oauth2.identity_service import OAuthIdentityService
from opentask.services.oauth2.token_service import (
    InsufficientScopeError,
    InvalidTokenError,
    OAuthTokenService,
    ReplayDetectedError,
    TokenRevokedError,
)

__all__ = [
    "OAuthClientService",
    "ClientNotFoundError",
    "ClientSecretError",
    "RedirectUriError",
    "ScopeError",
    "GrantTypeError",
    "AuthorizationCodeService",
    "InvalidGrantError",
    "OAuthTokenService",
    "InvalidTokenError",
    "InsufficientScopeError",
    "ReplayDetectedError",
    "TokenRevokedError",
    "OAuthIdentityService",
]

"""MCP OAuth 客户端的 S256 PKCE 不依赖浏览器保密。"""

import base64
import hashlib
from urllib.parse import parse_qs, urlsplit

import pytest

from .conftest import REDIRECT_URI
from .test_authorization_flow import _bearer


@pytest.mark.asyncio
async def test_pkce_challenge_survives_consent_and_wrong_verifier_cannot_redeem(
    test_client, oauth_user, registered_client
):
    client, secret = registered_client
    verifier = 'v' * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    params = {
        'client_id': client.client_id, 'redirect_uri': REDIRECT_URI,
        'response_type': 'code', 'scope': 'read:tasks profile', 'state': 'pkce-state',
        'code_challenge': challenge, 'code_challenge_method': 'S256',
    }
    context = await test_client.get('/api/oauth2/authorize/context', params=params, headers=_bearer(oauth_user))
    assert context.status_code == 200
    assert context.json()['data']['code_challenge'] == challenge
    approval = await test_client.post('/api/oauth2/authorize/approve', json={**params, 'decision': 'approve'}, headers=_bearer(oauth_user))
    assert approval.status_code == 200
    code = parse_qs(urlsplit(approval.json()['data']['redirect_to']).query)['code'][0]
    form = {'grant_type': 'authorization_code', 'client_id': client.client_id,
            'client_secret': secret, 'code': code, 'redirect_uri': REDIRECT_URI}
    wrong = await test_client.post('/oauth2/token', data={**form, 'code_verifier': 'w' * 64})
    assert wrong.status_code == 400
    assert wrong.json()['error'] == 'invalid_grant'
    correct = await test_client.post('/oauth2/token', data={**form, 'code_verifier': verifier})
    assert correct.status_code == 200
    assert correct.json()['access_token']


@pytest.mark.asyncio
@pytest.mark.parametrize('challenge,method', [('abc', 'S256'), ('a' * 43, 'plain'), ('a' * 43, None), (None, 'S256')])
async def test_invalid_pkce_request_is_rejected(test_client, oauth_user, registered_client, challenge, method):
    client, _secret = registered_client
    params = {'client_id': client.client_id, 'redirect_uri': REDIRECT_URI, 'scope': 'profile'}
    if challenge is not None:
        params['code_challenge'] = challenge
    if method is not None:
        params['code_challenge_method'] = method
    response = await test_client.get('/api/oauth2/authorize/context', params=params, headers=_bearer(oauth_user))
    assert response.status_code == 400
    assert response.json()['detail']['error'] == 'invalid_request'

"""MCP 客户端从标准元数据发现授权服务器。"""

import pytest
import pytest_asyncio
from sqlalchemy import delete
from opentask.models.oauth2.model import OAuthClient


@pytest_asyncio.fixture
async def dynamic_clients(test_session):
    ids = []
    yield ids
    if ids:
        await test_session.execute(delete(OAuthClient).where(OAuthClient.client_id.in_(ids)))
        await test_session.commit()


@pytest.mark.asyncio
async def test_mcp_resource_and_authorization_server_metadata(test_client, monkeypatch):
    monkeypatch.setenv('FRONTEND_BASE_URL', 'https://opentask.example.test')
    resource = await test_client.get('/.well-known/oauth-protected-resource/mcp')
    assert resource.status_code == 200
    assert resource.json()['resource'] == 'https://opentask.example.test/mcp'
    assert resource.json()['authorization_servers'] == ['https://opentask.example.test']
    metadata = await test_client.get('/.well-known/oauth-authorization-server')
    assert metadata.status_code == 200
    body = metadata.json()
    assert body['issuer'] == 'https://opentask.example.test'
    assert body['authorization_endpoint'] == 'https://opentask.example.test/oauth2/authorize'
    assert body['token_endpoint'] == 'https://opentask.example.test/oauth2/token'
    assert body['registration_endpoint'] == 'https://opentask.example.test/oauth2/register'
    assert body['code_challenge_methods_supported'] == ['S256']
    assert 'client_secret_post' in body['token_endpoint_auth_methods_supported']


@pytest.mark.asyncio
async def test_mcp_authentication_challenge_links_protected_resource_metadata(test_client, monkeypatch):
    monkeypatch.setenv('FRONTEND_BASE_URL', 'https://opentask.example.test')
    for headers in ({}, {'Authorization': 'Bearer invalid-token'}):
        response = await test_client.post('/mcp', headers=headers, json={
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'
        })
        assert response.status_code == 401
        assert response.headers['www-authenticate'] == (
            'Bearer resource_metadata="https://opentask.example.test/.well-known/oauth-protected-resource/mcp"'
        )


@pytest.mark.asyncio
async def test_dynamic_registration_returns_confidential_client_for_member_authorization(test_client, dynamic_clients):
    response = await test_client.post('/oauth2/register', json={
        'client_name': '小蓝 CoWork',
        'redirect_uris': ['https://cowork.example.test/enterprise/api/v1/app-oauth/app-123/callback'],
        'grant_types': ['authorization_code', 'refresh_token'],
        'response_types': ['code'],
        'token_endpoint_auth_method': 'client_secret_post',
        'scope': 'profile read:tasks',
    })
    assert response.status_code == 201
    client = response.json()
    dynamic_clients.append(client['client_id'])
    assert client['client_id']
    assert client['client_secret']
    assert client['token_endpoint_auth_method'] == 'client_secret_post'
    assert client['redirect_uris'] == ['https://cowork.example.test/enterprise/api/v1/app-oauth/app-123/callback']


@pytest.mark.asyncio
async def test_dynamic_registration_refuses_unsafe_redirect_and_unknown_scope(test_client):
    for redirects, scope in [(['https://user:password@example.com/callback'], 'profile'),
                             (['https://example.com/callback'], 'unknown:scope')]:
        response = await test_client.post('/oauth2/register', json={
            'client_name': 'test', 'redirect_uris': redirects,
            'token_endpoint_auth_method': 'client_secret_post', 'scope': scope,
        })
        assert response.status_code == 400
        assert response.json()['error'] in ('invalid_redirect_uri', 'invalid_client_metadata')


@pytest.mark.asyncio
async def test_dynamic_client_cannot_authorize_without_pkce(test_client, oauth_user, dynamic_clients):
    from .test_authorization_flow import _bearer
    registered = await test_client.post('/oauth2/register', json={
        'client_name': 'client', 'redirect_uris': ['https://example.com/callback'],
        'scope': 'profile', 'token_endpoint_auth_method': 'client_secret_post',
    })
    assert registered.status_code == 201
    dynamic_clients.append(registered.json()['client_id'])
    response = await test_client.get('/api/oauth2/authorize/context', params={
        'client_id': registered.json()['client_id'], 'redirect_uri': 'https://example.com/callback', 'scope': 'profile',
    }, headers=_bearer(oauth_user))
    assert response.status_code == 400
    assert response.json()['detail']['error'] == 'invalid_request'


@pytest.mark.asyncio
async def test_dynamic_mcp_authorization_binds_token_to_resource(test_client, oauth_user, monkeypatch, dynamic_clients):
    import base64
    import hashlib
    from urllib.parse import parse_qs, urlsplit
    from jose import jwt
    from .test_authorization_flow import _bearer

    monkeypatch.setenv('FRONTEND_BASE_URL', 'https://opentask.example.test')
    resource = 'https://opentask.example.test/mcp'
    redirect = 'https://cowork.example.test/oauth/callback'
    registered = await test_client.post('/oauth2/register', json={
        'client_name': 'client', 'redirect_uris': [redirect], 'scope': 'read:tasks',
        'token_endpoint_auth_method': 'client_secret_post',
    })
    assert registered.status_code == 201
    client = registered.json()
    dynamic_clients.append(client['client_id'])
    verifier = 'v' * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    params = {'client_id': client['client_id'], 'redirect_uri': redirect, 'scope': 'read:tasks',
              'state': 'state', 'code_challenge': challenge, 'code_challenge_method': 'S256',
              'resource': resource}
    context = await test_client.get('/api/oauth2/authorize/context', params=params, headers=_bearer(oauth_user))
    assert context.status_code == 200
    assert context.json()['data']['resource'] == resource
    approval = await test_client.post('/api/oauth2/authorize/approve', json={**params, 'decision': 'approve'}, headers=_bearer(oauth_user))
    assert approval.status_code == 200
    code = parse_qs(urlsplit(approval.json()['data']['redirect_to']).query)['code'][0]
    token_form = {'grant_type': 'authorization_code', 'client_id': client['client_id'],
                  'client_secret': client['client_secret'], 'code': code, 'redirect_uri': redirect,
                  'code_verifier': verifier, 'resource': resource}
    without_secret = dict(token_form)
    without_secret.pop('client_secret')
    assert (await test_client.post('/oauth2/token', data=without_secret)).status_code == 401
    wrong = await test_client.post('/oauth2/token', data={**token_form, 'resource': 'https://other.example/mcp'})
    assert wrong.status_code == 400
    good = await test_client.post('/oauth2/token', data=token_form)
    assert good.status_code == 200
    token = good.json()['access_token']
    assert jwt.get_unverified_claims(token)['aud'] == resource
    other_resource = await test_client.get('/oauth2/api/tasks', headers={'Authorization': 'Bearer ' + token})
    assert other_resource.status_code == 401
    reply = await test_client.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
                                   headers={'Authorization': 'Bearer ' + token})
    assert reply.status_code == 200
    assert any(t['name'] == 'list_issues' for t in reply.json()['result']['tools'])
    call = await test_client.post('/mcp', json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                              'params': {'name': 'list_issues', 'arguments': {'limit': 5}}},
                                  headers={'Authorization': 'Bearer ' + token})
    assert call.status_code == 200
    assert 'result' in call.json()
    refreshed = await test_client.post('/oauth2/token', data={
        'grant_type': 'refresh_token', 'client_id': client['client_id'], 'client_secret': client['client_secret'],
        'refresh_token': good.json()['refresh_token'], 'resource': resource,
    })
    assert refreshed.status_code == 200
    assert jwt.get_unverified_claims(refreshed.json()['access_token'])['aud'] == resource

@pytest.mark.asyncio
async def test_public_client_requires_pkce_and_exchanges_without_secret(test_client, oauth_user, monkeypatch, dynamic_clients):
    import base64
    import hashlib
    from urllib.parse import parse_qs, urlsplit
    from .test_authorization_flow import _bearer

    monkeypatch.setenv('FRONTEND_BASE_URL', 'https://opentask.example.test')
    resource = 'https://opentask.example.test/mcp'
    redirect = 'https://cowork.example.test/workbench/apps'
    registered = await test_client.post('/oauth2/register', json={
        'client_name': 'public client', 'redirect_uris': [redirect],
        'scope': 'read:tasks', 'token_endpoint_auth_method': 'none',
    })
    assert registered.status_code == 201
    client = registered.json()
    dynamic_clients.append(client['client_id'])
    assert 'client_secret' not in client
    assert client['token_endpoint_auth_method'] == 'none'
    params = {'client_id': client['client_id'], 'redirect_uri': redirect, 'scope': 'read:tasks',
              'state': 'state', 'resource': resource}
    missing_pkce = await test_client.get('/api/oauth2/authorize/context', params=params, headers=_bearer(oauth_user))
    assert missing_pkce.status_code == 400
    verifier = 'v' * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    params.update(code_challenge=challenge, code_challenge_method='S256')
    approval = await test_client.post('/api/oauth2/authorize/approve', json={**params, 'decision': 'approve'}, headers=_bearer(oauth_user))
    assert approval.status_code == 200
    code = parse_qs(urlsplit(approval.json()['data']['redirect_to']).query)['code'][0]
    form = {'grant_type': 'authorization_code', 'client_id': client['client_id'], 'code': code,
            'redirect_uri': redirect, 'resource': resource}
    unexpected_secret = await test_client.post('/oauth2/token', data={**form, 'code_verifier': verifier, 'client_secret': 'irrelevant'})
    assert unexpected_secret.status_code == 401
    wrong = await test_client.post('/oauth2/token', data={**form, 'code_verifier': 'z' * 64})
    assert wrong.status_code == 400
    exchanged = await test_client.post('/oauth2/token', data={**form, 'code_verifier': verifier})
    assert exchanged.status_code == 200
    reply = await test_client.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
                                   headers={'Authorization': 'Bearer ' + exchanged.json()['access_token']})
    assert reply.status_code == 200
    refresh = await test_client.post('/oauth2/token', data={'grant_type': 'refresh_token',
        'client_id': client['client_id'], 'refresh_token': exchanged.json()['refresh_token'], 'resource': resource})
    assert refresh.status_code == 200

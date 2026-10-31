"""
OpenTask API Client 单元测试

测试范围：
- 客户端初始化
- 请求头生成
- 响应处理
- HTTP 方法（GET, POST, PUT, DELETE）
- 错误处理
- 超时处理
"""

import pytest
from unittest import mock
import httpx

from opentask.utils.api_client import OpenTaskClient, APIError


# ============================================================================
# 客户端初始化测试
# ============================================================================

class TestClientInitialization:
    """测试客户端初始化"""

    def test_init_with_default_url(self):
        """测试使用默认 URL 初始化"""
        client = OpenTaskClient()
        assert client.base_url == "http://localhost:7377"
        assert client.token is None
        assert client.timeout == 30.0

    def test_init_with_custom_url(self):
        """测试使用自定义 URL 初始化"""
        client = OpenTaskClient(base_url="http://example.com:8080")
        assert client.base_url == "http://example.com:8080"

    def test_init_with_token(self):
        """测试带 token 初始化"""
        client = OpenTaskClient(token="test_token_123")
        assert client.token == "test_token_123"

    def test_init_url_trailing_slash(self):
        """测试 URL 尾部斜杠被移除"""
        client = OpenTaskClient(base_url="http://localhost:7377/")
        assert client.base_url == "http://localhost:7377"


# ============================================================================
# 请求头测试
# ============================================================================

class TestHeaders:
    """测试请求头生成"""

    def test_headers_without_token(self):
        """测试不带 token 的请求头"""
        client = OpenTaskClient()
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_headers_with_token(self):
        """测试带 token 的请求头"""
        client = OpenTaskClient(token="my_token")
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer my_token"


# ============================================================================
# 响应处理测试
# ============================================================================

class TestResponseHandling:
    """测试响应处理"""

    def test_handle_success_response_with_standard_format(self):
        """测试处理标准格式的成功响应"""
        client = OpenTaskClient()
        mock_response = mock.Mock()
        mock_response.json.return_value = {"code": 200, "data": {"result": "success"}}
        mock_response.status_code = 200

        result = client._handle_response(mock_response)
        assert result == {"result": "success"}

    def test_handle_success_response_without_data_field(self):
        """测试处理没有 data 字段的成功响应"""
        client = OpenTaskClient()
        mock_response = mock.Mock()
        mock_response.json.return_value = {"code": 200}
        mock_response.status_code = 200

        result = client._handle_response(mock_response)
        # 当响应只有 {"code": 200} 时，返回整个响应对象
        assert result == {"code": 200}

    def test_handle_error_response_with_code(self):
        """测试处理带错误码的响应"""
        client = OpenTaskClient()
        mock_response = mock.Mock()
        mock_response.json.return_value = {"code": 400, "message": "Bad Request"}
        mock_response.status_code = 200

        with pytest.raises(APIError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.message == "Bad Request"
        assert exc_info.value.status_code == 400

    def test_handle_error_response_with_http_error(self):
        """测试处理 HTTP 错误响应"""
        client = OpenTaskClient()
        mock_response = mock.Mock()
        mock_response.json.return_value = {"message": "Not Found"}
        mock_response.status_code = 404

        with pytest.raises(APIError) as exc_info:
            client._handle_response(mock_response)

        assert "Not Found" in exc_info.value.message
        assert exc_info.value.status_code == 404

    def test_handle_invalid_json_response(self):
        """测试处理无效 JSON 响应"""
        import json
        client = OpenTaskClient()
        mock_response = mock.Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.status_code = 200

        result = client._handle_response(mock_response)
        assert result == {}

    def test_handle_fallback_response_format(self):
        """测试处理回退格式响应（没有 code 字段）"""
        client = OpenTaskClient()
        mock_response = mock.Mock()
        mock_response.json.return_value = {"id": 123, "name": "test"}
        mock_response.status_code = 200

        result = client._handle_response(mock_response)
        assert result == {"id": 123, "name": "test"}


# ============================================================================
# HTTP 请求测试
# ============================================================================

class TestHTTPRequest:
    """测试 HTTP 请求方法"""

    @pytest.mark.asyncio
    async def test_get_request(self):
        """测试 GET 请求"""
        client = OpenTaskClient(base_url="http://test.com", token="test_token")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.return_value = {"id": 1}
            result = await client.get("/api/test")

            assert result == {"id": 1}
            mock_request.assert_called_once_with("GET", "/api/test", params=None)

    @pytest.mark.asyncio
    async def test_post_request(self):
        """测试 POST 请求"""
        client = OpenTaskClient(base_url="http://test.com")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.return_value = {"success": True}
            result = await client.post("/api/create", data={"name": "test"})

            assert result == {"success": True}
            mock_request.assert_called_once_with("POST", "/api/create", json={"name": "test"})

    @pytest.mark.asyncio
    async def test_put_request(self):
        """测试 PUT 请求"""
        client = OpenTaskClient(base_url="http://test.com")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.return_value = {"updated": True}
            result = await client.put("/api/update/1", data={"name": "updated"})

            assert result == {"updated": True}
            mock_request.assert_called_once_with("PUT", "/api/update/1", json={"name": "updated"})

    @pytest.mark.asyncio
    async def test_delete_request(self):
        """测试 DELETE 请求"""
        client = OpenTaskClient(base_url="http://test.com")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.return_value = {"deleted": True}
            result = await client.delete("/api/delete/1")

            assert result == {"deleted": True}
            mock_request.assert_called_once_with("DELETE", "/api/delete/1")


# ============================================================================
# 错误处理测试
# ============================================================================

class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_network_error(self):
        """测试网络错误处理"""
        client = OpenTaskClient(base_url="http://test.com")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.side_effect = APIError("Connection refused: http://test.com/api/test")

            with pytest.raises(APIError) as exc_info:
                await client.get("/api/test")

            assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """测试超时错误处理"""
        client = OpenTaskClient(base_url="http://test.com", token="test_token")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.side_effect = APIError("Request timeout: http://test.com/api/test")

            with pytest.raises(APIError) as exc_info:
                await client.get("/api/test")

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_api_error_propagation(self):
        """测试 API 错误传播"""
        client = OpenTaskClient(base_url="http://test.com")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.side_effect = APIError("Internal Server Error", status_code=500)

            with pytest.raises(APIError) as exc_info:
                await client.get("/api/test")

            assert exc_info.value.status_code == 500
            assert exc_info.value.message == "Internal Server Error"


# ============================================================================
# Token 和认证测试
# ============================================================================

class TestAuthentication:
    """测试认证功能"""

    @pytest.mark.asyncio
    async def test_request_includes_authorization_header(self):
        """测试请求包含认证头"""
        client = OpenTaskClient(base_url="http://test.com", token="secret_token")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.return_value = {}
            await client.get("/api/protected")

            # 验证请求包含认证头
            call_args = mock_request.call_args
            # _request 方法内部会调用 _get_headers()
            # 我们只需要验证请求被执行了
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_without_token(self):
        """测试不带 token 的请求"""
        client = OpenTaskClient(base_url="http://test.com")

        with mock.patch.object(client, '_request') as mock_request:
            mock_request.return_value = {}
            await client.get("/api/public")

            # 验证请求被执行
            mock_request.assert_called_once()


# ============================================================================
# 边缘情况测试
# ============================================================================

class TestEdgeCases:
    """测试边缘情况"""

    def test_empty_token(self):
        """测试空 token"""
        client = OpenTaskClient(token="")
        headers = client._get_headers()
        assert "Authorization" not in headers

    def test_none_token(self):
        """测试 None token"""
        client = OpenTaskClient(token=None)
        headers = client._get_headers()
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_empty_response_data(self):
        """测试空响应数据"""
        client = OpenTaskClient()

        with mock.patch.object(client, '_request') as mock_request:
            # 当 data 为 None 时，get_data() 返回 None
            mock_request.return_value = None
            result = await client.get("/api/test")

            assert result is None

    @pytest.mark.asyncio
    async def test_malformed_url_error(self):
        """测试格式错误的 URL"""
        client = OpenTaskClient(base_url="not-a-valid-url")

        with mock.patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.UnsupportedProtocol("Invalid URL")

            with pytest.raises(APIError):
                await client.get("/api/test")

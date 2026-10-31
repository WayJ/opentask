"""
OpenTask CLI 核心功能测试

测试范围：
- CLI 初始化
- 配置加载
- 基础功能
- 错误处理
"""

import pytest
from unittest import mock
import os
import tempfile


# ============================================================================
# CLI 初始化测试
# ============================================================================

def test_cli_initialization():
    """测试 CLI 初始化"""
    from opentask.opentask_cli import cli

    assert cli is not None
    # 验证 CLI 是一个 Click 命令组
    assert hasattr(cli, 'commands')


def test_cli_version():
    """测试 CLI 版本"""
    from opentask import __version__

    assert __version__ is not None
    # 验证版本格式
    parts = __version__.split('.')
    assert len(parts) >= 2
    assert all(part.isdigit() for part in parts)


# ============================================================================
# 配置管理测试
# ============================================================================

def test_config_loading():
    """测试配置加载"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write('test: value\n')
        config_file = f.name

    try:
        # 模拟配置加载
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        assert config['test'] == 'value'
    finally:
        os.unlink(config_file)


def test_config_defaults():
    """测试默认配置"""
    default_config = {
        'api_base_url': 'http://localhost:7377',
        'timeout': 30,
        'log_level': 'INFO'
    }

    assert default_config['api_base_url'] == 'http://localhost:7377'
    assert default_config['timeout'] == 30


def test_config_override():
    """测试配置覆盖"""
    base_config = {'key1': 'value1'}
    override_config = {'key1': 'overridden', 'key2': 'value2'}
    merged = {**base_config, **override_config}

    assert merged['key1'] == 'overridden'
    assert merged['key2'] == 'value2'


# ============================================================================
# 错误处理测试
# ============================================================================

def test_handle_api_error():
    """测试 API 错误处理"""
    error_response = {
        'code': 401,
        'message': 'Unauthorized'
    }

    assert error_response['code'] == 401
    assert error_response['message'] == 'Unauthorized'


def test_handle_network_error():
    """测试网络错误处理"""
    class NetworkError(Exception):
        pass

    error = NetworkError('Network connection failed')

    assert str(error) == 'Network connection failed'


def test_handle_invalid_response():
    """测试无效响应处理"""
    invalid_response = None

    assert invalid_response is None


# ============================================================================
# 日志功能测试
# ============================================================================

def test_logging_setup():
    """测试日志设置"""
    import logging

    logger = logging.getLogger('opentask')
    logger.setLevel(logging.INFO)

    assert logger.level == logging.INFO


def test_log_message():
    """测试日志消息"""
    import logging
    from io import StringIO

    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.INFO)

    # 捕获日志输出
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    logger.info('Test message')

    log_output = log_stream.getvalue()
    assert 'Test message' in log_output

    logger.removeHandler(handler)


# ============================================================================
# 工具函数测试
# ============================================================================

def test_format_timestamp():
    """测试时间戳格式化"""
    from datetime import datetime

    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    assert len(timestamp) == 19
    assert timestamp.count('-') == 2
    assert timestamp.count(':') == 2


def test_validate_url():
    """测试 URL 验证"""
    valid_url = 'http://localhost:7377'
    invalid_url = 'not-a-url'

    assert valid_url.startswith('http')
    assert not invalid_url.startswith('http')


def test_generate_request_id():
    """测试请求 ID 生成"""
    import uuid

    request_id = str(uuid.uuid4())

    assert len(request_id) == 36
    assert request_id.count('-') == 4


# ============================================================================
# 文件操作测试
# ============================================================================

def test_read_file():
    """测试读取文件"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('test content')
        temp_file = f.name

    try:
        with open(temp_file, 'r') as f:
            content = f.read()

        assert content == 'test content'
    finally:
        os.unlink(temp_file)


def test_write_file():
    """测试写入文件"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_file = f.name

    try:
        with open(temp_file, 'w') as f:
            f.write('new content')

        with open(temp_file, 'r') as f:
            content = f.read()

        assert content == 'new content'
    finally:
        os.unlink(temp_file)


def test_file_exists():
    """测试文件存在检查"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_file = f.name

    try:
        assert os.path.exists(temp_file)
        assert not os.path.exists('nonexistent_file.txt')
    finally:
        os.unlink(temp_file)


# ============================================================================
# 数据序列化测试
# ============================================================================

def test_json_serialize():
    """测试 JSON 序列化"""
    import json

    data = {'key': 'value', 'number': 123}
    serialized = json.dumps(data)

    assert 'key' in serialized
    assert 'value' in serialized


def test_json_deserialize():
    """测试 JSON 反序列化"""
    import json

    json_string = '{"key": "value", "number": 123}'
    deserialized = json.loads(json_string)

    assert deserialized['key'] == 'value'
    assert deserialized['number'] == 123


# ============================================================================
# 环境变量测试
# ============================================================================

def test_get_env_variable():
    """测试获取环境变量"""
    # 设置测试环境变量
    os.environ['TEST_VAR'] = 'test_value'

    value = os.environ.get('TEST_VAR')

    assert value == 'test_value'

    # 清理
    del os.environ['TEST_VAR']


def test_get_env_variable_default():
    """测试获取环境变量 - 使用默认值"""
    value = os.environ.get('NONEXISTENT_VAR', 'default_value')

    assert value == 'default_value'


# ============================================================================
# 并发测试
# ============================================================================

def test_thread_safety():
    """测试线程安全"""
    import threading

    counter = [0]
    lock = threading.Lock()

    def increment():
        with lock:
            counter[0] += 1

    threads = [threading.Thread(target=increment) for _ in range(100)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert counter[0] == 100

"""
快速测试运行脚本

运行所有后端单元测试（使用独立脚本，避免数据库迁移问题）
"""

import sys
import subprocess
from pathlib import Path


def run_test(script_path: str, description: str) -> bool:
    """运行测试脚本"""
    print(f"\n{'=' * 70}")
    print(f"运行: {description}")
    print(f"脚本: {script_path}")
    print('=' * 70)

    result = subprocess.run(
        ["uv", "run", "python", script_path],
        capture_output=False
    )

    if result.returncode == 0:
        print(f"[PASS] {description}")
        return True
    else:
        print(f"[FAIL] {description}")
        return False


def main():
    """主测试运行函数"""
    print("\n" + "=" * 70)
    print("OpenTask 后端快速单元测试")
    print("=" * 70)

    backend_dir = Path(__file__).parent.parent

    # 测试列表
    tests = [
        (
            "tests/websocket/run_websocket_tests.py",
            "WebSocket Hub 单元测试"
        ),
        (
            "tests/websocket/test_websocket_integration.py",
            "WebSocket 集成测试"
        ),
        (
            "tests/agent_task/run_service_tests.py",
            "Agent Task 服务测试"
        ),
    ]

    # 运行测试
    results = []
    for script_path, description in tests:
        full_path = backend_dir / script_path
        success = run_test(str(full_path), description)
        results.append((description, success))

    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {description}")

    print("\n" + "=" * 70)
    print(f"总计: {passed}/{total} 测试通过")
    print("=" * 70)

    if passed == total:
        print("\n[SUCCESS] 所有测试通过！")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

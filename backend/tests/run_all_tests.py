"""
后端单元测试运行脚本

运行所有后端单元测试并生成报告
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """运行命令并返回是否成功"""
    print(f"\n{'=' * 70}")
    print(f"运行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print('=' * 70)

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"[PASS] {description}")
        return True
    else:
        print(f"[FAIL] {description}")
        return False


def main():
    """主测试运行函数"""
    print("\n" + "=" * 70)
    print("OpenTask 后端单元测试套件")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"

    # 测试结果
    results = {}

    # 1. WebSocket Hub 测试
    print("\n" + "=" * 70)
    print("测试套件 1: WebSocket Hub 服务")
    print("=" * 70)

    websocket_tests = [
        (
            ["uv", "run", "python", "-m", "pytest", "tests/websocket/test_hub_service.py", "-v"],
            "WebSocket Hub 服务单元测试"
        ),
        (
            ["uv", "run", "python", "-m", "pytest", "tests/websocket/test_message_routing.py", "-v"],
            "WebSocket 消息路由测试"
        ),
        (
            ["uv", "run", "python", "tests/websocket/test_websocket_integration.py"],
            "WebSocket 集成测试"
        ),
    ]

    websocket_passed = 0
    for cmd, desc in websocket_tests:
        if run_command(cmd, desc):
            websocket_passed += 1

    results["websocket"] = {
        "total": len(websocket_tests),
        "passed": websocket_passed,
        "tests": websocket_tests
    }

    # 2. Agent Task 测试
    print("\n" + "=" * 70)
    print("测试套件 2: Agent Task 服务")
    print("=" * 70)

    agent_task_tests = [
        (
            ["uv", "run", "python", "-m", "pytest", "tests/agent_task/test_agent_task_service.py", "-v"],
            "Agent Task 服务单元测试"
        ),
    ]

    agent_task_passed = 0
    for cmd, desc in agent_task_tests:
        if run_command(cmd, desc):
            agent_task_passed += 1

    results["agent_task"] = {
        "total": len(agent_task_tests),
        "passed": agent_task_passed,
        "tests": agent_task_tests
    }

    # 3. Requirement Task 测试
    print("\n" + "=" * 70)
    print("测试套件 3: Requirement Task 服务")
    print("=" * 70)

    requirement_tests = [
        (
            ["uv", "run", "python", "-m", "pytest", "tests/requirement/test_task_service.py", "-v"],
            "Requirement Task 服务单元测试"
        ),
    ]

    requirement_passed = 0
    for cmd, desc in requirement_tests:
        if run_command(cmd, desc):
            requirement_passed += 1

    results["requirement"] = {
        "total": len(requirement_tests),
        "passed": requirement_passed,
        "tests": requirement_tests
    }

    # 4. 其他测试
    print("\n" + "=" * 70)
    print("测试套件 4: 其他服务测试")
    print("=" * 70)

    other_tests = [
        (
            ["uv", "run", "python", "-m", "pytest", "tests/test_utils.py", "-v"],
            "工具函数测试"
        ),
    ]

    other_passed = 0
    for cmd, desc in other_tests:
        if run_command(cmd, desc):
            other_passed += 1

    results["other"] = {
        "total": len(other_tests),
        "passed": other_passed,
        "tests": other_tests
    }

    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    total_tests = sum(r["total"] for r in results.values())
    total_passed = sum(r["passed"] for r in results.values())

    for suite_name, suite_results in results.items():
        suite_name_chinese = {
            "websocket": "WebSocket Hub",
            "agent_task": "Agent Task",
            "requirement": "Requirement Task",
            "other": "其他"
        }.get(suite_name, suite_name)

        passed = suite_results["passed"]
        total = suite_results["total"]
        status = "[PASS]" if passed == total else f"[{passed}/{total}]"

        print(f"{status} {suite_name_chinese}: {passed}/{total}")

    print("\n" + "=" * 70)
    overall_status = "[PASS]" if total_passed == total_tests else f"[{total_passed}/{total_tests}]"
    print(f"{overall_status} 总计: {total_passed}/{total_tests} 测试通过")
    print("=" * 70)

    if total_passed == total_tests:
        print("\n[SUCCESS] 所有测试通过！")
        return 0
    else:
        print(f"\n[FAIL] {total_tests - total_passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

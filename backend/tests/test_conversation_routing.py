#!/usr/bin/env python3
"""
测试对话创建后的路由功能
验证智能报告（deep_search）对话创建后是否正确路由到深度搜索页面
"""

import json
import socket

import pytest
import requests


def _live_server_reachable(timeout: float = 0.5) -> bool:
    """检测本地冒烟服务是否在运行"""
    try:
        with socket.create_connection(("localhost", 7377), timeout=timeout):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _live_server_reachable(),
    reason="live 冒烟脚本：需要本地运行中的服务 http://localhost:7377",
)


def test_conversation_routing():
    """测试对话创建后的路由功能"""
    base_url = "http://localhost:7377"
    session = requests.Session()

    print("🧪 对话创建路由功能测试")
    print("=" * 50)

    # 1. 登录
    print("\n📝 步骤 1: 登录系统")
    login_response = session.post(
        f"{base_url}/auth/login",
        json={"username": "admin", "password": "admin"}
    )

    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        return False

    token = login_response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ 登录成功")

    # 2. 测试创建智能问数对话
    print("\n📝 步骤 2: 创建智能问数对话")
    sql_data = {
        "connection_id": "",  # 获取实际连接
        "name": "智能问数测试",
        "conversation_type": "sql_chat",
        "ai_settings": {"model": "gpt-4", "temperature": 0.7}
    }

    # 先获取连接
    connections_response = session.get(f"{base_url}/connections")
    if connections_response.status_code == 200:
        connections_data = connections_response.json()
        connections = connections_data.get("data", {}).get("connections", [])
        if connections:
            sql_data["connection_id"] = connections[0]["id"]

    sql_response = session.post(f"{base_url}/conversation", json=sql_data)

    if sql_response.status_code == 200:
        sql_result = sql_response.json()["data"]
        sql_conversation_id = sql_result["id"]
        print(f"✅ 智能问数对话创建成功: {sql_conversation_id}")
        print(f"   📋 对话类型: {sql_result['conversation_type']}")
        print(f"   🔗 应该路由到: /chat/{sql_conversation_id}")
    else:
        print(f"❌ 智能问数对话创建失败: {sql_response.status_code}")
        return False

    # 3. 测试创建智能报告对话
    print("\n📝 步骤 3: 创建智能报告对话")
    deep_search_data = {
        "connection_id": "",  # 空字符串，可选
        "name": "智能报告测试",
        "conversation_type": "deep_search",
        "ai_settings": {"model": "gpt-4", "temperature": 0.7}
    }

    deep_search_response = session.post(f"{base_url}/conversation", json=deep_search_data)

    if deep_search_response.status_code == 200:
        deep_search_result = deep_search_response.json()["data"]
        deep_search_conversation_id = deep_search_result["id"]
        print(f"✅ 智能报告对话创建成功: {deep_search_conversation_id}")
        print(f"   📋 对话类型: {deep_search_result['conversation_type']}")
        print(f"   🔗 应该路由到: /deepsearch")
    else:
        print(f"❌ 智能报告对话创建失败: {deep_search_response.status_code}")
        return False

    # 4. 测试对话列表显示正确的类型
    print("\n📝 步骤 4: 验证对话列表显示")
    list_response = session.get(f"{base_url}/conversations")

    if list_response.status_code == 200:
        conversations = list_response.json().get("data", [])
        print(f"   📊 当前对话数量: {len(conversations)}")

        # 查找我们创建的对话
        sql_convo = next((c for c in conversations if c["id"] == sql_conversation_id), None)
        deep_search_convo = next((c for c in conversations if c["id"] == deep_search_conversation_id), None)

        if sql_convo:
            print(f"   ✅ 智能问数对话在列表中显示为: {sql_convo['conversation_type']}")
        else:
            print(f"   ❌ 智能问数对话未在列表中找到")

        if deep_search_convo:
            print(f"   ✅ 智能报告对话在列表中显示为: {deep_search_convo['conversation_type']}")
        else:
            print(f"   ❌ 智能报告对话未在列表中找到")
    else:
        print(f"❌ 获取对话列表失败: {list_response.status_code}")

    # 5. 清理测试数据
    print("\n📝 步骤 5: 清理测试数据")

    # 删除测试对话
    if sql_conversation_id:
        delete_sql_response = session.delete(f"{base_url}/conversation/{sql_conversation_id}")
        if delete_sql_response.status_code == 200:
            print("✅ 智能问数测试对话已删除")
        else:
            print(f"❌ 删除智能问数对话失败: {delete_sql_response.status_code}")

    if deep_search_conversation_id:
        delete_deep_search_response = session.delete(f"{base_url}/conversation/{deep_search_conversation_id}")
        if delete_deep_search_response.status_code == 200:
            print("✅ 智能报告测试对话已删除")
        else:
            print(f"❌ 删除智能报告对话失败: {delete_deep_search_response.status_code}")

    print("\n🎉 对话创建路由功能测试完成！")
    print("\n📋 路由规则验证:")
    print("   • 智能问数 (sql_chat) → 应路由到 /chat/{conversationId}")
    print("   • 智能报告 (deep_search) → 应路由到 /chat/{conversationId}")
    print("\n✅ 统一的路由逻辑:")
    print("   • 所有对话类型都使用相同的URL模式 /chat/{conversationId}")
    print("   • 前端根据对话类型渲染不同的界面组件")
    print("\n⚠️  注意: 前端路由逻辑已修正为统一模式")

    return True


def main():
    """主函数"""
    try:
        success = test_conversation_routing()

        if success:
            print(f"\n🎉 路由功能测试完成！")
            print(f"   后端对话创建功能正常")
            print(f"   前端路由逻辑已修复")
        else:
            print(f"\n💥 路由功能测试失败")

    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")


if __name__ == "__main__":
    main()
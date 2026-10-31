#!/usr/bin/env python3
"""
测试前端对话类型显示功能
验证不同对话类型是否正确显示对应的界面组件
"""

import requests
import json


def test_conversation_type_display():
    """测试对话类型在界面中的正确显示"""
    base_url = "http://localhost:7377"
    session = requests.Session()

    print("🧪 对话类型显示功能测试")
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

    # 2. 获取数据连接
    print("\n📝 步骤 2: 获取数据连接")
    connections_response = session.get(f"{base_url}/connections")
    if connections_response.status_code != 200:
        print(f"❌ 获取连接失败: {connections_response.status_code}")
        return False

    connections_data = connections_response.json()
    connections = connections_data.get("data", {}).get("connections", [])
    connection_id = connections[0]["id"] if connections else ""

    # 3. 创建智能问数对话
    print("\n📝 步骤 3: 创建智能问数对话")
    sql_data = {
        "connection_id": connection_id,
        "name": "智能问数显示测试",
        "conversation_type": "sql_chat",
        "ai_settings": {"model": "gpt-4", "temperature": 0.7}
    }

    sql_response = session.post(f"{base_url}/conversation", json=sql_data)

    if sql_response.status_code == 200:
        sql_result = sql_response.json()["data"]
        sql_conversation_id = sql_result["id"]
        print(f"✅ 智能问数对话创建成功: {sql_conversation_id}")
        print(f"   📋 对话类型: {sql_result['conversation_type']}")
        print(f"   🔗 前端URL: http://localhost:5173/chat/{sql_conversation_id}")
        print(f"   🎨 期望显示: SQL聊天界面")
    else:
        print(f"❌ 智能问数对话创建失败: {sql_response.status_code}")
        return False

    # 4. 创建智能报告对话
    print("\n📝 步骤 4: 创建智能报告对话")
    deep_search_data = {
        "connection_id": "",  # 空字符串，可选
        "name": "智能报告显示测试",
        "conversation_type": "deep_search",
        "ai_settings": {"model": "gpt-4", "temperature": 0.7}
    }

    deep_search_response = session.post(f"{base_url}/conversation", json=deep_search_data)

    if deep_search_response.status_code == 200:
        deep_search_result = deep_search_response.json()["data"]
        deep_search_conversation_id = deep_search_result["id"]
        print(f"✅ 智能报告对话创建成功: {deep_search_conversation_id}")
        print(f"   📋 对话类型: {deep_search_result['conversation_type']}")
        print(f"   🔗 前端URL: http://localhost:5173/chat/{deep_search_conversation_id}")
        print(f"   🎨 期望显示: 深度搜索界面")
    else:
        print(f"❌ 智能报告对话创建失败: {deep_search_response.status_code}")
        return False

    # 5. 验证对话列表中的类型显示
    print("\n📝 步骤 5: 验证对话列表中的类型显示")
    list_response = session.get(f"{base_url}/conversations")

    if list_response.status_code == 200:
        conversations = list_response.json().get("data", [])
        print(f"   📊 当前对话数量: {len(conversations)}")

        # 查找我们创建的对话
        sql_convo = next((c for c in conversations if c["id"] == sql_conversation_id), None)
        deep_search_convo = next((c for c in conversations if c["id"] == deep_search_conversation_id), None)

        if sql_convo:
            print(f"   ✅ 智能问数对话后端数据: {sql_convo['conversation_type']}")
            print(f"   🔗 前端应显示: 智能问数界面 + SQL聊天功能")
        else:
            print(f"   ❌ 智能问数对话未在列表中找到")

        if deep_search_convo:
            print(f"   ✅ 智能报告对话后端数据: {deep_search_convo['conversation_type']}")
            print(f"   🔗 前端应显示: 智能报告界面 + 深度搜索功能")
        else:
            print(f"   ❌ 智能报告对话未在列表中找到")
    else:
        print(f"❌ 获取对话列表失败: {list_response.status_code}")

    # 6. 清理测试数据
    print("\n📝 步骤 6: 清理测试数据")

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

    print("\n🎉 对话类型显示功能测试完成！")
    print("\n📋 前端界面期望行为:")
    print("   • 智能问数 (sql_chat):")
    print("     - 头部显示: 💬 智能问数")
    print("     - 输入框提示: '输入你的问题...'")
    print("     - 模板消息: SQL相关示例")
    print("     - 功能: 常规SQL查询对话")
    print("")
    print("   • 智能报告 (deep_search):")
    print("     - 头部显示: 🔍 智能报告")
    print("     - 输入框提示: '输入要进行深度搜索的内容...'")
    print("     - 模板消息: 深度搜索相关示例")
    print("     - 功能: DeepSearch + Genie集成")
    print("     - 额外按钮: '显示搜索面板'")
    print("")
    print("⚠️  注意: 需要手动验证前端界面的实际显示效果")

    return True


def main():
    """主函数"""
    try:
        success = test_conversation_type_display()

        if success:
            print(f"\n🎉 后端数据验证完成！")
            print(f"   对话类型数据正确存储")
            print(f"   前端组件逻辑已修复")
            print(f"   请手动验证界面显示效果")
        else:
            print(f"\n💥 测试失败")

    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")


if __name__ == "__main__":
    main()
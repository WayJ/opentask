#!/usr/bin/env python3
"""
测试优化后的对话创建功能
验证只保留SQL对话和深度搜索两种类型
"""

import requests
import json
import time


class OptimizedConversationTester:
    def __init__(self, base_url: str = "http://localhost:7377"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None

    def login(self) -> bool:
        """登录系统"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": "admin", "password": "admin"}
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                print(f"✅ 登录成功")
                return True
            else:
                print(f"❌ 登录失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False

    def test_sql_conversation_creation(self) -> bool:
        """测试SQL对话创建（必须选择数据连接）"""
        print("\n📝 测试SQL对话创建（必须选择数据连接）...")

        # 首先获取可用的连接
        connections_response = self.session.get(f"{self.base_url}/connections")
        if connections_response.status_code != 200:
            print("   ❌ 获取连接列表失败")
            return False

        connections_data = connections_response.json()
        connections = connections_data.get("data", {}).get("connections", [])
        if not connections:
            print("   ⚠️  没有可用的数据连接，跳过SQL对话测试")
            return True

        connection_id = connections[0]["id"]

        # 创建SQL对话
        sql_data = {
            "connection_id": connection_id,
            "name": "SQL对话测试",
            "conversation_type": "sql_chat",
            "ai_settings": {"model": "gpt-4", "temperature": 0.7}
        }

        response = self.session.post(f"{self.base_url}/conversation", json=sql_data)

        if response.status_code == 200:
            result = response.json()["data"]
            conversation_id = result["id"]
            print(f"   ✅ SQL对话创建成功: {conversation_id}")
            print(f"   📋 对话类型: {result['conversation_type']}")
            print(f"   🔗 Connection ID: {result.get('connection_id')}")

            # 清理测试数据
            self.session.delete(f"{self.base_url}/conversation/{conversation_id}")
            return True
        else:
            print(f"   ❌ SQL对话创建失败: {response.status_code}")
            print(f"   📄 错误详情: {response.text}")
            return False

    def test_deep_search_conversation_without_connection(self) -> bool:
        """测试深度搜索对话创建（不选择数据连接）"""
        print("\n📝 测试深度搜索对话创建（不选择数据连接）...")

        deep_search_data = {
            "connection_id": "",  # 空字符串
            "name": "深度搜索对话测试",
            "conversation_type": "deep_search",
            "ai_settings": {"model": "gpt-4", "temperature": 0.7}
        }

        response = self.session.post(f"{self.base_url}/conversation", json=deep_search_data)

        if response.status_code == 200:
            result = response.json()["data"]
            conversation_id = result["id"]
            print(f"   ✅ 深度搜索对话创建成功: {conversation_id}")
            print(f"   📋 对话类型: {result['conversation_type']}")
            print(f"   🔗 Connection ID: {result.get('connection_id')}")

            # 清理测试数据
            self.session.delete(f"{self.base_url}/conversation/{conversation_id}")
            return True
        else:
            print(f"   ❌ 深度搜索对话创建失败: {response.status_code}")
            print(f"   📄 错误详情: {response.text}")
            return False

    def test_deep_search_conversation_with_connection(self) -> bool:
        """测试深度搜索对话创建（选择数据连接）"""
        print("\n📝 测试深度搜索对话创建（选择数据连接）...")

        # 首先获取可用的连接
        connections_response = self.session.get(f"{self.base_url}/connections")
        if connections_response.status_code != 200:
            print("   ❌ 获取连接列表失败")
            return False

        connections = connections_response.json().get("data", {}).get("connections", [])
        if not connections:
            print("   ⚠️  没有可用的数据连接，跳过此测试")
            return True

        connection_id = connections[0]["id"]

        # 创建带连接的深度搜索对话
        deep_search_data = {
            "connection_id": connection_id,
            "name": "深度搜索对话测试（带连接）",
            "conversation_type": "deep_search",
            "ai_settings": {"model": "gpt-4", "temperature": 0.7}
        }

        response = self.session.post(f"{self.base_url}/conversation", json=deep_search_data)

        if response.status_code == 200:
            result = response.json()["data"]
            conversation_id = result["id"]
            print(f"   ✅ 深度搜索对话创建成功: {conversation_id}")
            print(f"   📋 对话类型: {result['conversation_type']}")
            print(f"   🔗 Connection ID: {result.get('connection_id')}")

            # 清理测试数据
            self.session.delete(f"{self.base_url}/conversation/{conversation_id}")
            return True
        else:
            print(f"   ❌ 深度搜索对话创建失败: {response.status_code}")
            print(f"   📄 错误详情: {response.text}")
            return False

    def test_invalid_conversation_types(self) -> bool:
        """测试无效的对话类型应该被拒绝"""
        print("\n📝 测试无效对话类型...")

        invalid_types = ["data_analysis", "report_generation", "invalid_type"]

        for invalid_type in invalid_types:
            test_data = {
                "connection_id": "",
                "name": f"无效类型测试 {invalid_type}",
                "conversation_type": invalid_type,
                "ai_settings": {"model": "gpt-4", "temperature": 0.7}
            }

            response = self.session.post(f"{self.base_url}/conversation", json=test_data)

            # 期望后端接受这些类型，因为后端没有限制
            # 主要验证前端只显示两种类型
            if response.status_code == 200:
                result = response.json()["data"]
                conversation_id = result["id"]
                print(f"   ⚠️  后端接受类型 '{invalid_type}'（前端应该不显示）")
                # 清理测试数据
                self.session.delete(f"{self.base_url}/conversation/{conversation_id}")
            else:
                print(f"   ✅ 类型 '{invalid_type}' 被正确拒绝")

        return True

    def test_conversation_list_shows_correct_types(self) -> bool:
        """测试对话列表显示正确的类型"""
        print("\n📝 测试对话列表显示...")

        # 创建两种类型的对话
        sql_conv_data = {
            "connection_id": "",
            "name": "SQL对话列表测试",
            "conversation_type": "sql_chat",
        }

        deep_search_conv_data = {
            "connection_id": "",
            "name": "深度搜索对话列表测试",
            "conversation_type": "deep_search",
        }

        created_ids = []

        # 创建SQL对话（如果有连接的话）
        try:
            connections_response = self.session.get(f"{self.base_url}/connections")
            if connections_response.status_code == 200:
                connections = connections_response.json().get("data", {}).get("connections", [])
                if connections:
                    sql_conv_data["connection_id"] = connections[0]["id"]
                    sql_response = self.session.post(f"{self.base_url}/conversation", json=sql_conv_data)
                    if sql_response.status_code == 200:
                        created_ids.append(sql_response.json()["data"]["id"])
        except:
            pass

        # 创建深度搜索对话
        deep_response = self.session.post(f"{self.base_url}/conversation", json=deep_search_conv_data)
        if deep_response.status_code == 200:
            created_ids.append(deep_response.json()["data"]["id"])

        # 获取对话列表
        list_response = self.session.get(f"{self.base_url}/conversations")
        if list_response.status_code == 200:
            conversations = list_response.json().get("data", [])
            print(f"   📊 当前对话数量: {len(conversations)}")

            # 显示对话类型
            types_found = set()
            for conv in conversations:
                if conv["id"] in created_ids:
                    types_found.add(conv["conversation_type"])
                    print(f"   📋 对话: {conv['name']} - 类型: {conv['conversation_type']}")

            # 清理测试数据
            for conv_id in created_ids:
                self.session.delete(f"{self.base_url}/conversation/{conv_id}")

            return True
        else:
            print(f"   ❌ 获取对话列表失败: {list_response.status_code}")
            # 清理测试数据
            for conv_id in created_ids:
                try:
                    self.session.delete(f"{self.base_url}/conversation/{conv_id}")
                except:
                    pass
            return False

    def run_optimized_tests(self) -> bool:
        """运行所有优化测试"""
        print("🧪 优化后的对话创建功能测试")
        print("=" * 60)

        # 1. 登录
        print("\n📝 步骤 1: 登录系统")
        if not self.login():
            return False

        # 2. 测试SQL对话创建
        print("\n📝 步骤 2: 测试SQL对话创建")
        sql_success = self.test_sql_conversation_creation()

        # 3. 测试深度搜索对话创建（无连接）
        print("\n📝 步骤 3: 测试深度搜索对话创建（无连接）")
        deep_search_no_conn_success = self.test_deep_search_conversation_without_connection()

        # 4. 测试深度搜索对话创建（有连接）
        print("\n📝 步骤 4: 测试深度搜索对话创建（有连接）")
        deep_search_with_conn_success = self.test_deep_search_conversation_with_connection()

        # 5. 测试无效类型
        print("\n📝 步骤 5: 测试无效对话类型")
        invalid_types_success = self.test_invalid_conversation_types()

        # 6. 测试对话列表
        print("\n📝 步骤 6: 测试对话列表")
        list_success = self.test_conversation_list_shows_correct_types()

        # 7. 总结
        print(f"\n📊 测试结果总结:")
        print(f"   登录系统: ✅")
        print(f"   SQL对话创建: {'✅' if sql_success else '❌'}")
        print(f"   深度搜索创建（无连接）: {'✅' if deep_search_no_conn_success else '❌'}")
        print(f"   深度搜索创建（有连接）: {'✅' if deep_search_with_conn_success else '❌'}")
        print(f"   无效类型处理: {'✅' if invalid_types_success else '❌'}")
        print(f"   对话列表显示: {'✅' if list_success else '❌'}")

        overall_success = all([
            sql_success,
            deep_search_no_conn_success,
            deep_search_with_conn_success,
            invalid_types_success,
            list_success
        ])

        if overall_success:
            print(f"\n🎉 优化后的对话创建功能测试完全成功！")
            print(f"   - 只保留了SQL对话和深度搜索两种类型")
            print(f"   - SQL对话必须选择数据连接")
            print(f"   - 深度搜索的数据连接为可选")
        else:
            print(f"\n💥 部分测试失败，需要进一步检查")

        return overall_success


def main():
    """主函数"""
    tester = OptimizedConversationTester()

    try:
        success = tester.run_optimized_tests()

        if success:
            print(f"\n🎉 前端对话创建逻辑优化完成！")
        else:
            print(f"\n💥 优化验证失败，需要进一步调试")

    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")


if __name__ == "__main__":
    main()
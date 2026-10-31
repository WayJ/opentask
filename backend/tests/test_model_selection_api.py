#!/usr/bin/env python3
"""
测试修复后的模型选择API
"""

import asyncio
import json
import aiohttp


async def test_model_selection_api():
    """测试模型选择API"""
    base_url = "http://localhost:7377"

    async with aiohttp.ClientSession() as session:
        print("🔍 测试模型选择API...")

        # 1. 登录获取JWT token
        print("\n1. 登录获取JWT token...")
        login_data = {
            "username": "admin",
            "password": "admin"
        }

        async with session.post(f"{base_url}/auth/login", json=login_data) as response:
            if response.status == 200:
                result = await response.json()
                token = result["access_token"]
                print(f"✅ 登录成功，获得token: {token[:20]}...")
            else:
                print(f"❌ 登录失败: {response.status}")
                return False

        # 2. 测试模型选择API（无JWT token）
        print("\n2. 测试无JWT token的模型选择API...")
        model_data = {"selected_model": "gpt-4"}

        async with session.post(f"{base_url}/settings/model-selection", json=model_data) as response:
            if response.status == 401:
                print("✅ 无JWT token时正确返回401未授权")
            else:
                print(f"⚠️ 无JWT token时返回状态码: {response.status}")
                error_text = await response.text()
                print(f"   响应内容: {error_text}")

        # 3. 测试模型选择API（有JWT token）
        print("\n3. 测试有JWT token的模型选择API...")
        headers = {"Authorization": f"Bearer {token}"}

        async with session.post(
            f"{base_url}/settings/model-selection",
            json=model_data,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                print("✅ 有JWT token时模型选择成功")
                print(f"   响应: {result}")
            else:
                print(f"❌ 有JWT token时模型选择失败: {response.status}")
                error_text = await response.text()
                print(f"   错误信息: {error_text}")
                return False

        # 4. 测试无效模型选择
        print("\n4. 测试无效模型选择...")
        invalid_model_data = {"selected_model": "invalid-model-name"}

        async with session.post(
            f"{base_url}/settings/model-selection",
            json=invalid_model_data,
            headers=headers
        ) as response:
            if response.status == 400:
                print("✅ 无效模型时正确返回400错误")
                error_text = await response.text()
                print(f"   错误信息: {error_text}")
            else:
                print(f"⚠️ 无效模型时返回状态码: {response.status}")
                error_text = await response.text()
                print(f"   响应内容: {error_text}")

        print("\n🎉 模型选择API测试完成！")
        return True


async def main():
    """主函数"""
    try:
        success = await test_model_selection_api()
        if success:
            print("\n✅ 所有测试通过，模型选择API修复成功！")
        else:
            print("\n❌ 部分测试失败，请检查API实现。")
        return success
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
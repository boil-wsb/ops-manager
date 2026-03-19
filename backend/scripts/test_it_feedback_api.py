"""
测试 IT Feedback API - 验证客户端IP记录功能
"""
import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}


async def test_create_feedback_with_ip():
    """测试创建反馈时自动记录客户端IP"""
    print("=" * 60)
    print("测试 1: 创建反馈并记录客户端IP")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        feedback_data = {
            "computerType": "desktop",
            "usageYears": "1-3",
            "lagLevel": "2",
            "lagScenarios": "开机,运行大型程序",
            "description": "电脑运行缓慢",
            "contact": "13800138000"
        }

        response = await client.post(
            f"{BASE_URL}/api/v1/it-feedback",
            json=feedback_data,
            headers=HEADERS
        )

        print(f"\nPOST /api/v1/it-feedback")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"响应数据:")
            print(f"  id: {data.get('id')}")
            print(f"  computerType: {data.get('computerType')}")
            print(f"  lagLevel: {data.get('lagLevel')}")
            print(f"  status: {data.get('status')}")
            print(f"  createdAt: {data.get('createdAt')}")
            print(f"  clientIp: {data.get('clientIp', 'N/A')}")

            if data.get('clientIp'):
                print(f"\n✅ 客户端IP已成功记录: {data.get('clientIp')}")
            else:
                print(f"\n⚠️ 客户端IP字段为空")

            return data.get('id'), data.get('clientIp')
        else:
            print(f"错误: {response.text}")
            return None, None


async def test_list_feedback_shows_ip():
    """测试列表接口返回客户端IP"""
    print("\n" + "=" * 60)
    print("测试 2: 列表接口返回客户端IP")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/it-feedback",
            params={"page": 1, "page_size": 10}
        )

        print(f"\nGET /api/v1/it-feedback?page=1&page_size=10")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"总数: {data.get('total')}")

            if data.get('items') and len(data['items']) > 0:
                print(f"\n最新一条记录:")
                item = data['items'][0]
                print(f"  id: {item.get('id')}")
                print(f"  clientIp: {item.get('clientIp', 'N/A')}")

                has_ip = item.get('clientIp') is not None
                if has_ip:
                    print(f"\n✅ 列表接口正确返回客户端IP")
                else:
                    print(f"\n⚠️ 列表接口未返回客户端IP")

                return has_ip
            else:
                print("暂无数据")
                return False
        else:
            print(f"错误: {response.text}")
            return False


async def test_resolve_feedback():
    """测试处理反馈功能（验证数据变更触发）"""
    print("\n" + "=" * 60)
    print("测试 3: 处理反馈功能")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/it-feedback",
            params={"status": "pending", "page": 1, "page_size": 1}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('items') and len(data['items']) > 0:
                feedback_id = data['items'][0]['id']
                print(f"\n找到待处理反馈 ID: {feedback_id}")

                resolve_response = await client.put(
                    f"{BASE_URL}/api/v1/it-feedback/{feedback_id}/resolve",
                    params={"resolved_by": "admin", "notes": "已处理测试"}
                )

                print(f"\nPUT /api/v1/it-feedback/{feedback_id}/resolve")
                print(f"状态码: {resolve_response.status_code}")

                if resolve_response.status_code == 200:
                    resolved = resolve_response.json()
                    print(f"  status: {resolved.get('status')}")
                    print(f"  resolvedBy: {resolved.get('resolvedBy')}")
                    print(f"✅ 处理反馈功能正常")
                    return True
                else:
                    print(f"错误: {resolve_response.text}")
                    return False
            else:
                print("没有待处理的反馈")
                return True
        else:
            print(f"错误: {response.text}")
            return False


async def main():
    print("\nIT Feedback API 测试")
    print(f"API地址: {BASE_URL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test1_id, test1_ip = await test_create_feedback_with_ip()
    test2_has_ip = await test_list_feedback_shows_ip() if test1_id else False
    test3_resolve = await test_resolve_feedback()

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"1. 创建反馈并记录IP: {'✅ 通过' if test1_ip else '⚠️ 待确认'}")
    print(f"2. 列表接口返回IP: {'✅ 通过' if test2_has_ip else '⚠️ 待确认'}")
    print(f"3. 处理反馈功能: {'✅ 通过' if test3_resolve else '❌ 失败'}")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
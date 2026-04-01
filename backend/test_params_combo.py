"""
测试不同的 AMiner Pro 参数组合
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

import httpx


async def test_different_params():
    """测试不同的参数组合"""
    print("=" * 80)
    print("测试不同的 AMiner Pro 参数组合")
    print("=" * 80)

    url = "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search/pro"
    headers = {'Authorization': os.environ['AMINER_API_TOKEN']}

    test_cases = [
        # 测试1: 只用 keyword
        {
            'name': '仅 keyword="QFD 铝合金轮毂"',
            'params': {'page': 0, 'size': 5, 'keyword': 'QFD 铝合金轮毂'}
        },
        # 测试2: 只用 title
        {
            'name': '仅 title="QFD 铝合金轮毂"',
            'params': {'page': 0, 'size': 5, 'title': 'QFD 铝合金轮毂'}
        },
        # 测试3: keyword=QFD, title=铝合金轮毂
        {
            'name': 'keyword="QFD", title="铝合金轮毂"',
            'params': {'page': 0, 'size': 5, 'keyword': 'QFD', 'title': '铝合金轮毂'}
        },
        # 测试4: keyword=铝合金轮毂, title=QFD (反过来)
        {
            'name': 'keyword="铝合金轮毂", title="QFD"',
            'params': {'page': 0, 'size': 5, 'keyword': '铝合金轮毂', 'title': 'QFD'}
        },
        # 测试5: keyword="QFD, 铝合金轮毂"
        {
            'name': 'keyword="QFD, 铝合金轮毂" (逗号分隔)',
            'params': {'page': 0, 'size': 5, 'keyword': 'QFD, 铝合金轮毂'}
        },
    ]

    async with httpx.AsyncClient(verify=False) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n测试{i}: {test_case['name']}")
            print("-" * 60)

            try:
                response = await client.get(url, headers=headers, params=test_case['params'])
                data = response.json()

                total = data.get('total', 0)
                items = data.get('data', data.get('items', []))

                print(f"结果数: {total}")
                if items:
                    print(f"本页返回: {len(items)} 篇")
                    print("\n前2篇:")
                    for j, item in enumerate(items[:2], 1):
                        title = item.get('title', 'N/A')[:70]
                        venue = item.get('venue_name', 'N/A')[:40]
                        year = item.get('year', 'N/A')
                        print(f"  {j}. [{year}] {title}")
                        print(f"     期刊: {venue}")
                else:
                    print("无结果")

            except Exception as e:
                print(f"错误: {e}")

            await asyncio.sleep(1)

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_different_params())

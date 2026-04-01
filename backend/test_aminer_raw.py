"""
检查 AMiner 原始返回数据
"""
import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

os.environ['AMINER_API_TOKEN'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

from services.aminer_search import AMinerSearchService


async def check_aminer_raw_data():
    """检查 AMiner 原始返回数据"""
    print("=" * 80)
    print("检查 AMiner 原始数据")
    print("=" * 80)

    async with AMinerSearchService(api_token=os.environ['AMINER_API_TOKEN']) as service:
        # 搜索 QFD
        result = await service.search_by_keyword(
            keyword="QFD",
            page=0,
            size=5
        )

        print(f"\n原始结果总数: {result.get('total', 0)}")
        print(f"返回数量: {len(result.get('items', []))}")

        for i, item in enumerate(result.get('items', []), 1):
            print(f"\n{i}. 原始数据:")
            print(f"   id: {item.get('id')}")
            print(f"   title: {item.get('title', 'N/A')}")
            print(f"   title_zh: {item.get('title_zh', 'None')}")
            print(f"   venue: {item.get('venue_name', 'N/A')}")
            print(f"   year: {item.get('year', 'N/A')}")
            print(f"   n_citation_bucket: {item.get('n_citation_bucket', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(check_aminer_raw_data())

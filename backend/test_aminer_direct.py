"""
直接测试 AMiner API
"""
import asyncio
import httpx

async def test_aminer_direct():
    """直接测试 AMiner API"""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODM2MTUyNjYsInRpbWVzdGFtcCI6MTc3NDk3NTI2NywidXNlcl9pZCI6IjY5Y2JmNTk4NDkwYmI4ZTY3M2EyMzk4ZSJ9.fLRR4tNtkxqLh56KYCQaHDKJNfKQhSd3MGGZX_-H78g"

    url = "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search"

    headers = {
        'Authorization': token
    }

    params = {
        'page': 1,
        'size': 5,
        'title': 'deep+learning'
    }

    print(f"Testing AMiner API with new token...")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print()

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

asyncio.run(test_aminer_direct())

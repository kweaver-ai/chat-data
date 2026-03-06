# -*- coding: utf-8 -*-
# @Time    : 2025/11/9 18:28
# @Author  : Glen.lv
# @File    : mock_request
# @Project : af-sailor

from starlette.requests import Request
from starlette.datastructures import Headers
from fastapi import FastAPI
import asyncio

from app.utils.password import get_authorization


# app = FastAPI()

# 目标函数（待测试）
async def get_headers(request: Request):
    # 打印所有可用的headers
    print("Available headers:", list(request.headers.keys()))
    print(f'request.headers:={request.headers}')
    print("All headers dict:", dict(request.headers))
    return dict(request.headers)
    auth_header = request.headers.get('Authorization')  # 注意使用小写
    print(f'auth_header={auth_header}')
    # all_headers = dict(request.headers)
    # if auth_header:
    #     all_headers['Authorization'] = auth_header
    # return all_headers

# 模拟 Request 对象
def mock_request(headers: Headers)-> Request:
    scope = {
        "type": "http",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],  # 字节编码
    }
    receive = lambda: None  # 空接收器（测试中无需真实数据）
    request = Request(scope, receive)
    return request

# 测试
async def main():
    auth = get_authorization("https://10.4.134.68", "", "").strip()
    print(f'auth={auth}')
    headers = Headers({"Authorization": auth})
    print(f'headers={headers}')
    # headers = {"X-Custom-Header": "test", "User-Agent": "mock"}
    request = mock_request(headers)
    result = await get_headers(request)

    print(f'result={result}')
# 输出: {'x-custom-header': 'test', 'user-agent': 'mock'}

if __name__ == "__main__":
    asyncio.run(main())

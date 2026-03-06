# -*- coding: utf-8 -*-
# @Time : 2023/12/19 14:16
# @Author : 窦梓瑜
# @Email : ziyu.dou@aishu.cn
# @File : __init__.py.py
# @Project : copilot
from typing import Callable

from fastapi import FastAPI, Request, Response

from app.handlers import router_init
from app.logs.logger import logger


async def start_event():
    # write_prompts_to_anydata()
    logger.info(msg='系统启动')


async def shutdown_event():
    logger.info(msg='系统关闭')


def write_prompts_to_anydata():
    from app.cores.prompt.manage.ad_service import PromptServices
    for num in range(10):
        try:
            import time
            time.sleep(3)
            # print(num)
            services = PromptServices()
            _, res = services.get_all_prompt_item()
            if res:
                services.save_prompt_to_anydata()
            else:
                services.update_prompt_id()
            break
        except Exception as e:
            print(e)
            if num ==  9:
                raise Exception("prompt 写入 AnyDATA 失败，请重启 POD")
            continue


async def user_define_middleware(request: Request,
                                 call_next: Callable) -> Response:
    response = await call_next(request)
    return response


def create_app():
    app = FastAPI(title="AF Sailor Agent",
                  description="AF Sailor Agent认知助手服务",
                  version="1.0.0",
                  on_startup=[start_event],
                  on_shutdown=[shutdown_event]
                  )

    router_init(app)
    app.middleware('http')(user_define_middleware)
    
    # Add route for Chrome DevTools JSON file
    @app.get("/.well-known/appspecific/com.chrome.devtools.json")
    async def chrome_devtools_json():
        return {}

    return app

# -*- coding: utf-8 -*-
# @Time : 2023/12/19 14:16
# @Author : 窦梓瑜
# @Email : ziyu.dou@xxx.cn
# @File : __init_.py
# @Project : copilot

# from typing import Callable
# from fastapi import FastAPI, Request, Response
from fastapi import FastAPI
from app.handlers import router_init
from app.logs.logger import logger


async def start_event_handler():
    # write_prompts_to_anydata()
    table_completion_clock()
    # Uvicorn 会记录日志’Application startup complete.‘， 无需重复记录
    # logger.info(msg='系统启动')


async def shutdown_event_handler():
    table_completion_clock(flag='shutdown')
    # Uvicorn 会记录日志’Application shutdown complete.‘， 无需重复记录
    # logger.info(msg='系统关闭')


# async def user_define_middleware(request: Request,
#                                  call_next: Callable) -> Response:
#     response = await call_next(request)
#     return response


def table_completion_clock(flag='start'):
    from config import settings
    from apscheduler.schedulers.background import BackgroundScheduler

    from app.cores.understand.commons.on_clock_task import on_clock_task, already_running, create_lock, delete_lock

    # 关闭任务 or 启动任务
    if flag == 'shutdown':
        if already_running():
            logger.info(f'补全任务定时清理任务停止。')
            # 删除锁文件
            delete_lock()
    else:
        # 如果没有启动定时任务则启动，否则不重复启动
        if not already_running():
            # 新建锁文件
            create_lock()

            scheduler = BackgroundScheduler()

            delta_time = settings.TABLE_COMPLETION_DELTA_CHECK_TIME
            try:
                delta_time = int(delta_time)
            except Exception:
                delta_time = 60 * 60
            try:
                scheduler.add_job(on_clock_task, 'interval', seconds=delta_time)
                scheduler.start()
                logger.info(f'补全任务定时清理任务启动，间隔时间{delta_time}秒....')
            except Exception as e:
                logger.info(f'补全任务定时清理任务报错：{e}')


# def write_prompts_to_anydata():
#     from app.cores.prompt.manage.ad_service import PromptServices
#     for num in range(10):
#         try:
#             import time
#             time.sleep(3)
#             logger.info(f'write_prompts_to_anydata(), num: {num}')
#             services = PromptServices()
#             _, res = services.get_all_prompt_item()
#             if res:
#                 services.save_prompt_to_anydata()
#             else:
#                 services.update_prompt()
#             break
#         except Exception as e:
#             logger.info(f'write_prompts_to_anydata(), 写入异常，异常信息：{e}')
#             if num ==  9:
#                 raise Exception("prompt 写入 AnyDATA 失败，请重启 POD")
#             continue

def create_app():
    app = FastAPI(title="AF Sailor",
                  description="AF Sailor认知助手服务",
                  version="1.0.0",
                  on_startup=[start_event_handler],
                  on_shutdown=[shutdown_event_handler]
                  )

    router_init(app)
    # app.middleware('http')(user_define_middleware)

    return app

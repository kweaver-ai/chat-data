"""
@File: util.py
@Date:2024-03-14
@Author : Danny.gao
@Desc: 工具类
"""

import time
import numpy as np

from app.logs.logger import logger

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f'执行函数 {func.__name__} 耗时： {end_time - start_time} 秒')
        return result
    return wrapper


if __name__ == '__main__':
    pass

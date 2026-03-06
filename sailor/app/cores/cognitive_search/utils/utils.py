# -*- coding: utf-8 -*-
# @Time    : 2025/7/6 11:33
# @Author  : Glen.lv
# @File    : utils
# @Project : af-sailor
from app.logs.logger import logger


def safe_str_to_int(s: str) -> int | None:
    try:
        return int(s)
    except (ValueError, TypeError) as e:
        # 这里可以添加日志记录或者其他错误处理逻辑
        logger.error(f'str 字符型转换成 int 整型发生错误! 错误信息 = {e}')
        return None  # 或者返回一个默认值，比如 0

def safe_str_to_float(s: str) -> float | None:
    try:
        return float(s)
    except (ValueError, TypeError) as e:
        # 这里可以添加日志记录或者其他错误处理逻辑
        logger.error(f'str 字符型转换成 float 浮点型发生错误! 错误信息 = {e}')
        return None  # 或者返回一个默认值，比如 0
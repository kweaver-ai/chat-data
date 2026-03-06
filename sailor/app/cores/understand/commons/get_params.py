"""
@File: get_params.py
@Date:2024-03-13
@Author : Danny.gao
@Desc:
"""

import json
import aiohttp
import requests
from pydantic import BaseModel, Field

from app.logs.logger import logger
from config import settings

af_svc_url = settings.TABLE_COMPLETION_AF_SVC_URL
# af_svc_url = 'http://10.4.109.234:8133/api/internal/configuration-center/v1/byType-list/9'


class ResponseParams(BaseModel):
    task_ex_time: int = Field(..., description='任务超时时间，单位秒')
    llm_input_len: int = Field(..., description='大模型输入的最长字符长度限制，明显小于大模型本身的token限制')
    llm_out_len: int = Field(..., description='大模型输出的最长字符长度限制，明显小于大模型本身的token限制')


RESPONSE_PROPS = {
    'task_ex_time': 86400,
    'llm_input_len': 4000,
    'llm_out_len': 4000
}


def af_params_connector():
    try:
        res = requests.get(af_svc_url, timeout=30).json()
        logger.info(f'AF 获取数据元补全参数字典（原始数据）：{res}')
        PROPS = RESPONSE_PROPS.copy()
        for item in res:
            key = item['key']
            value = item['value']
            value = float(value)
            if str(key).startswith('sailor_'):
                key = str(key).replace('sailor_', '', 1)
            PROPS[key] = value if key in PROPS else PROPS[key]
        logger.info(f'AF 获取数据元补全参数字典（替换sailor_前缀后）：{PROPS}')
        return ResponseParams(**PROPS)
    except Exception as e:
        logger.info(f'AF 获取数据元补全参数字典失败: url=\'{af_svc_url}\' {e}')
    return ResponseParams(**RESPONSE_PROPS)


if __name__ == '__main__':
    import asyncio
    res = af_params_connector()
    print(res)


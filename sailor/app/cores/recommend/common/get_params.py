"""
@File: get_params.py
@Date:2024-03-13
@Author : Danny.gao
@Desc:
"""

import json
import aiohttp

from app.logs.logger import logger
from config import settings
from app.cores.recommend._models import DictParams

af_svc_url = settings.AF_SVC_URL
# af_svc_url = 'http://10.4.35.55:8133/api/internal/configuration-center/v1/byType-list/6'


async def af_params_connector():
    def convert_params_to_dict(params):
        result = {}
        for param in params:
            if 'key' not in param or 'value' not in param:
                continue
            keys = param['key'].split('.')
            value = param['value']
            current_dict = result
            for key in keys[:-1]:
                if key not in current_dict:
                    current_dict[key] = {}
                current_dict = current_dict[key]
            current_dict[keys[-1]] = value
        return result

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(af_svc_url, verify_ssl=False, timeout=30) as resp:
                res = await resp.text()
        res = json.loads(res)
        # res = [
        #     {
        #         'key': 'rec_label.query.vector_min_score',
        #         'value': '0.5'
        #     },
        #     {
        #         'key': 'rec_label.query.query_min_score',
        #         'value': '0.5'
        #     }
        # ]
        PROPS = convert_params_to_dict(res)
        return DictParams(**PROPS).dict()
    except Exception as e:
        logger.info(f'\nAF 获取参数字典失败: url=\'{af_svc_url}\'，错误信息：{e}')
    return DictParams().dict()


if __name__ == '__main__':
    import asyncio
    res = asyncio.run(af_params_connector())
    print(res)


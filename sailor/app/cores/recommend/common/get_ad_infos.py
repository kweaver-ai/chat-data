"""
@File: get_ad_infos.py
@Date: 2024-12-18
@Author: Danny.gao
@Desc: 
"""


import json
import aiohttp
from config import settings
from app.logs.logger import logger


ad_basic_infos_url = settings.AD_BASIC_INFOS_URL


async def ad_basic_infos_connector():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ad_basic_infos_url, verify_ssl=False, timeout=30) as resp:
                res = await resp.text()
        res = json.loads(res)
        kg_id = res.get('smart_recommendation_graph_id', '')
        appid = res.get('app_id', '')
        return kg_id, appid
    except Exception:
        logger.info(f'AF 获取参数字典失败: url=\'{ad_basic_infos_url}\'')
    return '', ''


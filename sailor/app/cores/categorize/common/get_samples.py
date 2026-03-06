"""
@File: get_samples.py
@Date:2024-08-07
@Author : Danny.gao
@Desc:
"""

import random

from app.cores.understand.commons._api import AnyFabricServices
from app.logs.logger import logger

af_func = AnyFabricServices()


async def get_samples(technical_name, view_source_catalog_name, af_auth, num=100):
    samples = []
    try:
        splits = view_source_catalog_name.split('.') if view_source_catalog_name else []
        if not splits:
            return samples
        if len(splits) == 1:
            splits.append('default')
        catalog = {
            'source': splits[0],
            'schema': splits[1],
            'technical_name': technical_name
        }
        headers = {
            'Authorization': af_auth
        }
        sample_datas = await af_func.get_view_sample_by_source(catalog=catalog, headers=headers)
        datas = sample_datas.get('data', [])
        # 随机选择 num 条数据
        datas = random.sample(datas, num) if len(datas) > num else datas
        columns = sample_datas.get('columns', [])
        for data in datas:
            sample = {}
            for value, col in zip(data, columns):
                print(col['name'], value)
                name = col.get('name', '')
                if name and value:
                    sample[name] = value
            samples.append(sample)
    except Exception as e:
        logger.info(f'{e}')
        logger.info('获取样例数据失败！！！')
    return samples
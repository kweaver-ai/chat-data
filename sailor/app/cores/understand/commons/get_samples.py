"""
@File: get_samples.py
@Date:2024-08-07
@Author : Danny.gao
@Desc:
"""

from app.cores.understand.commons._api import AnyFabricServices
from app.logs.logger import logger

af_func = AnyFabricServices()


async def get_one_sample(technical_name, view_source_catalog_name, af_auth):
    sample = {}
    try:
        splits = view_source_catalog_name.split('.') if view_source_catalog_name else []
        if not splits:
            return sample
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
        samples = await af_func.get_view_sample_by_source(catalog=catalog, headers=headers)
        datas = samples.get('data', [])
        columns = samples.get('columns', [])
        if datas:
            data = datas[0]
            for value, col in zip(data, columns):
                print(col['name'], value)
                name = col.get('name', '')
                if name and value:
                    sample[name] = value
    except Exception as e:
        logger.info(f'{e}')
        logger.info('获取样例数据失败！！！')
    return sample
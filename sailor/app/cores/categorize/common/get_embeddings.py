"""
@File: get_embeddings.py
@Date:2024-03-11
@Author : Danny.gao
@Desc:
"""

import json
import aiohttp
from aiohttp.client_exceptions import InvalidURL, ClientConnectorError
from asyncio.exceptions import TimeoutError

from config import settings
from app.logs.logger import logger
from app.utils.exception import M3ERequestException

m3e_model_url = f'{settings.ML_EMBEDDING_URL}/{settings.ML_EMBEDDING_URL_suffix}'


async def m3e_embeddings(texts):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(m3e_model_url, json={"texts": texts}, verify_ssl=False, timeout=30) as resp:
                res = await resp.text()
        embeddings = json.loads(res)
        assert len(embeddings) == len(texts)
        return embeddings
    except TimeoutError:
        logger.info(f'M3E embedding服务异常：url=\'{m3e_model_url}\', Timeout')
    except (InvalidURL, ClientConnectorError):
        logger.info(f'M3E embedding服务异常：url=\'{m3e_model_url}\', Invalid URL')
    except AssertionError:
        logger.info(f'M3E embedding服务异常：url=\'{m3e_model_url}\', URL not found')
    except Exception:
        logger.info(f'M3E embedding服务异常：url=\'{m3e_model_url}\' ，Internal Server Error')
        # return M3ERequestException(reason=f'')
    return False


if __name__ == '__main__':
    import asyncio
    result = asyncio.run(m3e_embeddings(texts=['你好']))
    print(result)
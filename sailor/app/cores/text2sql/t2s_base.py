import json
import re
from typing import Optional, Union

import aiohttp
import requests
from pydantic import BaseModel

from app.cores.text2sql.t2s_config import T2SConfig
from app.cores.text2sql.t2s_error import Text2SQLError
from app.logs.logger import logger


class HTTPMethod:
    """HTTP Method
    """
    POST = "POST"
    GET = "GET"


class API(BaseModel):
    url: str
    params: Optional[dict] = {}
    payload: Union[dict, list] = None
    data: str | dict = None
    headers: Optional[dict] = {}
    method: str = HTTPMethod.GET
    stream: bool = False
    is_sql: bool = False

    def call(
            self,
            timeout: int = T2SConfig.timeout.value,
            verify: bool = False,
            raw_content: bool = False,
    ):
        # logger.info(f"headers = {self.headers}")
        if self.method == HTTPMethod.GET:
            logger.info(f"call GET url={self.url}")
            resp = requests.get(
                self.url,
                params=self.params,
                headers=self.headers,
                timeout=timeout,
                verify=verify,
            )
            logger.info("success")
        elif self.method == HTTPMethod.POST:
            logger.info(f"call POST url={self.url}")
            resp = requests.post(
                self.url,
                params=self.params,
                json=self.payload,
                data=self.data,
                headers=self.headers,
                timeout=timeout,
                verify=verify,
                stream=self.stream

            )
        else:
            raise Text2SQLError(
                reason="method not support",
                url=self.url
            )
        if int(resp.status_code) == 200:
            if raw_content:
                return resp.content

            return resp.json()

        try:
            detail = resp.json()
        except json.decoder.JSONDecodeError:
            detail = {}
        raise Text2SQLError(
            url=self.url,
            status=resp.status_code,
            reason=resp.reason,
            detail=detail
        )

    async def call_async(
            self,
            timeout: int = T2SConfig.timeout.value,
            raw_content: bool = False,
            verify: bool = False,
    ):
        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=verify),
                headers=self.headers
        ) as session:
            # logger.info(f"headers = {self.headers}")
            timeout = aiohttp.ClientTimeout(total=timeout)
            if self.method == HTTPMethod.GET:
                # logger.info(f"call GET url={self.url}")
                async with session.get(
                        self.url,
                        params=self.params,
                        timeout=timeout,
                ) as resp:
                    logger.info(f"call GET url={self.url}")
                    if int(resp.status) == 200:
                        if raw_content:
                            return await resp.read()
                        res = await resp.json(content_type=None)
                        return res
                    logger.warning(f'{self.url}调用异常：\n{await resp.text()}')
                    try:
                        detail = await resp.json(content_type=None)
                    except requests.exceptions.JSONDecodeError:
                        detail = {}
                    raise Text2SQLError(
                        url=self.url,
                        status=resp.status,
                        reason=resp.reason,
                        detail=detail
                    )
            elif self.method == HTTPMethod.POST:
                async with session.post(
                        self.url,
                        params=self.params,
                        data=self.data,
                        json=self.payload,
                        timeout=timeout,

                ) as resp:
                    logger.info(f"call POST url={self.url}")
                    if int(resp.status / 100) == 2:
                        if self.stream:
                            prefix = "data: "
                            res = ""
                            async for msg in resp.content.iter_any():
                                msg_decode = msg.decode('utf-8')
                                if prefix in msg_decode:
                                    res += msg_decode.replace(prefix, "").replace("\r\n\r\n", "")
                            res = res.replace("--end--", "")
                            return res
                        if raw_content:
                            return await resp.read()
                        return await resp.json(content_type=None)
                    try:
                        detail = await resp.text()
                    except requests.exceptions.JSONDecodeError:
                        detail = {}
                    except json.decoder.JSONDecodeError as e:
                        detail = str(e)

                    raise Text2SQLError(
                        url=self.url,
                        status=resp.status,
                        reason=resp.reason,
                        detail=detail
                    )
            else:
                raise Text2SQLError(
                    reason="method not support",
                    url=self.url
                )

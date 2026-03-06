import json
from typing import Optional

import aiohttp
import requests
import urllib3
from pydantic import BaseModel

from app.cores.prompt.manage.api_error import BaseError
from config import Config

urllib3.disable_warnings()


class HTTPMethod:
    """HTTP Method
    """
    POST = "POST"
    GET = "GET"


class API(BaseModel):
    url: str
    params: Optional[dict] = {}
    payload: list | dict = None
    data: str | dict = None
    headers: Optional[dict] = {}
    method: str = HTTPMethod.GET

    def call(
        self,
        timeout: int = Config.TIMEOUT,
        verify: bool = False,
        raw_content: bool = False,
    ):
        if self.method == HTTPMethod.GET:
            resp = requests.get(
                self.url,
                params=self.params,
                headers=self.headers,
                timeout=timeout,
                verify=verify
            )
        elif self.method == HTTPMethod.POST:
            resp = requests.post(
                self.url,
                params=self.params,
                json=self.payload,
                data=self.data,
                headers=self.headers,
                timeout=timeout,
                verify=verify
            )
        else:
            raise BaseError(
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
        raise BaseError(
            url=self.url,
            status=resp.status_code,
            reason=resp.reason,
            detail=detail
        )

    async def call_async(
        self,
        timeout: int = Config.TIMEOUT,
        raw_content: bool = False,
        verify: bool = False,
        use_stream: bool = False,

    ):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=verify),
            headers=self.headers
        ) as session:
            timeout = aiohttp.ClientTimeout(total=timeout)
            if self.method == HTTPMethod.GET:
                async with session.get(
                    self.url,
                    params=self.params,
                    timeout=timeout
                ) as resp:
                    if int(resp.status) == 200:
                        if use_stream:
                            return resp.content

                        if raw_content:
                            return await resp.read()
                        res = await resp.json(content_type=None)
                        return res
                    try:
                        detail = await resp.json(content_type=None)
                    except requests.exceptions.JSONDecodeError:
                        detail = {}

                    raise BaseError(
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
                    timeout=timeout
                ) as resp:
                    if int(resp.status / 100) == 2:
                        if raw_content:
                            return await resp.read()
                        if use_stream:
                            return resp
                        res = await resp.json(content_type=None)
                        return res

                    try:
                        detail = await resp.json(content_type=None)
                    except requests.exceptions.JSONDecodeError:
                        detail = {}
                    except json.decoder.JSONDecodeError as e:
                        detail = e

                    raise BaseError(
                        url=self.url,
                        status=resp.status,
                        reason=resp.reason,
                        detail=detail
                    )
            else:
                raise BaseError(
                    reason="method not support",
                    url=self.url
                )

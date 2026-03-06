import json
# import re
from typing import Optional, Union
from enum import Enum, unique

import aiohttp
import requests
from pydantic import BaseModel

# from app.cores.text2sql.t2s_config import T2SConfig
from app.cores.cognitive_search.utils.search_error import SearchError

@unique
class TimeConfig(Enum):
    TIMES: int = 3
    timeout: int = 300000


class HTTPMethod:
    """HTTP Method
    """
    POST = "POST"
    GET = "GET"


class API(BaseModel):
    """
    Represents an API request with various configurations and methods to send the request.

    Summary:
    This class is used to configure and send HTTP requests. It supports both synchronous and asynchronous calls using
    the `requests` and `aiohttp` libraries, respectively. The class allows setting URL, parameters, payload, headers,
    and other request options. It also provides methods to handle the response, including parsing JSON content or
    returning raw content.

    Attributes:
    - url (str): The URL to which the request will be sent.
    - params (Optional[dict]): Optional dictionary of query parameters for the request.
    - payload (Union[dict, list]): The data to be sent in the body of a POST request.
    - data (str | dict): Additional data to be sent in the body of the request.
    - headers (Optional[dict]): Optional dictionary of headers to be included in the request.
    - method (str): The HTTP method to use for the request (default is 'GET').
    - stream (bool): Whether to stream the response (default is False).
    - is_sql (bool): A flag indicating if the request is related to SQL (default is False).

    Methods:
    - call: Sends a synchronous HTTP request.
    - call_async: Sends an asynchronous HTTP request.
    """
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
            timeout: int = TimeConfig.timeout.value,
            verify: bool = False,
            raw_content: bool = False,
    ):
        """
        Sends an HTTP request to the specified URL and processes the response.

        Summary:
        This method sends an HTTP GET or POST request based on the `method` attribute. It handles the response,
        returning the JSON content if the status code is 200. If the status code is not 200, it raises a
        `SearchError` with details from the response.

        Parameters:
        - timeout: int, optional
          The number of seconds to wait for the server to send data before giving up.
        - verify: bool, optional
          Whether to verify the SSL certificate.
        - raw_content: bool, optional
          Whether to return the raw content of the response instead of parsing it as JSON.

        Returns:
        - dict or bytes
          Returns the JSON content of the response if `raw_content` is False. Returns the raw content as bytes if
          `raw_content` is True.

        Raises:
        - SearchError
          Raised if the HTTP method is not supported or if the response status code is not 200.
        """
        if self.method == HTTPMethod.GET:
            resp = requests.get(
                self.url,
                params=self.params,
                headers=self.headers,
                timeout=timeout,
                verify=verify,
            )
        elif self.method == HTTPMethod.POST:
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
            raise SearchError(
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
        raise SearchError(
            url=self.url,
            status=resp.status_code,
            reason=resp.reason,
            detail=detail
        )

    async def call_async(
            self,
            timeout: int = TimeConfig.timeout.value,
            raw_content: bool = False,
            verify: bool = False,
    ):
        """
        Sends an asynchronous HTTP request to the specified URL using the aiohttp library.

        Summary:
        This function performs an asynchronous HTTP GET or POST request. It supports setting a custom timeout,
        verifying SSL certificates, and handling both raw and JSON content. The method can also handle streaming
        responses for POST requests. If the response status is not 200 for GET or 2xx for POST, it raises a
        `SearchError` with detailed information about the error.

        Args:
            timeout (int): The total timeout for the request in seconds. Defaults to the value from T2SConfig.timeout.
            raw_content (bool): If True, returns the raw content of the response. Defaults to False.
            verify (bool): If True, verifies the SSL certificate. Defaults to False.

        Raises:
            SearchError: Raised if the response status is not 200 for GET or 2xx for POST, or if the method is not
            supported.

        Returns:
            Any: The response content, which can be raw bytes, a string, or a JSON object, depending on the request
            and the `raw_content` parameter.
        """
        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=verify),
                headers=self.headers
        ) as session:
            timeout = aiohttp.ClientTimeout(total=timeout)
            if self.method == HTTPMethod.GET:
                async with session.get(
                        self.url,
                        params=self.params,
                        timeout=timeout,
                ) as resp:
                    if int(resp.status) == 200:
                        if raw_content:
                            return await resp.read()
                        res = await resp.json(content_type=None)
                        return res
                    print('}}}}}}}}}}}}}}}',await resp.text())
                    try:
                        detail = await resp.json(content_type=None)
                    except requests.exceptions.JSONDecodeError:
                        detail = {}
                    raise SearchError(
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
                    # 不需要捕获（requests异常在异步上下文中不会出现）
                    # except requests.exceptions.JSONDecodeError:
                    #     detail = {}
                    except json.decoder.JSONDecodeError as e:
                        detail = e

                    raise SearchError(
                        url=self.url,
                        status=resp.status,
                        reason=resp.reason,
                        detail=detail
                    )
            else:
                raise SearchError(
                    reason="method not support",
                    url=self.url
                )

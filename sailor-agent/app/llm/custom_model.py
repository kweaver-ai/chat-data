# -*- coding: utf-8 -*-
# @Author:  Xavier.chen@aishu.cn
# @Date: 2024-11-06

from typing import Any, cast
from langchain_core.pydantic_v1 import Field
from httpx import Client, AsyncClient
import openai

from langchain_community.chat_models import ChatOpenAI

from openai._base_client import SyncHttpxClientWrapper, AsyncHttpxClientWrapper
from openai._constants import DEFAULT_CONNECTION_LIMITS, DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES
from openai._types import Timeout


class _ChatCompletionsProxy:
    """过滤 LangChain 透传到 OpenAI v1 的不兼容字段（如 `id`）。"""

    def __init__(self, inner: Any):
        self._inner = inner

    def create(self, **kwargs: Any):
        kwargs.pop("id", None)
        return self._inner.create(**kwargs)


class _AsyncChatCompletionsProxy:
    def __init__(self, inner: Any):
        self._inner = inner

    async def create(self, **kwargs: Any):
        kwargs.pop("id", None)
        return await self._inner.create(**kwargs)


class CustomChatOpenAI(ChatOpenAI):
    """
    Custom ChatOpenAI class to support more parameters

    Parameters:
    """

    """verify_ssl: Default is True"""
    verify_ssl: bool = True

    # client: Any = Field(default=None)  #: :meta private:
    # async_client: Any = Field(default=None)  #: :meta private:

    def _get_client_params(self, **kwargs):
        # Client params of openai.OpenAI
        # api_key: str | None = None,
        # organization: str | None = None,
        # project: str | None = None,
        # base_url: str | httpx.URL | None = None,
        # timeout: Union[float, Timeout, None, NotGiven] = NOT_GIVEN,
        # max_retries: int = DEFAULT_MAX_RETRIES,
        # default_headers: Mapping[str, str] | None = None,
        # default_query: Mapping[str, object] | None = None,

        client_params = {
            "api_key": kwargs.get("openai_api_key"),
            "organization": kwargs.get("openai_organization"),
            "project": kwargs.get("openai_project"),
            "base_url": kwargs.get("openai_api_base"),
            "max_retries": kwargs.get("max_retries", DEFAULT_MAX_RETRIES),
            "timeout": cast(Timeout, kwargs.get("request_timeout", DEFAULT_TIMEOUT)),
            "default_headers": kwargs.get("default_headers"),
            "default_query": kwargs.get("default_query"),
        }

        http_params = {
            "proxies": kwargs.get("proxies"),
            "transport": kwargs.get("transport"),
            "limits": kwargs.get("limits", DEFAULT_CONNECTION_LIMITS),
        }

        return client_params, http_params

    def __init__(self, *args, **kwargs):
        client_params, http_params = self._get_client_params(**kwargs)

        # http_client or SyncHttpxClientWrapper(
        #     base_url=base_url,
        #     # cast to a valid type because mypy doesn't understand our type narrowing
        #     timeout=cast(Timeout, timeout),
        #     proxies=proxies,
        #     transport=transport,
        #     limits=limits,
        #     follow_redirects=True,
        # )
        http_client = SyncHttpxClientWrapper(
            verify=kwargs.get("verify_ssl", True),
            **http_params
        )

        client = _ChatCompletionsProxy(
            openai.OpenAI(**client_params, http_client=http_client).chat.completions
        )

        async_http_client = AsyncHttpxClientWrapper(
            verify=kwargs.get("verify_ssl", True),
            **http_params
        )

        async_client = _AsyncChatCompletionsProxy(
            openai.AsyncOpenAI(**client_params, http_client=async_http_client).chat.completions
        )

        super().__init__(client=client, async_client=async_client, *args, **kwargs)


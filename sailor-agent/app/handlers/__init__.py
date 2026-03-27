# -*- coding: utf-8 -*-
from app.handlers.agent_management_handler import AgentManagementRouter
from app.handlers.config_handler import ConfigRouter
from app.handlers.memory_handler import MemoryAPIRouter
from app.handlers.search_handler import search_api
from app.handlers.data_understand_handler import DataUnderstandAPIRouter
from app.routers import API_V1_STR
from app.routers.agent_temp_router import ToolRouter

from app.tools.tool_api_router import BaseToolAPIRouter
from app.tools import _TOOLS_MAPPING

def router_init(app):
    app.include_router(
        search_api,
        prefix=API_V1_STR,
        tags=['search'],
        include_in_schema=True,
        responses={404: {"description": "Not found"}},
    )

    # 工具路由
    tool_router = BaseToolAPIRouter(prefix=ToolRouter, tools_mapping=_TOOLS_MAPPING)
    app.include_router(
        tool_router,
        prefix=API_V1_STR,
        tags=['tools'],
        include_in_schema=True,
        responses={404: {"description": "Not found"}},
    )

    # 数据理解工具路由
    app.include_router(
        DataUnderstandAPIRouter,
        prefix=API_V1_STR,
        tags=['data_understand'],
        include_in_schema=True,
        responses={404: {"description": "Not found"}},
    )

    # 记忆工具路由
    app.include_router(
        MemoryAPIRouter,
        prefix=API_V1_STR,
        tags=['memory'],
        include_in_schema=True,
        responses={404: {"description": "Not found"}},
    )

    # 智能体管理路由
    app.include_router(
        AgentManagementRouter,
        prefix=f"{API_V1_STR}/assistant",
        tags=['agent_management'],
        include_in_schema=True,
        responses={404: {"description": "Not found"}},
    )

    # 配置管理路由
    app.include_router(
        ConfigRouter,
        prefix=f"{API_V1_STR}/system",
        tags=['config_management'],
        include_in_schema=True,
        responses={404: {"description": "Not found"}},
    )


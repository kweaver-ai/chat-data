# -*- coding: utf-8 -*-
# from langserve import add_routes

# from app.cores.agent import af_agent_executor_with_chat_history
# from app.routers.agent_router import common_agent_router
# @Time : 2023/12/20 16:35
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : __init_.py
# @Project : copilot
from app.handlers.basic_handler import basic_router
from app.handlers.categorize_handler import data_categorize_router
# from app.handlers.chat_handler import chat_router
# from app.handlers.chat_handler_v2 import chat_router_v2
from app.handlers.cognitive_assistant_handler import qa_router
from app.handlers.cognitive_search_handler import cognitive_search_router
from app.handlers.data_understand_handler import data_understand_router
from app.handlers.prompt_handler import prompt_router
from app.handlers.recommend_handler import recommend_router
from app.handlers.test_llm_handler import test_llm_router
from app.handlers.text2sql_handler import text2sql_router
from app.handlers.categorize_handler import data_categorize_router
from app.handlers.generate_fake_samples import generate_fake_samples_router
from app.handlers.data_comprehension_handler import data_comprehension_router
from app.handlers.retriever_handler import retriever_router

from app.routers import API_V1_STR


def router_init(app):
    app.include_router(
        basic_router,
        prefix=API_V1_STR,
        tags=["basic_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )

    # app.include_router(
    #     chat_router,
    #     # prefix=API_V1_STR,
    #     tags=["chat_api"],
    #     # dependencies=[Depends(get_token_header)],
    #     include_in_schema=False,
    #     responses={404: {"description": "Not found"}},
    # )
    #
    # app.include_router(
    #     chat_router_v2,
    #     # prefix=API_V1_STR,
    #     tags=["chat_api"],
    #     # dependencies=[Depends(get_token_header)],
    #     include_in_schema=False,
    #     responses={404: {"description": "Not found"}},
    # )

    app.include_router(
        prompt_router,
        prefix=API_V1_STR,
        tags=["prompt_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )

    app.include_router(
        text2sql_router,
        prefix=API_V1_STR,
        tags=["text2sql_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )

    app.include_router(
        router=cognitive_search_router,
        prefix=API_V1_STR,
        tags=["asset_search_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )

    app.include_router(
        recommend_router,
        prefix=API_V1_STR,
        tags=['recommend_api'],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},  # 添加错误码信息
    )

    app.include_router(
        qa_router,
        prefix=API_V1_STR,
        tags=['qa_api'],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},  # 添加错误码信息
    )

    app.include_router(
        test_llm_router,
        prefix=API_V1_STR,
        tags=['test_llm'],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},  # 添加错误码信息
    )

    app.include_router(
        data_understand_router,
        prefix=API_V1_STR,
        tags=["data_understand_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )

    app.include_router(
        data_categorize_router,
        prefix=API_V1_STR,
        tags=["data_categorize_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )
    app.include_router(
        router=data_comprehension_router,
        prefix=API_V1_STR,
        tags=["data_comprehension_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )
    app.include_router(
        generate_fake_samples_router,
        prefix=API_V1_STR,
        tags=["genearate_fake_samples_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )
    app.include_router(
        router=retriever_router,
        prefix=API_V1_STR,
        tags=["retriever_api"],
        # dependencies=[Depends(get_token_header)],
        include_in_schema=False,
        responses={404: {"description": "Not found"}},
    )


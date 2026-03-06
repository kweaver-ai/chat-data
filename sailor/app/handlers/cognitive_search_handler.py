# -*- coding: utf-8 -*-
# @Time    : 2024/1/21 11:58
# @Author  : Glen.lv
# @File    : cognitive_search_handler
# @Project : copilot

from typing import List, Dict, Optional
from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, ValidationError
from textwrap import dedent

from app.logs.logger import logger
from app.routers import (CatalogSearchRouter, AssetSearchRouter, ResourceSearchRouter, ResourceAnalysisRouter,
                         CatalogAnalysisRouter, FormviewAnalysisRouter, FormviewSearchCatalogRouter,
                         FormviewAnalysisCatalogRouter,
                         # TestRouter, TestAssetRouter
                         )

from app.cores.cognitive_search.re_asset_search import run_func, run_func_resource, run_func_catalog
from app.cores.cognitive_search.ai_asset_search import (run_func_formview, formview_catalog_analysis_main,
                                                        formview_resource_analysis_main)
from app.cores.cognitive_search.re_analysis_search import (resource_analysis_main, catalog_analysis_main,
                                                           resource_analysis_search_kecc)
from app.cores.cognitive_search.search_func import query_m3e
from app.cores.cognitive_search.search_model import (ANALYSIS_SEARCH_EMPTY_RESULT, AssetSearchParams,
                                                     AnalysisSearchParams)
from config import settings
from app.cores.cognitive_search.search_config.get_params import get_search_configs

cognitive_search_router = APIRouter()


# class AssetSearchParams(BaseModel):
#     query: str
#     limit: Optional[int] = 5
#     stopwords: List
#     stop_entities: Optional[List] = None
#     filter: Optional[Dict] = None
#     ad_appid: str
#     kg_id: int
#     available_option: Optional[int] = 0
#     entity2service: Optional[Dict] = None
#     required_resource: Optional[Dict] = None
#     subject_id: Optional[str] = None
#     subject_type: Optional[str] = None
#     roles: Optional[List] = None
#     af_editions: Optional[str] = None
#
#
# class AnalysisSearchParams(BaseModel):
#     query: str  # 用户query
#     limit: Optional[int] = 5 # 返回结果上限
#     stopwords: List
#     stop_entities: Optional[List] = None
#     filter: Optional[Dict] = None # 筛选项， 分析问答型搜索暂不支持筛选项， 保留字段
#     ad_appid: str
#     kg_id: int # 认知搜索图谱id
#     entity2service: Optional[Dict] = None
#     required_resource: Optional[Dict] = None
#     available_option: Optional[int] = 2
#     subject_id: Optional[str] = None  # 用户id
#     subject_type: Optional[str] = None # 用户类型
#     roles: Optional[List] = None  # 用户角色
#     if_display_graph: Optional[bool] = False # 是否显示图谱, 首页智能问数需要显示, 标品不需要


# 可能已废弃
@cognitive_search_router.post(AssetSearchRouter, include_in_schema=False, summary="数据资产认知搜索接口")
async def asset_search(query_dict: AssetSearchParams, file_path):
    search_configs = get_search_configs()
    response = await run_func(query_dict, file_path,search_configs)
    return {"res": response}


# 目录版搜索列表
@cognitive_search_router.post(CatalogSearchRouter, include_in_schema=False, summary="认知搜索接口_数据目录版")
async def catalog_search(request: Request, query_dict=Body(...)):
    # params_error = validate_params(query_dict)
    # if params_error is not None:
    #     return JSONResponse(status_code=400, content=params_error)
    try:
        # 使用 pydantic 进行参数校验
        query_dict = AssetSearchParams(**query_dict)
    except ValidationError as e:
        # 处理 pydantic 抛出的验证错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    # 调用主函数
    search_configs = get_search_configs()
    response = await run_func_catalog(request, query_dict,search_configs)
    return {"res": response}


# 资源版搜索列表
@cognitive_search_router.post(ResourceSearchRouter, include_in_schema=False, summary="认知搜索接口_数据资源版")
async def resource_search(request: Request, query_dict=Body(...)):

    # params_error = validate_params(query_dict)
    # if params_error is not None:
    #     return JSONResponse(status_code=400, content=params_error)
    try:
        # 使用 pydantic 进行参数校验
        query_dict = AssetSearchParams(**query_dict)
    except ValidationError as e:
        # 处理 pydantic 抛出的验证错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    # 调用主函数
    search_configs = get_search_configs()
    response = await run_func_resource(request, query_dict,search_configs)
    return {"res": response}


# 资源版分析型搜索
# @cognitive_search_router.post(ResourceAnalysisRouter, include_in_schema=False,
#                               summary="分析问答型认知搜索接口_数据资源版")
# async def resource_analysis(request: Request, query_dict=Body(...)):
#     # 入参校验, 没有必要用自己编写的函数进行校验,
#     # 因为已经定义了pydantic数据模型, pydantic 的校验功能已经能够满足对参数的基本验证需求
#     # params_error = validate_params(query_dict)
#     # if params_error is not None:
#     #     return JSONResponse(status_code=400, content=params_error)
#     # 入参校验通过，根据接口入参，生成主函数入参
#     # query_dict = analysisSearchParams(**query_dict)
#     # async def resource_analysis(request,query_dict: analysisSearchParams):
#     try:
#         # 使用 pydantic 进行参数校验
#         query_dict = AnalysisSearchParams(**query_dict)
#     except ValidationError as e:
#         # 处理 pydantic 抛出的验证错误
#         return JSONResponse(status_code=400, content={"error": str(e)})
#
#     # 调用主函数
#     #
#     response, res_status, explanation_status = await resource_analysis_main(request, query_dict)
#     # 返回结果
#     return {"res": response, "res_status": res_status, "explanation_status": explanation_status}


# 资源版分析型搜索(包含部门职责知识增强),新增API,需要前端适配, 或者替换原API ResourceAnalysisRouter
# @cognitive_search_router.post(ResourceAnalysisKECCRouter, include_in_schema=False,
#                               summary="分析问答型认知搜索接口_数据资源版(包含部门职责知识增强)")
# async def resource_analysis_kecc(request: Request, request_body=Body(...)):
#     try:
#         # 使用 pydantic 进行参数校验
#         analysis_search_params = AnalysisSearchParams(**request_body)
#     except ValidationError as e:
#         # 处理 pydantic 抛出的验证错误
#         return JSONResponse(status_code=400, content={"error": str(e)})
#     # 调用主函数
#     main_response, res_status, explanation_status = await resource_analysis_main_kecc(
#         request=request,
#         search_params=analysis_search_params
#     )
#     # 返回结果
#     return {"res": main_response, "res_status": res_status, "explanation_status": explanation_status}

# 资源版分析型搜索(包含部门职责知识增强), 或者替换原API ResourceAnalysisRouter
@cognitive_search_router.post(ResourceAnalysisRouter, include_in_schema=False,
                              summary="分析问答型认知搜索接口_数据资源版(包含部门职责知识增强)")
async def resource_analysis(request: Request, request_body=Body(...)):
    # logger.info(f'request = \n{request.json()}')
    logger.info(f'request_body = \n{request_body}')
    search_configs = get_search_configs()
    logger.info(dedent(
        f"""
        分析问答型认知搜索 相关配置参数: 
        服务超市 direct_qa = {search_configs.direct_qa}
        找数问答是否控制普通用户的表权限 = {search_configs.sailor_search_if_auth_in_find_data_qa}
        是否进行基于历史问答对的知识增强 = {search_configs.sailor_search_if_history_qa_enhance}
        是否进行基于'组织结构-职责-信息系统'的知识增强 = {search_configs.sailor_search_if_kecc}
        """).strip())
    try:
        # 使用 pydantic 进行参数校验
        analysis_search_params = AnalysisSearchParams(**request_body)
    except ValidationError as e:
        # 处理 pydantic 抛出的验证错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    # 调用主函数
    # 如果有部门职责知识增强, 需要对普通用户进行问答资源的权限管控
    if ((search_configs.direct_qa=='true' or search_configs.direct_qa=='false')
            # 用户是否需要数据资源的权限，在函数中控制
            # and search_configs.sailor_search_if_auth_in_find_data_qa=='1'
            and search_configs.sailor_search_if_history_qa_enhance=='0'
            and search_configs.sailor_search_if_kecc=='1' ):
        # resource_analysis_main_kecc 原来只有向量搜索的能力， cognitive_analysis_main_kecc 增加关键词搜索+关联搜索能力
        main_response, res_status, explanation_status = await resource_analysis_search_kecc(
            request=request,
            search_params=analysis_search_params
        )
    # 需要对普通用户进行问答资源的权限管控, 两种知识增强都没有
    elif ((search_configs.direct_qa=='true' or search_configs.direct_qa=='false')
            and search_configs.sailor_search_if_auth_in_find_data_qa=='1'
            and search_configs.sailor_search_if_history_qa_enhance=='0'
            and search_configs.sailor_search_if_kecc=='0' ):
        main_response, res_status, explanation_status = await resource_analysis_main(
            request=request,
            search_params=analysis_search_params
        )
    else:
        logger.error(f"""********** 暂不支持的场景: \n服务超市 direct_qa = {search_configs.direct_qa}
        \n找数问答是否控制普通用户的表权限 = {search_configs.sailor_search_if_auth_in_find_data_qa}
        \n是否进行基于历史问答对的知识增强 = {search_configs.sailor_search_if_history_qa_enhance}
        \n是否进行基于'组织结构-职责-信息系统'的知识增强 = {search_configs.sailor_search_if_kecc}""")
        # return {},"000","000"
        return ANALYSIS_SEARCH_EMPTY_RESULT
        # 返回结果
    # logger.info(f"""********** 分析问答型搜索算法原始结果\n{main_response}""")
    logger.info(f"""********** 分析问答型搜索算法 结果的有效性 标签，分别为指标、逻辑视图、接口服务 0：无效，1：有效\n{res_status}""")
    logger.info(f"""********** 分析问答型搜索算法 解释话术的有效性 标签，分别为指标、逻辑视图、接口服务 0：无效，1：有效\n{explanation_status}""")
    return {"res": main_response, "res_status": res_status, "explanation_status": explanation_status}

# 目录版分析型搜索
@cognitive_search_router.post(CatalogAnalysisRouter, include_in_schema=False,
                              summary="分析问答型认知搜索接口_数据目录版")
async def catalog_analysis(request: Request, query_dict=Body(...)):
    # params_error = validate_params(query_dict)
    # if params_error is not None:
    #     return JSONResponse(status_code=400, content=params_error)
    try:
        # 使用 pydantic 进行参数校验
        query_dict = AnalysisSearchParams(**query_dict)
    except ValidationError as e:
        # 处理 pydantic 抛出的验证错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    # 调用主函数
    response, res_status, explanation_status = await catalog_analysis_main(request, query_dict)
    return {"res": response, "res_status": res_status, "explanation_status": explanation_status}


# 场景分析,资源版分析问答型部分,
# 列表 复用认知搜索列表
@cognitive_search_router.post(FormviewAnalysisRouter, include_in_schema=False,
                              summary="分析问答型认知搜索接口_场景分析_数据资源版")
async def formview_analysis(request: Request, query_dict=Body(...)):
    # params_error = validate_params(query_dict)
    # if params_error is not None:
    #     return JSONResponse(status_code=400, content=params_error)
    try:
        # 使用 pydantic 进行参数校验
        query_dict = AnalysisSearchParams(**query_dict)
    except ValidationError as e:
        # 处理 pydantic 抛出的验证错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    # 调用主函数
    # query_dict = AnalysisSearchParams(**query_dict)
    response, res_status, explanation_status = await formview_resource_analysis_main(request, query_dict)
    return {"res": response, "res_status": res_status, "explanation_status": explanation_status}


# 场景分析,目录版，分析问答型部分
@cognitive_search_router.post(FormviewAnalysisCatalogRouter, include_in_schema=False,
                              summary="分析问答型认知搜索接口_场景分析_数据目录版")
async def formview_analysis_catalog(request: Request, query_dict=Body(...)):
    # params_error = validate_params(query_dict)
    # if params_error is not None:
    #     return JSONResponse(status_code=400, content=params_error)
    try:
        # 使用 pydantic 进行参数校验
        query_dict = AnalysisSearchParams(**query_dict)
    except ValidationError as e:
        # 处理 pydantic 抛出的验证错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    # 调用主函数
    # query_dict = AnalysisSearchParams(**query_dict)
    response, res_status, explanation_status = await formview_catalog_analysis_main(request, query_dict)
    return {"res": response, "res_status": res_status, "explanation_status": explanation_status}


# 场景分析，目录版，列表部分
@cognitive_search_router.post(FormviewSearchCatalogRouter, include_in_schema=False,
                              summary="认知搜索接口_场景分析_数据目录版")
async def formview_Search_catalog(request: Request, query_dict=Body(...)):
    # params_error = validate_params(query_dict)
    # if params_error is not None:
    #     return JSONResponse(status_code=400, content=params_error)
    try:
        # 使用 pydantic 进行参数校验
        query_dict = AnalysisSearchParams(**query_dict)
    except ValidationError as e:
        # 处理 pydantic 抛出的验证错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    # 调用主函数
    # query_dict = AnalysisSearchParams(**query_dict)
    response = await run_func_formview(request, query_dict)
    return {"res": response}


# # 测试用
# @cognitive_search_router.post(TestRouter, include_in_schema=False, summary="分析问答型算法测试专用")
# async def _cognitive_search_test_(request: Request, query_dict=Body(...)):
#
#     ANALYSIS_SEARCH_EMPTY_RESULT = ({}, "000", "000")
#     response=""
#
#     return {"res": response}
#
# @cognitive_search_router.post(TestAssetRouter, include_in_schema=False, summary="搜索列表算法测试专用")
# async def _cognitive_search_test_asset(request: Request, query_dict=Body(...)):
#     search_params = AssetSearchParams(**query_dict)
#     response = await run_func_resource(request, search_params)
#     return {"res": response}

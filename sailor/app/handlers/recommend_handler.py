# -*- coding: utf-8 -*-

"""
@Time ：2024/1/5 10:12
@Auth ：Danny.gao
@File ：recommend_handler.py
@Desc ：
@Motto：ABC(Always Be Coding)
"""

from fastapi import APIRouter
from app.logs.logger import logger

from app.routers import RecommendCodeRouter, CheckCodeRouter, \
    RecommendViewRouter, RecommendFieldRuleRouter, RecommendExploreRuleRouter, RecommendSubjectModelRouter
from app.cores.recommend.recommend_v2 import (recommend_code_func, recommend_view_func, recommend_field_rule_func,
                                              recommend_explore_rule_func, recommend_check_code_func, recommendSubjectModel)
from app.cores.recommend._models import *

recommend_router = APIRouter()


# @recommend_router.post(RecommendTableRouter, include_in_schema=False)
# async def recommend_table(params: RecommendTableParams):
#     return {"res": await recommendTable(params.af_query, params.graph_id, params.appid)}


# @recommend_router.post(RecommendFlowRouter, include_in_schema=False)
# async def recommend_flow(params: RecommendFlowParams):
#     logger.info("参数： {}".format(params.model_dump()))
#     return {"res": await recommendFlow(params.af_query, params.graph_id, params.appid)}


@recommend_router.post(RecommendCodeRouter, include_in_schema=False)
async def recommend_code(params: RecommendCodeParams):
    logger.info("参数： {}".format(params.model_dump()))
    return {"res": await recommend_code_func(params.query)}


@recommend_router.post(CheckCodeRouter, include_in_schema=False)
async def check_code(params: CheckCodeParams):
    logger.info("参数： {}".format(params.model_dump()))
    flag, msg, rec_infos, log_infos = await recommend_check_code_func(datas=params.query)
    status = 200 if flag else 500
    msg = f'success\n{msg}' if flag else f'fail\n{msg}'
    msg = msg.strip('\n')
    final_res = {
        'code': status,
        'msg': msg,
        'data': rec_infos,
        'log': log_infos
    }
    return final_res


@recommend_router.post(RecommendViewRouter, include_in_schema=False)
async def recommend_table(params: RecommendViewParams):
    return {"res": await recommend_view_func(params.query)}


# @recommend_router.post(RecommendLabelRouter, include_in_schema=False)
# async def recommend_label(params: RecommendLabelParams):
#     flag, msg, rec_infos, log_infos = await recommendLabel(data=params.query_items, config=params.config)
#     status = 200 if flag else 500
#     msg = f'success\n{msg}' if flag else f'fail\n{msg}'
#     msg = msg.strip('\n')
#     final_res = {
#         'code': status,
#         'msg': msg,
#         'data': rec_infos,
#         'log': log_infos
#     }
#     return final_res


# @recommend_router.post(CheckIndicatorRouter, include_in_schema=False)
# async def check_indicator(params: CheckIndicatorParams):
#
#     logger.info("参数： {}".format(params.model_dump()))
#     flag, msg, rec_infos, log_infos = await checkIndicator(datas=params.query, config=params.config)
#     status = 200 if flag else 500
#     msg = f'success\n{msg}' if flag else f'fail\n{msg}'
#     msg = msg.strip('\n')
#     final_res = {
#         'code': status,
#         'msg': msg,
#         'data': rec_infos,
#         'log': log_infos
#     }
#     return final_res
#
# @recommend_router.post(RecommendFieldSubjectRouter, include_in_schema=False)
# async def recommend_field_subject(params: RecommendFieldSubjectParams):
#     logger.info("参数： {}".format(params.model_dump()))
#     flag, msg, rec_infos, log_infos = await recommendFieldSubject(params.query, config=params.config)
#     status = 200 if flag else 500
#     msg = f'success\n{msg}' if flag else f'fail\n{msg}'
#     msg = msg.strip('\n')
#     final_res = {
#         'code': status,
#         'msg': msg,
#         'data': rec_infos,
#         'log': log_infos
#     }
#     return final_res

@recommend_router.post(RecommendSubjectModelRouter, include_in_schema=False)
async def recommend_subject_model(params: RecommendSubjectModelParams):
    logger.info("参数： {}".format(params.model_dump()))
    flag, msg, rec_infos, log_infos = await recommendSubjectModel(params.query)
    status = 200 if flag else 500
    msg = f'success\n{msg}' if flag else f'fail\n{msg}'
    msg = msg.strip('\n')
    final_res = {
        'code': status,
        'msg': msg,
        'data': rec_infos,
        'log': log_infos
    }
    return final_res

@recommend_router.post(RecommendFieldRuleRouter, include_in_schema=False)
async def recommend_field_rule(params: RecommendFieldRuleParams):
    logger.info("参数： {}".format(params.model_dump()))
    flag, msg, rec_infos, log_infos = await recommend_field_rule_func(datas=params.query)
    status = 200 if flag else 500
    msg = f'success\n{msg}' if flag else f'fail\n{msg}'
    msg = msg.strip('\n')
    final_res = {
        'code': status,
        'msg': msg,
        'data': rec_infos,
        'log': log_infos
    }
    return final_res


@recommend_router.post(RecommendExploreRuleRouter, include_in_schema=False)
async def recommend_explore_rule(params: RecommendExploreRuleParams):
    flag, msg, rec_infos, log_infos = await recommend_explore_rule_func(datas=params.query)
    status = 200 if flag else 500
    msg = f'success\n{msg}' if flag else f'fail\n{msg}'
    msg = msg.strip('\n')
    final_res = {
        'code': status,
        'msg': msg,
        'data': rec_infos,
        'log': log_infos
    }
    return final_res
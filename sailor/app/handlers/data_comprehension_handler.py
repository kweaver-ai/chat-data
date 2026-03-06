from fastapi import APIRouter, Body, Request, Query, HTTPException, Depends
from typing import Optional

from app.cores.data_comprehension.dc_error import validate
from app.cores.data_comprehension.dc_func import get_data_comprehension
from pydantic import BaseModel

from app.routers import ComprehensionRouter
from app.logs.logger import logger
from app.cores.data_comprehension.dc_model import (BUSINESS_OBJECT, SUPPORTED_DIMENSIONS,
                                                   create_empty_data_comprehension_response)
from app.cores.cognitive_search.search_config.get_params import SearchConfigs, get_search_configs

data_comprehension_router = APIRouter()


# 创建依赖函数获取配置，用于依赖注入
async def get_search_configs_dependency() -> SearchConfigs:
    search_configs: Optional[SearchConfigs] = get_search_configs()
    if search_configs is None:
        raise HTTPException(status_code=500, detail="获取配置信息失败")
    return search_configs


class DataComprehensionParams(BaseModel):
    catalog_id: str
    dimension: str


@data_comprehension_router.get(ComprehensionRouter, include_in_schema=False, summary="数据理解接口")
async def data_comprehension(
        request: Request,
        catalog_id: Optional[str] = Query(None),
        dimension: Optional[str] = Query(None),
        search_configs: SearchConfigs = Depends(get_search_configs_dependency)
):
    logger.info(f"data_comprehension request.headers = {request.headers}")
    # 确保所有头字段的值都是字符串
    for key, value in request.headers.items():
        # logger.info(f"headers key = {key}, value = {value}")
        if not isinstance(value, str):
            logger.info("invalid key-value: ", key, value)
            # headers[key] = str(value)
    logger.info(f'数据资源目录的数据理解接口入参：\ncatalog_id = {catalog_id}  \ndimension = {dimension}')

    error_msg  = validate(
        catalog_id=catalog_id,
        dimension=dimension
    )
    if error_msg:
        logger.warning(f"Parameter validation failed，error_msg = {error_msg}")
        return create_empty_data_comprehension_response(
            dimension=dimension,
            error_str=error_msg
        )

    try:
        authorization = request.headers.get('Authorization')
        if authorization is None or authorization.strip() == "":
            error_msg = "Authorization header is missing"
            return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )

        # 调用数据理解主函数
        response = await get_data_comprehension(
            authorization=authorization,
            catalog_id=catalog_id,
            dimension=dimension,
            search_configs=search_configs
        )
        logger.info(f'data comprehension response = {response}')
        return response

    except Exception as e:
        logger.error(f"Error in data_comprehension: {e}", exc_info=True)
        # 返回统一的错误响应
        error_msg = "Internal server error: data comprehension"
        return create_empty_data_comprehension_response(
            dimension=dimension,
            error_str=error_msg
        )
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi import Body, Request
from fastapi.responses import StreamingResponse, JSONResponse
import json

from pydantic import ValidationError

from app.cores.cognitive_assistant.qa import QA
from app.cores.cognitive_assistant.qa_error import validate, corr_params, validate_dip
from app.cores.cognitive_assistant.qa_model import QAParamsModel, QAParamsModelDIP
from app.cores.cognitive_search.search_config.get_params import SearchConfigs, get_search_configs
from app.routers.cognitive_assistant_router import QARouter
from app.logs.logger import logger

qa_router = APIRouter()


async def get_search_configs_dependency() -> SearchConfigs:
    search_configs: Optional[SearchConfigs] = get_search_configs()
    if search_configs is None:
        raise HTTPException(status_code=500, detail="获取配置信息失败")
    return search_configs


@qa_router.post(QARouter)
async def qa(
        request: Request,
        params=Body(...),
        search_configs: SearchConfigs = Depends(get_search_configs_dependency)
):
    logger.info(f"/api/af-sailor{request.url.path} is called: input params = \n{params}")

    # error_dict = validate_dip(params)
    # if error_dict is not None:
    #     raise HTTPException(status_code=400, detail=error_dict)

    # 从请求头中提取 subject_id 和 subject_type（如果参数中没有提供）
    if params.get("subject_id") is None:
        params["subject_id"] = request.headers.get("X-Account-Id")
    if params.get("subject_type") is None:
        params["subject_type"] = request.headers.get("X-Account-Type")

    # available_option字段：0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的）
    # "is_permissions"：表示目前资源的权限，（available_option字段，传参为1时返回），"1"代表有权限，"0"代表无权限
    if search_configs.sailor_search_if_auth_in_find_data_qa == '0':
        params["available_option"] = 1
    else:
        params["available_option"] = 2

    # QAParamsModelDIP 相对于入参 params 增加了 "available_option"， 减少了 "session_id"
    try:
        params = QAParamsModelDIP(**corr_params(params))
    except ValidationError as e:
        # 处理 Pydantic 验证错误
        error_msg = f"参数验证失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    except Exception as e:
        # 处理其他可能的异常
        error_msg = f"参数处理失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        if params.stream:
            return StreamingResponse(
                QA().stream(
                    request=request,
                    params=params,
                    search_configs=search_configs
                ),
                media_type="text/event-stream"
            )
        else:
            res = await QA().forward(
                request=request,
                params=params,
                search_configs=search_configs
            )
            return JSONResponse(status_code=200, content=res)
    except Exception as e:
        error_msg = f"QA处理失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail={"error": error_msg})


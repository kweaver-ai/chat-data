# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, Body, Depends, Query, Path
from app.service.config_service import ConfigService
from app.models.config_models import SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse, \
    SystemConfigListResponse, GroupedSystemConfigResponse
from app.utils.get_token import get_token

ConfigRouter = APIRouter()

# 初始化服务
config_service = ConfigService()


@ConfigRouter.post(
    "/config",
    summary="创建配置",
    description="创建新的系统配置",
    response_model=SystemConfigResponse,
    responses={
        200: {
            "description": "配置创建成功",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/SystemConfigResponse"
                    }
                }
            }
        }
    }
)
async def create_config(
    request: Request,
    config_data: SystemConfigCreate = Body(..., description="配置创建请求参数"),
    token: str = Depends(get_token)
):
    """创建配置
    
    创建新的系统配置。
    
    Args:
        request: HTTP请求对象
        config_data: 配置创建请求参数
        token: 认证令牌
    
    Returns:
        SystemConfigResponse: 配置创建响应
    """
    config = config_service.create_config(config_data)
    return config


@ConfigRouter.get(
    "/config/list",
    summary="获取配置列表",
    description="获取系统配置列表，支持分页和条件查询",
    response_model=SystemConfigListResponse,
    responses={
        200: {
            "description": "成功获取配置列表",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/SystemConfigListResponse"
                    }
                }
            }
        }
    }
)
async def list_configs(
    request: Request,
    config_key: str = Query(None, description="配置键"),
    config_group: str = Query(None, description="配置分组"),
    config_group_type: int = Query(None, description="配置分组类型"),
    size: int = Query(10, description="每页大小", ge=1, le=100),
    pagination_marker_str: str = Query("", description="分页标记"),
    token: str = Depends(get_token)
):
    """获取配置列表
    
    获取系统配置列表，支持分页和条件查询。
    
    Args:
        request: HTTP请求对象
        config_key: 配置键
        config_group: 配置分组
        config_group_type: 配置分组类型
        size: 每页大小
        pagination_marker_str: 分页标记
        token: 认证令牌
    
    Returns:
        SystemConfigListResponse: 配置列表响应
    """
    result = config_service.list_configs(
        config_key=config_key,
        config_group=config_group,
        config_group_type=config_group_type,
        size=size,
        pagination_marker_str=pagination_marker_str
    )
    return result


@ConfigRouter.put(
    "/config/{config_id}",
    summary="更新配置",
    description="更新系统配置",
    response_model=SystemConfigResponse,
    responses={
        200: {
            "description": "配置更新成功",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/SystemConfigResponse"
                    }
                }
            }
        },
        404: {
            "description": "配置不存在"
        }
    }
)
async def update_config(
    request: Request,
    config_id: int = Path(..., description="配置ID"),
    config_data: SystemConfigUpdate = Body(..., description="配置更新请求参数"),
    token: str = Depends(get_token)
):
    """更新配置
    
    更新系统配置。
    
    Args:
        request: HTTP请求对象
        config_id: 配置ID
        config_data: 配置更新请求参数
        token: 认证令牌
    
    Returns:
        SystemConfigResponse: 配置更新响应
    """
    from fastapi import HTTPException
    config = config_service.update_config(config_id, config_data)
    if config is None:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@ConfigRouter.delete(
    "/config/{config_id}",
    summary="删除配置",
    description="删除系统配置",
    responses={
        200: {
            "description": "配置删除成功",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {
                                "type": "boolean",
                                "description": "删除是否成功"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def delete_config(
    request: Request,
    config_id: int = Path(..., description="配置ID"),
    updated_by: str = Body(..., embed=True, description="更新人"),
    token: str = Depends(get_token)
):
    """删除配置
    
    删除系统配置。
    
    Args:
        request: HTTP请求对象
        config_id: 配置ID
        updated_by: 更新人
        token: 认证令牌
    
    Returns:
        dict: 删除结果
    """
    result = config_service.delete_config(config_id, updated_by)
    return {"success": result}


@ConfigRouter.get(
    "/config/ws-category-list",
    summary="获取问数分类配置列表",
    description="获取问数分类配置列表，用于前端展示",
    response_model=GroupedSystemConfigResponse,
    responses={
        200: {
            "description": "成功获取问数分类配置列表",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/GroupedSystemConfigResponse"
                    }
                }
            }
        }
    }
)
async def get_ws_category_configs(request: Request, token: str = Depends(get_token)):
    """获取问数分类配置列表
    
    获取问数分类配置的系统配置列表，用于前端展示。
    
    Args:
        request: HTTP请求对象
        token: 认证令牌
    
    Returns:
        GroupedSystemConfigResponse: 分组配置列表响应
    """
    result = config_service.get_grouped_configs(0)
    return result

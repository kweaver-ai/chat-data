# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, RootModel
from typing import List, Optional, Dict
from app.models.common_models import PaginationResp


class SystemConfigBase(BaseModel):
    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    config_group: str = Field(..., description="配置分组")
    config_group_type: int = Field(default=0, description="配置分组类型0问数分类")
    config_desc: str = Field(None, description="配置描述")


class SystemConfigCreate(SystemConfigBase):
    pass
    # created_by: str = Field(None, description="创建人")
    # updated_by: str = Field(None, description="更新人")


class SystemConfigUpdate(BaseModel):
    config_value: Optional[str] = Field(..., description="配置值")
    config_group: Optional[str] = Field(..., description="配置分组")
    config_group_type: Optional[int] = Field(None, description="配置分组类型0问数分类")
    config_desc: Optional[str] = Field(..., description="配置描述")
    # updated_by: str = Field(None, description="更新人")


class SystemConfigResponse(SystemConfigBase):
    config_id: str = Field(..., description="配置id")
    # created_at: str = Field(..., description="创建时间")
    # updated_at: str = Field(..., description="更新时间")
    # deleted_at: int = Field(..., description="删除时间")
    # created_by: str = Field(None, description="创建人")
    # updated_by: str = Field(None, description="更新人")


class SystemConfigListResponse(PaginationResp[SystemConfigResponse]):
    pass


class SystemConfigQuery(BaseModel):
    config_key: Optional[str] = Field(None, description="配置键")
    config_group: Optional[str] = Field(None, description="配置分组")
    config_group_type: Optional[int] = Field(None, description="配置分组类型")
    size: int = Field(default=10, description="每页大小")
    pagination_marker_str: str = Field(default="", description="分页标记")


class GroupedSystemConfigResponse(BaseModel):
    """分组的系统配置响应模型，支持动态分组"""
    data: Dict[str, List[SystemConfigResponse]] = Field(..., description="动态分组的配置列表")

    class Config:
        schema_extra = {
            "example": {
                "data": {
                    "role": [{"config_id": "1", "config_key": "ROLE_USER", "config_value": "用户", "config_group": "role", "config_desc": "普通用户角色", "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00", "deleted_at": 0, "created_by": "system", "updated_by": "system"}],
                    "org_level": [{"config_id": "4", "config_key": "ORG_LEVEL_1", "config_value": "机构", "config_group": "org_level", "config_desc": "最高组织级别", "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00", "deleted_at": 0, "created_by": "system", "updated_by": "system"}]
                }
            }
        }

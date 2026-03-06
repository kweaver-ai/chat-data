# -*- coding: utf-8 -*-
"""
视图数据生成工具
根据 data_view_id 生成语义补全接口需要的视图数据格式
"""

from typing import Dict, Any, Optional, List
from app.api.af_api import Services
from data_retrieval.logs.logger import logger


async def generate_form_view_from_data_view_id(
    data_view_id: str,
    token: str,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    根据 data_view_id 生成语义补全接口需要的 form_view 格式数据
    
    Args:
        data_view_id: 数据视图ID
        token: 认证token（Bearer token）
        base_url: 可选的API基础URL（用于调试）
        
    Returns:
        符合语义补全接口输入格式的 form_view 字典，格式如下：
        {
            "form_view_id": "视图ID",
            "form_view_technical_name": "视图技术名称",
            "form_view_business_name": "视图业务名称",
            "form_view_desc": "视图描述",
            "form_view_fields": [
                {
                    "form_view_field_id": "字段ID",
                    "form_view_field_technical_name": "字段技术名称",
                    "form_view_field_business_name": "字段业务名称",
                    "form_view_field_type": "字段类型",
                    "form_view_field_desc": "字段描述",
                    "form_view_field_role": 字段角色（int类型，可选）
                }
            ]
        }
        
    Raises:
        Exception: 当获取视图信息失败时抛出异常
    """
    try:
        # 初始化服务
        service = Services(base_url=base_url) if base_url else Services()
        
        # 准备请求头
        headers = {
            "authorization": token if token.startswith("Bearer ") else f"Bearer {token}"
        }
        
        # 获取视图详情
        view_details = service.get_view_details_by_id(data_view_id, headers=headers)
        
        # 获取字段信息
        view_columns = service.get_view_column_by_id(data_view_id, headers=headers)
        
        # 尝试获取字段的脱敏、数据分级等信息（包含字段角色）
        field_info = None
        try:
            field_info = service.get_view_field_info(data_view_id, headers=headers)
        except Exception as e:
            logger.warning(f"获取字段信息失败（可能不包含字段角色）: {str(e)}")
            # 字段角色信息不是必需的，继续处理
        
        # 构建 form_view 数据
        form_view = {
            "form_view_id": data_view_id,
            "form_view_technical_name": view_details.get("technical_name", ""),
            "form_view_business_name": view_details.get("business_name", ""),
            "form_view_desc": view_details.get("description", ""),
            "form_view_fields": []
        }
        
        # 构建字段信息映射（用于查找字段角色）
        field_role_map = {}
        if field_info and isinstance(field_info, dict):
            # 假设 field_info 包含字段信息列表或字典
            if isinstance(field_info, list):
                for item in field_info:
                    field_id = item.get("field_id") or item.get("id")
                    field_role = item.get("field_role") or item.get("role")
                    if field_id and field_role is not None:
                        field_role_map[field_id] = field_role
            elif isinstance(field_info, dict):
                # 可能是以字段ID为key的字典
                for field_id, info in field_info.items():
                    if isinstance(info, dict):
                        field_role = info.get("field_role") or info.get("role")
                        if field_role is not None:
                            field_role_map[field_id] = field_role
        
        # 处理字段列表
        # view_columns 可能是列表或字典格式，需要根据实际API返回格式处理
        if isinstance(view_columns, list):
            # 如果是列表格式
            for column in view_columns:
                field_id = column.get("id") or column.get("field_id") or column.get("form_view_field_id")
                field_technical_name = column.get("technical_name") or column.get("field_name") or column.get("name")
                field_business_name = column.get("business_name") or column.get("field_business_name")
                field_type = column.get("field_type") or column.get("type") or column.get("data_type")
                field_desc = column.get("description") or column.get("field_description") or column.get("desc")
                
                # 获取字段角色（优先从 field_info 获取，其次从 column 本身获取）
                field_role = None
                if field_id and field_id in field_role_map:
                    field_role = field_role_map[field_id]
                elif column.get("field_role") is not None:
                    field_role = column.get("field_role")
                elif column.get("role") is not None:
                    field_role = column.get("role")
                
                form_field = {
                    "form_view_field_id": field_id or "",
                    "form_view_field_technical_name": field_technical_name or "",
                    "form_view_field_business_name": field_business_name or "",
                    "form_view_field_type": field_type or "",
                    "form_view_field_desc": field_desc or ""
                }
                
                # 如果存在字段角色，添加到字段信息中
                if field_role is not None:
                    form_field["form_view_field_role"] = int(field_role)
                
                form_view["form_view_fields"].append(form_field)
                
        elif isinstance(view_columns, dict):
            # 如果是字典格式，可能是以字段ID为key
            for field_id, column in view_columns.items():
                if isinstance(column, dict):
                    field_technical_name = column.get("technical_name") or column.get("field_name") or column.get("name")
                    field_business_name = column.get("business_name") or column.get("field_business_name")
                    field_type = column.get("field_type") or column.get("type") or column.get("data_type")
                    field_desc = column.get("description") or column.get("field_description") or column.get("desc")
                    
                    # 获取字段角色
                    field_role = None
                    if field_id in field_role_map:
                        field_role = field_role_map[field_id]
                    elif column.get("field_role") is not None:
                        field_role = column.get("field_role")
                    elif column.get("role") is not None:
                        field_role = column.get("role")
                    
                    form_field = {
                        "form_view_field_id": field_id or "",
                        "form_view_field_technical_name": field_technical_name or "",
                        "form_view_field_business_name": field_business_name or "",
                        "form_view_field_type": field_type or "",
                        "form_view_field_desc": field_desc or ""
                    }
                    
                    if field_role is not None:
                        form_field["form_view_field_role"] = int(field_role)
                    
                    form_view["form_view_fields"].append(form_field)
        else:
            logger.warning(f"视图字段信息格式未知: {type(view_columns)}")
        
        return form_view
        
    except Exception as e:
        logger.error(f"根据 data_view_id 生成 form_view 数据失败: data_view_id={data_view_id}, error={str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def generate_form_views_from_data_view_ids(
    data_view_ids: List[str],
    token: str,
    base_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    根据多个 data_view_id 生成语义补全接口需要的 form_view 列表
    
    Args:
        data_view_ids: 数据视图ID列表
        token: 认证token（Bearer token）
        base_url: 可选的API基础URL（用于调试）
        
    Returns:
        form_view 字典列表
        
    Raises:
        Exception: 当获取视图信息失败时抛出异常
    """
    form_views = []
    
    for view_id in data_view_ids:
        try:
            form_view = await generate_form_view_from_data_view_id(
                data_view_id=view_id,
                token=token,
                base_url=base_url
            )
            form_views.append(form_view)
        except Exception as e:
            logger.error(f"处理视图 {view_id} 时发生错误: {str(e)}")
            # 可以选择继续处理其他视图，或者抛出异常
            # 这里选择继续处理，但记录错误
            continue
    
    return form_views



if __name__ == "__main__":
    import asyncio

    # 示例用法
    data_view_ids = ["ce3c58c5-7aa8-409e-9166-ef825a503dc5", "view_id_2"]
    token = "Bearer your_token"

    asyncio.run(generate_form_view_from_data_view_id(data_view_ids, token))

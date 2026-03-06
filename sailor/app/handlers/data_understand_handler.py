# -*- coding:utf-8 -*-
"""
数据理解工具 Handler
包含敏感信息检测、业务对象识别、数据分类分级、质量规则识别、语义补全等接口
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter, Request, Body, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List

from app.tools.data_understand_tools.sensitive_data_detect_tools import SensitiveDataDetectTool
from app.tools.data_understand_tools.business_object_identification_tools import BusinessObjectIdentificationTool
from app.tools.data_understand_tools.data_classification_detect_tools import DataClassificationDetectTool
from app.tools.data_understand_tools.explore_rule_identification_tools import ExploreRuleIdentificationTool
from app.tools.data_understand_tools.semantic_complete_tool import SemanticCompleteTool
from app.routers.agent_temp_router import DataUnderstandRouter
from app.utils.get_token import get_token
from app.service.task_service import TaskService, TaskStatus
from app.service.kafka_service import KafkaService
from data_retrieval.logs.logger import logger


# 创建数据理解工具路由
DataUnderstandAPIRouter = APIRouter()


@DataUnderstandAPIRouter.post(f"{DataUnderstandRouter}/sensitive_data_detect")
async def sensitive_data_detect_api(
    request: Request,
    params: Dict[str, Any] = Body(...),
):
    """
    敏感信息检测接口
    
    检测数据库表中可能包含敏感信息的字段，识别个人身份信息、财务信息、健康信息等敏感数据类型，
    并生成匹配敏感字段的正则表达式。
    """
    authorization = request.headers.get('Authorization')
    params["configs"] = {
        "token": authorization
    }
    try:
        # 调用工具的异步 API 方法
        result = await SensitiveDataDetectTool.as_async_api_cls(params)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        logger.error(f"敏感信息检测接口调用失败: {str(e)}")
        return JSONResponse(
            content={"error": f"敏感信息检测失败: {str(e)}"},
            status_code=500
        )


@DataUnderstandAPIRouter.post(f"{DataUnderstandRouter}/business_object_identification")
async def business_object_identification_api(
    request: Request,
    params: Dict[str, Any] = Body(...),
):
    """
    业务对象识别接口
    
    从库表列表中识别业务对象，分析表的业务含义和对象特征。
    """
    authorization = request.headers.get('Authorization')
    params["configs"] = {
        "token": authorization
    }
    try:
        result = await BusinessObjectIdentificationTool.as_async_api_cls(params)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        logger.error(f"业务对象识别接口调用失败: {str(e)}")
        return JSONResponse(
            content={"error": f"业务对象识别失败: {str(e)}"},
            status_code=500
        )


@DataUnderstandAPIRouter.post(f"{DataUnderstandRouter}/data_classification_detect")
async def data_classification_detect_api(
    request: Request,
    params: Dict[str, Any] = Body(...),
):
    """
    数据分类分级接口
    
    对数据库表进行业务分类和数据分级，识别业务领域、数据类型、数据来源和重要性级别。
    """
    authorization = request.headers.get('Authorization')
    params["configs"] = {
        "token": authorization
    }
    try:
        result = await DataClassificationDetectTool.as_async_api_cls(params)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        logger.error(f"数据分类分级接口调用失败: {str(e)}")
        return JSONResponse(
            content={"error": f"数据分类分级失败: {str(e)}"},
            status_code=500
        )


@DataUnderstandAPIRouter.post(f"{DataUnderstandRouter}/explore_rule_identification")
async def explore_rule_identification_api(
    request: Request,
    params: Dict[str, Any] = Body(...),
):
    """
    质量规则识别接口
    
    从库表列表中识别数据质量规则和约束条件，包括完整性、准确性、一致性、时效性、有效性、合理性等规则。
    """
    authorization = request.headers.get('Authorization')
    params["configs"] = {
        "token": authorization
    }
    try:
        result = await ExploreRuleIdentificationTool.as_async_api_cls(params)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        logger.error(f"质量规则识别接口调用失败: {str(e)}")
        return JSONResponse(
            content={"error": f"质量规则识别失败: {str(e)}"},
            status_code=500
        )


@DataUnderstandAPIRouter.post(f"{DataUnderstandRouter}/semantic_completion")
async def semantic_completion_api(
    request: Request,
    params: Dict[str, Any] = Body(...),
):
    """
    语义补全接口
    
    对库表数据的字段进行分析，补全缺失的字段含义。识别字段描述缺失、不准确或不完整的问题，并提供补全建议。
    """
    authorization = request.headers.get('Authorization')
    params["configs"] = {
        "token": authorization
    }
    try:
        result = await SemanticCompleteTool.as_async_api_cls(params)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        logger.error(f"语义补全接口调用失败: {str(e)}")
        return JSONResponse(
            content={"error": f"语义补全失败: {str(e)}"},
            status_code=500
        )


def _transform_result_to_kafka_format(
    form_view: Dict[str, Any],
    semantic_result: Optional[Dict[str, Any]],
    business_result: Optional[Dict[str, Any]],
    request_type: str,
    message_id: Optional[str] = None,
    status: str = "success",
    error: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    将工具返回的结果转换为 Kafka 消息格式
    
    Args:
        form_view: 输入的视图对象（支持新格式：view_id等，也兼容旧格式：form_view_id等）
        semantic_result: 语义补全结果（可选）
        business_result: 业务对象识别结果（可选）
        request_type: 请求类型（full_understanding 或 regenerate_business_objects）
        message_id: 消息ID（可选）
        status: 状态（success 或 failed）
        error: 错误信息（可选），格式为 {"code": "错误代码", "message": "错误消息"}
        
    Returns:
        转换后的 Kafka 消息格式
    """
    # 获取 view_id（兼容新格式和旧格式）
    view_id = (form_view.get("view_id") or 
              form_view.get("form_view_id") or "")
    
    # 构建基础消息
    kafka_message = {
        "form_view_id": view_id,  # Kafka消息仍使用form_view_id字段名
        "request_type": request_type,
        "process_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "status": status
    }
    
    # 添加 message_id（如果提供）
    if message_id:
        kafka_message["message_id"] = message_id
    
    # 如果状态为失败，添加 error 字段
    if status == "failed" and error:
        kafka_message["error"] = error
    
    # 处理语义补全结果
    if semantic_result:
        semantic_result_data = semantic_result.get("result", {})
        semantic_views = semantic_result_data.get("views", [])
        
        if semantic_views:
            semantic_view = semantic_views[0]
            
            # 提取 table_semantic（兼容新格式和旧格式）
            view_business_name = (semantic_view.get("view_business_name") or 
                                semantic_view.get("form_view_business_name") or "")
            desc = (semantic_view.get("desc") or 
                   semantic_view.get("view_desc") or 
                   semantic_view.get("form_view_desc") or "")
            
            kafka_message["table_semantic"] = {
                "table_business_name": view_business_name,
                "table_description": desc
            }
            
            # 提取 fields_semantic（包含需要补全的字段和未补全的字段）
            fields_semantic = []
            
            # 处理需要补全的字段（使用建议描述）
            fields_need_completion = (semantic_view.get("fields_need_completion") or 
                                     semantic_view.get("form_view_fields_need_completion", []))
            
            for field in fields_need_completion:
                # 使用建议的业务名称（如果存在），否则使用当前业务名称
                field_business_name = (field.get("suggested_business_name") or 
                                     field.get("field_business_name") or 
                                     field.get("form_view_field_business_name", ""))
                field_desc = (field.get("suggested_description") or 
                            field.get("current_description", ""))
                # 使用建议的字段角色（如果存在），否则使用当前字段角色
                field_role = (field.get("suggested_field_role") 
                            if field.get("suggested_field_role") is not None 
                            else field.get("field_role") or field.get("form_view_field_role"))
                
                field_id = (field.get("field_id") or 
                           field.get("form_view_field_id", ""))
                
                fields_semantic.append({
                    "form_view_field_id": field_id,
                    "field_business_name": field_business_name,
                    "field_role": field_role,
                    "field_description": field_desc
                })
            
            # 处理未补全的字段（描述准确的字段）
            fields_accurate = semantic_view.get("fields_accurate", [])
            for field in fields_accurate:
                field_id = field.get("field_id", "")
                field_business_name = field.get("field_business_name", "")
                field_desc = field.get("field_desc", "")
                field_role = field.get("field_role")
                
                if field_id:  # 确保字段ID存在
                    fields_semantic.append({
                        "form_view_field_id": field_id,
                        "field_business_name": field_business_name,
                        "field_role": field_role,
                        "field_description": field_desc
                    })
            
            kafka_message["fields_semantic"] = fields_semantic
    
    # 处理业务对象识别结果
    if business_result:
        business_result_data = business_result.get("result", {})
        business_objects_list = []
        
        # 从 views 或 tables 中提取业务对象（兼容新格式和旧格式）
        views_or_tables = (business_result_data.get("views") or 
                          business_result_data.get("tables", []))
        
        for view_or_table in views_or_tables:
            if view_or_table.get("is_business_object", False):
                business_object_info = view_or_table.get("business_object", {})
                object_attributes = view_or_table.get("object_attributes", {})
                
                # 构建业务对象
                business_obj = {
                    "object_name": business_object_info.get("object_name_cn", business_object_info.get("object_name_en", ""))
                }
                
                # 提取业务对象属性
                # 优先使用 attributes 字段（包含所有属性及其业务名称）
                attributes_list = object_attributes.get("attributes", [])
                
                if attributes_list:
                    # 如果存在 attributes 字段，直接使用
                    attributes = []
                    for attr in attributes_list:
                        if attr.get("field_id"):
                            attr_item = {
                                "form_view_field_id": attr.get("field_id", ""),
                                "attr_name": attr.get("attr_name", attr.get("field_name", ""))
                            }
                            # 可选字段：属性类型和描述
                            if attr.get("attr_type"):
                                attr_item["attr_type"] = attr.get("attr_type")
                            if attr.get("attr_description"):
                                attr_item["attr_description"] = attr.get("attr_description")
                            attributes.append(attr_item)
                else:
                    # 兼容旧格式：合并 primary_key, key_fields, relationship_fields
                    attributes = []
                    
                    # 主键
                    primary_key = object_attributes.get("primary_key", {})
                    if primary_key and primary_key.get("field_id"):
                        attributes.append({
                            "form_view_field_id": primary_key.get("field_id", ""),
                            "attr_name": primary_key.get("field_name", "")
                        })
                    
                    # 关键字段
                    key_fields = object_attributes.get("key_fields", [])
                    for field in key_fields:
                        if field.get("field_id"):
                            attributes.append({
                                "form_view_field_id": field.get("field_id", ""),
                                "attr_name": field.get("field_name", "")
                            })
                    
                    # 关联字段
                    relationship_fields = object_attributes.get("relationship_fields", [])
                    for field in relationship_fields:
                        if field.get("field_id"):
                            attributes.append({
                                "form_view_field_id": field.get("field_id", ""),
                                "attr_name": field.get("field_name", "")
                            })
                
                business_obj["attributes"] = attributes
                business_objects_list.append(business_obj)
        
        kafka_message["business_objects"] = business_objects_list
        
        # 提取未关联到业务对象的字段（non_attribute_fields）
        no_pattern_fields_list = []
        for view_or_table in views_or_tables:
            object_attributes = view_or_table.get("object_attributes", {})
            non_attribute_fields = object_attributes.get("non_attribute_fields", [])
            
            for field in non_attribute_fields:
                field_id = field.get("field_id", "")
                field_business_name = field.get("field_business_name", "")
                field_desc = field.get("field_desc", "")
                field_role = field.get("field_role")
                
                if field_id:  # 确保字段ID存在
                    no_pattern_fields_list.append({
                        "form_view_field_id": field_id,
                        "field_business_name": field_business_name,
                        "field_role": field_role,
                        "field_description": field_desc
                    })
        
        # 如果有未关联字段，添加到 Kafka 消息中
        if no_pattern_fields_list:
            kafka_message["no_pattern_fields"] = no_pattern_fields_list
        else:
            kafka_message["no_pattern_fields"] = []
    
    return kafka_message


def _send_failed_kafka_message(
    task_id: str,
    form_view: Dict[str, Any],
    request_type: str,
    message_id: Optional[str],
    error_msg: str
):
    """
    发送失败消息到 Kafka
    
    Args:
        task_id: 任务ID
        form_view: 输入的 form_view 对象
        request_type: 请求类型
        message_id: 消息ID（可选）
        error_msg: 错误消息
    """
    try:
        from config import settings
        from app.service.kafka_service import KAFKA_AVAILABLE
        
        if KAFKA_AVAILABLE:
            kafka_service = KafkaService()
            
            # 构建错误信息
            error = {
                "code": "AI_SERVICE_ERROR",
                "message": error_msg
            }
            
            # 构建失败消息
            kafka_message = _transform_result_to_kafka_format(
                form_view=form_view,
                semantic_result=None,
                business_result=None,
                request_type=request_type,
                message_id=message_id,
                status="failed",
                error=error
            )
            
            topic = getattr(settings, 'KAFKA_TASK_RESULT_TOPIC', 'data-understanding-responses')
            kafka_service.send_message(
                topic=topic,
                message=kafka_message,
                key=message_id or task_id
            )
            kafka_service.close()
    except Exception as e:
        logger.error(f"发送失败消息到Kafka时发生错误: task_id={task_id}, error={str(e)}")


def _convert_views_to_old_format(views: List[Dict]) -> List[Dict]:
    """
    将新格式的视图数据（form_view_*）转换为业务对象识别工具期望的旧格式
    
    Args:
        views: 新格式的视图数据列表，支持 form_view_* 格式（也兼容旧的 view_* 格式）
        
    Returns:
        旧格式的数据列表
    """
    old_format_list = []
    
    for view in views:
        # 兼容 form_view_* 和 view_* 格式
        view_id = view.get("form_view_id") or view.get("view_id", "")
        view_technical_name = view.get("form_view_technical_name") or view.get("view_technical_name", "")
        view_business_name = view.get("form_view_business_name") or view.get("view_business_name", "")
        view_desc = view.get("form_view_desc") or view.get("view_desc", "")
        
        old_format_item = {
            "table_id": view_id,
            "table_name": view_technical_name,
            "table_business_name": view_business_name,
            "table_description": view_desc,
            "fields": []
        }
        
        # 转换字段数据
        view_fields = view.get("form_view_fields") or view.get("view_fields", [])
        for field in view_fields:
            # 兼容 form_view_field_* 和 view_field_* 格式
            field_id = field.get("form_view_field_id") or field.get("view_field_id", "")
            field_technical_name = field.get("form_view_field_technical_name") or field.get("view_field_technical_name", "")
            field_business_name = field.get("form_view_field_business_name") or field.get("view_field_business_name", "")
            field_type = field.get("form_view_field_type") or field.get("view_field_type", "")
            field_desc = field.get("form_view_field_desc") or field.get("view_field_desc", "")
            
            old_format_field = {
                "field_id": field_id,
                "field_name": field_technical_name,
                "field_business_name": field_business_name,
                "field_type": field_type,
                "field_description": field_desc
            }
            old_format_item["fields"].append(old_format_field)
        
        old_format_list.append(old_format_item)
    
    return old_format_list


async def _execute_semantic_and_business_analysis_task(
    task_id: str,
    params: Dict[str, Any],
    authorization: str,
    message_id: Optional[str] = None
):
    """
    执行语义补全和业务对象识别任务（后台异步执行）
    
    Args:
        task_id: 任务ID
        params: 任务参数
        authorization: 授权token
        message_id: 消息ID，用于写入Kafka（可选）
    """
    task_service = TaskService()
    
    try:
        # 更新任务状态为运行中
        task_service.update_task_status(task_id, TaskStatus.RUNNING, progress=10)
        
        # 准备参数，将 token 放入 auth 中
        if "auth" not in params:
            params["auth"] = {}
        params["auth"]["token"] = authorization
        
        # 获取 request_type
        request_type = params.get("request_type", "full_understanding")
        
        # 处理输入：接受单个 form_view 或 views 列表（兼容旧格式）
        form_view = params.get("form_view")
        views = params.get("views", [])
        
        # 保存原始 form_view 用于后续 Kafka 消息
        original_form_view = form_view if form_view else (views[0] if views else {})
        
        # 如果提供了 form_view，转换为列表格式
        if form_view:
            if not isinstance(form_view, dict):
                task_service.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error="form_view参数必须是对象"
                )
                # 发送失败消息到 Kafka
                _send_failed_kafka_message(task_id, original_form_view, request_type, message_id, "form_view参数必须是对象")
                return
            views = [form_view]
        elif not views:
            task_service.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error="form_view或views参数不能为空"
            )
            # 发送失败消息到 Kafka
            _send_failed_kafka_message(task_id, original_form_view, request_type, message_id, "form_view或views参数不能为空")
            return
        
        # 确保 views 是列表格式
        if not isinstance(views, list):
            task_service.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error="views参数必须是列表"
            )
            # 发送失败消息到 Kafka
            _send_failed_kafka_message(task_id, original_form_view, request_type, message_id, "views参数必须是列表")
            return
        
        # 更新 params，确保 views 是列表格式
        params["views"] = views
        
        # 获取 request_type，默认为 full_understanding
        request_type = params.get("request_type", "full_understanding")
        
        semantic_result = None
        business_result = None
        
        # 根据 request_type 决定执行哪些工具
        if request_type == "full_understanding":
            # 执行语义补全和业务对象识别
            old_format_views = _convert_views_to_old_format(views)
            # 为业务对象识别准备参数
            business_params = params.copy()
            business_params["views"] = old_format_views
            
            # 更新进度
            task_service.update_task_status(task_id, TaskStatus.RUNNING, progress=20)
            
            # 调用语义补全工具（使用新格式）
            semantic_result = await SemanticCompleteTool.as_async_api_cls_with_views(params)
            
            # 更新进度
            task_service.update_task_status(task_id, TaskStatus.RUNNING, progress=60)
            
            # 调用业务对象识别工具（使用旧格式）
            business_result = await BusinessObjectIdentificationTool.as_async_api_cls_with_views(business_params)
            
            # 更新进度
            task_service.update_task_status(task_id, TaskStatus.RUNNING, progress=90)
            
        elif request_type == "regenerate_business_objects":
            # 只执行业务对象识别
            old_format_views = _convert_views_to_old_format(views)
            # 为业务对象识别准备参数
            business_params = params.copy()
            business_params["views"] = old_format_views
            
            # 更新进度
            task_service.update_task_status(task_id, TaskStatus.RUNNING, progress=30)
            
            # 只调用业务对象识别工具（使用旧格式）
            business_result = await BusinessObjectIdentificationTool.as_async_api_cls_with_views(business_params)
            
            # 更新进度
            task_service.update_task_status(task_id, TaskStatus.RUNNING, progress=90)
        
        # 组装结果（单个 view 的格式）
        result = {}
        
        # 如果有语义补全结果，提取第一个 view
        if semantic_result:
            semantic_result_data = semantic_result.get("result", {})
            semantic_views = semantic_result_data.get("views", [])
            semantic_view_result = semantic_views[0] if semantic_views else {}
            
            result["semantic_completion_result"] = {
                "form_view": semantic_view_result,
                "summary": semantic_result_data.get("summary", {}),
                "summary_text": semantic_result.get("summary_text", ""),
                "result_cache_key": semantic_result.get("result_cache_key", "")
            }
        
        # 如果有业务对象识别结果，提取第一个对象
        if business_result:
            business_result_data = business_result.get("result", {})
            # 兼容新格式（views）和旧格式（tables）
            views_or_tables = (business_result_data.get("views") or 
                             business_result_data.get("tables", []))
            
            # 找到第一个业务对象
            business_object_result = {}
            for view_or_table in views_or_tables:
                if view_or_table.get("is_business_object", False):
                    # 合并 business_object, object_attributes, business_characteristics
                    business_object_result = {
                        **view_or_table.get("business_object", {}),
                        **view_or_table.get("object_attributes", {}),
                        **view_or_table.get("business_characteristics", {})
                    }
                    break
            
            result["business_object_identification_result"] = {
                "business_object": business_object_result,
                "summary": business_result_data.get("summary", business_result_data.get("business_objects_summary", {})),
                "summary_text": business_result.get("summary_text", ""),
                "result_cache_key": business_result.get("result_cache_key", "")
            }
        
        # 更新任务状态为已完成
        task_service.update_task_status(task_id, TaskStatus.COMPLETED, result=result, progress=100)
        
        logger.info(f"任务执行完成: task_id={task_id}")
        
        # 将结果发送到Kafka（异步执行，失败不影响任务状态）
        try:
            from config import settings
            from app.service.kafka_service import KAFKA_AVAILABLE
            
            if KAFKA_AVAILABLE:
                kafka_service = KafkaService()
                
                # 获取原始 form_view（从 params 中）
                original_form_view = views[0] if views else {}
                
                # 转换结果为 Kafka 消息格式
                kafka_message = _transform_result_to_kafka_format(
                    form_view=original_form_view,
                    semantic_result=semantic_result,
                    business_result=business_result,
                    request_type=request_type,
                    message_id=message_id,
                    status="success"
                )
                
                # 发送到Kafka主题
                topic = getattr(settings, 'KAFKA_TASK_RESULT_TOPIC', 'data-understanding-responses')
                success = kafka_service.send_message(
                    topic=topic,
                    message=kafka_message,
                    key=message_id or task_id  # 使用message_id或task_id作为key
                )
                
                if success:
                    logger.info(f"任务结果已发送到Kafka: task_id={task_id}, topic={topic}")
                else:
                    logger.warning(f"任务结果发送到Kafka失败: task_id={task_id}, topic={topic}")
                
                # 关闭Kafka连接
                kafka_service.close()
            else:
                logger.warning(f"Kafka不可用，跳过发送任务结果到Kafka: task_id={task_id}")
            
        except ImportError:
            # Kafka服务未安装
            logger.warning(f"Kafka服务未安装，跳过发送任务结果到Kafka: task_id={task_id}")
        except Exception as kafka_error:
            # Kafka发送失败不应该影响任务完成状态
            logger.error(f"发送任务结果到Kafka时发生错误: task_id={task_id}, error={str(kafka_error)}")
            import traceback
            logger.error(traceback.format_exc())
        
    except Exception as e:
        logger.error(f"任务执行失败: task_id={task_id}, error={str(e)}")
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        task_service.update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
        
        # 发送失败消息到 Kafka
        try:
            form_view = params.get("form_view")
            views = params.get("views", [])
            original_form_view = form_view if form_view else (views[0] if views else {})
            request_type = params.get("request_type", "full_understanding")
            _send_failed_kafka_message(task_id, original_form_view, request_type, message_id, str(e))
        except Exception as kafka_error:
            logger.error(f"发送失败消息到Kafka时发生错误: task_id={task_id}, error={str(kafka_error)}")


@DataUnderstandAPIRouter.post(f"{DataUnderstandRouter}/view_semantic_and_business_analysis")
async def view_semantic_and_business_analysis_api(
    request: Request,
    params: Dict[str, Any] = Body(...),
):
    """
    逻辑视图语义补全和业务对象识别接口（异步任务模式）
    
    对输入的逻辑视图数据进行语义补全和业务对象识别分析。
    立即返回任务ID，任务在后台异步执行。
    
    输入参数：
    - form_view: 单个视图对象（form_view_* 格式）
    - request_type: 请求类型
        - "regenerate_business_objects": 只识别业务对象
        - "full_understanding": 语义理解和业务对象（默认）
    - message_id: 消息ID，用于写入Kafka（可选）
    - 其他参数：auth, config, query 等
    """
    authorization = request.headers.get('Authorization')
    
    # 验证 request_type 参数
    request_type = params.get("request_type", "full_understanding")
    valid_request_types = ["regenerate_business_objects", "full_understanding"]
    if request_type not in valid_request_types:
        return JSONResponse(
            content={
                "error": f"request_type参数无效，必须是以下值之一: {', '.join(valid_request_types)}"
            },
            status_code=400
        )
    
    # 验证参数：接受单个 form_view 或 views 列表（兼容旧格式）
    form_view = params.get("form_view")
    views = params.get("views", [])
    
    # 如果提供了 form_view，转换为列表格式
    if form_view:
        if not isinstance(form_view, dict):
            return JSONResponse(
                content={"error": "form_view参数必须是对象"},
                status_code=400
            )
        views = [form_view]
    elif not views:
        return JSONResponse(
            content={"error": "form_view或views参数不能为空"},
            status_code=400
        )
    
    # 确保 views 是列表格式
    if not isinstance(views, list):
        return JSONResponse(
            content={"error": "views参数必须是列表"},
            status_code=400
        )
    
    # 提取 message_id（可选参数）
    message_id = params.get("message_id")
    
    # 创建任务
    task_service = TaskService()
    user_id = params.get("auth", {}).get("user_id", "")
    task_id = task_service.create_task(
        task_type="semantic_and_business_analysis",
        params=params,
        user_id=user_id
    )
    
    # 在后台异步执行任务
    asyncio.create_task(_execute_semantic_and_business_analysis_task(
        task_id=task_id,
        params=params,
        authorization=authorization,
        message_id=message_id
    ))
    
    # 立即返回任务ID和message_id
    response_content = {
        "task_id": task_id,
        "status": "pending",
        "message": "任务已创建，正在后台执行"
    }
    if message_id:
        response_content["message_id"] = message_id
    
    return JSONResponse(
        content=response_content,
        status_code=202  # 202 Accepted
    )


@DataUnderstandAPIRouter.post(f"{DataUnderstandRouter}/view_semantic_and_business_analysis_sync")
async def view_semantic_and_business_analysis_sync_api(
    request: Request,
    params: Dict[str, Any] = Body(...),
):
    """
    逻辑视图语义补全和业务对象识别接口（同步模式）
    
    对输入的逻辑视图数据进行语义补全和业务对象识别分析。
    同步执行并直接返回结果。
    
    输入参数：
    - form_view: 单个视图对象（form_view_* 格式）
    - request_type: 请求类型
        - "regenerate_business_objects": 只识别业务对象
        - "full_understanding": 语义理解和业务对象（默认）
    - message_id: 消息ID，用于写入Kafka（可选）
    - 其他参数：auth, config, query 等
    
    返回：
    - 直接返回分析结果，包含语义补全和业务对象识别结果
    """
    authorization = request.headers.get('Authorization', "")
    
    # 验证 request_type 参数
    request_type = params.get("request_type", "full_understanding")
    valid_request_types = ["regenerate_business_objects", "full_understanding"]
    if request_type not in valid_request_types:
        return JSONResponse(
            content={
                "error": f"request_type参数无效，必须是以下值之一: {', '.join(valid_request_types)}"
            },
            status_code=400
        )
    
    # 验证参数：接受单个 form_view 或 views 列表（兼容旧格式）
    form_view = params.get("form_view")
    views = params.get("views", [])
    
    # 如果提供了 form_view，转换为列表格式
    if form_view:
        if not isinstance(form_view, dict):
            return JSONResponse(
                content={"error": "form_view参数必须是对象"},
                status_code=400
            )
        views = [form_view]
    elif not views:
        return JSONResponse(
            content={"error": "form_view或views参数不能为空"},
            status_code=400
        )
    
    # 确保 views 是列表格式
    if not isinstance(views, list):
        return JSONResponse(
            content={"error": "views参数必须是列表"},
            status_code=400
        )
    
    # 提取 message_id（可选参数）
    message_id = params.get("message_id")
    
    # 保存原始 form_view 用于后续 Kafka 消息
    original_form_view = form_view if form_view else (views[0] if views else {})
    
    try:
        # 准备参数，将 token 放入 auth 中
        if "auth" not in params:
            params["auth"] = {}
        params["auth"]["token"] = authorization
        
        # 更新 params，确保 views 是列表格式
        params["views"] = views
        
        semantic_result = None
        business_result = None
        
        # 根据 request_type 决定执行哪些工具
        if request_type == "full_understanding":
            # 执行语义补全和业务对象识别
            old_format_views = _convert_views_to_old_format(views)
            # 为业务对象识别准备参数
            business_params = params.copy()
            business_params["views"] = old_format_views
            
            # 调用语义补全工具（使用新格式）
            semantic_result = await SemanticCompleteTool.as_async_api_cls_with_views(params)
            
            # 调用业务对象识别工具（使用旧格式）
            business_result = await BusinessObjectIdentificationTool.as_async_api_cls_with_views(business_params)
            
        elif request_type == "regenerate_business_objects":
            # 只执行业务对象识别
            old_format_views = _convert_views_to_old_format(views)
            # 为业务对象识别准备参数
            business_params = params.copy()
            business_params["views"] = old_format_views
            
            # 只调用业务对象识别工具（使用旧格式）
            business_result = await BusinessObjectIdentificationTool.as_async_api_cls_with_views(business_params)
        
        # 组装结果（单个 view 的格式）
        result = {}
        
        # 如果有语义补全结果，提取第一个 view
        if semantic_result:
            semantic_result_data = semantic_result.get("result", {})
            semantic_views = semantic_result_data.get("views", [])
            semantic_view_result = semantic_views[0] if semantic_views else {}
            
            result["semantic_completion_result"] = {
                "form_view": semantic_view_result,
                "summary": semantic_result_data.get("summary", {}),
                "summary_text": semantic_result.get("summary_text", ""),
                "result_cache_key": semantic_result.get("result_cache_key", "")
            }
        
        # 如果有业务对象识别结果，提取第一个对象
        if business_result:
            business_result_data = business_result.get("result", {})
            # 兼容新格式（views）和旧格式（tables）
            views_or_tables = (business_result_data.get("views") or 
                             business_result_data.get("tables", []))
            
            # 找到第一个业务对象
            business_object_result = {}
            for view_or_table in views_or_tables:
                if view_or_table.get("is_business_object", False):
                    # 合并 business_object, object_attributes, business_characteristics
                    business_object_result = {
                        **view_or_table.get("business_object", {}),
                        **view_or_table.get("object_attributes", {}),
                        **view_or_table.get("business_characteristics", {})
                    }
                    break
            
            result["business_object_identification_result"] = {
                "business_object": business_object_result,
                "summary": business_result_data.get("summary", business_result_data.get("business_objects_summary", {})),
                "summary_text": business_result.get("summary_text", ""),
                "result_cache_key": business_result.get("result_cache_key", "")
            }
        
        # 将结果发送到Kafka（异步执行，失败不影响返回结果）
        try:
            from config import settings
            from app.service.kafka_service import KAFKA_AVAILABLE
            
            if KAFKA_AVAILABLE:
                kafka_service = KafkaService()
                
                # 转换结果为 Kafka 消息格式
                kafka_message = _transform_result_to_kafka_format(
                    form_view=original_form_view,
                    semantic_result=semantic_result,
                    business_result=business_result,
                    request_type=request_type,
                    message_id=message_id,
                    status="success"
                )
                
                # 发送到Kafka主题
                topic = getattr(settings, 'KAFKA_DATA_UNDERSTAND_RESULT_TOPIC', 'data-understanding-responses')
                success = kafka_service.send_message(
                    topic=topic,
                    message=kafka_message,
                    key=message_id or "sync_request"  # 使用message_id或默认key
                )
                
                if success:
                    logger.info(f"同步接口结果已发送到Kafka: topic={topic}")
                else:
                    logger.warning(f"同步接口结果发送到Kafka失败: topic={topic}")
                
                # 关闭Kafka连接
                kafka_service.close()
            else:
                logger.warning(f"Kafka不可用，跳过发送结果到Kafka")
            
        except ImportError:
            # Kafka服务未安装
            logger.warning(f"Kafka服务未安装，跳过发送结果到Kafka")
        except Exception as kafka_error:
            # Kafka发送失败不应该影响返回结果
            logger.error(f"发送结果到Kafka时发生错误: error={str(kafka_error)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 返回结果
        return JSONResponse(content=result, status_code=200)
        
    except Exception as e:
        logger.error(f"同步接口执行失败: error={str(e)}")
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        
        # 发送失败消息到 Kafka
        try:
            _send_failed_kafka_message("sync_request", original_form_view, request_type, message_id, str(e))
        except Exception as kafka_error:
            logger.error(f"发送失败消息到Kafka时发生错误: error={str(kafka_error)}")
        
        return JSONResponse(
            content={"error": f"执行失败: {str(e)}"},
            status_code=500
        )


@DataUnderstandAPIRouter.get(f"{DataUnderstandRouter}/task/{{task_id}}/status")
async def get_task_status_api(
    task_id: str,
    request: Request
):
    """
    查询任务状态接口
    
    Args:
        task_id: 任务ID
    """
    task_service = TaskService()
    task_status = task_service.get_task_status(task_id)
    
    if not task_status:
        return JSONResponse(
            content={"error": "任务不存在"},
            status_code=404
        )
    
    return JSONResponse(content=task_status, status_code=200)


@DataUnderstandAPIRouter.get(f"{DataUnderstandRouter}/task/{{task_id}}/result")
async def get_task_result_api(
    task_id: str,
    request: Request
):
    """
    获取任务结果接口
    
    Args:
        task_id: 任务ID
    """
    task_service = TaskService()
    task_result = task_service.get_task_result(task_id)
    
    if not task_result:
        # 如果任务不存在或未完成，返回任务状态
        task_status = task_service.get_task_status(task_id)
        if not task_status:
            return JSONResponse(
                content={"error": "任务不存在"},
                status_code=404
            )
        else:
            return JSONResponse(
                content={
                    "error": "任务尚未完成",
                    "status": task_status.get("status")
                },
                status_code=400
            )
    
    return JSONResponse(content=task_result, status_code=200)
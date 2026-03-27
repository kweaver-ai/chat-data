# -*- coding: utf-8 -*-
"""
数据视图样例数据查询工具

基于 app.api.af_api.Services.get_data_view_sample_data 封装为 LangChain 工具，
用于根据数据视图 UUID 获取样例数据。
"""

from textwrap import dedent
from typing import Any, Dict, List, Optional, Type

from langchain_core.callbacks import (
    CallbackManagerForToolRun,
    AsyncCallbackManagerForToolRun,
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.pydantic_v1 import validator

from app.api.af_api import Services
from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.errors import ToolFatalError
from app.tools.base import (
    ToolName,
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from app.utils.llm import CustomChatOpenAI
from config import get_settings
from app.utils.password import get_authorization
from app.session.redis_session import RedisHistorySession


_SETTINGS = get_settings()


class DataViewSampleDataArgs(BaseModel):
    """工具入参模型"""

    ids: List[str] = Field(description="数据视图 UUID 列表（form_view_id / entity_id 列表），最多10个")
    limit: int = Field(default=10, description="返回的样例数据条数，默认10条，最大值10条")
    fields: Optional[List[str]] = Field(default=None, description="指定返回的列名列表（可选），如果指定则只返回这些列的数据")

    @validator('ids')
    def validate_ids(cls, v):
        # 检查 None（虽然字段是必填的，但为了安全还是检查）
        if v is None:
            raise ValueError("ids 不能为 None")
        # 检查空列表
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("ids 不能为空列表")
        # 检查数量限制
        if len(v) > 10:
            raise ValueError(f"ids 最多支持10个，当前有 {len(v)} 个")
        # 检查列表中的元素是否都是字符串
        if not all(isinstance(item, str) and item for item in v):
            raise ValueError("ids 中的每个元素必须是非空字符串")
        return v

    @validator('limit')
    def validate_limit(cls, v):
        if v is None:
            return 10
        if not isinstance(v, int):
            raise ValueError("limit 必须是整数")
        if v < 1:
            raise ValueError("limit 必须大于0")
        if v > 10:
            raise ValueError("limit 最大值为10")
        return v

    @validator('fields')
    def validate_fields(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("fields 必须是列表")
        if len(v) == 0:
            return None  # 空列表视为未指定
        # 检查列表中的元素是否都是非空字符串
        if not all(isinstance(item, str) and item for item in v):
            raise ValueError("fields 中的每个元素必须是非空字符串")
        return v


class DataViewSampleDataTool(LLMTool):
    """
    数据视图样例数据查询工具（批量版）

    说明：
    - 给定数据视图 UUID 列表（ids），批量调用 AF 的数据视图样例数据接口，返回各视图的样例数据。
    - 该工具用于获取数据视图的样例数据，帮助用户了解数据结构。
    - 最多支持10个视图的批量查询。
    """

    name: str = "data_view_sample_data_tool"
    description: str = dedent(
        """
        数据视图样例数据查询工具（批量版）：
        - 输入数据视图 UUID 列表（ids），最多10个；
        - 批量调用数据视图样例数据接口，获取各视图的样例数据；
        - 返回批量样例数据结果，供上层链路后续加工使用。
        参数：
        - ids: 数据视图 UUID 列表（form_view_id / entity_id 列表），最多10个
        - limit: 返回的样例数据条数，默认10条，最大值10条
        - fields: 指定返回的列名列表（可选），如果指定则只返回这些列的数据
        """
    )

    args_schema: Type[BaseModel] = DataViewSampleDataArgs

    # 认证与会话相关配置
    token: str = ""
    user_id: str = ""
    background: str = ""

    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None

    # AF 服务封装
    service: Any = None
    headers: Dict[str, str] = {}
    base_url: str = ""  # 可选：用于覆盖默认 AF 地址

    return_direct: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 会话
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)

        # token / headers
        token_value = kwargs.get("token") or self.token
        if token_value:
            self.token = token_value
            self.headers = {"Authorization": self.token}
        else:
            self.headers = {}

        # Service 实例
        self.base_url = kwargs.get("base_url", self.base_url or "")
        self.service = Services(base_url=self.base_url) if self.base_url else Services()

    def _filter_fields(self, result: Dict[str, Any], fields: Optional[List[str]]) -> Dict[str, Any]:
        """
        根据指定的字段列表过滤结果数据。
        
        Args:
            result: 原始结果数据
            fields: 指定的列名列表，如果为 None 或空列表则返回所有列
            
        Returns:
            过滤后的结果数据
        """
        # 如果 fields 为空（None 或空列表），返回所有列
        if not fields or len(fields) == 0:
            return result
        
        if not isinstance(result, dict):
            return result
        
        # 检查是否有 columns 和 data 字段（标准格式）
        if "columns" not in result or "data" not in result:
            # 如果不是标准格式，直接返回
            return result
        
        columns = result.get("columns", [])
        data = result.get("data", [])
        
        if not isinstance(columns, list) or not isinstance(data, list):
            return result
        
        # 构建列名到索引的映射
        column_name_to_index = {}
        for idx, col in enumerate(columns):
            if isinstance(col, dict) and "name" in col:
                column_name_to_index[col["name"]] = idx
        
        # 找到指定字段的索引
        field_indices = []
        filtered_columns = []
        for field in fields:
            if field in column_name_to_index:
                idx = column_name_to_index[field]
                field_indices.append(idx)
                filtered_columns.append(columns[idx])
            else:
                logger.warning(f"[DataViewSampleDataTool] 字段 '{field}' 不存在于数据中，将被忽略")
        
        if not field_indices:
            logger.warning(f"[DataViewSampleDataTool] 指定的字段都不存在，返回空结果")
            result["columns"] = []
            result["data"] = []
            return result
        
        # 过滤数据：只保留指定索引位置的值
        filtered_data = []
        for row in data:
            if isinstance(row, list):
                filtered_row = [row[idx] if idx < len(row) else None for idx in field_indices]
                filtered_data.append(filtered_row)
            else:
                # 如果不是列表格式，保持原样
                filtered_data.append(row)
        
        result["columns"] = filtered_columns
        result["data"] = filtered_data
        
        return result

    def _query_single_sample_data(self, formview_uuid: str, limit: int = 10, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        同步调用底层样例数据接口（单个视图）。
        兼容处理有数据和没数据的返回结果。
        
        Args:
            formview_uuid: 数据视图 UUID
            limit: 返回的样例数据条数，默认10条，最大值10条
            fields: 指定返回的列名列表（可选），如果指定则只返回这些列的数据
        """
        if not formview_uuid:
            raise ToolFatalError("formview_uuid 不能为空")
        
        # 限制 limit 的范围
        limit = max(1, min(10, limit))

        logger.info(f"[DataViewSampleDataTool] start query sample data, formview_uuid={formview_uuid}, limit={limit}, fields={fields}")

        try:
            # Services.get_data_view_sample_data 返回样例数据（dict）
            # 如果数据量为0，会返回空结果并标记 total=0
            result = self.service.get_data_view_sample_data(formview_uuid=formview_uuid, headers=self.headers)
            
            # 确保返回结果格式统一，兼容有数据和没数据的情况
            if not isinstance(result, dict):
                data_list = result if result else []
                if isinstance(data_list, list):
                    # 截取指定条数
                    data_list = data_list[:limit]
                result = {"data": data_list, "total": len(data_list) if isinstance(data_list, list) else 0}
            elif "total" not in result:
                # 如果有数据但没有 total 字段，尝试从 data 字段计算
                if "data" in result:
                    data_list = result["data"]
                    if isinstance(data_list, list):
                        # 截取指定条数
                        data_list = data_list[:limit]
                        result["data"] = data_list
                    result["total"] = len(data_list) if isinstance(data_list, list) else 0
                else:
                    # 如果没有 data 字段，假设整个 result 就是数据
                    data_list = result if isinstance(result, list) else [result]
                    data_list = data_list[:limit]
                    result = {"data": data_list, "total": len(data_list)}
            else:
                # 如果有 total 字段，也需要截取 data 字段
                if "data" in result and isinstance(result["data"], list):
                    original_total = result.get("total", len(result["data"]))
                    result["data"] = result["data"][:limit]
                    # total 保持原始值，表示总数据量，而不是返回的数据量
                    result["total"] = original_total
            
            # 如果指定了 fields 且不为空，过滤列；否则返回所有列
            if fields and len(fields) > 0:
                result = self._filter_fields(result, fields)
            
            logger.info(f"[DataViewSampleDataTool] query success, formview_uuid={formview_uuid}, total={result.get('total', 0)}, returned={len(result.get('data', []))}, columns={len(result.get('columns', []))}")
            
        except Exception as e:
            logger.error(f"[DataViewSampleDataTool] get_data_view_sample_data failed, formview_uuid={formview_uuid}, error={e}")
            raise ToolFatalError(f"获取数据视图样例数据失败 (formview_uuid={formview_uuid}): {e}") from e

        return result

    def _query_sample_data_batch(self, ids: List[str], limit: int = 10, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        批量调用底层样例数据接口。
        兼容处理有数据和没数据的返回结果。
        
        注意：参数验证由 DataViewSampleDataArgs validator 处理，这里只做运行时检查。
        
        Args:
            ids: 数据视图 UUID 列表
            limit: 返回的样例数据条数，默认10条，最大值10条
            fields: 指定返回的列名列表（可选），如果指定则只返回这些列的数据
        """
        if not self.headers:
            raise ToolFatalError("缺少认证信息，请提供有效的 token")
        
        # 运行时检查（validator 已经验证过，这里作为双重保险）
        if not ids:
            raise ToolFatalError("ids 不能为空")
        if len(ids) > 10:
            raise ToolFatalError(f"ids 最多支持10个，当前有 {len(ids)} 个")
        
        # 限制 limit 的范围
        limit = max(1, min(10, limit))

        logger.info(f"[DataViewSampleDataTool] start batch query sample data, ids={ids}, count={len(ids)}, limit={limit}, fields={fields}")

        batch_result = {}
        for formview_uuid in ids:
            try:
                result = self._query_single_sample_data(formview_uuid=formview_uuid, limit=limit, fields=fields)
                batch_result[formview_uuid] = result
            except Exception as e:
                # 单个视图失败时，记录错误但继续处理其他视图
                logger.error(f"[DataViewSampleDataTool] failed to query formview_uuid={formview_uuid}, error={e}")
                batch_result[formview_uuid] = {
                    "error": str(e),
                    "data": [],
                    "total": 0,
                    "empty": True
                }

        logger.info(f"[DataViewSampleDataTool] batch query completed, success={len([r for r in batch_result.values() if 'error' not in r])}, total={len(batch_result)}")
        
        return batch_result

    @construct_final_answer
    def _run(
        self,
        ids: List[str],
        limit: int = 10,
        fields: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """
        同步执行接口（LangChain 同步工具入口）
        """
        result = self._query_sample_data_batch(ids=ids, limit=limit, fields=fields)
        # 不写入 redis，仅返回结果
        return result

    @async_construct_final_answer
    async def _arun(
        self,
        ids: List[str],
        limit: int = 10,
        fields: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        异步执行接口（LangChain 异步工具入口）
        """
        # 这里底层调用是同步的，为兼容直接放到线程池 / 简单同步调用都可以
        # 目前为了简单直接复用同步逻辑
        result = self._query_sample_data_batch(ids=ids, limit=limit, fields=fields)
        return result


    # -------- 作为独立异步 API 的封装 --------
    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
        cls,
        params: dict,
    ):
        """
        将工具转换为异步 API 类方法，供外部 HTTP 调用：

        请求示例 JSON：
        {
          "llm": { ... 可选，沿用其他工具配置 ... },
          "auth": {
            "auth_url": "http://xxx",   // 可选，获取 token 时使用
            "user": "xxx",              // 可选
            "password": "xxx",          // 可选
            "token": "Bearer xxx",      // 推荐，直接透传 AF 的 token
            "user_id": "123456"         // 可选
          },
          "config": {
            "base_url": "http://af-data-view-host",  // 可选，覆盖默认 DATA_VIEW_URL
            "session_type": "redis"                  // 目前仅占位
          },
          "ids": ["xxx", "yyy"],                     // 必填，数据视图 UUID 列表，最多10个
          "limit": 10,                                // 可选，返回的样例数据条数，默认10条，最大值10条
          "fields": ["column1", "column2"]            // 可选，指定返回的列名列表，如果指定则只返回这些列的数据
        }
        """
        # LLM 这里实际上不会被使用，但为了与现有框架保持一致，仍按约定创建
        llm_dict = {
            "model_name": _SETTINGS.TOOL_LLM_MODEL_NAME,
            "openai_api_key": _SETTINGS.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": _SETTINGS.TOOL_LLM_OPENAI_API_BASE,
        }
        llm_dict.update(params.get("llm", {}))
        llm = CustomChatOpenAI(**llm_dict)

        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")

        # 如果没有直接传 token，则尝试根据 user/password 获取
        if not token or token == "''":
            user = auth_dict.get("user", "")
            password = auth_dict.get("password", "")
            if not user or not password:
                raise ToolFatalError("缺少 token，且未提供 user/password 获取 token")
            try:
                token = get_authorization(auth_dict.get("auth_url", _SETTINGS.AF_DEBUG_IP), user, password)
            except Exception as e:
                logger.error(f"[DataViewSampleDataTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e

        config_dict = params.get("config", {})

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
            base_url=config_dict.get("base_url", ""),
        )

        # 获取 ids 参数
        ids = params.get("ids")
        
        # 如果 ids 是 None（未提供），报错
        if ids is None:
            raise ToolFatalError("ids 是必填参数")
        
        # 确保 ids 是列表类型
        if not isinstance(ids, list):
            ids = [ids]
        
        # 检查空列表（validator 会处理，但这里也检查一下以提供更清晰的错误信息）
        if len(ids) == 0:
            raise ToolFatalError("ids 不能为空列表")
        
        # 检查数量限制（validator 会处理，但这里也检查一下以提供更清晰的错误信息）
        if len(ids) > 10:
            raise ToolFatalError(f"ids 最多支持10个，当前有 {len(ids)} 个")

        # 获取 limit 参数，默认10
        limit = params.get("limit", 10)
        if limit is None:
            limit = 10
        # 限制范围
        limit = max(1, min(10, int(limit)))

        # 获取 fields 参数，可选
        fields = params.get("fields")
        if fields is not None and not isinstance(fields, list):
            fields = [fields] if fields else None

        # 直接走异步接口
        res = await tool.ainvoke(input={"ids": ids, "limit": limit, "fields": fields})
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema，便于自动注册为 HTTP API。"""
        return {
            "post": {
                "summary": "data_view_sample_data_tool",
                "description": "根据数据视图 UUID 列表批量调用 AF 数据视图样例数据接口，返回各视图的样例数据。",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "llm": {
                                        "type": "object",
                                        "description": "LLM 配置参数（本工具不会真正使用，仅保持接口一致）",
                                    },
                                    "auth": {
                                        "type": "object",
                                        "description": "认证参数",
                                        "properties": {
                                            "auth_url": {"type": "string"},
                                            "user": {"type": "string"},
                                            "password": {"type": "string"},
                                            "token": {"type": "string"},
                                            "user_id": {"type": "string"},
                                        },
                                    },
                                    "config": {
                                        "type": "object",
                                        "description": "工具配置参数",
                                        "properties": {
                                            "base_url": {
                                                "type": "string",
                                                "description": "AF 数据视图服务基础 URL（可选）",
                                            },
                                            "session_type": {
                                                "type": "string",
                                                "description": "会话类型，目前仅占位",
                                                "enum": ["in_memory", "redis"],
                                                "default": "redis",
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "背景信息（可选，不影响结果）",
                                            },
                                        },
                                    },
                                    "ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "数据视图 UUID 列表（form_view_id / entity_id 列表），最多10个",
                                        "maxItems": 10,
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "返回的样例数据条数，默认10条，最大值10条",
                                        "minimum": 1,
                                        "maximum": 10,
                                        "default": 10,
                                    },
                                    "fields": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "指定返回的列名列表（可选），如果指定则只返回这些列的数据",
                                    },
                                },
                                "required": ["ids"],
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {},
                                }
                            }
                        },
                    }
                },
            }
        }

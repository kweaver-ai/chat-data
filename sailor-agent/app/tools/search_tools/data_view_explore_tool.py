# -*- coding: utf-8 -*-
"""
数据视图探查结果查询工具（批量版）

基于 app.api.af_api.Services.get_data_explore_batch 封装为 LangChain 工具，
用于按多个数据视图 ID 批量获取探查报告中的字段探查结果。
"""

from textwrap import dedent
from typing import Any, Dict, Optional, Type, List

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


class DataViewExploreArgs(BaseModel):
    """工具入参模型"""

    ids: List[str] = Field(description="数据视图 ID 列表（form_view_id / entity_id 列表）")
    field_ids: Optional[List[str]] = Field(default=None,
                                           description="字段 ID 列表（可选），如果指定则只返回这些字段的探查结果")
    rule_names: Optional[List[str]] = Field(default=None,
                                            description="规则名称列表（可选），如果指定则只返回匹配这些规则名称的探查结果，参数值与 rule_name 匹配")
    rule_scope: Optional[str] = Field(default=None,
                                      description="规则作用域（可选），指定 rule_names 过滤的范围：'metadata' 表示只过滤元数据探查详情（explore_metadata_details），'field' 表示只过滤字段级探查详情（explore_field_details），None 表示同时过滤两者")

    @validator('rule_scope')
    def validate_rule_scope(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("rule_scope 必须是字符串")
        v_lower = v.lower()
        if v_lower not in ['metadata', 'field']:
            raise ValueError("rule_scope 必须是 'metadata' 或 'field'")
        return v_lower


class DataViewExploreTool(LLMTool):
    """
    数据视图探查结果查询工具（批量版）

    说明：
    - 给定数据视图 ID 列表（ids），调用 AF 的批量数据视图探查接口，返回各视图的字段探查结果。
    - 该工具本身不做 LLM 推理，只负责把结构化探查结果返回给上层链路。
    """

    name: str = "data_view_explore_tool"
    description: str = dedent(
        """
        数据视图探查结果查询工具：
        - 输入数据视图 ID 列表（ids）；
        - 调用批量数据视图探查接口，获取各视图的字段探查结果；
        - 返回服务端原始批量探查结果，供上层链路后续加工使用。
        参数：
        - ids: 数据视图 ID 列表（form_view_id / entity_id 列表）
        - field_ids: 字段 ID 列表（可选），如果指定则只返回这些字段的探查结果
        - rule_names: 规则名称列表（可选），如果指定则只返回匹配这些规则名称的探查结果
        - rule_scope: 规则作用域（可选），'metadata' 表示只过滤元数据探查详情，'field' 表示只过滤字段级探查详情，None 表示同时过滤两者
        """
    )

    args_schema: Type[BaseModel] = DataViewExploreArgs

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

    def _filter_explore_result(
            self,
            result: Dict[str, Any],
            field_ids: Optional[List[str]] = None,
            rule_names: Optional[List[str]] = None,
            rule_scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据字段ID和规则名称过滤探查结果。

        Args:
            result: 原始探查结果
            field_ids: 字段ID列表，如果为None或空列表则不过滤字段
            rule_names: 规则名称列表，如果为None或空列表则不过滤规则
            rule_scope: 规则作用域，'metadata' 表示只过滤元数据探查详情，'field' 表示只过滤字段级探查详情，None 表示同时过滤两者

        Returns:
            过滤后的探查结果
        """
        if not isinstance(result, dict):
            return result

        # 处理 reports 结构: {"reports": [...]}
        if "reports" not in result or not isinstance(result["reports"], list):
            return result

        reports = result["reports"]

        filtered_reports = []
        for report in reports:
            if not isinstance(report, dict):
                filtered_reports.append(report)
                continue

            report_data = report.get("report", {})
            if not isinstance(report_data, dict):
                filtered_reports.append(report)
                continue

            # 如果指定了 rule_names，只返回匹配的探查结果层级
            if rule_names and len(rule_names) > 0:
                # 删除 overview（因为它是探查结果的一部分，但不包含 rule_name）
                if "overview" in report_data:
                    del report_data["overview"]

                # 过滤元数据级探查详情
                # 只有当 rule_scope 为 None 或 'metadata' 时才处理元数据级
                if rule_scope is None or rule_scope == 'metadata':
                    if "explore_metadata_details" in report_data:
                        metadata_details = report_data["explore_metadata_details"]
                        if isinstance(metadata_details, dict) and "explore_details" in metadata_details:
                            explore_details = metadata_details["explore_details"]
                            if isinstance(explore_details, list):
                                filtered_details = [
                                    detail for detail in explore_details
                                    if isinstance(detail, dict) and detail.get("rule_name") in rule_names
                                ]
                                if filtered_details:
                                    metadata_details["explore_details"] = filtered_details
                                else:
                                    # 如果没有匹配的规则，删除该层级
                                    del report_data["explore_metadata_details"]
                else:
                    # 如果 rule_scope 是 'field'，删除元数据级探查详情
                    if "explore_metadata_details" in report_data:
                        del report_data["explore_metadata_details"]

                # 过滤字段级探查详情
                # 只有当 rule_scope 为 None 或 'field' 时才处理字段级
                if rule_scope is None or rule_scope == 'field':
                    if "explore_field_details" in report_data:
                        field_details = report_data["explore_field_details"]
                        if isinstance(field_details, list):
                            filtered_field_details = []
                            for field_detail in field_details:
                                if not isinstance(field_detail, dict):
                                    continue

                                field_id = field_detail.get("field_id")

                                # 如果指定了 field_ids，只保留匹配的字段
                                if field_ids and len(field_ids) > 0:
                                    if field_id not in field_ids:
                                        continue

                                # 过滤该字段下的规则
                                details = field_detail.get("details", [])
                                if isinstance(details, list) and len(details) > 0:
                                    filtered_details = [
                                        detail for detail in details
                                        if isinstance(detail, dict) and detail.get("rule_name") in rule_names
                                    ]
                                    # 只有当过滤后有匹配的规则时，才保留该字段
                                    if filtered_details:
                                        field_detail["details"] = filtered_details
                                        filtered_field_details.append(field_detail)
                                # 如果 details 不是列表、为空或为 None，不保留该字段（因为没有匹配的规则）

                            if filtered_field_details:
                                report_data["explore_field_details"] = filtered_field_details
                            else:
                                # 如果没有匹配的字段，删除该层级
                                if "explore_field_details" in report_data:
                                    del report_data["explore_field_details"]
                else:
                    # 如果 rule_scope 是 'metadata'，删除字段级探查详情
                    if "explore_field_details" in report_data:
                        del report_data["explore_field_details"]

                # 删除其他探查详情层级（explore_row_details, explore_view_details）
                # 因为这些层级不包含 rule_name，所以如果指定了 rule_names，就不返回它们
                if "explore_row_details" in report_data:
                    del report_data["explore_row_details"]
                if "explore_view_details" in report_data:
                    del report_data["explore_view_details"]
            else:
                # 如果没有指定 rule_names 和 rule_scope，但指定了 field_ids
                # 只返回 explore_metadata_details 和 explore_field_details 中指定字段的探查结果
                if field_ids and len(field_ids) > 0:
                    # 删除其他探查详情层级（overview, explore_row_details, explore_view_details）
                    if "overview" in report_data:
                        del report_data["overview"]
                    if "explore_row_details" in report_data:
                        del report_data["explore_row_details"]
                    if "explore_view_details" in report_data:
                        del report_data["explore_view_details"]

                    # explore_metadata_details 保留全部（因为它是元数据级，不涉及字段过滤）
                    # explore_field_details 只保留匹配 field_ids 的字段
                    if "explore_field_details" in report_data:
                        field_details = report_data["explore_field_details"]
                        if isinstance(field_details, list):
                            filtered_field_details = [
                                field_detail for field_detail in field_details
                                if isinstance(field_detail, dict) and field_detail.get("field_id") in field_ids
                            ]
                            if filtered_field_details:
                                report_data["explore_field_details"] = filtered_field_details
                            else:
                                # 如果没有匹配的字段，删除该层级
                                if "explore_field_details" in report_data:
                                    del report_data["explore_field_details"]
                else:
                    # 如果没有指定 rule_names、rule_scope 和 field_ids，保留所有探查结果
                    # 不做任何过滤
                    pass

                filtered_reports.append(report)

        # 更新结果
        result["reports"] = filtered_reports

        return result

    def _query_explore_result(
            self,
            ids: List[str],
            field_ids: Optional[List[str]] = None,
            rule_names: Optional[List[str]] = None,
            rule_scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步调用底层批量探查接口。
        """
        if not ids:
            raise ToolFatalError("ids 不能为空")
        if not self.headers:
            raise ToolFatalError("缺少认证信息，请提供有效的 token")

        logger.info(
            f"[DataViewExploreTool] start batch query explore result, ids={ids}, field_ids={field_ids}, rule_names={rule_names}, rule_scope={rule_scope}")

        try:
            # Services.get_data_explore_batch 返回批量探查结果（dict）
            batch_result = self.service.get_data_explore_batch(entity_ids=ids, headers=self.headers)
        except Exception as e:
            logger.error(f"[DataViewExploreTool] get_data_explore_batch failed, ids={ids}, error={e}")
            raise ToolFatalError(f"批量获取数据视图探查结果失败: {e}") from e

        logger.info(f"[DataViewExploreTool] batch success, ids={ids}")

        # 如果指定了 field_ids 或 rule_names，进行过滤
        if (field_ids and len(field_ids) > 0) or (rule_names and len(rule_names) > 0):
            batch_result = self._filter_explore_result(batch_result, field_ids=field_ids, rule_names=rule_names,
                                                       rule_scope=rule_scope)
            logger.info(
                f"[DataViewExploreTool] filtered result with field_ids={field_ids}, rule_names={rule_names}, rule_scope={rule_scope}")

        return batch_result

    @construct_final_answer
    def _run(
            self,
            ids: List[str],
            field_ids: Optional[List[str]] = None,
            rule_names: Optional[List[str]] = None,
            rule_scope: Optional[str] = None,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """
        同步执行接口（LangChain 同步工具入口）
        """
        result = self._query_explore_result(ids=ids, field_ids=field_ids, rule_names=rule_names, rule_scope=rule_scope)
        # 不写入 redis，仅返回结果
        return result

    @async_construct_final_answer
    async def _arun(
            self,
            ids: List[str],
            field_ids: Optional[List[str]] = None,
            rule_names: Optional[List[str]] = None,
            rule_scope: Optional[str] = None,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        异步执行接口（LangChain 异步工具入口）
        """
        # 这里底层调用是同步的，为兼容直接放到线程池 / 简单同步调用都可以
        # 目前为了简单直接复用同步逻辑
        result = self._query_explore_result(ids=ids, field_ids=field_ids, rule_names=rule_names, rule_scope=rule_scope)
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
          "ids": ["id1", "id2"],                    // 必填，数据视图 ID 列表
          "field_ids": ["field1", "field2"],         // 可选，字段 ID 列表，如果指定则只返回这些字段的探查结果
          "rule_names": ["重复值检查", "最大值"],      // 可选，规则名称列表，如果指定则只返回匹配这些规则名称的探查结果
          "rule_scope": "metadata"                   // 可选，规则作用域：'metadata' 表示只过滤元数据探查详情，'field' 表示只过滤字段级探查详情，不指定则同时过滤两者
        }
        """
        # LLM 这里实际上不会被使用，但为了与现有框架保持一致，仍按约定创建
        from app.utils.llm_params import merge_llm_params
        llm_dict = {
            "model_name": _SETTINGS.TOOL_LLM_MODEL_NAME,
            "openai_api_key": _SETTINGS.TOOL_LLM_OPENAI_API_KEY,
            "openai_api_base": _SETTINGS.TOOL_LLM_OPENAI_API_BASE,
        }
        llm_dict = merge_llm_params(llm_dict, params.get("llm", {}) or {})
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
                logger.error(f"[DataViewExploreTool] get token error: {e}")
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

        # 兼容：优先使用 ids，如未提供则尝试从 view_id 构造
        ids = params.get("ids")
        if not ids:
            view_id = params.get("view_id", "")
            if not view_id:
                raise ToolFatalError("ids 是必填参数（也可提供单个 view_id 以兼容旧用法）")
            ids = [view_id]

        # 获取 field_ids、rule_names 和 rule_scope 参数
        field_ids = params.get("field_ids")
        if field_ids is not None and not isinstance(field_ids, list):
            field_ids = [field_ids] if field_ids else None

        # 兼容 rule_name（单数）和 rule_names（复数）
        rule_names = params.get("rule_names")
        if rule_names is None:
            # 兼容旧版本：如果提供了单个 rule_name，转换为列表
            rule_name = params.get("rule_name")
            if rule_name is not None:
                rule_names = [rule_name] if isinstance(rule_name, str) else rule_name
        if rule_names is not None and not isinstance(rule_names, list):
            rule_names = [rule_names] if rule_names else None

        rule_scope = params.get("rule_scope")
        if rule_scope is not None:
            rule_scope = rule_scope.lower() if isinstance(rule_scope, str) else None
            if rule_scope not in [None, 'metadata', 'field']:
                raise ToolFatalError("rule_scope 必须是 'metadata' 或 'field'")

        # 直接走异步接口
        res = await tool.ainvoke(
            input={"ids": ids, "field_ids": field_ids, "rule_names": rule_names, "rule_scope": rule_scope})
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema，便于自动注册为 HTTP API。"""
        return {
            "post": {
                "summary": "data_view_explore_tool",
                "description": "根据数据视图 ID 调用 AF 数据视图探查接口，返回 explore_field_details 列表。",
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
                                        "description": "数据视图 ID 列表（form_view_id / entity_id 列表）",
                                    },
                                    "field_ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "字段 ID 列表（可选），如果指定则只返回这些字段的探查结果",
                                    },
                                    "rule_names": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "规则名称列表（可选），如果指定则只返回匹配这些规则名称的探查结果，参数值与 rule_name 匹配",
                                    },
                                    "rule_name": {
                                        "type": "string",
                                        "description": "单个规则名称（兼容旧版本，将被转换为列表）",
                                    },
                                    "rule_scope": {
                                        "type": "string",
                                        "description": "规则作用域（可选），指定 rule_names 过滤的范围：'metadata' 表示只过滤元数据探查详情（explore_metadata_details），'field' 表示只过滤字段级探查详情（explore_field_details），不指定则同时过滤两者",
                                        "enum": ["metadata", "field"],
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


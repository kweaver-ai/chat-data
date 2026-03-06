# -*- coding: utf-8 -*-
import json
import traceback
from textwrap import dedent
from typing import Optional, Type, Any, Dict, List
from collections import OrderedDict
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun

from data_retrieval.api.base import API, HTTPMethod
from data_retrieval.logs.logger import logger
from data_retrieval.sessions import BaseChatHistorySession
from app.utils.password import get_authorization
from data_retrieval.errors import ToolFatalError
from app.session.redis_session import RedisHistorySession
from app.session.in_memory_session import InMemoryChatSession
from app.tools.base import ToolMultipleResult
from config import settings

from data_retrieval.tools.base import (
    ToolName,
    ToolResult,
    AFTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator
)


# settings = get_settings()


def CreateSession(session_type: str):
    """创建会话对象，使用本地的 settings 配置"""
    if session_type == "redis":
        return RedisHistorySession()
    elif session_type == "in_memory":
        return InMemoryChatSession()
    else:
        raise ValueError(f"不支持的 session_type: {session_type}")


class AfSailorToolModel(BaseModel):
    question: str = Field(..., description="自然语言问题或者自然语言表述。")
    extraneous_information: str = Field(
        default="",
        description="用户在多轮对话中重复强调的信息"
    )

class AfSailorToolResult(ToolResult):
    def __init__(
        self,
        cites=None,
        table: str | dict = None,
        new_table: str | dict = None,
        df2json: str = None,
        text: str = None,
        explain: str = None,
        chart: str | dict = None,
        new_chart: str | dict = None,
        related_info: str | dict = None
    ):
        super().__init__(
            cites=cites,
            table=table,
            new_table=new_table,
            df2json=df2json,
            text=text,
            explain=explain,
            chart=chart,
            new_chart=new_chart
        )
        self.related_info = related_info

    def __repr__(self):
        return dedent(
            f"""
             AfSailorToolResult(
                 cites={self.cites},
                 table={self.table}, 
                 df2json={self.df2json}, 
                 text={self.text}, 
                 explain={self.explain},
                 chart={self.chart},
                 new_table={self.new_table},
                 new_chart={self.new_chart},
                 related_info={self.related_info}
             )
        """
        )

    def to_ori_json(self):
        result = super().to_ori_json()
        result["related_info"] = self.related_info
        return result

    def to_json(self):
        base_result = super().to_json()
        base_result["result"]["res"]["related_info"] = self.related_info
        return base_result

class AfSailorTool(AFTool):
    name: str = ToolName.from_sailor.value
    description: str = dedent("""
    这是一个数据搜索工具：工具可以对问题进行数据资源元数据搜索，并返回搜索结果，调用方式是：search(question, extraneous_information),其中 question 参数是用户所问的问题, 不允许结合上下文总结成新问题
    特别注意: 
    - 如果对话上下文中包含了引用的数据资源缓存，在用其他工具获取数据前，你需要根据数据资源的名称和描述判断当前的 Question 是否能用 `缓存的数据资源` 来回答，不满足或不确定时需要重新搜索数据
    - 本工具在结果输出时，可能会用类似 "<i slice_idx=0>1</i> 这样的格式来表示数据资源的编号，请保持这样的格式
    """)
    args_schema: Type[BaseModel] = AfSailorToolModel
    parameter: dict = {}
    session: Optional[BaseChatHistorySession] = None
    session_type: str = "redis"

    def __init__(
        self,
        parameter: dict,
        *args,
        **kwargs: Any
    ):
        # 从 kwargs 中移除 token，避免传递给基类导致 Pydantic 验证错误
        kwargs_without_token = {k: v for k, v in kwargs.items() if k != "token"}
        super().__init__(*args, **kwargs_without_token)
        logger.info(f'parameter: {parameter}')
        self.parameter = parameter
        if kwargs.get("session") is None:
            session_type = kwargs.get("session_type", self.session_type)
            self.session = CreateSession(session_type)
        if not self.parameter.get("direct_qa", ""):
            self.description = "这是一个数据搜索工具：工具可以对问题进行数据资源搜索，并返回搜索结果"
        # token 作为实例属性，从 parameter 中获取
        # 使用 object.__setattr__ 绕过 Pydantic 的字段验证
        object.__setattr__(self, 'token', self.parameter.get("token", ""))
        logger.info(f'token: {self.token}')


    def _service(
        self,
        url: str = "",
        **kwargs: Any
    ):
        if not url:
            url = settings.SAILOR_URL + "/api/af-sailor/v1/assistant/qa"
        if settings.AF_DEBUG_IP:
            url = settings.AF_DEBUG_IP + "/api/af-sailor/v1/assistant/qa"
        
        question = kwargs.get("question", "")
        if not question:
            logger.warning(f"question 参数为空或不存在，kwargs: {kwargs}")
            raise ValueError("question 参数是必需的，不能为空")
        
        self.parameter["query"] = question
        self.parameter["af_editions"] = kwargs.get("af_editions", "catalog")
        extraneous_info = kwargs.get("extraneous_information")
        if extraneous_info is not None and extraneous_info:
            self.parameter["query"] += extraneous_info
        
        logger.debug(f"构建的 query: {self.parameter['query']}")
        
        api = API(
            url=url,
            method=HTTPMethod.POST,
            headers={"Authorization": self.token},
            payload=self.parameter
        )
        return api

    def _parser(
        self,
        result: AfSailorToolResult
    ):
        # 刷新结果缓存key
        self.refresh_result_cache_key()
        logger.info(f"_parser 调用 - 对象ID: {id(self)}, 新缓存键: {self._result_cache_key}")

        # 把 result.cites 转成 ordered_dict
        result.cites = [OrderedDict(cite) for cite in result.cites]
        res_json = {
            "text": result.text,
            # "related_info": result.related_info,
            "cites": result.cites,
            "result_cache_key": self._result_cache_key
        }
        # 将执行结果保存，暂时支持 redis
        try:
            logger.info(f"准备调用 add_agent_logs，session_id: {self._result_cache_key}")
            logger.info(f"session 对象类型: {type(self.session)}")
            logger.info(f"session 对象: {self.session}")
            
            # 检查 session 是否有 client 属性
            if hasattr(self.session, 'client'):
                logger.info(f"session.client 存在，类型: {type(self.session.client)}")
                # 尝试测试 Redis 连接
                try:
                    ping_result = self.session.client.ping()
                    logger.info(f"Redis ping 结果: {ping_result}")
                except Exception as ping_e:
                    logger.error(f"Redis ping 失败: {ping_e}")
            else:
                logger.warning("session 对象没有 client 属性")
            
            # 检查日志数据
            logger.info(f"准备写入的 logs 数据大小: {len(json.dumps(res_json, ensure_ascii=False))} 字节")
            logger.debug(f"准备写入的 logs 内容: {res_json}")
            
            result = self.session.add_agent_logs(
                session_id=self._result_cache_key,
                logs=res_json
            )
            logger.info(f"add_agent_logs 执行完成，返回值: {result}")
            
            # 验证数据是否真的写入了 Redis
            try:
                if hasattr(self.session, 'get_agent_logs'):
                    retrieved = self.session.get_agent_logs(self._result_cache_key)
                    if retrieved:
                        logger.info(f"验证：成功从 Redis 读取数据，数据大小: {len(json.dumps(retrieved, ensure_ascii=False))} 字节")
                    else:
                        logger.warning(f"验证：从 Redis 读取的数据为空，可能写入失败")
                elif hasattr(self.session, 'client'):
                    # 直接使用 client 验证
                    retrieved = self.session.client.get(self._result_cache_key)
                    if retrieved:
                        logger.info(f"验证：成功从 Redis 读取数据（直接使用 client），数据大小: {len(retrieved)} 字节")
                    else:
                        logger.warning(f"验证：从 Redis 读取的数据为空（直接使用 client），可能写入失败")
            except Exception as verify_e:
                logger.error(f"验证 Redis 数据时出错: {verify_e}")
                
        except Exception as e:
            logger.error(f"add_agent_logs 执行失败: {e}")
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
            # 不抛出异常，避免影响主流程，但记录错误

        # 删除 cites 中的子图信息，防止大模型看到
        for cite in res_json.get("cites", []):
            if "connected_subgraph" in cite:
                del cite["connected_subgraph"]

        return res_json

    @construct_final_answer
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        *args,
        **kwargs: Any
    ):
        try:
            api = self._service(**kwargs)
            result = api.call()
            if isinstance(result, str):
                result = json.loads(result)
            logger.debug(f"Search API Response: {result}")
            result = AfSailorToolResult(**result["result"]["res"])
            result = self._parser(result)
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.info(f"Sailor工具执行错误，实际错误为{tb_str}")
            result = AfSailorToolResult(
                text=["抱歉，可能由于网络延迟或当前服务器繁忙，当前回答尚未完成。"]
            ).to_json()
        return result

    @async_construct_final_answer
    async def _arun(
        self,
        run_manager: Optional[AsyncCallbackManagerForToolRun],
        *args,
        **kwargs: Any
    ):
        try:
            api = self._service(**kwargs)
            result = await api.call_async()
            logger.info(f'type of search tool result: {type(result)}')
            logger.info(f'search tool result: {result}')

            if not result:
                return {
                    "text": ["没有找到对应的数据资源"],
                }
            if isinstance(result, str):
                result = json.loads(result)
            logger.debug(f"Search API Response: {result}")
            result = AfSailorToolResult(**result.get("result", {}).get("res", {}))
            result = self._parser(result)
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.info(f"Sailor工具执行错误，实际错误为{tb_str}")
            result = AfSailorToolResult(
                text=["工具执行错误，请重新提问。"]
            ).to_json()
        return result
    
    def handle_result(
            self,
            result_cache_key: str,
            log: Dict[str, Any],
            ans_multiple: ToolMultipleResult
    ) -> None:
        logger.info(f"handle_result 调用 - 对象ID: {id(self)}, 当前缓存键: {self._result_cache_key}")
        if self.session:
            tool_res = self.session.get_agent_logs(
                result_cache_key
            )
            if tool_res:
                log["result"] = tool_res

                cites_cache = []
                for cite in tool_res.get("cites", []):
                    cc = {
                        "id": cite.get("id", ""),
                        "type": cite.get("type", ""),
                        "title": cite.get("title", ""),
                    }
                    cites_cache.append(cc)

                ans_multiple.sailor_search_result = cites_cache
                ans_multiple.text = tool_res.get("text", [])

                ans_multiple.cache_keys[result_cache_key] = {
                    "tool_name": self.name,
                    "result_cache_key": result_cache_key,
                    "datasource_num": len(tool_res.get("cites", []))
                }

    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
            cls,
            params: dict
    ):
        resources = params.get('resources', {})
        parameters = resources.get('parameters', {})
        auth_dict = params.get("auth", {})
        token = resources.get('token', '')
        logger.info(f"resources.get('token', '')={token}")
        if token:
            parameters["token"] = token
        if not token or token == "''":
            # user = auth_dict.get("user", "")
            # password = auth_dict.get("password", "")
            # try:
            #     token = get_authorization(auth_dict.get("auth_url", settings.AF_DEBUG_IP), user, password)
            # except Exception as e:
            #     logger.error(f"Error: {e}")
            #     raise ToolFatalError(reason="获取 token 失败", detail=e) from e
            user = resources.get("user", "")
            password = resources.get("password", "")
            auth_url = resources.get("auth_url", settings.AF_DEBUG_IP)
            parameters['user'] = user
            parameters['password'] = password
            parameters['auth_url'] = auth_url

            try:
                parameters["token"] = get_authorization(auth_dict.get("auth_url", settings.AF_DEBUG_IP), user, password)
            except Exception as e:
                logger.error(f"Error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e

        config_dict = params.get("config", {})
        parameters.update(config_dict)
        tool = cls(parameter=parameters)

        # Input Params
        input_params = params.get("input", {})
        logger.info(f"input_params: {input_params}")
        
        # 确保 input 是字典格式
        if not isinstance(input_params, dict):
            logger.warning(f"input_params 不是字典格式: {type(input_params)}, 值: {input_params}")
            input_params = {}
        
        try:
            # invoke tool - LangChain 会根据 args_schema 验证并展开参数
            res = await tool.ainvoke(input=input_params)
            return res
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(f"调用工具失败: {e}, 详细错误: {tb_str}")
            raise

    @staticmethod
    async def get_api_schema():
        """获取 API Schema"""
        return {
            "post": {
                "summary": ToolName.from_sailor.value,
                "description": "这是一个数据搜索工具：工具可以对问题进行数据资源元数据搜索，并返回搜索结果",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "resources": {
                                        "type": "object",
                                        "description": "资源配置信息",
                                        "properties": {
                                            "parameters": {
                                                "type": "object",
                                                "description": "资源配置信息"
                                            },
                                            "auth_url": {
                                                "type": "string",
                                                "description": "认证服务URL"
                                            },
                                            "user": {
                                                "type": "string",
                                                "description": "用户名"
                                            },
                                            "password": {
                                                "type": "string",
                                                "description": "密码"
                                            },
                                            "token": {
                                                "type": "string",
                                                "description": "认证令牌，如提供则无需用户名和密码"
                                            }
                                        },
                                        "required": ["parameters"]
                                    },
                                    "config": {
                                        "type": "object",
                                        "description": "工具配置参数",
                                        "properties": {
                                            "direct_qa": {
                                                "type": "string",
                                                "description": "背景信息"
                                            },
                                            "session_type": {
                                                "type": "string",
                                                "description": "会话类型",
                                                "enum": ["in_memory", "redis"],
                                                "default": "in_memory"
                                            },
                                            "session_id": {
                                                "type": "string",
                                                "description": "会话ID"
                                            }
                                        }
                                    },
                                    "input": {
                                        "type": "object",
                                        "description": "输入参数",
                                        "properties": {
                                            "question": {
                                                "type": "string",
                                                "description": "自然语言问题或者自然语言表述"
                                            },
                                            "extraneous_information": {
                                                "type": "string",
                                                "description": "用户在多轮对话中重复强调的信息",
                                                "default": ""
                                            },
                                            "af_editions": {
                                                "type": "string",
                                                "description": "数据版本类型，数据目录、数据资源",
                                                "default": "catalog"
                                            },
                                        },
                                        "required": ["question"]
                                    }
                                },
                                "required": ["resources", "input"]
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
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        }


# class MultiQuerySearchToolModel(BaseModel):
#     queries: List[str] = Field(..., description="搜索词列表")
#     extraneous_information: str = Field(
#         default="",
#         description="用户在多轮对话中重复强调的信息"
#     )
#
#
# class MultiQuerySearchTool(AFTool):
#     name: str = "multi_query_search"
#     description: str = dedent("""
#     这是一个支持多个搜索词的数据搜索工具：工具可以对多个问题进行相关数据资源、字段、部门、信息系统的搜索，并返回搜索结果，调用方式是：search(query, extraneous_information),其中 query 参数是用户所问的问题, 不允许结合上下文总结成新问题
#     特别注意:
#     - 如果对话上下文中包含了引用的数据资源缓存，在用其他工具获取数据前，你需要根据数据资源的名称和描述判断当前的 Query 是否能用 `缓存的数据资源` 来回答，不满足或不确定时需要重新搜索数据
#     - 本工具在结果输出时，可能会用类似 "<i slice_idx=0>1</i> 这样的格式来表示数据资源的编号，请保持这样的格式
#     """)
#     args_schema: Type[BaseModel] = MultiQuerySearchToolModel
#     parameter: dict = {}
#     session: Optional[BaseChatHistorySession] = None
#     session_type: str = "redis"
#
#     def __init__(
#             self,
#             parameter: dict,
#             *args,
#             **kwargs: Any
#     ):
#         super().__init__(*args, **kwargs)
#         self.parameter = parameter
#         if kwargs.get("session") is None:
#             session_type = kwargs.get("session_type", self.session_type)
#             self.session = CreateSession(session_type)
#         if not self.parameter.get("direct_qa", ""):
#             self.description = "这是一个支持多个搜索词的数据搜索工具：工具可以对多个问题进行相关数据资源、字段、部门、信息系统的搜索，并返回搜索结果"
#
#     def _service(
#             self,
#             url: str = "",
#             query: str = "",
#             **kwargs: Any
#     ):
#         if not url:
#             url = settings.SAILOR_URL + "/api/af-sailor/v1/assistant/qa"
#         if settings.AF_DEBUG_IP:
#             url = settings.AF_DEBUG_IP + "/api/af-sailor/v1/assistant/qa"
#         self.parameter["query"] = query
#         if kwargs.get("extraneous_information") is not None:
#             self.parameter["query"] += kwargs["extraneous_information"]
#         api = API(
#             url=url,
#             method=HTTPMethod.POST,
#             headers={"Authorization": self.parameter["token"]},
#             payload=self.parameter
#         )
#         return api
#
#     def _parser(
#             self,
#             result: AfSailorToolResult
#     ):
#         self.refresh_result_cache_key()
#         logger.info(f"_parser 调用 - 对象ID: {id(self)}, 新缓存键: {self._result_cache_key}")
#
#         result.cites = [OrderedDict(cite) for cite in result.cites]
#         res_json = {
#             "text": result.text,
#             "cites": result.cites,
#             "result_cache_key": self._result_cache_key
#         }
#         self.session.add_agent_logs(
#             self._result_cache_key,
#             logs=res_json
#         )
#
#         for cite in res_json.get("cites", []):
#             if "connected_subgraph" in cite:
#                 del cite["connected_subgraph"]
#
#         return res_json
#
#     def _run_single_query(
#             self,
#             query: str,
#             extraneous_information: str = "",
#             run_manager: Optional[CallbackManagerForToolRun] = None,
#     ):
#         try:
#             api = self._service(query=query, extraneous_information=extraneous_information)
#             result = api.call()
#             if isinstance(result, str):
#                 result = json.loads(result)
#             logger.debug(f"Search API Response: {result}")
#             result = AfSailorToolResult(**result["result"]["res"])
#             result = self._parser(result)
#             return result
#         except Exception as e:
#             tb_str = traceback.format_exc()
#             logger.info(f"Sailor工具执行错误，实际错误为{tb_str}")
#             result = AfSailorToolResult(
#                 text=["抱歉，可能由于网络延迟或当前服务器繁忙，当前回答尚未完成。"]
#             ).to_json()
#             return result
#
#     @construct_final_answer
#     def _run(
#             self,
#             run_manager: Optional[CallbackManagerForToolRun] = None,
#             *args,
#             **kwargs: Any
#     ):
#         queries = kwargs.get("queries", [])
#         extraneous_information = kwargs.get("extraneous_information", "")
#
#         if not queries:
#             return {
#                 "text": ["没有提供搜索词"],
#                 "cites": [],
#                 "result_cache_key": ""
#             }
#
#         results = []
#         for query in queries:
#             single_result = self._run_single_query(query, extraneous_information, run_manager)
#             results.append({
#                 "query": query,
#                 "result": single_result
#             })
#
#         combined_text = []
#         combined_cites = []
#         cache_keys = []
#
#         for res in results:
#             if isinstance(res["result"], dict):
#                 combined_text.extend(res["result"].get("text", []))
#                 combined_cites.extend(res["result"].get("cites", []))
#                 if "result_cache_key" in res["result"]:
#                     cache_keys.append(res["result"]["result_cache_key"])
#
#         return {
#             "text": combined_text,
#             "cites": combined_cites,
#             "result_cache_key": ",".join(cache_keys) if cache_keys else "",
#             "individual_results": results
#         }
#
#     async def _arun_single_query(
#             self,
#             query: str,
#             extraneous_information: str = "",
#             run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
#     ):
#         try:
#             api = self._service(query=query, extraneous_information=extraneous_information)
#             result = await api.call_async()
#             if not result:
#                 return {
#                     "text": ["没有找到对应的数据资源"],
#                 }
#             if isinstance(result, str):
#                 result = json.loads(result)
#             logger.debug(f"Search API Response: {result}")
#             result = AfSailorToolResult(**result.get("result", {}).get("res", {}))
#             result = self._parser(result)
#             return result
#         except Exception as e:
#             tb_str = traceback.format_exc()
#             logger.info(f"Sailor工具执行错误，实际错误为{tb_str}")
#             result = AfSailorToolResult(
#                 text=["工具执行错误，请重新提问。"]
#             ).to_json()
#             return result
#
#     @async_construct_final_answer
#     async def _arun(
#             self,
#             run_manager: Optional[AsyncCallbackManagerForToolRun],
#             *args,
#             **kwargs: Any
#     ):
#         queries = kwargs.get("queries", [])
#         extraneous_information = kwargs.get("extraneous_information", "")
#
#         if not queries:
#             return {
#                 "text": ["没有提供搜索词"],
#                 "cites": [],
#                 "result_cache_key": ""
#             }
#
#         results = []
#         for query in queries:
#             single_result = await self._arun_single_query(query, extraneous_information, run_manager)
#             results.append({
#                 "query": query,
#                 "result": single_result
#             })
#
#         combined_text = []
#         combined_cites = []
#         cache_keys = []
#
#         for res in results:
#             if isinstance(res["result"], dict):
#                 combined_text.extend(res["result"].get("text", []))
#                 combined_cites.extend(res["result"].get("cites", []))
#                 if "result_cache_key" in res["result"]:
#                     cache_keys.append(res["result"]["result_cache_key"])
#
#         return {
#             "text": combined_text,
#             "cites": combined_cites,
#             "result_cache_key": ",".join(cache_keys) if cache_keys else "",
#             "individual_results": results
#         }
#
#     def handle_result(
#             self,
#             result_cache_key: str,
#             log: Dict[str, Any],
#             ans_multiple: ToolMultipleResult
#     ) -> None:
#         logger.info(f"handle_result 调用 - 对象ID: {id(self)}, 当前缓存键: {self._result_cache_key}")
#         if self.session:
#             tool_res = self.session.get_agent_logs(
#                 result_cache_key
#             )
#             if tool_res:
#                 log["result"] = tool_res
#
#                 cites_cache = []
#                 for cite in tool_res.get("cites", []):
#                     cc = {
#                         "id": cite.get("id", ""),
#                         "type": cite.get("type", ""),
#                         "title": cite.get("title", ""),
#                     }
#                     cites_cache.append(cc)
#
#                 ans_multiple.sailor_search_result = cites_cache
#                 ans_multiple.text = tool_res.get("text", [])
#
#                 ans_multiple.cache_keys[result_cache_key] = {
#                     "tool_name": self.name,
#                     "result_cache_key": result_cache_key,
#                     "datasource_num": len(tool_res.get("cites", []))
#                 }
#
#     @classmethod
#     @api_tool_decorator
#     async def as_async_api_cls(
#             cls,
#             params: dict
#     ):
#         resources = params.get('resources', {})
#         parameters = resources.get('parameters', {})
#         token = resources.get('token', '')
#         if not token or token == "''":
#             user = resources.get("user", "")
#             password = resources.get("password", "")
#             auth_url = resources.get("auth_url", settings.AF_DEBUG_IP)
#             parameters['user'] = user
#             parameters['password'] = password
#             parameters['auth_url'] = auth_url
#
#             try:
#                 parameters["token"] = get_authorization(auth_url, user, password)
#             except Exception as e:
#                 logger.error(f"Error: {e}")
#                 raise ToolFatalError(reason="获取 token 失败", detail=e) from e
#
#         config_dict = params.get("config", {})
#         parameters.update(config_dict)
#         tool = cls(parameter=parameters)
#
#         # Input Params
#         input = params.get("input", {})
#
#         # invoke tool
#         res = await tool.ainvoke(input=input)
#         return res
#
#     @staticmethod
#     async def get_api_schema():
#         return {
#             "type": "object",
#             "properties": {
#                 "resources": {
#                     "type": "object",
#                     "description": "资源配置信息",
#                     "properties": {
#                         "parameters": {
#                             "type": "object",
#                             "description": "资源配置信息"
#                         },
#                         "auth_url": {
#                             "type": "string",
#                             "description": "认证服务URL"
#                         },
#                         "user": {
#                             "type": "string",
#                             "description": "用户名"
#                         },
#                         "password": {
#                             "type": "string",
#                             "description": "密码"
#                         },
#                         "token": {
#                             "type": "string",
#                             "description": "认证令牌，如提供则无需用户名和密码"
#                         }
#                     },
#                     "required": ["parameters"]
#                 },
#                 "config": {
#                     "type": "object",
#                     "description": "工具配置参数",
#                     "properties": {
#                         "direct_qa": {
#                             "type": "string",
#                             "description": "背景信息"
#                         },
#                         "session_type": {
#                             "type": "string",
#                             "description": "会话类型",
#                             "enum": ["in_memory", "redis"],
#                             "default": "in_memory"
#                         },
#                         "session_id": {
#                             "type": "string",
#                             "description": "会话ID"
#                         },
#                     }
#                 },
#                 "input": {
#                     "type": "object",
#                     "description": "输入参数",
#                     "properties": {
#                         "input": {
#                             "type": "string",
#                             "description": "用户输入的自然语言查询"
#                         },
#                         "knowledge_enhanced_information": {
#                             "type": "object",
#                             "description": "知识增强信息"
#                         },
#                         "extra_info": {
#                             "type": "string",
#                             "description": "额外信息"
#                         }
#                     },
#                     "required": ["input"]
#                 }
#             },
#             "required": ["resources", "input"]
#         }

import asyncio
import json
from textwrap import dedent
from typing import Any, Dict, List, Optional, Type

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.session.redis_session import RedisHistorySession
from app.utils.llm import CustomChatOpenAI
from app.utils.password import get_authorization
from app.errors import ToolFatalError
from config import get_settings

from app.tools.base import (
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from app.tools.todo_list.task_manager import TaskStatus, TaskListStatus
from app.parsers.base import BaseJsonParser


_SETTINGS = get_settings()


# Redis 缓存过期时间（24小时）
CACHE_EXPIRE_TIME = 60 * 60 * 24

# 工具名称
TOOL_NAME = "todo_list_tool"


class TodoListArgs(BaseModel):
    """任务拆分工具入参"""

    query: str = Field(default="", description="由意图理解工具丰富后的用户问题")
    scene: str = Field(default="", description="由意图理解工具得出的用户问题场景")
    strategy: str = Field(default="", description="指定当前场景下的拆解策略")
    session_id: str = Field(default="", description="当前会话ID，用来获取/保存当前会话的任务列表")
    tools: List[Dict[str, str]] = Field(  # [{"name": "...","purpose": "..."}]
        default_factory=list,
        description="可用工具列表，用于指导任务拆分。每项包含: name(工具名称), purpose(工具作用/适用场景)",
    )


class TodoListTool(LLMTool):
    """
    任务拆分工具

    这是一个将用户问题拆成一个个不可分割的任务列表的工具。

    功能：
    - 根据会话ID获取历史任务列表
    - 结合当前问题、场景和拆解策略，使用大模型拆解为任务列表
    - 支持追问场景下，从某个拆解点重新规划后续任务
    - 将任务列表以 string 结构保存到 Redis（24 小时过期）
    """

    name: str = TOOL_NAME
    description: str = dedent(
        """
        任务拆分工具。

        根据用户问题、问题场景和拆解策略，将问题拆解成一组带依赖关系的任务列表，并保存到 Redis 中。

        参数:
        - query: 由意图理解工具丰富后的用户问题
        - scene: 由意图理解工具得出的用户问题场景
        - strategy: 指定当前场景下的拆解策略
        - session_id: 当前会话ID，用来获取当前会话的任务列表
        - tools: 可用工具列表（name/purpose），用于指导任务拆分为可落地的步骤

        该工具会：
        1. 通过 session_id 从 Redis 中获取任务列表
        2. 使用大模型判断当前问题与历史任务之间的关系，得到任务拆解点
        3. 结合问题、拆解点、拆解策略，由大模型生成任务列表
        4. 将任务列表标记为未开始状态，保存到 Redis（string 结构，24 小时过期），并返回
        """
    )

    args_schema: Type[BaseModel] = TodoListArgs

    # 会话与 LLM 相关配置
    token: str = ""
    user_id: str = ""
    background: str = ""

    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("session") is None:
            self.session = CreateSession(self.session_type)
        # RedisHistorySession 已在 CreateSession 中创建，这里只是为了类型提示清晰
        if isinstance(self.session, RedisHistorySession):
            logger.info("TodoListTool 使用 RedisHistorySession 作为会话存储")

    # ---------------- Redis 相关工具方法 ----------------

    def _get_redis_key(self, session_id: str) -> str:
        """根据会话ID生成 Redis key"""
        return f"{TOOL_NAME}/session/{session_id}"

    def _load_session_tasks(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        通过会话ID获取任务列表

        逻辑：
        1. 通过会话ID查询 Redis 得到任务列表
        2. 如果查不到或者任务已经完成，返回 None
        3. 如果查到是未完成状态，将任务列表返回
        """
        if not isinstance(self.session, RedisHistorySession):
            logger.warning("当前 session 非 RedisHistorySession，无法加载任务列表")
            return None

        key = self._get_redis_key(session_id)
        raw = self.session.client.get(key)
        if not raw:
            return None

        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
        except Exception as e:
            logger.warning(f"解析 Redis 中的任务列表失败，将视为无历史任务: {e}")
            return None

        status = data.get("status", "")
        tasks: List[Dict[str, Any]] = data.get("tasks", [])

        # 如果整体状态为 completed，或者所有任务都完成，则视为无历史任务
        if status == "completed" or (
            tasks
            and all(t.get("status") == "completed" for t in tasks)
        ):
            return None

        return data

    def _save_session_tasks(self, session_id: str, task_obj: Dict[str, Any]):
        """
        将任务列表保存到 Redis，string 结构，24 小时过期
        """
        if not isinstance(self.session, RedisHistorySession):
            logger.warning("当前 session 非 RedisHistorySession，无法保存任务列表")
            return

        key = self._get_redis_key(session_id)
        try:
            value = json.dumps(task_obj, ensure_ascii=False)
            self.session.client.setex(key, CACHE_EXPIRE_TIME, value)
            logger.info(f"任务列表已保存到 Redis，key={key}")
        except Exception as e:
            logger.error(f"保存任务列表到 Redis 失败: {e}")
            raise ToolFatalError(f"保存任务列表到缓存失败: {str(e)}")

    # ---------------- 任务列表生成 ----------------
    def _generate_tasks_with_llm(
        self,
        history_tasks: Optional[Dict[str, Any]],
        query: str,
        scene: str,
        strategy: str,
        tools: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        让大模型根据当前问题、任务列表、拆解策略，生成/调整任务列表。
        """
        history_tasks_obj = history_tasks or {
            "query": "",
            "status": TaskListStatus.PENDING.value,
            "tasks": [],
        }

        prompt_content = dedent(
            """
            你是一个任务拆解专家。

            现在有一个用户问题需要被拆解为一组任务，要求：
            - 该任务粒度「不可再拆」且「可执行」
            - 任务之间有依赖，上一步的输出一定要是下一步的输入，保证流程严格
            - 保证完整逻辑的同时，尽量减少步骤，避免不必要的执行步骤
            - 根据各个工具的特点进行最优拆解，不需要所有的工具都用到

            我会给你：
            - 当前用户问题（query_now）
            - 问题场景（scene）
            - 拆解策略说明（strategy），里面任务拆分的逻辑和要求
            - 历史任务列表（history_tasks），可能为空（当前实现中，仅作为参考，不做局部复用拆解）
            - 可用工具列表（tools）：包含每个工具的 name 与 purpose，请务必拆分成可由这些工具执行的最小可执行单元；
              当某一步不需要工具时，也要明确标注其产出，以便后续工具消费。

            任务对象结构要求：
            {
              "query": "用户问题",
              "status": "任务列表整体状态，初始为 pending（枚举：pending/running/completed）",
              "tasks": [
                {
                  "id": 1,                     // 任务ID，从 1 开始递增
                  "title": "任务标题，简洁表达要做什么",
                  "detail": "任务详细内容，包含输入/输出、验收标准等",
                  "tools": [                   // 本任务将使用到的工具（可为空数组）
                    { "name": "tool_name", "inputs": "关键输入说明", "outputs": "期望产出说明" }
                  ],
                  "blockedBy": [ ... ],        // 依赖的任务ID 数组，可以为空数组
                  "status": "pending"          // 任务状态（枚举：pending/running/completed/failed/cancelled），初始为 pending
                }
              ]
            }

            生成规则：
            1. 所有任务的 status 必须初始化为 "pending"。
            2. id 必须是从 1 开始连续递增的整数。
            3. blockedBy 只允许引用已存在的任务 id，不能出现循环依赖。
            4. 明确任务与工具的对应关系：
               - 当可用工具（tools）能完成该任务时，请在任务文本中注明所用工具的 name 以及所需关键输入；
               - 无需强制所有任务都绑定工具，但必须保证整条链路可落地、可执行；
               - 尽量拆分为“工具可直接执行”的最小步骤，避免巨大笼统步骤。
            5. 任务粒度要细到可以交给不同的工具或执行单元完成。

            请只返回 JSON，不要包含多余的解释文字。
            """
        )

        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(
                content=json.dumps(
                    {
                        "query_now": query,
                        "scene": scene,
                        "strategy": strategy,
                        "history_tasks": history_tasks_obj,
                        "tools": tools or [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            ),
        ]

        try:
            prompt = ChatPromptTemplate.from_messages(messages)
            chain = prompt | self.llm | BaseJsonParser()
            result = chain.invoke({})
        except Exception as e:
            logger.error(f"大模型任务拆解失败: {e}")
            raise ToolFatalError(f"大模型任务拆解失败: {str(e)}")

        # 简单校验与兜底
        if not isinstance(result, dict):
            raise ToolFatalError("大模型返回的任务列表格式不正确")

        tasks = result.get("tasks", [])
        if not isinstance(tasks, list) or not tasks:
            raise ToolFatalError("大模型未生成任何任务")

        # 统一补齐字段并强制初始状态
        normalized_tasks: List[Dict[str, Any]] = []
        for idx, t in enumerate(tasks, start=1):
            title = t.get("title") or t.get("name") or ""
            detail = t.get("detail") or t.get("description") or ""
            tools_used = t.get("tools", []) or []
            if isinstance(tools_used, dict):
                tools_used = [tools_used]
            # 兜底字段
            blocked_by = t.get("blockedBy", []) or []
            if not isinstance(blocked_by, list):
                blocked_by = [blocked_by]
            normalized_tasks.append(
                {
                    "id": idx,
                    "title": title,
                    "detail": detail,
                    "tools": tools_used,
                    "blockedBy": blocked_by,
                    "status": TaskStatus.PENDING.value,
                }
            )

        task_obj = {
            "query": query,
            "status": TaskListStatus.PENDING.value,
            "tasks": normalized_tasks,
        }
        return task_obj

    # ---------------- LLMTool 接口实现 ----------------

    @construct_final_answer
    def _run(
        self,
        query: str,
        scene: str = "",
        strategy: str = "",
        session_id: str = "",
        tools: Optional[List[Dict[str, str]]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """
        同步执行任务拆分工具
        """
        return asyncio.run(
            self._arun(
                query=query,
                scene=scene,
                strategy=strategy,
                session_id=session_id,
                tools=tools or [],
                run_manager=run_manager,
            )
        )

    @async_construct_final_answer
    async def _arun(
        self,
        query: str,
        scene: str = "",
        strategy: str = "",
        session_id: str = "",
        tools: Optional[List[Dict[str, str]]] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        异步执行任务拆分工具
        """
        try:
            if not query or not query.strip():
                logger.warning("query 参数为空")
                return {
                    "result": "query 参数不能为空",
                    "tasks": [],
                }

            if not session_id or not session_id.strip():
                logger.warning("session_id 参数为空")
                return {
                    "result": "session_id 参数不能为空",
                    "tasks": [],
                }

            # 1. 通过会话ID获取任务列表（当前实现仅作为上下文参考，不做局部拆解复用）
            history_tasks = self._load_session_tasks(session_id)

            # 2. 直接结合当前问题、历史任务和拆解策略，让大模型生成全新的任务列表
            task_obj = self._generate_tasks_with_llm(
                history_tasks=history_tasks,
                query=query,
                scene=scene,
                strategy=strategy,
                tools=(tools or []),
            )

            # 3. 将任务列表标记为未开始状态，同时保存问题，保存到 Redis，然后返回
            self._save_session_tasks(session_id, task_obj)

            return {
                "result": "任务列表生成成功",
                "session_id": session_id,
                "tasks": task_obj.get("tasks", []),
                "status": task_obj.get("status"),
            }
        except Exception as e:
            logger.error(f"执行任务拆分工具失败: {e}")
            raise ToolFatalError(f"执行任务拆分工具失败: {str(e)}")

    # ---------------- 配置与 API 封装 ----------------

    @classmethod
    def from_config(cls, params: Dict[str, Any]):
        """
        从配置创建工具实例

        参数:
        - llm: LLM 配置
        - auth: 认证配置（token, user, password, user_id, auth_url）
        - config: 其他配置（background, session_type）
        """
        # LLM 配置
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
                token = get_authorization(
                    auth_dict.get("auth_url", _SETTINGS.AF_DEBUG_IP),
                    user,
                    password,
                )
            except Exception as e:
                logger.error(f"[TodoListTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e

        config_dict = params.get("config", {})

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
        )

        return tool

    # -------- 作为独立异步 API 的封装 --------
    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
        cls,
        params: dict,
    ):
        """
        将工具转换为异步 API 类方法，供外部 HTTP 调用。

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
            "session_type": "redis"     // 可选，会话类型
          },
          "query": "用户问题",            // 必填
          "scene": "问题场景",           // 可选
          "strategy": "拆解策略说明",    // 可选
          "session_id": "会话ID",       // 必填，用于在 Redis 中区分任务列表
          "tools": [                   // 可选，可用工具列表
            {"name": "tool_name", "purpose": "该工具的作用与适用场景"}
          ]
        }
        """
        # LLM 配置
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
                token = get_authorization(
                    auth_dict.get("auth_url", _SETTINGS.AF_DEBUG_IP),
                    user,
                    password,
                )
            except Exception as e:
                logger.error(f"[TodoListTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e

        config_dict = params.get("config", {})

        tool = cls(
            llm=llm,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
        )

        query = params.get("query", "")
        scene = params.get("scene", "")
        strategy = params.get("strategy", "")
        session_id = params.get("session_id", "")
        tools = params.get("tools", [])

        res = await tool.ainvoke(
            input={
                "query": query,
                "scene": scene,
                "strategy": strategy,
                "session_id": session_id,
                "tools": tools,
            }
        )
        return res

    @staticmethod
    async def get_api_schema():
        """获取 API Schema，便于自动注册为 HTTP API。"""
        return {
            "post": {
                "summary": "todo_list_tool",
                "description": "任务拆分工具，根据用户问题、场景和拆解策略生成任务列表，并保存到 Redis。",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "llm": {
                                        "type": "object",
                                        "description": "LLM 配置参数（可选）",
                                    },
                                    "auth": {
                                        "type": "object",
                                        "description": "认证参数",
                                        "properties": {
                                            "auth_url": {
                                                "type": "string",
                                                "description": "认证服务URL（可选）",
                                            },
                                            "user": {
                                                "type": "string",
                                                "description": "用户名（可选）",
                                            },
                                            "password": {
                                                "type": "string",
                                                "description": "密码（可选）",
                                            },
                                            "token": {
                                                "type": "string",
                                                "description": "认证令牌，如提供则无需用户名和密码（推荐）",
                                            },
                                            "user_id": {
                                                "type": "string",
                                                "description": "用户ID（可选）",
                                            },
                                        },
                                    },
                                    "config": {
                                        "type": "object",
                                        "description": "工具配置参数",
                                        "properties": {
                                            "session_type": {
                                                "type": "string",
                                                "description": "会话类型",
                                                "enum": ["in_memory", "redis"],
                                                "default": "redis",
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "背景信息（可选）",
                                            },
                                        },
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "由意图理解工具丰富后的用户问题（必填）",
                                    },
                                    "scene": {
                                        "type": "string",
                                        "description": "由意图理解工具得出的用户问题场景（可选）",
                                    },
                                    "strategy": {
                                        "type": "string",
                                        "description": "当前场景下的拆解策略说明（可选）",
                                    },
                                    "session_id": {
                                        "type": "string",
                                        "description": "会话ID，用于区分并缓存任务列表（必填）",
                                    },
                                    "tools": {
                                        "type": "array",
                                        "description": "可用工具列表，用于指导任务拆分",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "工具名称（必填，需与系统已注册工具一致）",
                                                },
                                                "purpose": {
                                                    "type": "string",
                                                    "description": "工具作用/适用场景（必填，用于指导大模型拆分任务）",
                                                },
                                                "inputs": {
                                                    "type": "string",
                                                    "description": "该工具需要的关键输入参数说明（可选，用字符串描述即可）",
                                                },
                                                "outputs": {
                                                    "type": "string",
                                                    "description": "该工具主要输出参数说明（可选，用字符串描述即可）",
                                                },
                                                "examples": {
                                                    "type": "array",
                                                    "description": "工具使用示例（可选，用于指导大模型写出更可执行的任务描述）",
                                                    "items": {"type": "string"},
                                                },
                                            },
                                            "required": ["name", "purpose"]
                                        }
                                    },
                                },
                                "required": ["query", "session_id"],
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
                                    "properties": {
                                        "result": {"type": "string"},
                                        "session_id": {"type": "string"},
                                        "status": {"type": "string"},
                                        "tasks": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer"},
                                                    "title": {"type": "string"},
                                                    "detail": {"type": "string"},
                                                    "tools": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "name": {
                                                                    "type": "string"
                                                                },
                                                                "inputs": {
                                                                    "type": "string"
                                                                },
                                                                "outputs": {
                                                                    "type": "string"
                                                                }
                                                            },
                                                            "required": [
                                                                "name"
                                                            ]
                                                        }
                                                    },
                                                    "blockedBy": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "integer"
                                                        },
                                                    },
                                                    "status": {
                                                        "type": "string"
                                                    },
                                                },
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }


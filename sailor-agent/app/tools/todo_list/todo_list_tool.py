import asyncio
import copy
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
from app.utils.llm_params import merge_llm_params

from app.tools.base import (
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)
from app.tools.todo_list.task_manager import TaskManager, TaskStatus, TaskListStatus
from app.parsers.base import BaseJsonParser


_SETTINGS = get_settings()


# Redis 缓存过期时间（24小时）
CACHE_EXPIRE_TIME = 60 * 60 * 24

# 工具名称
TOOL_NAME = "todo_list_tool"

# 任务列表操作模式（与 docs/todo_list.md 一致）
TODO_LIST_MODE_GENERATE = "generate"
TODO_LIST_MODE_ADJUST = "adjust"


class TodoListArgs(BaseModel):
    """任务拆分工具入参"""

    query: str = Field(default="", description="由意图理解工具丰富后的用户问题")
    scene: str = Field(default="", description="由意图理解工具得出的用户问题场景")
    strategy: str = Field(
        default="",
        description="generate 模式下为拆解策略；adjust 模式下为调整原因（调节原因）",
    )
    mode: str = Field(
        default=TODO_LIST_MODE_GENERATE,
        description=(
            '操作模式："generate" 新生成完整任务列表（默认）；'
            '"adjust" 在会话已有未完成任务列表上按调整原因重排/增删未完成任务'
        ),
    )
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
    - 根据会话ID获取历史任务列表（若为空或已完成则视为无历史任务）
    - mode=generate：结合问题、历史（可为空）与拆解策略，生成完整任务列表
    - mode=adjust：在 Redis 中已有未完成任务列表上，按 strategy 中的调整原因修改未完成任务（已完成任务保持不变）
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
        - strategy: generate 时为拆解策略；adjust 时为调整原因
        - mode: generate（默认）新生成；adjust 调整已有未完成任务列表
        - session_id: 当前会话ID，用来获取当前会话的任务列表
        - tools: 可用工具列表（name/purpose），用于指导任务拆分为可落地的步骤

        该工具会：
        1. 通过 session_id 从 Redis 获取历史任务列表（查不到或已完成则视为无历史任务；adjust 时必须存在未完成列表）
        2. 按 mode 调用大模型：新生成完整列表，或基于历史调整未完成任务
        3. 保存到 Redis（string 结构，24 小时过期），并返回
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

    @staticmethod
    def _task_text_from_raw(t: Dict[str, Any]) -> str:
        tx = (t.get("task") or "").strip()
        if tx:
            return tx
        title = (t.get("title") or t.get("name") or "").strip()
        detail = (t.get("detail") or t.get("description") or "").strip()
        if title and detail:
            return f"{title} {detail}".strip()
        return title or detail

    def _apply_adjust_locked_completed(
        self,
        history_tasks: Dict[str, Any],
        llm_tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """调整模式：已 completed 的任务与历史完全一致，其余以模型输出为准（按 id 合并）。"""
        hist = history_tasks.get("tasks") or []
        locked: Dict[int, Dict[str, Any]] = {}
        for t in hist:
            try:
                tid = int(t.get("id"))
            except (TypeError, ValueError):
                continue
            if t.get("status") == TaskStatus.COMPLETED.value:
                locked[tid] = copy.deepcopy(t)

        by_id: Dict[int, Dict[str, Any]] = {}
        for t in llm_tasks:
            try:
                tid = int(t.get("id", 0))
            except (TypeError, ValueError):
                continue
            if tid <= 0:
                continue
            by_id[tid] = t

        for tid, frozen in locked.items():
            by_id[tid] = frozen

        if not by_id:
            raise ToolFatalError("大模型未返回有效任务")

        ordered = [by_id[k] for k in sorted(by_id.keys())]
        return self._finalize_tasks_shape(ordered, force_all_pending=False)

    def _finalize_tasks_shape(
        self,
        tasks: List[Dict[str, Any]],
        *,
        force_all_pending: bool,
    ) -> List[Dict[str, Any]]:
        """统一为 Redis 结构（含 task 字段）；generate 时子任务一律 pending。"""
        out: List[Dict[str, Any]] = []
        for t in tasks:
            try:
                tid = int(t.get("id", 0))
            except (TypeError, ValueError):
                continue
            if tid <= 0:
                continue
            blocked_by = t.get("blockedBy", []) or []
            if not isinstance(blocked_by, list):
                blocked_by = [blocked_by]
            tools_used = t.get("tools", []) or []
            if isinstance(tools_used, dict):
                tools_used = [tools_used]
            text = self._task_text_from_raw(t)
            st = TaskStatus.PENDING.value if force_all_pending else (
                t.get("status") or TaskStatus.PENDING.value
            )
            row: Dict[str, Any] = {
                "id": tid,
                "task": text,
                "blockedBy": blocked_by,
                "status": st,
            }
            if tools_used:
                row["tools"] = tools_used
            out.append(row)
        return out

    def _normalize_generate_tasks(
        self,
        raw_tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """新生成：按顺序重排 id=1..n，与既有行为一致。"""
        normalized: List[Dict[str, Any]] = []
        for idx, t in enumerate(raw_tasks, start=1):
            blocked_by = t.get("blockedBy", []) or []
            if not isinstance(blocked_by, list):
                blocked_by = [blocked_by]
            tools_used = t.get("tools", []) or []
            if isinstance(tools_used, dict):
                tools_used = [tools_used]
            text = self._task_text_from_raw(t)
            row: Dict[str, Any] = {
                "id": idx,
                "task": text,
                "blockedBy": blocked_by,
                "status": TaskStatus.PENDING.value,
            }
            if tools_used:
                row["tools"] = tools_used
            normalized.append(row)
        return normalized

    def _generate_tasks_with_llm(
        self,
        mode: str,
        history_tasks: Optional[Dict[str, Any]],
        query: str,
        scene: str,
        strategy: str,
        tools: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        调用大模型：mode=generate 新生成；mode=adjust 基于历史调整（strategy 为调整原因）。
        """
        history_tasks_obj = history_tasks or {
            "query": "",
            "status": TaskListStatus.PENDING.value,
            "resorted": False,
            "tasks": [],
        }

        if mode == TODO_LIST_MODE_ADJUST:
            prompt_content = dedent(
                """
                你是一个任务列表调整专家。输入中有一份「历史任务列表」，其中部分任务可能已执行完成。

                你会收到：
                - 当前用户问题（query_now）
                - 问题场景（scene）
                - 调整原因（adjustment_reason），说明为什么要改、希望如何改
                - 历史任务列表（history_tasks），包含各任务 id、task 文本、blockedBy、status
                - 可用工具列表（tools）

                你的任务：
                - 根据调整原因，对「尚未完成」的任务进行增删改或重排依赖；已 status 为 completed 的任务必须保持完全不变（同一 id 下 task、blockedBy、status 均不得改动）。
                - 输出一份**完整**的新任务列表（包含所有已完成任务原样保留 + 调整后的未完成任务）。
                - blockedBy 只允许引用本次输出中存在的任务 id，不得循环依赖。

                顶层 JSON 结构：
                {
                  "query": "用户问题（使用 query_now）",
                  "status": "任务列表整体状态（pending/running/completed 之一，需与任务实际进度一致）",
                  "resorted": false,
                  "tasks": [
                    {
                      "id": 1,
                      "task": "任务内容",
                      "blockedBy": [],
                      "status": "pending|running|completed|failed|cancelled"
                    }
                  ]
                }

                请只返回 JSON，不要包含多余的解释文字。
                """
            )
            human_payload = {
                "query_now": query,
                "scene": scene,
                "adjustment_reason": strategy,
                "history_tasks": history_tasks_obj,
                "tools": tools or [],
            }
        else:
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
                - 历史任务列表（history_tasks），可能为空（仅作上下文参考）
                - 可用工具列表（tools）：包含每个工具的 name 与 purpose

                顶层 JSON 结构（与 Redis 缓存一致）：
                {
                  "query": "用户问题（使用 query_now）",
                  "status": "pending",
                  "resorted": false,
                  "tasks": [
                    {
                      "id": 1,
                      "task": "任务内容，可注明所用工具 name 及关键输入输出",
                      "blockedBy": [],
                      "status": "pending"
                    }
                  ]
                }

                生成规则：
                1. 所有任务的 status 必须初始化为 "pending"。
                2. id 必须是从 1 开始连续递增的整数。
                3. blockedBy 只允许引用已存在的任务 id，不能出现循环依赖。
                4. 任务粒度要细到可以交给不同的工具或执行单元完成。

                请只返回 JSON，不要包含多余的解释文字。
                """
            )
            human_payload = {
                "query_now": query,
                "scene": scene,
                "strategy": strategy,
                "history_tasks": history_tasks_obj,
                "tools": tools or [],
            }

        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(
                content=json.dumps(
                    human_payload,
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

        if not isinstance(result, dict):
            raise ToolFatalError("大模型返回的任务列表格式不正确")

        tasks = result.get("tasks", [])
        if not isinstance(tasks, list) or not tasks:
            raise ToolFatalError("大模型未生成任何任务")

        resorted = bool(result.get("resorted", False))

        if mode == TODO_LIST_MODE_ADJUST:
            if not history_tasks:
                raise ToolFatalError("调整模式缺少历史任务列表")
            merged = self._apply_adjust_locked_completed(history_tasks, tasks)
            overall = TaskManager.recalculate_overall_status(merged)
            return {
                "query": query,
                "status": overall,
                "resorted": resorted,
                "tasks": merged,
            }

        normalized_tasks = self._normalize_generate_tasks(tasks)
        return {
            "query": query,
            "status": TaskListStatus.PENDING.value,
            "resorted": resorted,
            "tasks": normalized_tasks,
        }

    # ---------------- LLMTool 接口实现 ----------------

    @construct_final_answer
    def _run(
        self,
        query: str,
        scene: str = "",
        strategy: str = "",
        mode: str = TODO_LIST_MODE_GENERATE,
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
                mode=mode,
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
        mode: str = TODO_LIST_MODE_GENERATE,
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

            op_mode = (mode or TODO_LIST_MODE_GENERATE).strip()
            if op_mode not in (TODO_LIST_MODE_GENERATE, TODO_LIST_MODE_ADJUST):
                return {
                    "result": f"mode 参数不合法：{mode}，仅支持 generate 或 adjust",
                    "session_id": session_id,
                    "tasks": [],
                }

            history_tasks = self._load_session_tasks(session_id)

            if op_mode == TODO_LIST_MODE_ADJUST:
                if not history_tasks:
                    return {
                        "result": "adjust 模式下会话没有可调整的任务列表（不存在或已全部完成）",
                        "session_id": session_id,
                        "tasks": [],
                    }

            task_obj = self._generate_tasks_with_llm(
                mode=op_mode,
                history_tasks=history_tasks,
                query=query,
                scene=scene,
                strategy=strategy,
                tools=(tools or []),
            )

            self._save_session_tasks(session_id, task_obj)

            ok_msg = (
                "任务列表调整成功"
                if op_mode == TODO_LIST_MODE_ADJUST
                else "任务列表生成成功"
            )
            return {
                "result": ok_msg,
                "session_id": session_id,
                "mode": op_mode,
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
          "strategy": "拆解策略或调整原因", // generate 为拆解策略；adjust 为调整原因
          "mode": "generate",           // 可选，generate（默认）| adjust
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
        mode = params.get("mode", TODO_LIST_MODE_GENERATE)
        session_id = params.get("session_id", "")
        tools = params.get("tools", [])

        res = await tool.ainvoke(
            input={
                "query": query,
                "scene": scene,
                "strategy": strategy,
                "mode": mode,
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
                "description": "任务拆分工具：mode=generate 新生成任务列表；mode=adjust 按原因调整未完成任务。结果保存到 Redis。",
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
                                        "description": "generate 时为拆解策略；adjust 时为调整原因（可选）",
                                    },
                                    "mode": {
                                        "type": "string",
                                        "description": "generate 新生成（默认）；adjust 在已有未完成任务列表上调整",
                                        "enum": ["generate", "adjust"],
                                        "default": "generate",
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
                                        "mode": {
                                            "type": "string",
                                            "enum": ["generate", "adjust"],
                                        },
                                        "status": {"type": "string"},
                                        "tasks": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer"},
                                                    "task": {"type": "string"},
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


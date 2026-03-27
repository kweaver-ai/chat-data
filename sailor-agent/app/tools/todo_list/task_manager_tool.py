import asyncio
import json
from textwrap import dedent
from typing import Any, Dict, List, Optional, Type

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.pydantic_v1 import BaseModel, Field

from app.logs.logger import logger
from app.session import BaseChatHistorySession, CreateSession
from app.session.redis_session import RedisHistorySession
from app.utils.password import get_authorization
from app.errors import ToolFatalError
from config import get_settings

from app.tools.base import (
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
    api_tool_decorator,
)

from .todo_list_tool import CACHE_EXPIRE_TIME, TOOL_NAME
from .task_manager import TaskManager


_SETTINGS = get_settings()

# 任务管理工具名称（与 todo_list 共用 Redis key 前缀 TOOL_NAME）
TASK_MANAGER_TOOL_NAME = "task_manager_tool"


class TaskManagerArgs(BaseModel):
    """任务管理工具入参"""

    session_id: str = Field(
        default="",
        description="当前会话ID，用来获取/更新当前会话的任务列表",
    )
    op: str = Field(
        default="get_runnable",
        description='操作类型："get_runnable" 获取可执行任务；"update_status" 更新任务状态',
    )
    task_id: Optional[int] = Field(
        default=None,
        description='当 op 为 "update_status" 时必填，要更新的任务ID',
    )
    status: Optional[str] = Field(
        default=None,
        description='当 op 为 "update_status" 时必填，新状态：pending/running/completed/failed/cancelled',
    )
    adjust: bool = Field(
        default=False,
        description="是否需要根据当前任务结果调整后续任务（如某一步即可视为全部完成）",
    )
    reason: str = Field(
        default="",
        description="调整原因说明，仅在 adjust 为 True 时有意义",
    )


class TaskManagerTool(LLMTool):
    """
    任务管理工具

    基于 TodoList 工具生成的任务列表，提供：
    - 获取当前会话可执行任务
    - 查询被卡住的任务、已完成任务
    - 更新任务状态，并在必要时调整/清理整个任务列表
    """

    name: str = TASK_MANAGER_TOOL_NAME
    description: str = dedent(
        """
        任务管理工具。基于会话ID管理任务执行顺序与状态。

        参数:
        - session_id: 当前会话ID，用来获取/更新当前会话的任务列表
        - op: 操作类型，"get_runnable" 获取可执行任务；"update_status" 更新任务状态
        - task_id: 当 op 为 update_status 时必填，要更新的任务ID
        - status: 当 op 为 update_status 时必填，新状态
        - adjust: 是否需要根据当前任务结果调整后续任务
        - reason: 调整原因（可选）

        该工具会：
        1. 根据 session_id 从 Redis 获取任务列表（与 todo_list_tool 共用 key）
        2. op=get_runnable 时返回可执行/被阻塞/已完成任务
        3. op=update_status 时更新指定任务状态，完成时自动解锁后续任务，可选取消剩余任务
        """
    )

    args_schema: Type[BaseModel] = TaskManagerArgs

    token: str = ""
    user_id: str = ""
    background: str = ""
    session_type: str = "redis"
    session: Optional[BaseChatHistorySession] = None
    task_list_manager: Optional[TaskManager] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.session is None:
            self.session = CreateSession(self.session_type)
        if not isinstance(self.session, RedisHistorySession):
            raise ToolFatalError("TaskManagerTool 目前仅支持 RedisHistorySession")
        # 任务列表的状态计算/更新为纯内存逻辑，不需要 session
        self.task_list_manager = TaskManager()

    # ---------------- Redis 相关 ----------------

    def _get_redis_key(self, session_id: str) -> str:
        """根据会话ID生成 Redis key（与 todo_list_tool 一致）"""
        return f"{TOOL_NAME}/session/{session_id}"

    def _load_task_obj(self, session_id: str) -> Optional[Dict[str, Any]]:
        """通过会话ID获取任务列表对象"""
        if not isinstance(self.session, RedisHistorySession):
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
            logger.warning(f"[TaskManagerTool] 解析 Redis 中的任务列表失败: {e}")
            return None
        tasks: List[Dict[str, Any]] = data.get("tasks", [])
        status = data.get("status", "")
        if not tasks:
            return None
        if status == "completed" or all(t.get("status") == "completed" for t in tasks):
            return None
        return data

    def _save_task_obj(self, session_id: str, task_obj: Dict[str, Any]) -> None:
        """保存任务列表对象"""
        if not isinstance(self.session, RedisHistorySession):
            raise ToolFatalError("当前 session 非 RedisHistorySession")
        key = self._get_redis_key(session_id)
        try:
            value = json.dumps(task_obj, ensure_ascii=False)
            self.session.client.setex(key, CACHE_EXPIRE_TIME, value)
        except Exception as e:
            logger.error(f"[TaskManagerTool] 保存任务列表失败: {e}")
            raise ToolFatalError(f"保存任务列表到缓存失败: {str(e)}")

    def _delete_task_obj(self, session_id: str) -> None:
        """删除会话对应的任务列表"""
        if not isinstance(self.session, RedisHistorySession):
            return
        key = self._get_redis_key(session_id)
        try:
            self.session.client.delete(key)
        except Exception as e:
            logger.error(f"[TaskManagerTool] 删除任务列表失败: {e}")
            raise ToolFatalError(f"删除任务列表失败: {str(e)}")

    # ---------------- 获取可执行任务 / 更新状态 ----------------

    def get_runnable_tasks(self, session_id: str) -> Dict[str, Any]:
        """获取当前会话可执行任务"""
        if not session_id or not session_id.strip():
            raise ToolFatalError("session_id 参数不能为空")
        task_obj = self._load_task_obj(session_id)
        if not task_obj:
            return {
                "result": "当前会话没有未完成的任务列表",
                "session_id": session_id,
                "tasks": [],
                "runnable_tasks": [],
                "blocked_tasks": [],
                "completed_tasks": [],
                "status": "empty",
            }
        result = self.task_list_manager.get_runnable_from_obj(task_obj)
        return {
            "result": "获取可执行任务成功",
            "session_id": session_id,
            "tasks": result.get("tasks", []),
            "runnable_tasks": result.get("runnable_tasks", []),
            "blocked_tasks": result.get("blocked_tasks", []),
            "completed_tasks": result.get("completed_tasks", []),
            "status": result.get("status", task_obj.get("status", "pending")),
        }

    def update_task_status(
        self,
        session_id: str,
        task_id: int,
        status: str,
        adjust: bool = False,
        reason: str = "",
    ) -> Dict[str, Any]:
        """更新任务状态"""
        if not session_id or not session_id.strip():
            raise ToolFatalError("session_id 参数不能为空")
        task_obj = self._load_task_obj(session_id)
        if not task_obj:
            raise ToolFatalError("当前会话没有可更新的任务列表")
        res = self.task_list_manager.update_task_in_obj(
            task_obj=task_obj,
            task_id=task_id,
            status=status,
            adjust=adjust,
            reason=reason,
        )
        updated_obj: Dict[str, Any] = res.get("task_obj", task_obj)
        overall_status: str = res.get("status", updated_obj.get("status", "pending"))
        tasks: List[Dict[str, Any]] = res.get("tasks", updated_obj.get("tasks", []))
        all_finished: bool = res.get("all_finished", False)
        if all_finished:
            self._delete_task_obj(session_id)
            return {
                "result": "所有任务已完成或取消，任务列表已删除",
                "session_id": session_id,
                "status": "completed",
                "tasks": tasks,
            }
        self._save_task_obj(session_id, updated_obj)
        return {
            "result": "更新任务状态成功",
            "session_id": session_id,
            "status": overall_status,
            "tasks": tasks,
            "runnable_tasks": res.get("runnable_tasks", []),
            "blocked_tasks": res.get("blocked_tasks", []),
            "completed_tasks": res.get("completed_tasks", []),
        }

    # ---------------- LLMTool 接口实现 ----------------

    @construct_final_answer
    def _run(
        self,
        session_id: str,
        op: str = "get_runnable",
        task_id: Optional[int] = None,
        status: Optional[str] = None,
        adjust: bool = False,
        reason: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """同步执行任务管理操作"""
        return asyncio.run(
            self._arun(
                session_id=session_id,
                op=op,
                task_id=task_id,
                status=status,
                adjust=adjust,
                reason=reason,
                run_manager=run_manager,
            )
        )

    @async_construct_final_answer
    async def _arun(
        self,
        session_id: str,
        op: str = "get_runnable",
        task_id: Optional[int] = None,
        status: Optional[str] = None,
        adjust: bool = False,
        reason: str = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """异步执行任务管理操作"""
        if not session_id or not session_id.strip():
            raise ToolFatalError("session_id 参数不能为空")
        if op == "get_runnable":
            return self.get_runnable_tasks(session_id)
        if op == "update_status":
            if task_id is None:
                raise ToolFatalError("task_id 参数不能为空（op 为 update_status 时）")
            if not status:
                raise ToolFatalError("status 参数不能为空（op 为 update_status 时）")
            return self.update_task_status(
                session_id=session_id,
                task_id=task_id,
                status=status,
                adjust=adjust,
                reason=reason,
            )
        raise ToolFatalError(f"不支持的操作类型 op={op}")

    # ---------------- 配置与 API 封装（与 todo_list_tool 一致） ----------------

    @classmethod
    def from_config(cls, params: Dict[str, Any]) -> "TaskManagerTool":
        """
        从配置创建工具实例。本工具不依赖 LLM，llm 传 None；auth/config 与 todo_list_tool 保持一致。
        """
        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")
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
                logger.error(f"[TaskManagerTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e
        config_dict = params.get("config", {})
        return cls(
            llm=None,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
        )

    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(cls, params: dict) -> Dict[str, Any]:
        """
        将任务管理工具转换为异步 API 类方法，供外部 HTTP 调用。
        请求体需包含 session_id、op，当 op 为 update_status 时需 task_id、status。
        """
        auth_dict = params.get("auth", {})
        token = auth_dict.get("token", "")
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
                logger.error(f"[TaskManagerTool] get token error: {e}")
                raise ToolFatalError(reason="获取 token 失败", detail=e) from e
        config_dict = params.get("config", {})
        tool = cls(
            llm=None,
            token=token,
            user_id=auth_dict.get("user_id", ""),
            background=config_dict.get("background", ""),
            session=RedisHistorySession(),
            session_type=config_dict.get("session_type", "redis"),
        )
        session_id = params.get("session_id", "")
        op = params.get("op", "get_runnable")
        task_id = params.get("task_id")
        status = params.get("status")
        adjust = params.get("adjust", False)
        reason = params.get("reason", "")
        return await tool.ainvoke(
            input={
                "session_id": session_id,
                "op": op,
                "task_id": task_id,
                "status": status,
                "adjust": adjust,
                "reason": reason,
            }
        )

    @staticmethod
    async def get_api_schema() -> Dict[str, Any]:
        """获取 API Schema，便于自动注册为 HTTP API。"""
        return {
            "post": {
                "summary": TASK_MANAGER_TOOL_NAME,
                "description": "任务管理工具：获取可执行任务、更新任务状态。与 todo_list_tool 共用 Redis 任务列表。",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "auth": {
                                        "type": "object",
                                        "description": "认证参数（与 todo_list_tool 一致）",
                                        "properties": {
                                            "auth_url": {
                                                "type": "string",
                                                "description": "认证服务URL（可选，获取 token 时使用）",
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
                                        "description": "工具配置参数（可选）",
                                        "properties": {
                                            "session_type": {
                                                "type": "string",
                                                "description": "会话类型（可选）",
                                                "default": "redis",
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "背景信息（可选）",
                                            },
                                        },
                                    },
                                    "session_id": {
                                        "type": "string",
                                        "description": "会话ID（必填）",
                                    },
                                    "op": {
                                        "type": "string",
                                        "description": "操作：get_runnable | update_status（必填）",
                                        "enum": ["get_runnable", "update_status"],
                                    },
                                    "task_id": {
                                        "type": "integer",
                                        "description": "op=update_status 时必填",
                                    },
                                    "status": {
                                        "type": "string",
                                        "description": "op=update_status 时必填",
                                    },
                                    "adjust": {
                                        "type": "boolean",
                                        "description": "是否需要根据当前任务结果调整后续任务（可选）",
                                        "default": False,
                                    },
                                    "reason": {
                                        "type": "string",
                                        "description": "调整原因说明，仅在 adjust 为 True 时有意义（可选）"
                                    },
                                },
                                "required": ["session_id", "op"],
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
                                                    "title": {
                                                        "type": "string"
                                                    },
                                                    "detail": {
                                                        "type": "string"
                                                    },
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
                                                    "blockedBy": {"type": "array", "items": {"type": "integer"}},
                                                    "status": {"type": "string"},
                                                },
                                            },
                                        },
                                        "runnable_tasks": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        },
                                        "blocked_tasks": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        },
                                        "completed_tasks": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }

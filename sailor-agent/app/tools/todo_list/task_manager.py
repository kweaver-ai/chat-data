from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.errors import ToolFatalError
from app.logs.logger import logger


class TaskStatus(str, Enum):
    """
    单个子任务的状态枚举。

    - pending: 尚未开始执行
    - running: 正在执行中
    - completed: 已正常执行完成
    - failed: 执行失败，后续可能需要人工或其他逻辑介入
    - cancelled: 被上层逻辑取消，不再执行
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskListStatus(str, Enum):
    """
    任务列表（整组任务）的整体状态枚举。

    - pending: 还没开始执行，所有子任务都处于 pending
    - running: 部分子任务已完成，仍有待执行或执行中的任务
    - completed: 所有子任务都已结束（完成/失败/取消），列表生命周期结束
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class TaskManager:
    """
    纯内存任务管理器，不关心存储与会话，只负责：
    - 计算当前任务列表中可执行/被阻塞/已完成的任务
    - 更新某个任务的状态
    - 在任务完成时解锁依赖它的任务
    - 计算任务列表整体状态

    任务结构与 TodoListTool 生成的结构保持一致：
    task_obj = {
      "query": "...",
      "status": "pending|running|completed",
      "tasks": [
        {
          "id": 1,
          "title": "任务标题",
          "detail": "任务详细内容",
          "tools": [{"name": "tool_name", "inputs": "...", "outputs": "..."}],
          "blockedBy": [],
          "status": "pending"
        },
        ...
      ]
    }
    """

    @staticmethod
    def split_tasks_by_status_and_dependency(
        tasks: List[Dict[str, Any]]
    ) -> Tuple[
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
    ]:
        """
        根据任务状态和依赖拆分任务：
        - runnable: 状态为 pending 且 blockedBy 为空
        - blocked: 非 completed，且 blockedBy 不为空
        - completed: 状态为 completed
        """
        runnable: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []
        completed: List[Dict[str, Any]] = []

        for t in tasks:
            status = t.get("status", TaskStatus.PENDING.value)
            blocked_by = t.get("blockedBy") or []
            if status == TaskStatus.COMPLETED.value:
                completed.append(t)
            elif status == TaskStatus.PENDING.value and not blocked_by:
                runnable.append(t)
            else:
                blocked.append(t)

        return runnable, blocked, completed

    @staticmethod
    def recalculate_overall_status(tasks: List[Dict[str, Any]]) -> str:
        """
        根据子任务状态计算任务列表整体状态
        - 全部处于终态（completed/failed/cancelled）: completed
        - 存在 pending/running: running
        - 其他情况: pending
        """
        if not tasks:
            return TaskListStatus.COMPLETED.value

        terminal_statuses = (
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        )
        all_terminal = all(
            t.get("status") in terminal_statuses for t in tasks
        )
        any_pending_or_running = any(
            t.get("status") in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value)
            for t in tasks
        )

        if all_terminal:
            return TaskListStatus.COMPLETED.value
        if any_pending_or_running:
            return TaskListStatus.RUNNING.value
        return TaskListStatus.PENDING.value

    @staticmethod
    def unlock_dependent_tasks(
        tasks: List[Dict[str, Any]],
        finished_task_id: int,
    ) -> None:
        """
        在某个任务完成后，自动解锁后续任务：
        - 将其从其他任务的 blockedBy 列表中移除
        """
        for t in tasks:
            blocked_by = t.get("blockedBy") or []
            if finished_task_id in blocked_by:
                t["blockedBy"] = [i for i in blocked_by if i != finished_task_id]

    def get_runnable_from_obj(
        self,
        task_obj: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        基于内存中的 task_obj 计算：
        - runnable_tasks: 当前可以执行的任务
        - blocked_tasks: 被前置任务阻塞的任务
        - completed_tasks: 已完成任务
        """
        tasks: List[Dict[str, Any]] = task_obj.get("tasks", []) or []
        if not tasks:
            return {
                "tasks": [],
                "runnable_tasks": [],
                "blocked_tasks": [],
                "completed_tasks": [],
                "status": "empty",
            }

        runnable, blocked, completed = self.split_tasks_by_status_and_dependency(tasks)
        # 按任务 id 升序返回“最先可执行”的任务（可并行多个）
        runnable.sort(key=lambda x: int(x.get("id", 0)))

        return {
            "tasks": tasks,
            "runnable_tasks": runnable,
            "blocked_tasks": blocked,
            "completed_tasks": completed,
            "status": task_obj.get("status", "pending"),
        }

    def update_task_in_obj(
        self,
        task_obj: Dict[str, Any],
        task_id: int,
        status: str,
        adjust: bool = False,
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        在给定的 task_obj 上更新任务状态（纯内存，不做持久化）：

        - 更新 task_id 对应任务的 status
        - status == "completed" 时，自动解锁依赖该任务的后续任务
        - adjust == True 时，将其余未完成任务标记为 cancelled
        - 返回：更新后的 task_obj 以及拆分出的 runnable/blocked/completed 列表
        """
        tasks: List[Dict[str, Any]] = task_obj.get("tasks", []) or []

        target: Optional[Dict[str, Any]] = None
        for t in tasks:
            if int(t.get("id")) == int(task_id):
                target = t
                break

        if not target:
            raise ToolFatalError(f"未在任务列表中找到 id={task_id} 的任务")

        old_status = target.get("status")
        target["status"] = status
        logger.info(
            f"[TaskManager] update task status: "
            f"id={task_id}, {old_status} -> {status}, adjust={adjust}"
        )

        if status == TaskStatus.COMPLETED.value:
            self.unlock_dependent_tasks(tasks, int(task_id))

        if adjust:
            for t in tasks:
                if t is target:
                    continue
                if t.get("status") not in (
                    TaskStatus.COMPLETED.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.CANCELLED.value,
                ):
                    t["status"] = TaskStatus.CANCELLED.value
            logger.info(
                f"[TaskManager] adjust tasks for task_id={task_id}, reason={reason}"
            )

        overall_status = self.recalculate_overall_status(tasks)
        task_obj["status"] = overall_status

        runnable, blocked, completed = self.split_tasks_by_status_and_dependency(tasks)

        # 是否整体结束：全部任务已结束，或当前更新的是「最后一个任务」且其状态已终止，则视为整体结束并由上层删除列表
        terminal_statuses = (
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        )
        all_finished = all(t.get("status") in terminal_statuses for t in tasks)
        if not all_finished and tasks:
            last_task_id = max(int(t.get("id")) for t in tasks)
            if int(task_id) == last_task_id and status in terminal_statuses:
                all_finished = True  # 最后一个任务已结束，直接视为整体结束，由上层删除任务列表

        return {
            "task_obj": task_obj,
            "status": overall_status,
            "tasks": tasks,
            "runnable_tasks": runnable,
            "blocked_tasks": blocked,
            "completed_tasks": completed,
            "all_finished": all_finished,
        }


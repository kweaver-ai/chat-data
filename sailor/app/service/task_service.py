# -*- coding: utf-8 -*-
"""
异步任务管理服务
用于管理异步任务的创建、状态查询和结果获取
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from app.utils.id_generator import generate_snowflake_id
from app.session.redis_session import RedisHistorySession
from app.logs.logger import logger


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class TaskService:
    """任务管理服务"""
    
    def __init__(self, redis_client=None):
        """
        初始化任务服务
        
        Args:
            redis_client: Redis客户端，如果为None则创建新的连接
        """
        if redis_client:
            self.redis_client = redis_client
        else:
            session = RedisHistorySession()
            self.redis_client = session.client
        
        # 任务数据在Redis中的过期时间（秒），默认7天
        self.task_ttl = 7 * 24 * 60 * 60
    
    def _get_task_key(self, task_id: str) -> str:
        """获取任务在Redis中的key"""
        return f"task:{task_id}"
    
    def create_task(
        self,
        task_type: str,
        params: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """
        创建新任务
        
        Args:
            task_type: 任务类型，如 "semantic_and_business_analysis"
            params: 任务参数
            user_id: 用户ID（可选）
            
        Returns:
            任务ID
        """
        task_id = str(generate_snowflake_id())
        
        task_data = {
            "task_id": task_id,
            "task_type": task_type,
            "status": TaskStatus.PENDING.value,
            "params": params,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
            "progress": 0
        }
        
        # 存储任务数据到Redis
        task_key = self._get_task_key(task_id)
        self.redis_client.setex(
            task_key,
            self.task_ttl,
            json.dumps(task_data, ensure_ascii=False)
        )
        
        logger.info(f"创建任务: task_id={task_id}, task_type={task_type}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典，如果任务不存在则返回None
        """
        task_key = self._get_task_key(task_id)
        task_data_str = self.redis_client.get(task_key)
        
        if not task_data_str:
            return None
        
        try:
            task_data = json.loads(task_data_str)
            return task_data
        except json.JSONDecodeError as e:
            logger.error(f"解析任务数据失败: task_id={task_id}, error={e}")
            return None
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        progress: Optional[int] = None
    ) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 任务状态
            result: 任务结果（可选）
            error: 错误信息（可选）
            progress: 进度百分比（0-100，可选）
            
        Returns:
            是否更新成功
        """
        task_data = self.get_task(task_id)
        if not task_data:
            logger.warning(f"任务不存在: task_id={task_id}")
            return False
        
        # 更新任务数据
        task_data["status"] = status.value
        task_data["updated_at"] = datetime.now().isoformat()
        
        if result is not None:
            task_data["result"] = result
        
        if error is not None:
            task_data["error"] = error
        
        if progress is not None:
            task_data["progress"] = progress
        
        # 保存到Redis
        task_key = self._get_task_key(task_id)
        self.redis_client.setex(
            task_key,
            self.task_ttl,
            json.dumps(task_data, ensure_ascii=False)
        )
        
        logger.info(f"更新任务状态: task_id={task_id}, status={status.value}")
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否删除成功
        """
        task_key = self._get_task_key(task_id)
        deleted = self.redis_client.delete(task_key)
        
        if deleted:
            logger.info(f"删除任务: task_id={task_id}")
        else:
            logger.warning(f"删除任务失败，任务不存在: task_id={task_id}")
        
        return deleted > 0
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态（简化版本，只返回状态相关信息）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息，包含 status, progress, created_at, updated_at
        """
        task_data = self.get_task(task_id)
        if not task_data:
            return None
        
        return {
            "task_id": task_data.get("task_id"),
            "task_type": task_data.get("task_type"),
            "status": task_data.get("status"),
            "progress": task_data.get("progress", 0),
            "created_at": task_data.get("created_at"),
            "updated_at": task_data.get("updated_at"),
            "error": task_data.get("error")
        }
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果，如果任务未完成或不存在则返回None
        """
        task_data = self.get_task(task_id)
        if not task_data:
            return None
        
        status = task_data.get("status")
        if status not in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
            return None
        
        return {
            "task_id": task_data.get("task_id"),
            "status": status,
            "result": task_data.get("result"),
            "error": task_data.get("error"),
            "created_at": task_data.get("created_at"),
            "updated_at": task_data.get("updated_at")
        }

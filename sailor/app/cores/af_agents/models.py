from pydantic import BaseModel, Field
from typing import Union, Optional, List, Dict
from enum import Enum


class AgentQAModel(BaseModel):
    """
    Data product Q&A model
    """

    # User information
    agent_id: str = Field(..., description="agent_id")
    agent_key: str = Field(..., description="agent_key")
    agent_version: str = Field(..., description="agent_version，可以指定版本，默认值为latest")
    stream: bool = Field(..., description="是否流式返回")
    inc_stream: bool = Field(..., description="是否增量流式返回，仅在stream为true时有效")
    conversation_id: str = Field(..., description="会话ID")

    # Question and resource information
    query: str = Field(..., description="用户提问问题")

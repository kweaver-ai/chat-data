from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union


# class AfChatInputModel(BaseModel):
#     query: str
#     session_id: str
#     authorization: str
#     appid: str


class AfChatInputModel(BaseModel):
    subject_id: str
    subject_type: str
    af_editions: str
    session_id: str
    stream: Optional[bool] = True
    query: str
    limit: Optional[int] = 5
    stopwords: List
    stop_entities: Union[List, None]
    filter: Union[Dict, None]
    ad_appid: str
    kg_id: int
    entity2service: Union[Dict, None]
    required_resource: Union[Dict, None]


class Role:
    AI: str = "专家"
    HUMAN: str = "用户"


class Params(BaseModel):
    param: str


class Action(BaseModel):
    action: str
    action_input: Params


class AnyFabricEndpointModel(BaseModel):
    query: str = Field(..., description="向工具提供的问题")

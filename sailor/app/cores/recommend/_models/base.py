"""
@File: base.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 各种模型
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List


############################################## 通用 枚举值
class STATUS(str, Enum):
    """
    状态枚举类
    """
    SUCCESS = 'success'
    FAILURE = 'fail'

class TASK_TYPE(str, Enum):
    """
    任务类型
    """
    RECOMMEND = 'recommend'
    CHECK = 'check'
    ALIGN = 'align'
    GENERATE = 'generate'

############################################## 算法的通用 Model
class QueryParameters(BaseModel):
    top_n: Optional[int] = 10
    query_min_score: Optional[float] = 0.75  # 关键字检索得分
    vector_min_score: Optional[float] = 0.75 # 向量检索得分

class RuleParameters(BaseModel):
    # 规则应用模块
    with_execute: Optional[bool] = None   # 默认不会执行这个模块
    name: Optional[str] = None # 规则名称
    # TODO: 规则参数

class MLParameters(BaseModel):
    # 机器学习模块
    with_execute: Optional[bool] = None # 默认不会执行这个模块
    name: Optional[str] = None  # 算法名称
    # TODO：算法参数

class LLMParameters(BaseModel):
    # 大模型模块
    with_execute: Optional[bool] = None # 默认不会执行这个模块
    llm_name: Optional[str] = None  # 大模型的名称
    prompt_name: Optional[str] = None   # 提示词的名称
    pass

class RequestParams(BaseModel):
    rule: Optional[RuleParameters] = RuleParameters()
    ml: Optional[MLParameters] = MLParameters()
    llm: Optional[LLMParameters] = LLMParameters()

class ResponseParams(BaseModel):
    with_all: Optional[bool] = None    # 所有中间结果都返回
    with_recall: Optional[bool] = None # 是否需要召回结果
    with_rank: Optional[bool] = None # 是否需要重排序结果
    with_filter: Optional[bool] = None # 是否需要过滤结果
    with_align: Optional[bool] = None # 是否需要对齐结果
    with_generate: Optional[bool] = None # 是否需要生成结果
    with_check: Optional[bool] = None # 是否需要校验结果


class ConfigParams(BaseModel):
    query: Optional[QueryParameters] = QueryParameters()    # 召回阶段的得分
    # recall: Optional[ConfigParams] = None # 默认都会有这个模块
    # rank: Optional[ConfigParams] = None # 默认都会有这个模块
    filter: Optional[RequestParams] = RequestParams()
    align: Optional[RequestParams] = RequestParams()
    generate: Optional[RequestParams] = RequestParams()
    check: Optional[RequestParams] = RequestParams()
    log: Optional[ResponseParams] = ResponseParams()
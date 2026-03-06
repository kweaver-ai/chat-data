# -*- coding: utf-8 -*-
# @Time : 2024/1/31 13:56
# @Author : KaiNing.Zhang

from pydantic import BaseModel, Field


class AFQAInputParameterModel(BaseModel):
    host: str = Field(..., description="认知助手所在服务器的url", example="https://10.4.113.103")
    query: str = Field(..., description="用户的问题", example="xxx信息技术股份有限公司有哪些产品")
    user: str = Field(..., description="后台存储了多轮对话的历史信息，根绝user来获取相应对话历史信息", example="foo")
    token: str = Field(..., description="用户鉴权的字符串", example="Bearer ory_at_b9tUg-YGpkS_t3sVytOrWPa4lTEz_9sJpV9fyUYr5rA.2jsKxtgAd3iVp_x8spsv4ls4YAlNOW-rH9skqczeJnw")

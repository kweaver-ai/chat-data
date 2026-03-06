# -*- coding: utf-8 -*-
# @Time : 2023/12/20 20:13
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : prompt_handler.py
# @Project : copilot
from fastapi import APIRouter
from pydantic import BaseModel
from app.routers import PromptRouter
from app.cores.prompt.prompt_demo import prompt


prompt_router = APIRouter()


class PromptParams(BaseModel):  # 继承了BaseModel
    role: str
    content: str


@prompt_router.post(PromptRouter, include_in_schema=False)
def prompt_api(params: PromptParams):
    return {"res": prompt(params.role, params.content)}

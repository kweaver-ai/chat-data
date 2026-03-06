# -*- coding: utf-8 -*-
# @Time : 2023/12/20 20:14
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : text2sql_handler.py
# @Project : copilot
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.routers import Text2SqlRouter
from app.cores.text2sql.t2s import Text2SQL
from typing import Optional

text2sql_router = APIRouter()


class Text2sqlParams(BaseModel):  # 继承了BaseModel
    user: str
    appid: str
    query: str
    search: Optional[list] = None


@text2sql_router.post(Text2SqlRouter, include_in_schema=False)
async def text2sql_api(request: Request, params: Text2sqlParams):
    t2s = Text2SQL(
        user=params.user,
        appid=params.appid,
        query=params.query,
        headers={"Authorization": request.headers.get('Authorization')}
    )
    print(params)
    return await t2s.call(params.search)

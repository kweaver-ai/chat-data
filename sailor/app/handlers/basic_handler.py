# -*- coding: utf-8 -*-
# @Time : 2023/12/21 9:45
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : basic_handler.py
# @Project : copilot
from fastapi import APIRouter
from app.routers import ReadyRouter, AliveRouter
basic_router = APIRouter()


@basic_router.get(ReadyRouter, include_in_schema=False)
def health_ready():
    return {"res": 0}


@basic_router.get(AliveRouter, include_in_schema=False)
def health_alive():
    return {"res": 0}

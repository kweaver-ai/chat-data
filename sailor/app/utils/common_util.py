# -*- coding: utf-8 -*-
# @Time : 2023/10/16 14:25
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : common_util.py
# @Project : mf-models-ie
from datetime import datetime


async def write_log(api=None, msg=None, user='root'):
    """
    :param api:
    :param msg:
    :param user:
    :return:
    """
    with open("log.log", mode="a", encoding='utf-8') as log:
        now = datetime.now()
        log.write(f"时间：{now}    API调用事件：{api}    用户：{user}    消息：{msg}\n")

"""
@File: Params.py
@Date:2024-08-07
@Author : Danny.gao
@Desc:
"""

import json
from enum import Enum


class Task_Status(Enum):
    INIT = 'Init'
    PROCESSING = 'Processing'
    PROCESSED = 'Processed'
    FAIL = 'Fail'
    SUCCESS = 'Success'


class Task_Info(Enum):
    INIT_INFO = '初始化'
    PROCESSING_INFO = '正在执行数据元补全任务'
    PROCESSED_INFO = '补全完成，但还没有发送kafka消息'
    FAIL_EX_INFO = '失败：超时（或许时pod重启，或许是补全时间过长），或者未知任务ID'
    FAIL_SEND_INFO = '失败：kafka消息发送，返回状态错误'
    FAIL_ERROR_INFO = '失败：补全报错, {e}'
    SUCCESS_INFO = '补全完成，且kafka消息发送成功'


class EnumEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Enum):
            return o.name  # 返回枚举成员的名称作为字符串
        return json.JSONEncoder.default(self, o)


# print(Task_Info.SUCCESS_INFO.value)
# -*- coding: utf-8 -*-
# @Time : 2023/12/20 19:32
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : chat_demo.py
# @Project : copilot

chat_dict = {
    "你好": "你好",
    "你是谁？": "我是Sailor对话机器人",
    "一年有几个月？": "一年有12个月"
}


def chat_func(input_str):
    if input_str in chat_dict:
        return chat_dict[input_str]
    else:
        return "对不起，不理解你的问题，请重新输入信息"

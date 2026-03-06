# -*- coding: utf-8 -*-
# @Time : 2023/12/27 17:01
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : baichuan2.py
# @Project : copilot
# from llmadapter.llms.llm_factory import llm_factory
# from llmadapter.schema import SystemMessage, HumanMessage, AIMessage


class BaiChuan2LLM(object):

    def __init__(self, openai_api_base, temperature=0.5, max_tokens=500, max_retries=10):
        # self.llm = llm_factory.create_llm("openai",
        #                              openai_api_base=openai_api_base,
        #                              model="baichuan2",
        #                              temperature=temperature,
        #                              max_tokens=max_tokens, max_retries=max_retries)
        self.llm = dict()

    def predict(self, input_prompt):
        return self.llm.predict(input_prompt, max_tokens=100)

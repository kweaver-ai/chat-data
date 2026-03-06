# -*- coding: utf-8 -*-
# @Time    : 2025/11/16 21:24
# @Author  : Glen.lv
# @File    : graph_func_manager
# @Project : af-sailor
from app.cores.cognitive_assistant.qa_api import FindNumberAPI


class GraphFunctionManager:
    def __init__(self):
        self.find_number_api = FindNumberAPI()

    async def graph_analysis(self, hits, properties_alias, entity_types, search_params,
                             request, source_type, graph_filter_params, data_params, re_limit=30):
        # 原 graph_analysis 函数的实现
        pass

    async def graph_analysis_no_auth(self, hits, properties_alias, entity_types, search_params,
                                     request, source_type, graph_filter_params, data_params, re_limit=30):
        # 原 graph_analysis_no_auth 函数的实现
        pass

    async def graph_analysis_formview(self, hits, properties_alias, entity_types, search_params,
                                      request, source_type, graph_filter_params, data_params):
        # 原 graph_analysis_formview 函数的实现
        pass

    async def get_kgotl(self, search_params, output, query, data_params_file_path, graph_filter_params):
        # 原 get_kgotl 函数的实现
        pass

    async def get_kgotl_qa(self, search_params):
        # 原 get_kgotl_qa 函数的实现
        pass


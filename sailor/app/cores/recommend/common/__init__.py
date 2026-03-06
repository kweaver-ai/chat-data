"""
@File: __init_.py
@Date:2024-03-12
@Author : Danny.gao
@Desc:
"""


# from app.cores.recommend.common.get_ad_builder import ad_opensearch_connector
# from app.cores.recommend.common.get_ad_infos import ad_basic_infos_connector
# from app.cores.recommend.common.get_embeddings import m3e_embeddings
from app.cores.recommend.common.get_params import af_params_connector
from app.cores.recommend.common._api import LLMServices
llm_func = LLMServices()

from app.cores.prompt.manage.ad_service import PromptServices
ad_service = PromptServices()
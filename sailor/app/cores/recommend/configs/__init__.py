"""
@File: __init_.py
@Date:2024-03-11
@Author : Danny.gao
@Desc: 参数配置
"""

""" opensearch检索引擎：参数 """
from app.cores.recommend.configs.config_recall import recall_table_params, recall_flow_params, \
    recall_code_params, recall_check_code_params, recall_view_params, recall_label_params, \
    recall_check_indicator_params, recall_field_subject_params,  recall_field_rule_params, \
    recall_explore_rule_params

from app.cores.recommend.configs.config_rank import rank_table_params, rank_flow_params, \
    rank_code_params, rank_check_code_params, rank_view_params, rank_label_params, \
    rank_check_indicator_params, rank_field_subject_params, rank_field_rule_params, \
    rank_explore_rule_params

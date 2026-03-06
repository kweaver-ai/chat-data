"""
@File: __init_.py
@Date:2024-02-26
@Author : Danny.gao
@Desc: 推荐模型
"""

from app.cores.recommend.configs import recall_table_params, recall_flow_params, \
    recall_code_params, recall_check_code_params, recall_view_params, recall_label_params, \
    recall_check_indicator_params, recall_field_subject_params, recall_field_rule_params, \
    recall_explore_rule_params
from app.cores.recommend.configs import rank_table_params, rank_flow_params, \
    rank_code_params, rank_check_code_params, rank_view_params, rank_label_params, \
    rank_check_indicator_params, rank_field_subject_params, rank_field_rule_params, \
    rank_explore_rule_params

from app.cores.recommend.models.model_recall import ModelRecall
from app.cores.recommend.models.model_rank import ModelRank
from app.cores.recommend.models.model_filter import ModelFilter
from app.cores.recommend.models.model_check import ModelCheck
from app.cores.recommend.models.model_align import ModelAlign
from app.cores.recommend.models.model_generate import ModelGenerate

table_recall = ModelRecall(params=recall_table_params)
flow_recall = ModelRecall(params=recall_flow_params)
code_recall = ModelRecall(params=recall_code_params)
view_recall = ModelRecall(params=recall_view_params)
label_recall = ModelRecall(params=recall_label_params)
field_subject_recall = ModelRecall(params=recall_field_subject_params)
field_rule_recall = ModelRecall(params=recall_field_rule_params)
explore_rule_recall = ModelRecall(params=recall_explore_rule_params)
check_code_recall = ModelRecall(params=recall_check_code_params)
check_indicator_recall = ModelRecall(params=recall_check_indicator_params)

table_rank = ModelRank(params=rank_table_params)
flow_rank = ModelRank(params=rank_flow_params)
code_rank = ModelRank(params=rank_code_params)
view_rank = ModelRank(params=rank_view_params)
label_rank = ModelRank(params=rank_label_params)
field_subject_rank = ModelRank(params=rank_field_subject_params)
field_rule_rank = ModelRank(params=rank_field_rule_params)
explore_rule_rank = ModelRank(params=rank_explore_rule_params)
check_code_rank = ModelRank(params=rank_check_code_params)
check_indicator_rank = ModelRank(params=rank_check_indicator_params)

label_filter = ModelFilter()
fiel_rule_filter = ModelFilter()
explore_rule_filter = ModelFilter()

check_code_check = ModelCheck()
check_indicator_check = ModelCheck()

field_subject_align = ModelAlign()

explore_rule_generate = ModelGenerate() 





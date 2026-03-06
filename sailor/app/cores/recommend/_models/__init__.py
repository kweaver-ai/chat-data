"""
@File: __init__.py.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from app.cores.recommend._models.base import ConfigParams
from app.cores.recommend._models.dict_params import DictParams

from app.cores.recommend._models.rec.table import RecommendTableParams
from app.cores.recommend._models.rec.flow import RecommendFlowParams
from app.cores.recommend._models.rec.code import RecommendCodeParams
from app.cores.recommend._models.rec.rule import RecommendFieldRuleParams
from app.cores.recommend._models.rec.view import RecommendViewParams
from app.cores.recommend._models.rec.label import RecommendLabelParams
from app.cores.recommend._models.rec.subject_model import RecommendSubjectModelParams

from app.cores.recommend._models.check.code import CheckCodeParams
from app.cores.recommend._models.check.indicator import CheckIndicatorParams

from app.cores.recommend._models.generate.explore_rule import RecommendExploreRuleParams

from app.cores.recommend._models.align.field_subject import RecommendFieldSubjectParams

""" opensearch检索引擎：参数 """

__all__ = [
    'ConfigParams',
    'DictParams',
    'RecommendTableParams',
    'RecommendFlowParams',
    'RecommendCodeParams',
    'RecommendFieldRuleParams',
    'RecommendViewParams',
    'RecommendLabelParams',
    'CheckCodeParams',
    'CheckIndicatorParams',
    'RecommendExploreRuleParams',
    'RecommendFieldSubjectParams',
    'RecommendSubjectModelParams'
]
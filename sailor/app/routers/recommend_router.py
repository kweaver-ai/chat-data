# -*- coding: utf-8 -*-

"""
@Time ：2024/1/5 10:03
@Auth ：Danny.gao
@File ：recommend_router.py
@Desc ：AF 智能推荐接口：表单推荐、流程推荐、标准推荐、字段标准一致性校验
@Motto：ABC(Always Be Coding)
"""

RecommendTableRouter = '/v1/recommend/table'    # 推荐表单
RecommendFlowRouter = '/v1/recommend/flow'  # 推荐流程
RecommendCodeRouter = '/v1/recommend/code'  # 推荐标准
CheckCodeRouter = '/v1/internal/recommend/check/code'   # 标准一致性
CheckIndicatorRouter = '/v1/internal/recommend/check/indicator' # 指标一致性
RecommendViewRouter = '/v1/recommend/view'  # 推荐视图
RecommendLabelRouter = '/v1/internal/recommend/label'   # 推荐标签
RecommendSubjectModelRouter = '/v1/internal/recommend/subject_model'   # 推荐主题模型 $
RecommendFieldSubjectRouter = '/v1/internal/recommend/field/subject' # 业务对象识别
RecommendFieldRuleRouter = '/v1/internal/recommend/field/rule'  # 推荐编码规则 $
RecommendExploreRuleRouter = '/v1/internal/recommend/explore/rule'  # 推荐质量规则


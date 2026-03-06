# -*- coding: utf-8 -*-
# @Time    : 2024/1/21 11:58
# @Author  : Glen.lv
# @File    : cognitive_search_router
# @Project : copilot

# 废弃
AssetSearchRouter = "/v1/search/cognitive_search/asset_search"
# 目录版搜索列表
CatalogSearchRouter = "/v1/search/cognitive_search/catalog_search"
# 资源版搜索列表
ResourceSearchRouter = "/v1/search/cognitive_search/resource_search"
# 资源版分析型搜索
ResourceAnalysisRouter = "/v1/search/cognitive_search/resource_analysis_search"

# 资源版分析型搜索(增加部门职责知识增强)
# 基于部门职责的知识增强
# 接口沿用资源版分析性搜索接口，对接新的处理函数
# ResourceAnalysisKECCRouter = "/v1/search/cognitive_search/resource_analysis_kecc_search"

# 目录版分析型搜索
CatalogAnalysisRouter = "/v1/search/cognitive_search/catalog_analysis_search"

# 场景分析,资源版搜索列表部分
# 列表 复用认知搜索列表，ResourceSearchRouter = "/v1/search/cognitive_search/resource_search"
# 场景分析,资源版分析型搜索部分,
FormviewAnalysisRouter = "/v1/search/cognitive_search/formview_analysis_search"

# 场景分析,目录版搜索列表部分
"""认知搜索——列表部分"""
FormviewSearchCatalogRouter = "/v1/search/cognitive_search/formview_search_catalog"
# 场景分析，目录版分析型搜索部分,
"""认知搜索——分析型问答部分"""
FormviewAnalysisCatalogRouter = "/v1/search/cognitive_search/formview_analysis_catalog"



# -*- coding: utf-8 -*-
# @Time : 2023/12/19 15:17
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : __init_.py
# @Project : copilot
from app.routers.basic_router import ReadyRouter, AliveRouter
from app.routers.chat_router import WebSocketRouter, WebSocketTestHtmlRouter, SSERouter, SSETestHtmlRouter
from app.routers.prompt_router import PromptRouter
from app.routers.text2sql_router import Text2SqlRouter
from app.routers.recommend_router import (RecommendTableRouter, RecommendFlowRouter, RecommendCodeRouter,
                                          CheckCodeRouter,
                                          RecommendViewRouter, RecommendLabelRouter, CheckIndicatorRouter,
                                          RecommendFieldSubjectRouter, RecommendFieldRuleRouter,
                                          RecommendExploreRuleRouter, RecommendSubjectModelRouter
                                          )
from app.routers.cognitive_search_router import (CatalogSearchRouter, AssetSearchRouter, ResourceSearchRouter,
                                                 ResourceAnalysisRouter, CatalogAnalysisRouter, FormviewAnalysisRouter,
                                                 FormviewSearchCatalogRouter, FormviewAnalysisCatalogRouter
                                                 )
                                                # , ResourceAnalysisKECCRouter)
from app.routers.data_understand_router import (TableCompletionRouter, TableCompletionOnlyRouter,
                                                TableCompletionTaskRouter
                                                )
from app.routers.categorize_router import DataCategorizeRouter
from app.routers.data_comprehension_router import ComprehensionRouter
from app.routers.retriever_router import DatacatalogConnectedSubgraphRetrieverRouter



API_V1_STR = "/api/af-sailor"
